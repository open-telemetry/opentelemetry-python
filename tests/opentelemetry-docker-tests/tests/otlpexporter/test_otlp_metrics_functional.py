# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import math
from collections.abc import Iterator

import pytest
from grpc import Compression as GRPCCompression
from inline_snapshot import snapshot

from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
    OTLPMetricExporter as GRPCMetricExporter,
)
from opentelemetry.exporter.otlp.proto.http import (
    Compression as HTTPCompression,
)
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    OTLPMetricExporter as HTTPMetricExporter,
)
from opentelemetry.metrics import Meter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics._internal.export import (
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.metrics.export import MetricExporter
from opentelemetry.sdk.metrics.view import (
    ExponentialBucketHistogramAggregation,
    View,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.test._otlp_test_server import OtlpProtoTestServer

from . import CUSTOM_HEADERS, ExporterConfig, _attrs_to_dict

METRIC_EXPORTER_CONFIGS: list[ExporterConfig[MetricExporter]] = [
    ExporterConfig(
        id="http",
        exporter_class=HTTPMetricExporter,
        kwargs={"endpoint": "http://localhost:4318/v1/metrics"},
    ),
    ExporterConfig(
        id="http-deflate",
        exporter_class=HTTPMetricExporter,
        kwargs={
            "endpoint": "http://localhost:4318/v1/metrics",
            "compression": HTTPCompression.Deflate,
        },
    ),
    ExporterConfig(
        id="http-gzip",
        exporter_class=HTTPMetricExporter,
        kwargs={
            "endpoint": "http://localhost:4318/v1/metrics",
            "compression": HTTPCompression.Gzip,
        },
    ),
    ExporterConfig(
        id="http-headers",
        exporter_class=HTTPMetricExporter,
        kwargs={
            "endpoint": "http://localhost:4318/v1/metrics",
            "headers": CUSTOM_HEADERS,
        },
    ),
    ExporterConfig(
        id="grpc",
        exporter_class=GRPCMetricExporter,
        kwargs={"insecure": True},
    ),
    ExporterConfig(
        id="grpc-gzip",
        exporter_class=GRPCMetricExporter,
        kwargs={"insecure": True, "compression": GRPCCompression.Gzip},
    ),
    ExporterConfig(
        id="grpc-headers",
        exporter_class=GRPCMetricExporter,
        kwargs={"insecure": True, "headers": CUSTOM_HEADERS},
    ),
]


class TestMetricsExporter:
    @pytest.fixture(
        scope="class", params=METRIC_EXPORTER_CONFIGS, ids=lambda c: c.id
    )
    def config(self, request) -> ExporterConfig[MetricExporter]:
        return request.param

    @pytest.fixture(scope="class")
    def reader(
        self,
        config: ExporterConfig[MetricExporter],
        server: OtlpProtoTestServer,
    ) -> PeriodicExportingMetricReader:
        return PeriodicExportingMetricReader(
            config.build(), export_interval_millis=math.inf
        )

    @pytest.fixture(scope="class")
    def meter_provider(
        self, reader: PeriodicExportingMetricReader
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
    def clear_server(self, server: OtlpProtoTestServer) -> None:
        server.clear()

    def test_sum_counter(
        self,
        meter: Meter,
        reader: PeriodicExportingMetricReader,
        server: OtlpProtoTestServer,
    ):
        counter = meter.create_counter("test.counter", unit="requests")
        counter.add(3, {"status": "ok"})
        counter.add(7, {"status": "ok"})
        counter.add(5, {"status": "error"})
        reader.force_flush(timeout_millis=5000)

        recorded = server.wait_for_metric(name="test.counter", timeout=5.0)
        assert recorded.metric.name == snapshot("test.counter")
        assert recorded.metric.unit == snapshot("requests")
        assert recorded.metric.HasField("sum")
        assert recorded.metric.sum.is_monotonic
        dps = {
            _attrs_to_dict(dp.attributes)["status"]: dp.as_int
            for dp in recorded.metric.sum.data_points
        }
        assert dps == snapshot({"ok": 10, "error": 5})

    def test_sum_up_down_counter(
        self,
        meter: Meter,
        reader: PeriodicExportingMetricReader,
        server: OtlpProtoTestServer,
    ):
        counter = meter.create_up_down_counter("test.up_down_counter")
        counter.add(10)
        counter.add(-3)
        reader.force_flush(timeout_millis=5000)

        recorded = server.wait_for_metric(
            name="test.up_down_counter", timeout=5.0
        )
        assert recorded.metric.HasField("sum")
        assert not recorded.metric.sum.is_monotonic
        assert recorded.metric.sum.data_points[0].as_int == 7

    def test_gauge(
        self,
        meter: Meter,
        reader: PeriodicExportingMetricReader,
        server: OtlpProtoTestServer,
    ):
        gauge = meter.create_gauge("test.gauge")
        gauge.set(42, {"status": "active"})
        reader.force_flush(timeout_millis=5000)

        recorded = server.wait_for_metric(name="test.gauge", timeout=5.0)
        assert recorded.metric.HasField("gauge")
        assert recorded.metric.gauge.data_points[0].as_int == snapshot(42)

    def test_explicit_bucket_histogram(
        self,
        meter: Meter,
        reader: PeriodicExportingMetricReader,
        server: OtlpProtoTestServer,
    ):
        histogram = meter.create_histogram("test.histogram")
        histogram.record(5)
        histogram.record(15)
        histogram.record(150)
        reader.force_flush(timeout_millis=5000)

        recorded = server.wait_for_metric(name="test.histogram", timeout=5.0)
        assert recorded.metric.HasField("histogram")
        dp = recorded.metric.histogram.data_points[0]
        assert dp.count == 3
        assert math.isclose(dp.sum, 170.0, abs_tol=1e-5)
        assert len(dp.bucket_counts) > 0
        assert len(dp.explicit_bounds) > 0

    def test_exponential_histogram(
        self,
        config: ExporterConfig[MetricExporter],
        server: OtlpProtoTestServer,
    ):
        reader = PeriodicExportingMetricReader(
            config.build(), export_interval_millis=math.inf
        )
        meter_provider = MeterProvider(
            metric_readers=[reader],
            resource=Resource.create({"service.name": "test-service"}),
            views=[
                View(
                    instrument_name="test.exp.histogram",
                    aggregation=ExponentialBucketHistogramAggregation(),
                )
            ],
        )
        meter = meter_provider.get_meter(__name__)
        histogram = meter.create_histogram("test.exp.histogram")
        for v in [1.0, 2.0, 4.0]:
            histogram.record(v)
        reader.force_flush(timeout_millis=5000)

        recorded = server.wait_for_metric(
            name="test.exp.histogram", timeout=5.0
        )
        assert recorded.metric.HasField("exponential_histogram")
        dp = recorded.metric.exponential_histogram.data_points[0]
        assert dp.count == 3
        assert math.isclose(dp.sum, 7.0, abs_tol=1e-5)
        assert len(dp.positive.bucket_counts) > 0

        meter_provider.shutdown()

    def test_metric_data_point_attributes(
        self,
        meter: Meter,
        reader: PeriodicExportingMetricReader,
        server: OtlpProtoTestServer,
    ):
        counter = meter.create_counter("test.attrs.counter")
        counter.add(1, {"str_key": "hello", "int_key": 42})
        reader.force_flush(timeout_millis=5000)

        recorded = server.wait_for_metric(
            name="test.attrs.counter", timeout=5.0
        )
        attrs = _attrs_to_dict(recorded.metric.sum.data_points[0].attributes)
        assert attrs == snapshot({"str_key": "hello", "int_key": 42})

    def test_scope_attributes(
        self,
        meter_provider: MeterProvider,
        reader: PeriodicExportingMetricReader,
        server: OtlpProtoTestServer,
    ):
        meter = meter_provider.get_meter(
            "test.scope",
            version="1.0.0",
            attributes={"scope.key": "scope.val"},
        )
        counter = meter.create_counter("scope.counter")
        counter.add(1)
        reader.force_flush(timeout_millis=5000)

        recorded = server.wait_for_metric(name="scope.counter", timeout=5.0)
        assert recorded.scope.name == snapshot("test.scope")
        assert recorded.scope.version == snapshot("1.0.0")
        assert _attrs_to_dict(recorded.scope.attributes)[
            "scope.key"
        ] == snapshot("scope.val")

    def test_resource_attributes(
        self,
        meter: Meter,
        reader: PeriodicExportingMetricReader,
        server: OtlpProtoTestServer,
    ):
        counter = meter.create_counter("resource.counter")
        counter.add(1)
        reader.force_flush(timeout_millis=5000)

        recorded = server.wait_for_metric(name="resource.counter", timeout=5.0)
        resource_attrs = _attrs_to_dict(recorded.resource.attributes)
        assert resource_attrs["service.name"] == snapshot("test-service")
