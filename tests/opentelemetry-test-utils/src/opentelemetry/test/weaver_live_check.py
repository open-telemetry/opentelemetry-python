# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

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
    """
    raw: list[dict] = []

    def _collect(obj: Any) -> list[dict]:
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
    """Format violations list as human-readable text."""
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

    Captured process output is available as :attr:`stdout` and :attr:`stderr`,
    including after the live-check context has closed.

    The full :class:`LiveCheckReport` is attached as :attr:`report` for
    structured inspection beyond the human-readable message::

        with pytest.raises(LiveCheckError) as exc_info:
            weaver.end_and_check()

        err = exc_info.value
        assert any(
            v["id"] == "my_policy_check" and v["context"]["attribute_name"] == "my.attribute"
            for v in err.report.violations
        )
    """

    def __init__(self, message: str, report: "LiveCheckReport", stdout: str = "", stderr: str = "") -> None:
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
    """

    def __init__(self, report: dict[str, Any]) -> None:
        self._report = report

    def to_dict(self) -> dict[str, Any]:
        """Return a deep copy of the full report for inspection or JSON serialization."""
        return deepcopy(self._report)

    @property
    def samples(self) -> list[dict[str, Any]]:
        """Return a deep copy of the samples, or an empty list if absent."""
        return deepcopy(self._report.get("samples", []))

    @property
    def statistics(self) -> dict[str, Any]:
        """Return a deep copy of the statistics, or an empty dict if absent."""
        return deepcopy(self._report.get("statistics", {}))

    @functools.cached_property
    def violations(self) -> list[dict[str, Any]]:
        """Deduplicated list of semconv violations found in the report.

        Each item is a dict with keys: ``id``, ``message``, ``context``
        (the raw context dict from weaver, e.g. ``{"attribute_name": "foo"}``),
        ``signal_name``, ``signal_type``, ``count``.
        """
        return _extract_violations(self._report)

    def __getitem__(self, key: str) -> Any:
        return self._report[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._report.get(key, default)

    def __contains__(self, key: object) -> bool:
        return key in self._report

    def __repr__(self) -> str:
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

                # Signals weaver to stop, raises LiveCheckError listing violations
                # if any, or returns a LiveCheckReport on success.
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
        - :meth:`end` — signals weaver to stop and always returns a
          :class:`LiveCheckReport`.  Never raises for semconv violations; use
          this when you want to write your own assertions.
        - :meth:`end_and_check` — signals weaver to stop and raises
          :class:`LiveCheckError` with a human-readable violation list and the
          full report attached if weaver exits non-zero.  Returns a
          :class:`LiveCheckReport` on success.
        - :meth:`close` — stops weaver if not already stopped and terminates the
          process.  Never raises for semconv violations.  Idempotent; safe to
          call even if :meth:`end_and_check` or :meth:`end` was already called.
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

        ``extra_args`` is appended verbatim to the weaver command after the
        managed flags (``--registry``, ``--otlp-grpc-port``, etc.) and lets
        callers pass additional weaver options — for example ``["--quiet"]``
        or ``["--skip-policies"]`` — without subclassing.

        ``config`` selects a Weaver TOML configuration file. Managed command
        flags take precedence over values in that file.
        ``advice_data`` is passed to Weaver's ``--advice-data`` option to load
        JSON/YAML data for advice policies. Existing local paths are made
        absolute; other values (URLs, globs) are passed unchanged.
        ``startup_timeout`` controls how long to wait for the health endpoint,
        in seconds. It defaults to 30 seconds.
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
        return self.start()

    def __exit__(self, exc_type: Any, *_: object) -> None:
        if exc_type is not None:
            self._stopped = True
        self.close()

    def start(self) -> "WeaverLiveCheck":
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
        return f"http://localhost:{self._otlp_port}"

    def _do_stop(self, timeout: int) -> tuple["LiveCheckReport", int]:
        """Stop collection, read the report, shut down, and return (report, exit_code).

        Raises for infrastructure errors (HTTP failure, process communication).
        Never raises for semconv violations.
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
        response = post(f"http://localhost:{self._admin_port}/shutdown", timeout=timeout)
        response.raise_for_status()
        assert self._process is not None
        return self._process.wait(timeout=timeout)

    def _end(self, timeout: int) -> tuple[LiveCheckReport, int]:
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

        Raises :exc:`RuntimeError` for infrastructure problems (weaver failed
        to start, HTTP communication error, etc.).

        See https://github.com/open-telemetry/weaver/tree/main/crates/weaver_live_check#output
        for the report structure.
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
        attached as :attr:`LiveCheckError.report`.
        Use :meth:`end` if you need the report regardless of violations.

        Repeated calls check the cached result and raise again for violations.
        Raises :exc:`RuntimeError` if closed without requesting a report or if
        an earlier report request or shutdown failed.

        Raises :exc:`RuntimeError` for infrastructure problems (weaver failed
        to start, HTTP communication error, etc.).
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
        """Captured stdout so far, retained after close. Reading does not stop Weaver."""
        self._stdout = self._read_output(self._stdout_path, self._stdout)
        return self._stdout

    @property
    def stderr(self) -> str:
        """Captured stderr so far, retained after close. Reading does not stop Weaver."""
        self._stderr = self._read_output(self._stderr_path, self._stderr)
        return self._stderr

    def _read_weaver_logs(self) -> str | None:
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
