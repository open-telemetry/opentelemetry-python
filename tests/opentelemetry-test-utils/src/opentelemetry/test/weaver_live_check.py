# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import functools
import json
import logging
import os
import shutil
import socket
import subprocess
from collections import defaultdict
from itertools import chain
from typing import Any

from requests import Session, post
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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
        match obj:
            case {"live_check_result": {"all_advice": advices}, **_rest}:
                violations = [
                    a for a in advices if a.get("level") == "violation"
                ]
                return violations + list(
                    chain.from_iterable(_collect(v) for v in obj.values())
                )
            case dict():
                return list(
                    chain.from_iterable(_collect(v) for v in obj.values())
                )
            case list():
                return list(
                    chain.from_iterable(_collect(item) for item in obj)
                )
            case _:
                return []

    raw = _collect(report)

    groups: dict[tuple, list] = defaultdict(list)
    for violation in raw:
        ctx = violation.get("context")
        key = (
            violation.get("id"),
            violation.get("message"),
            json.dumps(ctx, sort_keys=True)
            if isinstance(ctx, (dict, list))
            else ctx,
            violation.get("signal_name"),
            violation.get("signal_type"),
        )
        groups[key].append(violation)

    violations = [
        {
            "id": k[0],
            "message": k[1],
            "context": vs[0].get(
                "context"
            ),  # preserve original dict, not JSON string
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

    The full :class:`LiveCheckReport` is attached as :attr:`report` for
    structured inspection beyond the human-readable message::

        with pytest.raises(LiveCheckError) as exc_info:
            weaver.end_and_check()

        err = exc_info.value
        assert any(
            v["id"] == "my_policy_check"
            and v["context"]["attribute_name"] == "my.attribute"
            for v in err.report.violations
        )
    """

    def __init__(self, message: str, report: "LiveCheckReport") -> None:
        super().__init__(message)
        self.report = report


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
            v["id"] == "my_policy_check"
            and v["context"]["attribute_name"] == "my.attribute"
            for v in report.violations
        )
    """

    def __init__(self, report: dict[str, Any]) -> None:
        self._report = report

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


    Requires the ``weaver`` binary on PATH:
    https://github.com/open-telemetry/weaver/releases

    Typical use as a context manager::

        def test_my_telemetry(self):
            with WeaverLiveCheck() as weaver:
                exporter = OTLPSpanExporter(
                    endpoint=weaver.otlp_endpoint, insecure=True
                )
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
        schema_version: str | None = None,
        policies_dir: str | None = None,
        inactivity_timeout: int = 30,
        otlp_port: int = 0,
        admin_port: int = 0,
    ):
        weaver_bin = shutil.which("weaver")
        if not weaver_bin:
            raise RuntimeError(
                "weaver binary not found on PATH. "
                "Install it from https://github.com/open-telemetry/weaver/releases"
            )

        self._otlp_port = otlp_port or _find_free_port()
        self._admin_port = admin_port or _find_free_port()
        self._ready = False
        self._stopped = False
        self._process: subprocess.Popen[bytes] | None = None

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

        if schema_version is None:
            schema_version = list(Schemas)[-1].value.rsplit("/", 1)[-1]

        command += [
            "--registry",
            f"https://github.com/open-telemetry/semantic-conventions/archive/refs/tags/v{schema_version}.tar.gz[model]",
        ]

        self._command = command
        logger.debug("Weaver command: %s", command)

    def __enter__(self) -> "WeaverLiveCheck":
        return self.start()

    def __exit__(self, exc_type: Any, *_: Any) -> None:
        if exc_type is not None:
            self._stopped = True
        self.close()

    def start(self, timeout: int = 60) -> "WeaverLiveCheck":
        logger.debug("Starting WeaverLiveCheck process...")
        self._process = subprocess.Popen(  # pylint: disable=consider-using-with
            self._command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            self._wait_for_ready(timeout=timeout)
            self._ready = True
        except Exception as exc:  # pylint: disable=broad-except
            logs = self._read_weaver_logs()
            logger.error(
                "WeaverLiveCheck did not start: %s, logs: %s", exc, logs
            )
            raise
        return self

    def _wait_for_ready(self, timeout: int = 60) -> None:
        retry = Retry(
            total=timeout,
            backoff_factor=1,
            backoff_max=1,
            # Any non-2xx response from /health means weaver isn't ready yet.
            status_forcelist=list(range(300, 600)),
            allowed_methods=["GET"],
        )
        session = Session()
        session.mount("http://", HTTPAdapter(max_retries=retry))
        try:
            response = session.get(
                f"http://localhost:{self._admin_port}/health", timeout=5
            )
            response.raise_for_status()
        except Exception as exc:  # pylint: disable=broad-except
            if self._process is not None and self._process.poll() is not None:
                raise RuntimeError(
                    f"WeaverLiveCheck process exited unexpectedly (code {self._process.returncode})"
                ) from exc
            raise TimeoutError(
                "WeaverLiveCheck did not become ready in time"
            ) from exc

    @property
    def otlp_endpoint(self) -> str:
        return f"http://localhost:{self._otlp_port}"

    def _do_stop(self, timeout: int) -> tuple["LiveCheckReport", int]:
        """POST /stop, wait for the process to exit, return (report, exit_code).

        Raises for infrastructure errors (HTTP failure, process communication).
        Never raises for semconv violations.
        """
        if not self._ready:
            raise RuntimeError(
                "WeaverLiveCheck process did not start successfully"
            )
        try:
            response = post(
                f"http://localhost:{self._admin_port}/stop", timeout=5
            )
            response.raise_for_status()
            report = LiveCheckReport(response.json())
            assert self._process is not None
            exit_code = self._process.wait(timeout=timeout)
        except Exception as exc:  # pylint: disable=broad-except
            logs = self._read_weaver_logs()
            logger.error(
                "Error communicating with weaver: %s, logs: %s", exc, logs
            )
            raise
        return report, exit_code

    def end(self, timeout: int = 30) -> "LiveCheckReport":
        """Signal weaver to stop and return the full :class:`LiveCheckReport`.

        Never raises for semconv violations — use this when you want to write
        your own assertions against :attr:`LiveCheckReport.violations` or the
        raw report data.

        Raises :exc:`RuntimeError` for infrastructure problems (weaver failed
        to start, HTTP communication error, etc.).

        See https://github.com/open-telemetry/weaver/tree/main/crates/weaver_live_check#output
        for the report structure.
        """
        if self._stopped:
            logger.warning(
                "end() called after weaver already stopped; returning empty report"
            )
            return LiveCheckReport({})
        self._stopped = True
        report, _ = self._do_stop(timeout)
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

        Raises :exc:`RuntimeError` for infrastructure problems (weaver failed
        to start, HTTP communication error, etc.).
        """
        if self._stopped:
            logger.warning(
                "end_and_check() called after weaver already stopped; returning empty report"
            )
            return LiveCheckReport({})
        self._stopped = True
        report, exit_code = self._do_stop(timeout)
        if exit_code == 0:
            # Success — no violations found, no errors communicating with weaver
            return report
        raise LiveCheckError(
            f"Semconv violations found:\n{_format_violations(report.violations)}",
            report,
        )

    def _read_weaver_logs(self) -> str | None:
        if self._process is None:
            return None
        try:
            if self._process.poll() is None:
                self._process.kill()
            out, err = self._process.communicate()
            return f"{out.decode()}\n{err.decode()}"
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Could not get weaver logs: %s", exc)
            return None

    def close(self) -> None:
        """Stop weaver and clean up the process.

        If weaver has not been stopped yet, sends the ``/stop`` signal and
        waits for the process to exit.  Never raises for semconv violations.
        Idempotent — safe to call multiple times or after :meth:`end` /
        :meth:`end_and_check` has already been called.
        """
        if not self._stopped:
            self._stopped = True
            if self._ready:
                try:
                    self._do_stop(timeout=30)
                    return  # process already exited cleanly
                except Exception as exc:  # pylint: disable=broad-except
                    logger.debug("Error stopping weaver during close: %s", exc)
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
