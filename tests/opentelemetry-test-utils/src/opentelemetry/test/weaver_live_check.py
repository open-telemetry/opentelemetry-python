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

import json
import logging
import os
import shutil
import socket
import subprocess
import time
from collections import defaultdict
from typing import Any

from requests import get, post
from requests.exceptions import ConnectionError as ReqConnectionError

from opentelemetry.semconv.schemas import Schemas

logger = logging.getLogger(__name__)


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


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

    def collect(obj: Any) -> None:
        if isinstance(obj, dict):
            if "live_check_result" in obj:
                for advice in obj["live_check_result"].get("all_advice", []):
                    if advice.get("level") == "violation":
                        raw.append(advice)
            for v in obj.values():
                collect(v)
        elif isinstance(obj, list):
            for item in obj:
                collect(item)

    collect(report)

    groups: dict[tuple, list] = defaultdict(list)
    for v in raw:
        ctx = v.get("context")
        key = (
            v.get("id"),
            v.get("message"),
            json.dumps(ctx, sort_keys=True)
            if isinstance(ctx, (dict, list))
            else ctx,
            v.get("signal_name"),
            v.get("signal_type"),
        )
        groups[key].append(v)

    violations = [
        {
            "id": k[0],
            "message": k[1],
            "context": k[2],
            "signal_name": k[3],
            "signal_type": k[4],
            "count": len(vs),
        }
        for k, vs in groups.items()
    ]
    violations.sort(key=lambda v: (-v["count"], v.get("message") or ""))
    return violations


def _format_violations(violations: list) -> str:
    """Format violations list as human-readable text (mirrors violations.j2 output)."""
    lines = []
    for v in violations:
        signal = ""
        signal_type = v.get("signal_type")
        signal_name = v.get("signal_name")
        if signal_type and signal_name:
            signal = f" on {signal_type} '{signal_name}'"
        elif signal_type:
            signal = f" on {signal_type}"
        elif signal_name:
            signal = f" on '{signal_name}'"
        lines.append(
            f"- [{v.get('id')}] {v.get('message')} ({v['count']} occurrence(s){signal})"
        )
    return "\n".join(lines)


class WeaverLiveCheck:
    """Runs ``weaver registry live-check`` as a subprocess and validates
    OTLP telemetry against OpenTelemetry semantic conventions.

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

                # Signals weaver to stop, raises AssertionError listing violations
                # if any, or returns the raw JSON report on success.
                report = weaver.end_and_check()
            # __exit__ calls close(), which is idempotent if end_and_check() was already called

    :meth:`end_and_check` returns the raw weaver JSON report when weaver exits
    successfully (exit code 0).  Use it for custom assertions on the report
    content beyond the built-in violation check::

        report = weaver.end_and_check()
        # report is the raw JSON dict from weaver; inspect it as needed, e.g.:
        self.assertIn("some_signal", str(report))

    Lifecycle:
        - :meth:`start` — launches weaver and waits for it to become ready.
        - :attr:`otlp_endpoint` — gRPC OTLP endpoint to point exporters at.
        - :meth:`end_and_check` — signals weaver to stop, collects the report, and
          raises :class:`AssertionError` with a human-readable violation list if weaver
          exits non-zero.  Returns the raw report dict on success.
        - :meth:`close` — calls :meth:`end_and_check` then terminates the process.
          Idempotent; safe to call even if :meth:`end_and_check` was already called.
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
        self._process = subprocess.Popen(
            self._command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            self._wait_for_ready(timeout=timeout)
            self._ready = True
        except Exception as e:
            logs = self._read_weaver_logs()
            logger.error(
                "WeaverLiveCheck did not start: %s, logs: %s", e, logs
            )
            raise
        return self

    def _wait_for_ready(self, timeout: int = 60) -> None:
        for i in range(timeout):
            if self._process is not None and self._process.poll() is not None:
                raise RuntimeError(
                    f"WeaverLiveCheck process exited unexpectedly (code {self._process.returncode})"
                )
            try:
                response = get(
                    f"http://localhost:{self._admin_port}/health", timeout=5
                )
                if response.status_code == 200:
                    return
                logger.debug(
                    "Health check returned %s, try %s", response.status_code, i
                )
            except ReqConnectionError as e:
                logger.debug("Health check connection error: %s", e)
            time.sleep(1)
        raise TimeoutError("WeaverLiveCheck did not become ready in time")

    @property
    def otlp_endpoint(self) -> str:
        return f"http://localhost:{self._otlp_port}"

    def end_and_check(self, timeout: int = 30) -> dict[str, Any]:
        if self._stopped:
            logger.warning(
                "end_and_check() called after weaver already stopped; returning empty report"
            )
            return {}
        self._stopped = True

        if not self._ready:
            raise RuntimeError(
                "WeaverLiveCheck process did not start successfully"
            )

        try:
            response = post(
                f"http://localhost:{self._admin_port}/stop", timeout=5
            )
            response.raise_for_status()
            report = response.json()
            assert self._process is not None
            exit_code = self._process.wait(timeout=timeout)
        except Exception as e:
            logs = self._read_weaver_logs()
            logger.error(
                "Error communicating with weaver: %s, logs: %s", e, logs
            )
            raise

        if exit_code == 0:
            return report

        violations = _extract_violations(report)
        raise AssertionError(
            f"Semconv violations found:\n{_format_violations(violations)}"
        )

    def _read_weaver_logs(self) -> str | None:
        if self._process is None:
            return None
        try:
            if self._process.poll() is None:
                self._process.kill()
            out, err = self._process.communicate()
            return f"{out.decode()}\n{err.decode()}"
        except Exception as e:
            logger.error("Could not get weaver logs: %s", e)
            return None

    def close(self) -> None:
        try:
            self.end_and_check()
        finally:
            if self._process and self._process.poll() is None:
                self._process.terminate()
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._process.kill()
