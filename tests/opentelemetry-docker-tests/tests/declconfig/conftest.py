# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from functools import cache
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

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
_ROUTING_PROBE_TIMEOUT = 2.0


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


def _make_collector(collector_config: Path, sink_endpoint: str) -> DockerContainer:
    return (
        DockerContainer(_get_collector_image())
        .with_volume_mapping(collector_config, _COLLECTOR_CONFIG_PATH)
        .with_command(f"--config={_COLLECTOR_CONFIG_PATH}")
        .with_env("OTLP_SINK_ENDPOINT", sink_endpoint)
        .with_kwargs(extra_hosts={"host.docker.internal": "host-gateway"})
        .with_exposed_ports(_HEALTH_CHECK_PORT)
        .waiting_for(HttpWaitStrategy(_HEALTH_CHECK_PORT).for_status_code(200))
    )


def _get_container_ip(container: DockerContainer) -> str:
    return container.get_docker_client().bridge_ip(container.get_wrapped_container().id)


@cache
def _container_ips_routable() -> bool:
    """Whether this host reaches containers at their bridge IP, without published ports.

    True on Linux and OrbStack, false on Docker Desktop for macOS and Windows,
    whose containers run in a VM the host has no route into.
    """
    # The sink is never contacted, the collector only has to start.
    with _make_collector(_DEFAULT_COLLECTOR_CONFIG, "http://127.0.0.1:1") as container:
        try:
            with urlopen(
                f"http://{_get_container_ip(container)}:{_HEALTH_CHECK_PORT}",
                timeout=_ROUTING_PROBE_TIMEOUT,
            ) as response:
                return response.status == 200
        except (URLError, OSError):
            return False


@pytest.hookimpl(optionalhook=True)
def pytest_xdist_auto_num_workers(config: pytest.Config) -> int | None:
    """Make ``-n auto`` run serially when collectors are only reachable through host ports."""
    return None if _container_ips_routable() else 1


@pytest.fixture(scope="session")
def collector_ips_routable() -> bool:
    routable = _container_ips_routable()
    if not routable and int(os.environ.get("PYTEST_XDIST_WORKER_COUNT", "1")) > 1:
        pytest.fail(
            "Collector containers aren't reachable at their IP from this host, so they bind"
            " their receiver ports on the host and scenarios can't run in parallel. Use -n 0."
        )
    return routable


@pytest.fixture
def otlp_sink() -> Iterator[OtlpProtoTestServer]:
    """Host side OTLP receiver the scenario's collector forwards to."""
    with OtlpProtoTestServer(host="0.0.0.0", port=0) as sink:
        yield sink


@pytest.fixture
def collector(scenario: Path, otlp_sink: OtlpProtoTestServer, collector_ips_routable: bool) -> Iterator[str]:
    """Start a collector with the scenario's config, or the default one, and yield its host.

    Scenario configs reach its receivers as
    ``<scheme>://${OTEL_COLLECTOR_ENDPOINT}:<port from collector-config.yaml>``.
    The host is the container's own IP where the host can route to it, so
    collectors don't share ports and scenarios can run in parallel. Otherwise
    the receiver ports are bound 1:1 on the host.
    """
    collector_config = scenario / "collector-config.yaml"
    if not collector_config.exists():
        collector_config = _DEFAULT_COLLECTOR_CONFIG
    container = _make_collector(collector_config, f"http://host.docker.internal:{otlp_sink.port}")
    if not collector_ips_routable:
        for port in _get_receiver_ports(collector_config):
            container.with_bind_ports(port, port)
    with container:
        yield _get_container_ip(container) if collector_ips_routable else container.get_container_host_ip()
