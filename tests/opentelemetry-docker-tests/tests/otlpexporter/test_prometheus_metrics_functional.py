# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import math
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from prometheus_client import CollectorRegistry, start_http_server

from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.metrics import Meter
from opentelemetry.proto.metrics.v1.metrics_pb2 import AggregationTemporality
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.test._otlp_test_server import (
    OtlpProtoTestServer,
    RecordedMetric,
)

from . import _attrs_to_dict

if TYPE_CHECKING:
    from collections.abc import Sequence

    from opentelemetry.proto.metrics.v1.metrics_pb2 import (
        HistogramDataPoint,
        Metric,
        NumberDataPoint,
    )

_PROMETHEUS_PORT = 9464

_CUMULATIVE = AggregationTemporality.AGGREGATION_TEMPORALITY_CUMULATIVE

_DEFAULT_HISTOGRAM_BOUNDS = [
    0.0,
    5.0,
    10.0,
    25.0,
    50.0,
    75.0,
    100.0,
    250.0,
    500.0,
    750.0,
    1000.0,
    2500.0,
    5000.0,
    7500.0,
    10000.0,
]


@dataclass
class PrometheusExporterConfig:
    id: str
    prefix: str = ""
    disable_target_info: bool = False
    scope_info_enabled: bool = True

    def build(self, registry: CollectorRegistry) -> PrometheusMetricReader:
        return PrometheusMetricReader(
            prefix=self.prefix,
            disable_target_info=self.disable_target_info,
            scope_info_enabled=self.scope_info_enabled,
            registry=registry,
        )

    def expected_name(self, base: str, *, is_counter: bool = False) -> str:
        name = f"{self.prefix}_{base}" if self.prefix else base
        if is_counter:
            name = f"{name}_total"
        return name


PROMETHEUS_EXPORTER_CONFIGS: list[PrometheusExporterConfig] = [
    PrometheusExporterConfig(id="default"),
    PrometheusExporterConfig(id="prefix", prefix="e2e"),
    PrometheusExporterConfig(id="no-target-info", disable_target_info=True),
    PrometheusExporterConfig(id="no-scope-info", scope_info_enabled=False),
]


# DataPointFlags bit set by the prometheus receiver for staleness markers, i.e.
# a series that was present on a previous scrape but is now absent. Such points
# carry no value and must be skipped.
_NO_RECORDED_VALUE_FLAG = 1


def _number(data_point: NumberDataPoint) -> float:
    """Return whichever of the NumberDataPoint value oneof is set."""
    which = data_point.WhichOneof("value")
    return getattr(data_point, which)


def _data_points(
    metric: Metric,
) -> Sequence[NumberDataPoint | HistogramDataPoint]:
    for field in ("sum", "gauge", "histogram", "exponential_histogram"):
        if metric.HasField(field):
            return getattr(metric, field).data_points
    return []


def _has_recorded_value(recorded: RecordedMetric) -> bool:
    return any(
        not (dp.flags & _NO_RECORDED_VALUE_FLAG)
        for dp in _data_points(recorded.metric)
    )


def _wait_for_metric_matching(
    server: OtlpProtoTestServer,
    predicate: Callable[[RecordedMetric], bool],
    timeout: float = 20.0,
) -> RecordedMetric:
    """Drain the OTLP sink until a metric matches ``predicate``."""
    deadline = time.monotonic() + timeout
    seen: list[str] = []
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(
                f"No matching metric within {timeout}s, saw names={seen!r}"
            )
        try:
            recorded = server.get_metric(timeout=remaining)
        except TimeoutError:
            raise TimeoutError(
                f"No matching metric within {timeout}s, saw names={seen!r}"
            ) from None
        if predicate(recorded) and _has_recorded_value(recorded):
            return recorded
        seen.append(recorded.metric.name)


def _wait_for_named_metric(
    server: OtlpProtoTestServer, name: str
) -> RecordedMetric:
    recorded = _wait_for_metric_matching(
        server, lambda r: r.metric.name == name
    )
    assert recorded.metric.name == name
    return recorded


class TestPrometheusMetricsExporter:
    @pytest.fixture(
        scope="class",
        params=PROMETHEUS_EXPORTER_CONFIGS,
        ids=lambda c: c.id,
    )
    def config(self, request) -> PrometheusExporterConfig:
        return request.param

    @pytest.fixture(scope="class")
    def registry(self) -> CollectorRegistry:
        return CollectorRegistry()

    @pytest.fixture(scope="class")
    def reader(
        self,
        config: PrometheusExporterConfig,
        registry: CollectorRegistry,
    ) -> PrometheusMetricReader:
        return config.build(registry)

    @pytest.fixture(scope="class")
    def http_server(
        self,
        registry: CollectorRegistry,
        reader: PrometheusMetricReader,
    ) -> Iterator[None]:
        httpd, _thread = start_http_server(
            port=_PROMETHEUS_PORT, addr="0.0.0.0", registry=registry
        )
        try:
            yield
        finally:
            httpd.shutdown()
            httpd.server_close()

    @pytest.fixture(scope="class")
    def meter_provider(
        self,
        reader: PrometheusMetricReader,
    ) -> Iterator[MeterProvider]:
        provider = MeterProvider(
            metric_readers=[reader],
            resource=Resource.create({"service.name": "test-service"}),
        )
        try:
            yield provider
        finally:
            provider.shutdown()

    @pytest.fixture(scope="class")
    def meter(self, meter_provider: MeterProvider) -> Meter:
        return meter_provider.get_meter(__name__)

    @pytest.fixture(autouse=True)
    def clear_server(
        self,
        server: OtlpProtoTestServer,
        http_server: None,
    ) -> None:
        server.clear()

    def test_counter(
        self,
        config: PrometheusExporterConfig,
        meter: Meter,
        server: OtlpProtoTestServer,
    ):
        counter = meter.create_counter("prom_counter")
        counter.add(3, {"status": "ok"})
        counter.add(7, {"status": "ok"})

        recorded = _wait_for_named_metric(
            server, config.expected_name("prom_counter", is_counter=True)
        )
        assert recorded.metric.HasField("sum")
        sum_ = recorded.metric.sum
        assert sum_.is_monotonic
        assert sum_.aggregation_temporality == _CUMULATIVE
        assert len(sum_.data_points) == 1
        (data_point,) = sum_.data_points
        assert _number(data_point) == 10
        assert _attrs_to_dict(data_point.attributes) == {"status": "ok"}

    def test_up_down_counter(
        self,
        config: PrometheusExporterConfig,
        meter: Meter,
        server: OtlpProtoTestServer,
    ):
        counter = meter.create_up_down_counter("prom_updown")
        counter.add(10)
        counter.add(-3)

        recorded = _wait_for_named_metric(
            server, config.expected_name("prom_updown")
        )
        # A cumulative non-monotonic sum is exported as a Prometheus gauge.
        assert recorded.metric.HasField("gauge")
        assert len(recorded.metric.gauge.data_points) == 1
        (data_point,) = recorded.metric.gauge.data_points
        assert _number(data_point) == 7
        assert _attrs_to_dict(data_point.attributes) == {}

    def test_gauge(
        self,
        config: PrometheusExporterConfig,
        meter: Meter,
        server: OtlpProtoTestServer,
    ):
        gauge = meter.create_gauge("prom_gauge")
        gauge.set(42, {"status": "active"})

        recorded = _wait_for_named_metric(
            server, config.expected_name("prom_gauge")
        )
        assert recorded.metric.HasField("gauge")
        assert len(recorded.metric.gauge.data_points) == 1
        (data_point,) = recorded.metric.gauge.data_points
        assert _number(data_point) == 42
        assert _attrs_to_dict(data_point.attributes) == {"status": "active"}

    def test_histogram(
        self,
        config: PrometheusExporterConfig,
        meter: Meter,
        server: OtlpProtoTestServer,
    ):
        histogram = meter.create_histogram("prom_histogram")
        histogram.record(5)
        histogram.record(15)
        histogram.record(150)

        recorded = _wait_for_named_metric(
            server, config.expected_name("prom_histogram")
        )
        assert recorded.metric.HasField("histogram")
        assert recorded.metric.histogram.aggregation_temporality == _CUMULATIVE
        assert len(recorded.metric.histogram.data_points) == 1
        (data_point,) = recorded.metric.histogram.data_points
        assert data_point.count == 3
        assert math.isclose(data_point.sum, 170.0, abs_tol=1e-5)
        assert _attrs_to_dict(data_point.attributes) == {}
        assert list(data_point.explicit_bounds) == _DEFAULT_HISTOGRAM_BOUNDS
        # 5 -> (0, 5], 15 -> (10, 25], 150 -> (100, 250].
        assert list(data_point.bucket_counts) == [
            0,
            1,
            0,
            1,
            0,
            0,
            0,
            1,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
        ]

    def test_data_point_attributes(
        self,
        config: PrometheusExporterConfig,
        meter: Meter,
        server: OtlpProtoTestServer,
    ):
        counter = meter.create_counter("prom_attrs")
        counter.add(1, {"str_key": "hello", "int_key": 42})

        recorded = _wait_for_named_metric(
            server, config.expected_name("prom_attrs", is_counter=True)
        )
        (data_point,) = recorded.metric.sum.data_points
        # Prometheus labels are strings, so integer attributes roundtrip as text.
        assert _attrs_to_dict(data_point.attributes) == {
            "str_key": "hello",
            "int_key": "42",
        }

    def test_target_info_resource(
        self,
        config: PrometheusExporterConfig,
        meter: Meter,
        server: OtlpProtoTestServer,
    ):
        counter = meter.create_counter("prom_target")
        counter.add(1)

        recorded = _wait_for_named_metric(
            server, config.expected_name("prom_target", is_counter=True)
        )
        resource_attrs = _attrs_to_dict(recorded.resource.attributes)
        # The resource's SDK/service attributes reach the receiver only via the
        # target_info metric
        if config.disable_target_info:
            assert "service_name" not in resource_attrs
            assert "telemetry_sdk_language" not in resource_attrs
        else:
            assert resource_attrs["service_name"] == "test-service"
            assert resource_attrs["telemetry_sdk_language"] == "python"

    def test_scope_info(
        self,
        config: PrometheusExporterConfig,
        meter_provider: MeterProvider,
        server: OtlpProtoTestServer,
    ):
        scoped_meter = meter_provider.get_meter("test-scope", version="1.2.3")
        counter = scoped_meter.create_counter("prom_scope")
        counter.add(1)

        recorded = _wait_for_named_metric(
            server, config.expected_name("prom_scope", is_counter=True)
        )
        if config.scope_info_enabled:
            assert recorded.scope.name == "test-scope"
            assert recorded.scope.version == "1.2.3"
        else:
            assert recorded.scope.name != "test-scope"
            assert "prometheusreceiver" in recorded.scope.name

    def test_scope_attributes(
        self,
        config: PrometheusExporterConfig,
        meter_provider: MeterProvider,
        server: OtlpProtoTestServer,
    ):
        scoped_meter = meter_provider.get_meter(
            "attr-scope",
            version="2.0",
            attributes={"scope.key": "scope.val"},
        )
        counter = scoped_meter.create_counter("prom_scope_attrs")
        counter.add(1)

        recorded = _wait_for_named_metric(
            server, config.expected_name("prom_scope_attrs", is_counter=True)
        )
        scope_attrs = _attrs_to_dict(recorded.scope.attributes)
        if config.scope_info_enabled:
            assert recorded.scope.name == "attr-scope"
            assert scope_attrs == {"scope_key": "scope.val"}
        else:
            assert scope_attrs == {}
