# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=protected-access

import unittest
from unittest.mock import patch

from opentelemetry.exporter.otlp.proto.common._internal.metrics_encoder import (
    encode_metrics,
)
from opentelemetry.exporter.otlp.proto.http import Compression
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    DEFAULT_ENDPOINT,
    DEFAULT_METRICS_EXPORT_PATH,
    DEFAULT_TIMEOUT,
    OTLPMetricExporter,
    _append_metrics_path,
    _split_metrics_data,
)
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    MetricExportResult,
    MetricsData,
    NumberDataPoint,
    ResourceMetrics,
    ScopeMetrics,
)
from opentelemetry.sdk.metrics.export import Gauge as SDKGauge
from opentelemetry.sdk.metrics.export import Metric, Sum as SDKSum
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope

_UNIFORM = "opentelemetry.exporter.otlp.proto.http.metric_exporter.uniform"


def _ok():
    return (200, "OK")


def _503():
    return (503, "Service Unavailable")


def _404():
    return (404, "Not Found")


def _make_metrics_data(n_gauge_points: int = 1) -> MetricsData:
    data_points = [
        NumberDataPoint(
            attributes={"i": i},
            start_time_unix_nano=0,
            time_unix_nano=1641946016139533244,
            value=float(i),
            exemplars=[],
        )
        for i in range(n_gauge_points)
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


def _empty_metrics_data() -> MetricsData:
    return MetricsData(resource_metrics=[])


class TestOTLPMetricExporter(unittest.TestCase):

    # ── constructor ───────────────────────────────────────────────────────────

    def test_constructor_defaults(self):
        exporter = OTLPMetricExporter()
        self.assertEqual(
            exporter._endpoint,
            DEFAULT_ENDPOINT + DEFAULT_METRICS_EXPORT_PATH,
        )
        self.assertEqual(exporter._timeout, DEFAULT_TIMEOUT)
        self.assertEqual(exporter._compression, Compression.NoCompression)
        self.assertEqual(
            exporter._request_headers["Content-Type"], "application/x-protobuf"
        )
        self.assertIsNone(exporter._max_export_batch_size)
        self.assertFalse(exporter._shutdown)
        exporter.shutdown()

    def test_generic_endpoint_env_var(self):
        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://collector:4318"}):
            exporter = OTLPMetricExporter()
        self.assertEqual(exporter._endpoint, "http://collector:4318/v1/metrics")
        exporter.shutdown()

    def test_metrics_endpoint_overrides_generic(self):
        with patch.dict("os.environ", {
            "OTEL_EXPORTER_OTLP_ENDPOINT": "http://generic:4318",
            "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT": "http://metrics:4318/v1/metrics",
        }):
            exporter = OTLPMetricExporter()
        self.assertEqual(exporter._endpoint, "http://metrics:4318/v1/metrics")
        exporter.shutdown()

    def test_constructor_arg_overrides_env(self):
        with patch.dict("os.environ", {
            "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT": "http://env:4318/v1/metrics",
        }):
            exporter = OTLPMetricExporter(endpoint="http://arg:4318/v1/metrics")
        self.assertEqual(exporter._endpoint, "http://arg:4318/v1/metrics")
        exporter.shutdown()

    def test_timeout_generic_env_var(self):
        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_TIMEOUT": "20"}):
            exporter = OTLPMetricExporter()
        self.assertEqual(exporter._timeout, 20.0)
        exporter.shutdown()

    def test_timeout_metrics_env_var_overrides_generic(self):
        with patch.dict("os.environ", {
            "OTEL_EXPORTER_OTLP_TIMEOUT": "20",
            "OTEL_EXPORTER_OTLP_METRICS_TIMEOUT": "5",
        }):
            exporter = OTLPMetricExporter()
        self.assertEqual(exporter._timeout, 5.0)
        exporter.shutdown()

    def test_compression_env_var_gzip(self):
        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_COMPRESSION": "gzip"}):
            exporter = OTLPMetricExporter()
        self.assertEqual(exporter._compression, Compression.Gzip)
        self.assertEqual(exporter._request_headers.get("Content-Encoding"), "gzip")
        exporter.shutdown()

    def test_compression_metrics_env_overrides_generic(self):
        with patch.dict("os.environ", {
            "OTEL_EXPORTER_OTLP_COMPRESSION": "gzip",
            "OTEL_EXPORTER_OTLP_METRICS_COMPRESSION": "deflate",
        }):
            exporter = OTLPMetricExporter()
        self.assertEqual(exporter._compression, Compression.Deflate)
        exporter.shutdown()

    def test_max_export_batch_size_arg(self):
        exporter = OTLPMetricExporter(max_export_batch_size=100)
        self.assertEqual(exporter._max_export_batch_size, 100)
        exporter.shutdown()

    # ── export ────────────────────────────────────────────────────────────────

    def test_export_success_empty_data(self):
        exporter = OTLPMetricExporter()
        with patch.object(exporter, "_export", return_value=_ok()):
            result = exporter.export(_empty_metrics_data())
        self.assertEqual(result, MetricExportResult.SUCCESS)
        exporter.shutdown()

    def test_export_success_with_data(self):
        exporter = OTLPMetricExporter()
        with patch.object(exporter, "_export", return_value=_ok()):
            result = exporter.export(_make_metrics_data(2))
        self.assertEqual(result, MetricExportResult.SUCCESS)
        exporter.shutdown()

    def test_export_after_shutdown_returns_failure(self):
        exporter = OTLPMetricExporter()
        exporter.shutdown()
        result = exporter.export(_empty_metrics_data())
        self.assertEqual(result, MetricExportResult.FAILURE)

    def test_export_non_retryable_failure(self):
        exporter = OTLPMetricExporter()
        with patch.object(exporter, "_export", return_value=_404()):
            result = exporter.export(_empty_metrics_data())
        self.assertEqual(result, MetricExportResult.FAILURE)
        exporter.shutdown()

    def test_export_retry_then_deadline_exceeded(self):
        exporter = OTLPMetricExporter(timeout=0.01)
        with patch.object(exporter, "_export", return_value=_503()):
            with patch(_UNIFORM, return_value=100.0):
                result = exporter.export(_empty_metrics_data())
        self.assertEqual(result, MetricExportResult.FAILURE)
        exporter.shutdown()

    def test_export_max_retries_exhausted(self):
        exporter = OTLPMetricExporter(timeout=100)
        with patch.object(exporter, "_export", return_value=_503()):
            with patch(_UNIFORM, return_value=0.0001):
                with patch.object(exporter._shutdown_in_progress, "wait", return_value=False):
                    result = exporter.export(_empty_metrics_data())
        self.assertEqual(result, MetricExportResult.FAILURE)
        exporter.shutdown()

    def test_shutdown_interrupts_retry(self):
        exporter = OTLPMetricExporter(timeout=100)
        with patch.object(exporter, "_export", return_value=_503()):
            with patch(_UNIFORM, return_value=0.0001):
                with patch.object(exporter._shutdown_in_progress, "wait", return_value=True):
                    result = exporter.export(_empty_metrics_data())
        self.assertEqual(result, MetricExportResult.FAILURE)
        exporter.shutdown()

    def test_export_with_batch_size_sends_multiple_requests(self):
        # 3 data points with batch_size=1 → 3 separate HTTP requests
        exporter = OTLPMetricExporter(max_export_batch_size=1)
        call_count = 0

        def export_side_effect(*_args, **_kwargs):
            nonlocal call_count
            call_count += 1
            return _ok()

        with patch.object(exporter, "_export", side_effect=export_side_effect):
            result = exporter.export(_make_metrics_data(3))
        self.assertEqual(result, MetricExportResult.SUCCESS)
        self.assertEqual(call_count, 3)
        exporter.shutdown()

    # ── shutdown ──────────────────────────────────────────────────────────────

    def test_shutdown_sets_flag(self):
        exporter = OTLPMetricExporter()
        self.assertFalse(exporter._shutdown)
        exporter.shutdown()
        self.assertTrue(exporter._shutdown)

    def test_shutdown_twice_logs_warning(self):
        exporter = OTLPMetricExporter()
        exporter.shutdown()
        with self.assertLogs(level="WARNING") as cm:
            exporter.shutdown()
        self.assertTrue(any("already shutdown" in msg for msg in cm.output))

    def test_force_flush_returns_true(self):
        exporter = OTLPMetricExporter()
        self.assertTrue(exporter.force_flush())
        exporter.shutdown()


class TestAppendMetricsPath(unittest.TestCase):
    def test_with_trailing_slash(self):
        self.assertEqual(
            _append_metrics_path("http://localhost:4318/"),
            "http://localhost:4318/v1/metrics",
        )

    def test_without_trailing_slash(self):
        self.assertEqual(
            _append_metrics_path("http://localhost:4318"),
            "http://localhost:4318/v1/metrics",
        )


class TestSplitMetricsData(unittest.TestCase):

    def _make_request(self, n_points: int):
        return encode_metrics(_make_metrics_data(n_points))

    def test_split_no_batch_size_yields_unchanged(self):
        # max_export_batch_size=0 (falsy) → yields data as-is
        req = self._make_request(3)
        batches = list(_split_metrics_data(req, 0))
        self.assertEqual(len(batches), 1)
        self.assertIs(batches[0], req)

    def test_split_batch_larger_than_data_yields_one(self):
        req = self._make_request(3)
        batches = list(_split_metrics_data(req, 10))
        self.assertEqual(len(batches), 1)
        total_points = sum(
            len(sm.metrics[0].gauge.data_points)
            for batch in batches
            for rm in batch.resource_metrics
            for sm in rm.scope_metrics
        )
        self.assertEqual(total_points, 3)

    def test_split_batch_size_1_yields_one_per_point(self):
        req = self._make_request(3)
        batches = list(_split_metrics_data(req, 1))
        self.assertEqual(len(batches), 3)
        for batch in batches:
            total = sum(
                len(sm.metrics[0].gauge.data_points)
                for rm in batch.resource_metrics
                for sm in rm.scope_metrics
            )
            self.assertEqual(total, 1)

    def test_split_batch_size_2_yields_two_batches_for_four_points(self):
        req = self._make_request(4)
        batches = list(_split_metrics_data(req, 2))
        self.assertEqual(len(batches), 2)

    def test_split_empty_request_yields_nothing(self):
        req = encode_metrics(_empty_metrics_data())
        batches = list(_split_metrics_data(req, 1))
        self.assertEqual(len(batches), 0)

    def test_split_preserves_sum_metric(self):
        data = MetricsData(
            resource_metrics=[
                ResourceMetrics(
                    resource=Resource({"service.name": "test"}),
                    scope_metrics=[
                        ScopeMetrics(
                            scope=InstrumentationScope("test", "1.0"),
                            metrics=[
                                Metric(
                                    name="my.counter",
                                    description="",
                                    unit="1",
                                    data=SDKSum(
                                        data_points=[
                                            NumberDataPoint(
                                                attributes={},
                                                start_time_unix_nano=0,
                                                time_unix_nano=1641946016139533244,
                                                value=1,
                                                exemplars=[],
                                            ),
                                            NumberDataPoint(
                                                attributes={"host": "b"},
                                                start_time_unix_nano=0,
                                                time_unix_nano=1641946016139533244,
                                                value=2,
                                                exemplars=[],
                                            ),
                                        ],
                                        aggregation_temporality=AggregationTemporality.CUMULATIVE,
                                        is_monotonic=True,
                                    ),
                                )
                            ],
                            schema_url="",
                        )
                    ],
                    schema_url="",
                )
            ]
        )
        req = encode_metrics(data)
        batches = list(_split_metrics_data(req, 1))
        self.assertEqual(len(batches), 2)
        for batch in batches:
            sm = batch.resource_metrics[0].scope_metrics[0]
            metric = sm.metrics[0]
            self.assertEqual(metric.name, "my.counter")
            self.assertEqual(len(metric.sum.data_points), 1)
