# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Iterator

import pytest
from prometheus_client import CollectorRegistry, start_http_server

_PROMETHEUS_PORT = 9464


@pytest.fixture(scope="session")
def prometheus_registry() -> CollectorRegistry:
    return CollectorRegistry()


@pytest.fixture(scope="session", autouse=True)
def _prometheus_scrape_target(prometheus_registry: CollectorRegistry) -> Iterator[None]:
    """Keep a Prometheus HTTP endpoint up on :9464 for the whole docker-test session."""
    httpd, _thread = start_http_server(port=_PROMETHEUS_PORT, addr="0.0.0.0", registry=prometheus_registry)
    try:
        yield
    finally:
        httpd.shutdown()
        httpd.server_close()
