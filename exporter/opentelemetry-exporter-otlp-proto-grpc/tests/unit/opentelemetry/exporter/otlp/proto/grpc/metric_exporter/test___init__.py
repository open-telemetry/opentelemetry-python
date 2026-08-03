# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=protected-access

import unittest
from unittest.mock import Mock, patch

from opentelemetry.exporter.otlp._proto.grpc._pygrpc import api as grpc
from opentelemetry.exporter.otlp._proto.grpc._pygrpc.api import Compression, StatusCode

from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    MetricExportResult,
    MetricsData,
    NumberDataPoint,
    ResourceMetrics,
    ScopeMetrics,
)
from opentelemetry.sdk.metrics.export import Gauge as SDKGauge
from opentelemetry.sdk.metrics.export import Metric
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope

_INSECURE_CH = "opentelemetry.exporter.otlp.proto.grpc.exporter.insecure_channel"


class _FakeRpcError(grpc.RpcError):
    def __init__(self, code, details=""):
        self._code = code
        self._details = details

    def code(self):
        return self._code

    def details(self):
        return self._details


def _make_exporter(**kwargs):
    with patch(_INSECURE_CH):
        exporter = OTLPMetricExporter(insecure=True, **kwargs)
    return exporter


def _make_metrics_data(n_data_points: int = 1) -> MetricsData:
    data_points = [
        NumberDataPoint(
            attributes={"i": i},
            start_time_unix_nano=0,
            time_unix_nano=1641946016139533244,
            value=float(i),
            exemplars=[],
        )
        for i in range(n_data_points)
    ]
    return MetricsData(
        resource_metrics=[
            ResourceMetrics(
                resource=Resource({"service.name": "test"}),
                scope_metrics=[
                    ScopeMetrics(
                        scope=InstrumentationScope("test", "1.0"),
                        metrics=[
                            Metric(
                                name="my.gauge",
                                description="",
                                unit="1",
                                data=SDKGauge(data_points=data_points),
                            )
                        ],
                        schema_url="",
                    )
                ],
                schema_url="",
            )
        ]
    )


class TestOTLPMetricExporterConstructor(unittest.TestCase):

    def test_defaults(self):
        with patch(_INSECURE_CH) as mock_ch:
            exporter = OTLPMetricExporter(insecure=True)
        args, _ = mock_ch.call_args
        self.assertEqual(args[0], "localhost:4317")
        self.assertEqual(exporter._timeout, 10.0)
        self.assertIsNone(exporter._max_export_batch_size)
        exporter.shutdown()

    def test_metrics_endpoint_env_var(self):
        with patch.dict("os.environ", {
            "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT": "http://metrics-host:4317",
        }):
            with patch(_INSECURE_CH) as mock_ch:
                OTLPMetricExporter(insecure=True)
        args, _ = mock_ch.call_args
        self.assertEqual(args[0], "metrics-host:4317")

    def test_metrics_endpoint_overrides_generic(self):
        with patch.dict("os.environ", {
            "OTEL_EXPORTER_OTLP_ENDPOINT": "http://generic:4317",
            "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT": "http://metrics:4317",
        }):
            with patch(_INSECURE_CH) as mock_ch:
                OTLPMetricExporter(insecure=True)
        args, _ = mock_ch.call_args
        self.assertEqual(args[0], "metrics:4317")

    def test_metrics_timeout_env_var(self):
        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_METRICS_TIMEOUT": "15"}):
            exporter = _make_exporter()
        self.assertEqual(exporter._timeout, 15.0)
        exporter.shutdown()

    def test_metrics_insecure_env_var_true(self):
        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_METRICS_INSECURE": "true"}):
            with patch(_INSECURE_CH) as mock_insecure:
                OTLPMetricExporter()
        mock_insecure.assert_called_once()

    def test_metrics_headers_env_var(self):
        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_METRICS_HEADERS": "x-metric=1"}):
            exporter = _make_exporter()
        self.assertIn(("x-metric", "1"), exporter._headers)
        exporter.shutdown()

    def test_max_export_batch_size_stored(self):
        exporter = _make_exporter(max_export_batch_size=100)
        self.assertEqual(exporter._max_export_batch_size, 100)
        exporter.shutdown()

    def test_exporting_property(self):
        exporter = _make_exporter()
        self.assertEqual(exporter._exporting, "metrics")
        exporter.shutdown()


class TestOTLPMetricExporterExport(unittest.TestCase):

    def test_export_success(self):
        exporter = _make_exporter()
        result = exporter.export(_make_metrics_data())
        self.assertEqual(result, MetricExportResult.SUCCESS)
        exporter.shutdown()

    def test_export_empty_metrics(self):
        exporter = _make_exporter()
        result = exporter.export(MetricsData(resource_metrics=[]))
        self.assertEqual(result, MetricExportResult.SUCCESS)
        exporter.shutdown()

    def test_export_failure_non_retryable(self):
        exporter = _make_exporter()
        exporter._client.Export.side_effect = _FakeRpcError(StatusCode.PERMISSION_DENIED)
        result = exporter.export(_make_metrics_data())
        self.assertEqual(result, MetricExportResult.FAILURE)
        exporter.shutdown()

    def test_export_after_shutdown(self):
        exporter = _make_exporter()
        exporter.shutdown()
        result = exporter.export(_make_metrics_data())
        self.assertEqual(result, MetricExportResult.FAILURE)

    def test_force_flush_returns_true(self):
        exporter = _make_exporter()
        self.assertTrue(exporter.force_flush())
        exporter.shutdown()

    def test_set_meter_provider(self):
        from opentelemetry.sdk.metrics import MeterProvider
        exporter = _make_exporter()
        mp = MeterProvider()
        exporter.set_meter_provider(mp)  # should not raise
        exporter.shutdown()


class TestOTLPMetricExporterSplitBatch(unittest.TestCase):
    """Tests for batch splitting via max_export_batch_size."""

    def test_no_split_when_no_max_batch_size(self):
        exporter = _make_exporter()
        metrics_data = _make_metrics_data(n_data_points=5)
        result = exporter.export(metrics_data)
        self.assertEqual(result, MetricExportResult.SUCCESS)
        # Single Export call (no splitting)
        self.assertEqual(exporter._client.Export.call_count, 1)
        exporter.shutdown()

    def test_split_into_multiple_batches(self):
        # 5 data points, batch size 2 → 3 Export calls
        exporter = _make_exporter(max_export_batch_size=2)
        metrics_data = _make_metrics_data(n_data_points=5)
        result = exporter.export(metrics_data)
        self.assertEqual(result, MetricExportResult.SUCCESS)
        self.assertEqual(exporter._client.Export.call_count, 3)
        exporter.shutdown()

    def test_split_exact_batch_size(self):
        # 4 data points, batch size 4 → 1 Export call
        exporter = _make_exporter(max_export_batch_size=4)
        metrics_data = _make_metrics_data(n_data_points=4)
        result = exporter.export(metrics_data)
        self.assertEqual(result, MetricExportResult.SUCCESS)
        self.assertEqual(exporter._client.Export.call_count, 1)
        exporter.shutdown()

    def test_split_partial_failure_returns_failure(self):
        exporter = _make_exporter(max_export_batch_size=2)
        metrics_data = _make_metrics_data(n_data_points=4)
        call_count = [0]

        def fail_on_second(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise _FakeRpcError(StatusCode.PERMISSION_DENIED)

        exporter._client.Export.side_effect = fail_on_second
        result = exporter.export(metrics_data)
        self.assertEqual(result, MetricExportResult.FAILURE)
        exporter.shutdown()
