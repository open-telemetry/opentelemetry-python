# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import HttpWaitStrategy

from opentelemetry.test._otlp_test_server import OtlpProtoTestServer

collect_ignore_glob = ["scenarios/*"]

_DOCKER_COMPOSE_FILE = Path(__file__).parent.parent / "docker-compose.yml"
_DEFAULT_COLLECTOR_CONFIG = Path(__file__).parent / "collector-config.yaml"
_COLLECTOR_CONFIG_PATH = "/etc/otelcol/collector-config.yaml"
_HEALTH_CHECK_PORT = 13133
_ENDPOINT_PORT_RE = re.compile(r":(\d+)$")


def _get_collector_image() -> str:
    """Reuse the collector image pinned in docker-compose.yml."""
    with open(_DOCKER_COMPOSE_FILE, encoding="utf-8") as compose_file:
        return yaml.safe_load(compose_file)["services"]["otcollector"]["image"]


def _get_receiver_ports(collector_config: Path) -> list[int]:
    """Collect the ``host:port`` receiver endpoints declared in a collector config."""
    with open(collector_config, encoding="utf-8") as config_file:
        receivers = yaml.safe_load(config_file).get("receivers") or {}

    ports: set[int] = set()

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "endpoint" and isinstance(value, str) and (match := _ENDPOINT_PORT_RE.search(value)):
                    ports.add(int(match.group(1)))
                else:
                    _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(receivers)
    return sorted(ports)


@pytest.fixture
def otlp_sink() -> Iterator[OtlpProtoTestServer]:
    """Host side OTLP receiver the scenario's collector forwards to."""
    with OtlpProtoTestServer(host="0.0.0.0", port=0) as sink:
        yield sink


@pytest.fixture
def collector(scenario: Path, otlp_sink: OtlpProtoTestServer) -> Iterator[str]:
    """Start a collector with the scenario's config, or the default one, and yield its host.

    Receiver ports are bound 1:1 on the host, so scenario configs reach them
    as ``<scheme>://${OTEL_COLLECTOR_ENDPOINT}:<port from collector-config.yaml>``.
    """
    collector_config = scenario / "collector-config.yaml"
    if not collector_config.exists():
        collector_config = _DEFAULT_COLLECTOR_CONFIG
    container = (
        DockerContainer(_get_collector_image())
        .with_volume_mapping(collector_config, _COLLECTOR_CONFIG_PATH)
        .with_command(f"--config={_COLLECTOR_CONFIG_PATH}")
        .with_env("OTLP_SINK_ENDPOINT", f"http://host.docker.internal:{otlp_sink.port}")
        .with_kwargs(extra_hosts={"host.docker.internal": "host-gateway"})
        .with_exposed_ports(_HEALTH_CHECK_PORT)
        .waiting_for(HttpWaitStrategy(_HEALTH_CHECK_PORT).for_status_code(200))
    )
    for port in _get_receiver_ports(collector_config):
        container.with_bind_ports(port, port)
    with container:
        yield container.get_container_host_ip()
