# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Iterator

import pytest

from opentelemetry.test._otlp_test_server import OtlpProtoTestServer


@pytest.fixture(scope="class")
def server() -> Iterator[OtlpProtoTestServer]:
    test_server = OtlpProtoTestServer(host="0.0.0.0", port=4319).start()
    try:
        yield test_server
    finally:
        test_server.stop()
