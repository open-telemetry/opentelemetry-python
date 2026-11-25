# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Checking emitted telemetry against the OpenTelemetry semantic conventions.

Weaver is the OpenTelemetry tool that reads the semantic convention registry and
checks telemetry against it. Its ``registry live-check`` subcommand runs as a
server: it accepts OTLP over gRPC, accumulates what it is sent, and reports on
request which attributes and signals departed from the registry.

:class:`WeaverLiveCheck` runs that subcommand as a subprocess and exposes it to
a test. A test points an OTLP exporter at ``otlp_endpoint``, emits telemetry,
then calls :meth:`WeaverLiveCheck.end_and_check` to assert that weaver found
nothing, or :meth:`WeaverLiveCheck.end` to get the report and assert on it
directly. :class:`LiveCheckReport` wraps the JSON report and
:class:`LiveCheckError` is what a failed check raises.

The ``weaver`` binary has to be on ``PATH``, and constructing
:class:`WeaverLiveCheck` raises ``RuntimeError`` when no binary of that name is
found. Version 0.27 or later is required, and nothing checks the version: an
older weaver is accepted by the constructor and rejects one of the managed flags
later, which surfaces as a ``RuntimeError`` out of
:meth:`WeaverLiveCheck.start` naming only the exit status.
Downloads are at https://github.com/open-telemetry/weaver/releases

This module is experimental and its API may change without notice.
"""

import functools
import json
import logging
import os
import shutil
import socket
import subprocess
import tempfile
import time
from collections import defaultdict
from collections.abc import Sequence
from copy import deepcopy
from itertools import chain
from math import isfinite
from typing import Any

from requests import RequestException, get, post

from opentelemetry.semconv.schemas import Schemas

logger = logging.getLogger(__name__)


def _find_free_port() -> int:
    """Ask the operating system for a port that is free right now.

    Returns:
        A TCP port number. Binding to port ``0`` and reading back the assigned
        port is the only portable way to get one, and the socket is closed
        before the number is handed over, so another process can take the port
        between this call and weaver binding to it.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("", 0))
        return sock.getsockname()[1]


def _extract_violations(report: dict) -> list:
    """Extract and deduplicate violations from the full report.

    Get all violations using python version of this jq filter:
      [ .. | objects | select(has("live_check_result"))
        | .live_check_result.all_advice[]?
        | select(.level == "violation") ]
      | group_by(.id, .message, .context, .signal_name, .signal_type)
      | map({ ..., count: length })
      | sort_by(-.count, .message)

    The same violation is reported by weaver once per sample that triggered it,
    so a single wrong attribute on a thousand spans produces a thousand
    entries. Grouping them turns that into one entry with a count.

    Args:
        report: The full report as weaver returned it, already parsed from
            JSON. It is searched recursively, so the shape below the top level
            does not have to be known.

    Returns:
        One dict per distinct violation, with the keys ``id``, ``message``,
        ``context``, ``signal_name``, ``signal_type`` and ``count``, sorted by
        descending count and then by message. ``context`` is the original dict
        from weaver, not the JSON string used to group by it. A report with no
        violation gives an empty list.
    """
    raw: list[dict] = []

    def _collect(obj: Any) -> list[dict]:
        """Walk a parsed JSON value and gather every violation under it.

        Args:
            obj: Any value from the parsed report: a dict, a list, or a scalar.

        Returns:
            Every advice entry at level ``violation`` found anywhere below
            ``obj``, in traversal order and with duplicates kept. A scalar
            gives an empty list, which is what ends the recursion.
        """
        if isinstance(obj, dict):
            result: list[dict] = []
            lcr = obj.get("live_check_result")
            if isinstance(lcr, dict):
                advice_list = lcr.get("all_advice")
                if isinstance(advice_list, list):
                    result.extend(a for a in advice_list if a.get("level") == "violation")
            for value in obj.values():
                result.extend(_collect(value))
            return result
        if isinstance(obj, list):
            return list(chain.from_iterable(_collect(item) for item in obj))
        return []

    raw = _collect(report)

    groups: dict[tuple, list] = defaultdict(list)
    for violation in raw:
        ctx = violation.get("context")
        key = (
            violation.get("id"),
            violation.get("message"),
            json.dumps(ctx, sort_keys=True) if isinstance(ctx, (dict, list)) else ctx,
            violation.get("signal_name"),
            violation.get("signal_type"),
        )
        groups[key].append(violation)

    violations = [
        {
            "id": k[0],
            "message": k[1],
            "context": vs[0].get("context"),  # preserve original dict, not JSON string
            "signal_name": k[3],
            "signal_type": k[4],
            "count": len(vs),
        }
        for k, vs in groups.items()
    ]
    violations.sort(key=lambda v: (-v["count"], v.get("message") or ""))
    return violations


def _format_violations(violations: list) -> str:
    """Format violations list as human-readable text.

    Args:
        violations: The grouped violations produced by ``_extract_violations``.

    Returns:
        One line per violation, newline separated, each naming the violation
        id, the message, the occurrence count and the signal it was seen on.
        The signal part is omitted when weaver reported neither a signal type
        nor a signal name. An empty list gives an empty string.
    """
    lines = []
    for violation in violations:
        signal = ""
        signal_type = violation.get("signal_type")
        signal_name = violation.get("signal_name")
        if signal_type and signal_name:
            signal = f" on {signal_type} '{signal_name}'"
        elif signal_type:
            signal = f" on {signal_type}"
        elif signal_name:
            signal = f" on '{signal_name}'"
        lines.append(
            f"- [{violation.get('id')}] {violation.get('message')} ({violation['count']} occurrence(s){signal})"
        )
    return "\n".join(lines)


class LiveCheckError(AssertionError):
    """Raised by :meth:`WeaverLiveCheck.end_and_check` when semconv violations are found.

    Captured process output is available as ``stdout`` and ``stderr``,
    including after the live-check context has closed.

    The full :class:`LiveCheckReport` is attached as ``report`` for
    structured inspection beyond the human-readable message::

        with pytest.raises(LiveCheckError) as exc_info:
            weaver.end_and_check()

        err = exc_info.value
        assert any(
            v["id"] == "my_policy_check" and v["context"]["attribute_name"] == "my.attribute"
            for v in err.report.violations
        )

    Args:
        message: The failure message, which :meth:`WeaverLiveCheck.end_and_check`
            builds from the formatted violation list.
        report: The full report the violations came from, kept as ``report``.
        stdout: Everything weaver wrote to stdout up to the failure, kept as
            ``stdout``.
        stderr: Everything weaver wrote to stderr up to the failure, kept as
            ``stderr``.
    """

    def __init__(self, message: str, report: "LiveCheckReport", stdout: str = "", stderr: str = "") -> None:
        """Parameters are documented on the class docstring."""
        super().__init__(message)
        self.report = report
        self.stdout = stdout
        self.stderr = stderr


class LiveCheckReport:
    """The result of a weaver live-check run.

    Provides structured access to violations and the full raw JSON report.

    See https://github.com/open-telemetry/weaver/tree/main/crates/weaver_live_check#output
    for the full report structure.

    Example — asserting on metrics statistics::

        report = weaver.end()
        seen = report["statistics"]["seen_registry_metrics"]
        assert seen.get("http.server.request.duration") == 1

    Example — asserting on violations::

        report = weaver.end()
        assert any(
            v["id"] == "my_policy_check" and v["context"]["attribute_name"] == "my.attribute" for v in report.violations
        )

    Args:
        report: The report as weaver returned it, already parsed from JSON. It
            is stored, not copied, so the caller should not keep editing it.
    """

    def __init__(self, report: dict[str, Any]) -> None:
        """Parameters are documented on the class docstring."""
        self._report = report

    def to_dict(self) -> dict[str, Any]:
        """Return a deep copy of the full report for inspection or JSON serialization.

        Returns:
            A deep copy, so editing it does not affect this report or any later
            call. Use ``__getitem__`` or ``get`` to read one key without
            copying the whole report.
        """
        return deepcopy(self._report)

    @property
    def samples(self) -> list[dict[str, Any]]:
        """Return a deep copy of the samples, or an empty list if absent.

        A sample is one span, metric or log record as weaver received it,
        annotated with the advice weaver attached to it.

        Returns:
            A deep copy of the ``samples`` entry of the report, or an empty
            list when weaver recorded none. A fresh copy is built on every
            access, so bind it to a name rather than indexing the property
            repeatedly.
        """
        return deepcopy(self._report.get("samples", []))

    @property
    def statistics(self) -> dict[str, Any]:
        """Return a deep copy of the statistics, or an empty dict if absent.

        The statistics count what weaver saw, for example which registry
        metrics appeared and how often, which is how a test asserts that an
        instrument fired without inspecting individual samples.

        Returns:
            A deep copy of the ``statistics`` entry of the report, or an empty
            dict when weaver recorded none. A fresh copy is built on every
            access.
        """
        return deepcopy(self._report.get("statistics", {}))

    @functools.cached_property
    def violations(self) -> list[dict[str, Any]]:
        """Deduplicated list of semconv violations found in the report.

        Each item is a dict with keys: ``id``, ``message``, ``context``
        (the raw context dict from weaver, e.g. ``{"attribute_name": "foo"}``),
        ``signal_name``, ``signal_type``, ``count``.

        Returns:
            The violations, most frequent first and then by message. The list
            is computed once and cached on the instance, and it is the cached
            list itself rather than a copy, so editing it changes what later
            reads return. A report with no violation gives an empty list, which
            is not the same as :meth:`WeaverLiveCheck.end_and_check` passing:
            that method
            decides on weaver's exit status, so weaver can exit non-zero for a
            reason that produces no violation entry and raise
            :class:`LiveCheckError` with an empty list in the message.
        """
        return _extract_violations(self._report)

    def __getitem__(self, key: str) -> Any:
        """Read a top-level key of the raw report.

        Args:
            key: Top-level key of the weaver report, for example
                ``"statistics"``.

        Returns:
            The value as weaver returned it, not copied, so editing a dict or
            list obtained this way changes the report this object holds.

        Raises:
            KeyError: When the report has no such key, which is what happens
                for a section weaver omits when it is empty.
        """
        return self._report[key]

    def get(self, key: str, default: Any = None) -> Any:
        """Read a top-level key of the raw report, with a fallback.

        Args:
            key: Top-level key of the weaver report.
            default: Returned when the key is absent.

        Returns:
            The value as weaver returned it, not copied, or ``default`` when
            the key is absent.
        """
        return self._report.get(key, default)

    def __contains__(self, key: object) -> bool:
        """Report whether the raw report has a given top-level key.

        Args:
            key: Key to look for. Only top-level keys are considered.

        Returns:
            ``True`` when the report has that key.
        """
        return key in self._report

    def __repr__(self) -> str:
        """Return a short description naming the number of violations.

        Returns:
            A string such as ``LiveCheckReport(3 violations)``. Computing it
            extracts the violations, so the first ``repr`` of a report does the
            grouping work that :attr:`violations` caches.
        """
        num_violations = len(self.violations)
        return f"LiveCheckReport({num_violations} violation{'s' if num_violations != 1 else ''})"


# NOTE: WeaverLiveCheck is experimental and its API is subject to change.
class WeaverLiveCheck:
    """Runs ``weaver registry live-check`` as a subprocess and validates
    OTLP telemetry against OpenTelemetry semantic conventions.

    .. note::
        This class is experimental and its API is subject to change without notice.


    Requires Weaver 0.27 or later on PATH:
    https://github.com/open-telemetry/weaver/releases

    Typical use as a context manager::

        def test_my_telemetry(self):
            with WeaverLiveCheck() as weaver:
                exporter = OTLPSpanExporter(endpoint=weaver.otlp_endpoint, insecure=True)
                # ... configure provider, emit telemetry ...
                provider.force_flush()

                # Signals weaver to stop, returns a LiveCheckReport when weaver
                # exits zero, and raises LiveCheckError with the violations
                # listed in the message when it does not.
                report = weaver.end_and_check()
            # __exit__ calls close(), which is idempotent if end_and_check() was already called

    Use :meth:`end` when you need the full :class:`LiveCheckReport`
    regardless of whether violations were found — for example, to assert that
    specific metrics were observed or to inspect violation fields directly::

        with WeaverLiveCheck() as weaver:
            # ... configure provider, emit telemetry ...
            provider.force_flush()
            report = weaver.end()

        seen_metrics = report["statistics"]["seen_registry_metrics"]
        assert seen_metrics.get("http.server.request.duration") == 1

    Lifecycle:
        - :meth:`start` — launches weaver and waits for it to become ready.
        - :attr:`otlp_endpoint` — gRPC OTLP endpoint to point exporters at.
        - :meth:`end` — signals weaver to stop and returns the
          :class:`LiveCheckReport` whether or not it holds violations.  Never
          raises for semconv violations, which is why you write your own
          assertions against it; see the method itself for the three ways it
          raises instead of returning.
        - :meth:`end_and_check` — signals weaver to stop and raises
          :class:`LiveCheckError` with a human-readable violation list and the
          full report attached if weaver exits non-zero.  Returns a
          :class:`LiveCheckReport` on success.
        - :meth:`close` — stops weaver if not already stopped and terminates the
          process.  Never raises for semconv violations.  Idempotent; safe to
          call even if :meth:`end_and_check` or :meth:`end` was already called.

    Args:
        registry: Semantic convention registry to check against, as a
            directory, an archive URL or any other value weaver's
            ``--registry`` accepts. An existing local directory is made
            absolute. ``None`` downloads the published registry archive for
            ``schema_version`` from GitHub, which means the constructor
            configures a network download that ``start`` then performs.
        schema_version: Version of the published registry to download, for
            example ``"1.37.0"``. ``None`` takes the newest version known to
            ``opentelemetry.semconv.schemas.Schemas``, so the check follows the
            semantic conventions the installed SDK was built against. Ignored
            when ``registry`` is given.
        policies_dir: Directory of extra advice policies, passed to weaver's
            ``--advice-policies`` and made absolute. ``None`` runs only the
            policies built into weaver.
        inactivity_timeout: Seconds weaver waits without receiving telemetry
            before stopping on its own. A test slower than this between
            ``start`` and the first export finds weaver already gone.
        otlp_port: Port for weaver's OTLP gRPC listener. ``0`` picks a free one,
            which is what lets several of these run at once.
        admin_port: Port for weaver's admin HTTP listener, which serves the
            health, stop, report and shutdown endpoints this class calls.
            ``0`` picks a free one.
        extra_args: Further weaver arguments, appended verbatim after the
            managed flags, for example ``["--quiet"]``. ``None`` adds none.
        startup_timeout: Seconds to wait for weaver's health endpoint to answer
            before giving up.
        config: Weaver TOML configuration file, made absolute and passed to
            ``--config``. The managed flags above take precedence over values
            in it.
        advice_data: Value for weaver's ``--advice-data``, which loads JSON or
            YAML data for advice policies. An existing local path is made
            absolute; a URL or a glob is passed unchanged.

    Raises:
        ValueError: When ``startup_timeout`` is not positive and finite.
        RuntimeError: When no ``weaver`` binary is on ``PATH``. Nothing is
            started by the constructor, so this is raised before any
            subprocess exists.
    """

    def __init__(
        self,
        registry: str | None = None,
        schema_version: str | None = None,
        policies_dir: str | None = None,
        inactivity_timeout: int = 30,
        otlp_port: int = 0,
        admin_port: int = 0,
        extra_args: Sequence[str] | None = None,
        startup_timeout: float = 30,
        config: str | None = None,
        advice_data: str | None = None,
    ):
        """Build the ``weaver registry live-check`` command.

        Parameters are documented on the class docstring. No subprocess is
        started here: the command is assembled and the port numbers are chosen,
        and :meth:`start` runs it. Choosing a port does not hold it, as
        ``_find_free_port`` explains, so another process can take it before
        weaver binds.
        """
        if not isfinite(startup_timeout) or startup_timeout <= 0:
            raise ValueError("startup_timeout must be positive and finite")
        self._startup_timeout = startup_timeout
        weaver_bin = shutil.which("weaver")
        if not weaver_bin:
            raise RuntimeError(
                "weaver binary not found on PATH. Install it from https://github.com/open-telemetry/weaver/releases"
            )

        self._otlp_port = otlp_port or _find_free_port()
        self._admin_port = admin_port or _find_free_port()
        self._ready = False
        self._stopped = False
        self._result: tuple[LiveCheckReport, int] | None = None
        self._process: subprocess.Popen[bytes] | None = None
        self._stdout_path: str | None = None
        self._stderr_path: str | None = None
        self._stdout = ""
        self._stderr = ""

        command = [
            weaver_bin,
            "registry",
            "live-check",
            f"--inactivity-timeout={inactivity_timeout}",
            f"--otlp-grpc-port={self._otlp_port}",
            f"--admin-port={self._admin_port}",
            "--output=http",
            "--format=json",
        ]

        if policies_dir:
            command += ["--advice-policies", os.path.abspath(policies_dir)]

        if config is not None:
            command += ["--config", os.path.abspath(config)]
        if advice_data is not None:
            if os.path.exists(advice_data):
                advice_data = os.path.abspath(advice_data)
            command += ["--advice-data", advice_data]

        if registry is None:
            if schema_version is None:
                schema_version = list(Schemas)[-1].value.rsplit("/", 1)[-1]
            registry = f"https://github.com/open-telemetry/semantic-conventions/archive/refs/tags/v{schema_version}.tar.gz[model]"
        elif os.path.isdir(registry):
            registry = os.path.abspath(registry)

        command += ["--registry", registry]

        if extra_args:
            command.extend(extra_args)

        self._command = command
        logger.debug("Weaver command: %s", command)

    def __enter__(self) -> "WeaverLiveCheck":
        """Start weaver for the duration of the block.

        Returns:
            This instance, with weaver running and ready to receive telemetry.
        """
        return self.start()

    def __exit__(self, exc_type: Any, *_: object) -> None:
        """Close weaver, whether the block completed or raised.

        When the block raised, the instance is marked stopped before closing,
        so no report is requested. That keeps the original exception visible
        instead of replacing it with whatever the report request would fail
        with.

        Args:
            exc_type: Class of the exception raised in the block, or ``None``.
            *_: The exception value and traceback, which are not needed.
        """
        if exc_type is not None:
            self._stopped = True
        self.close()

    def start(self) -> "WeaverLiveCheck":
        """Launch weaver and wait for its health endpoint to answer.

        Weaver's stdout and stderr are redirected to temporary files, which
        :attr:`stdout` and :attr:`stderr` read and :meth:`close` deletes.

        Returns:
            This instance, so the call can be chained, as ``__enter__`` does.

        Raises:
            RuntimeError: When weaver exits before becoming ready. The
                collected output is logged at error level first, and the
                process is killed while collecting it.
            TimeoutError: When weaver is still running but has not answered the
                health endpoint within ``startup_timeout``.
        """
        logger.debug("Starting WeaverLiveCheck process...")
        # Redirect weaver's stdout/stderr to tempfiles
        stdout_fd, self._stdout_path = tempfile.mkstemp(prefix="weaver-stdout-", suffix=".log")
        stderr_fd, self._stderr_path = tempfile.mkstemp(prefix="weaver-stderr-", suffix=".log")
        try:
            self._process = subprocess.Popen(  # pylint: disable=consider-using-with
                self._command,
                stdout=stdout_fd,
                stderr=stderr_fd,
            )
        finally:
            os.close(stdout_fd)
            os.close(stderr_fd)
        try:
            self._wait_for_ready()
            self._ready = True
        except Exception as exc:  # pylint: disable=broad-except
            logs = self._read_weaver_logs()
            logger.error("WeaverLiveCheck did not start: %s, logs: %s", exc, logs)
            raise
        return self

    def _wait_for_ready(self) -> None:
        """Poll weaver's health endpoint until it answers or the deadline passes.

        Polls roughly four times a second. A connection error is expected while
        weaver is still binding its listener, so it is kept as the cause of
        whichever exception is eventually raised rather than reported at once.

        Raises:
            RuntimeError: When the weaver process exited, which is checked
                before each poll so a crash is reported straight away instead
                of after the full timeout.
            TimeoutError: When the deadline passes with weaver still running
                and still not answering.
        """
        deadline = time.monotonic() + self._startup_timeout
        last_error: RequestException | None = None
        while True:
            if self._process is not None and self._process.poll() is not None:
                raise RuntimeError(
                    f"WeaverLiveCheck process exited unexpectedly (code {self._process.returncode})"
                ) from last_error
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    f"WeaverLiveCheck did not become ready within {self._startup_timeout} seconds"
                ) from last_error
            try:
                response = get(
                    f"http://localhost:{self._admin_port}/health",
                    timeout=min(5, remaining),
                    allow_redirects=False,
                )
                if 200 <= response.status_code < 300:
                    return
            except RequestException as exc:
                last_error = exc
            time.sleep(min(0.25, max(0, deadline - time.monotonic())))

    @property
    def otlp_endpoint(self) -> str:
        """Return the endpoint to configure an OTLP exporter with.

        Returns:
            The endpoint of weaver's OTLP gRPC listener. The port is fixed at
            construction, so this is readable before :meth:`start`, but nothing
            listens there until weaver is running. It is plain gRPC with no
            TLS, so an exporter pointed at it has to be configured insecure.
        """
        return f"http://localhost:{self._otlp_port}"

    def _do_stop(self, timeout: int) -> tuple["LiveCheckReport", int]:
        """Stop collection, read the report, shut down, and return (report, exit_code).

        Raises for infrastructure errors (HTTP failure, process communication).
        Never raises for semconv violations.

        Args:
            timeout: Seconds allowed for each admin HTTP request and for the
                process to exit, not for the sequence as a whole.

        Returns:
            A tuple of the parsed report and the exit status of the weaver
            process. The status is the one ``_shutdown`` returns and means what
            that method documents: non-zero is any failure weaver reports,
            usually violations. It is returned rather than raised on.

        Raises:
            RuntimeError: When weaver never became ready, so there is nothing
                to stop.
            requests.RequestException: When an admin request fails or answers
                with an error status. Shutdown is still attempted in that case,
                and the collected weaver output is logged at error level.
        """
        if not self._ready:
            raise RuntimeError("WeaverLiveCheck process did not start successfully")
        try:
            try:
                response = post(f"http://localhost:{self._admin_port}/stop", timeout=timeout)
                response.raise_for_status()
                response = get(f"http://localhost:{self._admin_port}/report", timeout=timeout)
                response.raise_for_status()
                report = LiveCheckReport(response.json())
            except Exception:  # pylint: disable=broad-except
                try:
                    self._shutdown(timeout)
                except Exception as exc:  # pylint: disable=broad-except
                    logger.debug("Error shutting down weaver after report failure: %s", exc)
                raise
            exit_code = self._shutdown(timeout)
        except Exception as exc:  # pylint: disable=broad-except
            logs = self._read_weaver_logs()
            logger.error("Error communicating with weaver: %s, logs: %s", exc, logs)
            raise
        return report, exit_code

    def _shutdown(self, timeout: int) -> int:
        """Ask weaver to exit and wait for the process to do so.

        Args:
            timeout: Seconds allowed for the shutdown request and, separately,
                for the process to exit.

        Returns:
            The exit status of the weaver process. Non-zero is how weaver
            reports a failed check, which is usually violations but covers any
            failure it reports, and is negative when a signal killed it.

        Raises:
            requests.RequestException: When the shutdown request fails or
                answers with an error status.
            subprocess.TimeoutExpired: When the process has not exited within
                ``timeout`` after being asked to.
        """
        response = post(f"http://localhost:{self._admin_port}/shutdown", timeout=timeout)
        response.raise_for_status()
        assert self._process is not None
        return self._process.wait(timeout=timeout)

    def _end(self, timeout: int) -> tuple[LiveCheckReport, int]:
        """Stop weaver once and return the cached outcome on every later call.

        Args:
            timeout: Seconds passed on to ``_do_stop``, used only on the call
                that actually stops weaver.

        Returns:
            The tuple of report and exit status produced by the first call.

        Raises:
            RuntimeError: When weaver was already stopped without a report
                having been collected, which is the state :meth:`close` leaves
                behind and the state ``__exit__`` forces after the block
                raised.
        """
        if not self._stopped:
            self._stopped = True
            self._result = self._do_stop(timeout)
        if self._result is None:
            raise RuntimeError("WeaverLiveCheck stopped without a completed report request")
        return self._result

    def end(self, timeout: int = 30) -> "LiveCheckReport":
        """Signal weaver to stop and return the full :class:`LiveCheckReport`.

        Never raises for semconv violations — use this when you want to write
        your own assertions against :attr:`LiveCheckReport.violations` or the
        raw report data.

        Repeated calls return the cached report, including after :meth:`close`.
        Raises :exc:`RuntimeError` if closed without requesting a report or if
        an earlier report request or shutdown failed.

        Raises :exc:`RuntimeError` when weaver never became ready, so there is
        nothing to stop. An admin request that fails or answers with an error
        status is not turned into a :exc:`RuntimeError`: the
        ``requests.RequestException`` raised by ``_do_stop`` propagates.

        See https://github.com/open-telemetry/weaver/tree/main/crates/weaver_live_check#output
        for the report structure.

        Args:
            timeout: Seconds allowed for each step of stopping weaver: the stop
                request, the report request, the shutdown request and the
                process exit.

        Returns:
            The report, whether or not it holds violations.
        """
        report, _ = self._end(timeout)
        return report

    def end_and_check(self, timeout: int = 30) -> "LiveCheckReport":
        """Signal weaver to stop and assert no semconv violations were found.

        Returns the :class:`LiveCheckReport` when weaver exits successfully
        (exit code 0).

        Does **not** return if weaver exits with a non-zero status — raises
        :exc:`LiveCheckError` (a subclass of :exc:`AssertionError`) with a
        human-readable list of violations and the full :class:`LiveCheckReport`
        attached as ``LiveCheckError.report``.
        Use :meth:`end` if you need the report regardless of violations.

        Repeated calls check the cached result and raise again for violations.
        Raises :exc:`RuntimeError` if closed without requesting a report or if
        an earlier report request or shutdown failed.

        Raises :exc:`RuntimeError` when weaver never became ready, so there is
        nothing to stop. An admin request that fails or answers with an error
        status is not turned into a :exc:`RuntimeError`: the
        ``requests.RequestException`` raised by ``_do_stop`` propagates.

        Args:
            timeout: Seconds allowed for each step of stopping weaver.

        Returns:
            The report, when weaver exited with status zero.
        """
        report, exit_code = self._end(timeout)
        if exit_code == 0:
            # Success — no violations found, no errors communicating with weaver
            return report
        raise LiveCheckError(
            f"Semconv violations found:\n{_format_violations(report.violations)}",
            report,
            stdout=self.stdout,
            stderr=self.stderr,
        )

    @staticmethod
    def _read_output(path: str | None, cached: str) -> str:
        """Read one of weaver's output files, falling back to what was cached.

        Args:
            path: The temporary file to read, or ``None`` once :meth:`close`
                has deleted it.
            cached: The text captured before the file was deleted, returned
                when the file cannot be read.

        Returns:
            The file contents decoded as UTF-8, with undecodable bytes replaced
            rather than raising, since weaver output is read for a human. When
            ``path`` is ``None`` or the file cannot be opened, ``cached`` is
            returned and the failure is logged at debug level.
        """
        if path is None:
            return cached
        try:
            with open(path, "rb") as fp:
                return fp.read().decode(errors="replace")
        except OSError as exc:
            logger.debug("Could not read weaver output from %s: %s", path, exc)
            return cached

    @property
    def stdout(self) -> str:
        """Captured stdout so far, retained after close. Reading does not stop Weaver.

        Returns:
            Everything weaver has written to stdout. Reading re-reads the
            temporary file while weaver is running, so the value grows between
            calls, and returns the text captured at close afterwards.
        """
        self._stdout = self._read_output(self._stdout_path, self._stdout)
        return self._stdout

    @property
    def stderr(self) -> str:
        """Captured stderr so far, retained after close. Reading does not stop Weaver.

        Returns:
            Everything weaver has written to stderr, under the same rules as
            :attr:`stdout`.
        """
        self._stderr = self._read_output(self._stderr_path, self._stderr)
        return self._stderr

    def _read_weaver_logs(self) -> str | None:
        """Kill weaver and return everything it wrote, for a failure message.

        This is called on the error paths of :meth:`start` and ``_do_stop``,
        where weaver is not going to be asked politely again. It kills the
        process first so that the output files are complete.

        Returns:
            The stdout and stderr captured so far, joined by a newline.
            ``None`` when weaver was never started, and also ``None`` when
            reading failed, in which case the failure is logged at error level.
        """
        if self._process is None:
            return None
        try:
            if self._process.poll() is None:
                self._process.kill()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass

            return f"{self.stdout}\n{self.stderr}"
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Could not get weaver logs: %s", exc)
            return None

    def close(self) -> None:
        """Stop weaver and clean up the process.

        If weaver has not been stopped yet, collects the report and requests
        shutdown before waiting for exit. Never raises for semconv violations.
        Idempotent — safe to call multiple times or after :meth:`end` /
        :meth:`end_and_check` has already been called.
        """
        if not self._stopped:
            self._stopped = True
            if self._ready:
                try:
                    self._do_stop(timeout=30)
                except Exception as exc:  # pylint: disable=broad-except
                    logger.debug("Error stopping weaver during close: %s", exc)
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.debug("Weaver did not exit after kill; continuing output cleanup")
        self._stdout = self.stdout
        self._stderr = self.stderr
        for path in (self._stdout_path, self._stderr_path):
            if path is not None:
                try:
                    os.unlink(path)
                except OSError:
                    pass
        self._stdout_path = None
        self._stderr_path = None
