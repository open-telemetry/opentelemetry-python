# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Iterator

import pytest

from opentelemetry.test._otlp_test_server import OtlpProtoTestServer

from . import OTLP_FILE_DATA_DIR


@pytest.fixture(scope="session", autouse=True)
def clean_otlp_file_data() -> None:
    """Remove stale .jsonl files so the collector doesn't replay old runs."""
    for signal in ("traces", "metrics", "logs"):
        directory = OTLP_FILE_DATA_DIR / signal
        directory.mkdir(parents=True, exist_ok=True)
        for stale in directory.glob("*.jsonl"):
            stale.unlink()


@pytest.fixture(scope="class")
def server() -> Iterator[OtlpProtoTestServer]:
    test_server = OtlpProtoTestServer(host="0.0.0.0", port=4319).start()
    try:
        yield test_server
    finally:
        test_server.stop()
