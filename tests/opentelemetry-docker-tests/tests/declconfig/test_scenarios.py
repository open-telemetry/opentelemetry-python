# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from opentelemetry.test._otlp_test_server import OtlpProtoTestServer

from ._scenario import Received, load_scenario

_SCENARIOS_DIR = Path(__file__).parent / "scenarios"
_SCENARIOS = sorted(path for path in _SCENARIOS_DIR.iterdir() if path.is_dir())
_POLL_INTERVAL = 0.1
_STOP_GRACE_PERIOD = 5.0
# How long the sink must receive nothing after the app stops before `expect` is checked.
_SETTLE_PERIOD = 1.0
# Upper bound on settling, for sources that never go quiet.
_MAX_SETTLE_DURATION = 10.0


def _stop(process: subprocess.Popen[bytes]) -> None:
    """Interrupt the app so atexit (and SDK shutdown) runs, then kill it if it lingers."""
    if process.poll() is not None:
        return
    process.send_signal(signal.SIGINT)
    try:
        process.wait(timeout=_STOP_GRACE_PERIOD)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def _get_otel_config(scenario: Path) -> Path:
    yaml_config = scenario / "otel-config.yaml"
    return yaml_config if yaml_config.exists() else scenario / "otel-config.json"


def _drain_until_quiet(received: Received, sink: OtlpProtoTestServer) -> None:
    """Collect telemetry still in flight, such as what the SDK flushed on shutdown."""
    deadline = time.monotonic() + _MAX_SETTLE_DURATION
    quiet_until = time.monotonic() + _SETTLE_PERIOD
    while time.monotonic() < min(quiet_until, deadline):
        time.sleep(_POLL_INTERVAL)
        if received.drain(sink):
            quiet_until = time.monotonic() + _SETTLE_PERIOD


@pytest.mark.parametrize("scenario", _SCENARIOS, ids=[path.name for path in _SCENARIOS])
def test_scenario(scenario: Path, collector: str, otlp_sink: OtlpProtoTestServer, tmp_path: Path) -> None:
    spec = load_scenario(scenario / "scenario.yaml")
    instrument = shutil.which("opentelemetry-instrument")
    assert instrument is not None, "opentelemetry-instrument is not installed"

    stdout_path = tmp_path / "stdout.txt"
    stderr_path = tmp_path / "stderr.txt"

    def app_output() -> str:
        return f"stdout:\n{stdout_path.read_text()}\nstderr:\n{stderr_path.read_text()}"

    received = Received()
    with open(stdout_path, "wb") as stdout, open(stderr_path, "wb") as stderr:
        process = subprocess.Popen(
            [instrument, sys.executable, "run.py"],
            cwd=scenario,
            env={
                # Inherited OTEL_* variables would leak into the SDK.
                **{key: value for key, value in os.environ.items() if not key.startswith("OTEL_")},
                **spec.env,
                "OTEL_CONFIG_FILE": str(_get_otel_config(scenario)),
                "OTEL_COLLECTOR_ENDPOINT": collector,
            },
            stdout=stdout,
            stderr=stderr,
        )
        try:
            deadline = time.monotonic() + spec.timeout
            while time.monotonic() < deadline:
                received.drain(otlp_sink)
                returncode = process.poll()
                assert returncode in (None, 0), f"run.py exited with {returncode}:\n{app_output()}"
                received.exited = returncode == 0
                if not spec.unmet(received):
                    break
                time.sleep(_POLL_INTERVAL)
        finally:
            _stop(process)

    received.stdout = stdout_path.read_text()
    received.stderr = stderr_path.read_text()

    _drain_until_quiet(received, otlp_sink)
    unmet = spec.unmet(received)
    assert not unmet, (
        f"Timed out after {spec.timeout}s waiting for:\n"
        + "\n".join(f"  {condition.progress(received)}" for condition in unmet)
        + f"\n{app_output()}"
    )
    failures = spec.failed_expectations(received)
    assert not failures, "Unmet expectations:\n" + "\n".join(map(str, failures)) + f"\n{app_output()}"
