# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import io
import json
import unittest
from unittest.mock import Mock, patch

from opentelemetry.exporter.otlp.json.file.metric_exporter import (
    FileMetricExporter,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION,
    OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE,
)
from opentelemetry.sdk.metrics import (
    Counter,
    Histogram,
    MeterProvider,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.sdk.metrics._internal.aggregation import (
    AggregationTemporality,
    ExplicitBucketHistogramAggregation,
    ExponentialBucketHistogramAggregation,
)
from opentelemetry.sdk.metrics._internal.export import MetricExportResult
from opentelemetry.sdk.metrics._internal.point import (
    MetricsData,
    ResourceMetrics,
    ScopeMetrics,
)
from opentelemetry.sdk.metrics.export import (
    InMemoryMetricReader,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.test.metrictestutil import _generate_gauge, _generate_sum

_LOGGER_NAME = "opentelemetry.exporter.otlp.json.file.metric_exporter"


def _make_metrics_data() -> MetricsData:
    return MetricsData(
        resource_metrics=[
            ResourceMetrics(
                resource=Resource({"service.name": "test-service"}),
                scope_metrics=[
                    ScopeMetrics(
                        scope=InstrumentationScope("test-scope", "1.0"),
                        metrics=[_generate_sum("requests", 42)],
                        schema_url="",
                    )
                ],
                schema_url="",
            )
        ]
    )


class TestFileMetricExporter(unittest.TestCase):
    def setUp(self):
        self._stream = io.StringIO()
        self._exporter = FileMetricExporter(self._stream)

    def test_export_metrics_returns_success(self):
        result = self._exporter.export(_make_metrics_data())
        self.assertEqual(result, MetricExportResult.SUCCESS)

    def test_export_metrics_writes_valid_json(self):
        self._exporter.export(_make_metrics_data())
        lines = self._stream.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        json.loads(lines[0])

    def test_export_metric_name_in_output(self):
        self._exporter.export(_make_metrics_data())
        self.assertIn("requests", self._stream.getvalue())

    def test_stream_flushed_after_export(self):
        mock_stream = Mock()
        exporter = FileMetricExporter(mock_stream)
        exporter.export(_make_metrics_data())
        mock_stream.flush.assert_called_once()

    def test_custom_formatter_called(self):
        formatter = Mock(return_value="formatted\n")
        exporter = FileMetricExporter(self._stream, formatter=formatter)
        exporter.export(_make_metrics_data())
        formatter.assert_called_once()
        self.assertIn("formatted\n", self._stream.getvalue())

    def test_export_multiple_resource_metrics_writes_one_line_each(self):
        data = MetricsData(
            resource_metrics=[
                ResourceMetrics(
                    resource=Resource({"host": "a"}),
                    scope_metrics=[
                        ScopeMetrics(
                            scope=InstrumentationScope("s", "1"),
                            metrics=[_generate_sum("counter_a", 1)],
                            schema_url="",
                        )
                    ],
                    schema_url="",
                ),
                ResourceMetrics(
                    resource=Resource({"host": "b"}),
                    scope_metrics=[
                        ScopeMetrics(
                            scope=InstrumentationScope("s", "1"),
                            metrics=[_generate_gauge("gauge_b", 2)],
                            schema_url="",
                        )
                    ],
                    schema_url="",
                ),
            ]
        )
        self._exporter.export(data)
        lines = self._stream.getvalue().splitlines()
        self.assertEqual(len(lines), 2)

    def test_export_after_shutdown_returns_failure(self):
        self._exporter.shutdown()
        result = self._exporter.export(_make_metrics_data())
        self.assertEqual(result, MetricExportResult.FAILURE)

    def test_export_after_shutdown_logs_warning(self):
        self._exporter.shutdown()
        with self.assertLogs(_LOGGER_NAME, level="WARNING"):
            self._exporter.export(_make_metrics_data())

    def test_export_after_shutdown_writes_nothing(self):
        self._exporter.shutdown()
        self._exporter.export(_make_metrics_data())
        self.assertEqual(self._stream.getvalue(), "")

    def test_shutdown_idempotent_logs_warning(self):
        self._exporter.shutdown()
        with self.assertLogs(_LOGGER_NAME, level="WARNING"):
            self._exporter.shutdown()

    def test_force_flush_returns_true(self):
        self.assertTrue(self._exporter.force_flush())

    def test_export_stream_error_returns_failure(self):
        mock_stream = Mock()
        mock_stream.writelines.side_effect = OSError("disk full")
        exporter = FileMetricExporter(mock_stream)
        result = exporter.export(_make_metrics_data())
        self.assertEqual(result, MetricExportResult.FAILURE)

    def test_export_stream_error_logs_exception(self):
        mock_stream = Mock()
        mock_stream.writelines.side_effect = OSError("disk full")
        exporter = FileMetricExporter(mock_stream)
        with self.assertLogs(_LOGGER_NAME, level="ERROR"):
            exporter.export(_make_metrics_data())


class TestFileMetricExporterTemporality(unittest.TestCase):
    def setUp(self):
        self._stream = io.StringIO()

    def _exporter(self, **kwargs) -> FileMetricExporter:
        return FileMetricExporter(self._stream, **kwargs)

    def test_temporality_default_is_cumulative(self):
        exporter = self._exporter()
        for instrument_class in (
            Counter,
            UpDownCounter,
            Histogram,
            ObservableCounter,
            ObservableUpDownCounter,
            ObservableGauge,
        ):
            with self.subTest(instrument=instrument_class.__name__):
                self.assertEqual(
                    exporter._preferred_temporality[instrument_class],
                    AggregationTemporality.CUMULATIVE,
                )

    def test_temporality_delta_env(self):
        delta_cases = {
            Counter: AggregationTemporality.DELTA,
            UpDownCounter: AggregationTemporality.CUMULATIVE,
            Histogram: AggregationTemporality.DELTA,
            ObservableCounter: AggregationTemporality.DELTA,
            ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
            ObservableGauge: AggregationTemporality.CUMULATIVE,
        }
        with patch.dict(
            "os.environ",
            {OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE: "DELTA"},
        ):
            exporter = self._exporter()
        for instrument_class, expected in delta_cases.items():
            with self.subTest(instrument=instrument_class.__name__):
                self.assertEqual(
                    exporter._preferred_temporality[instrument_class],
                    expected,
                )

    def test_temporality_lowmemory_env(self):
        lowmemory_cases = {
            Counter: AggregationTemporality.DELTA,
            UpDownCounter: AggregationTemporality.CUMULATIVE,
            Histogram: AggregationTemporality.DELTA,
            ObservableCounter: AggregationTemporality.CUMULATIVE,
            ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
            ObservableGauge: AggregationTemporality.CUMULATIVE,
        }
        with patch.dict(
            "os.environ",
            {OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE: "LOWMEMORY"},
        ):
            exporter = self._exporter()
        for instrument_class, expected in lowmemory_cases.items():
            with self.subTest(instrument=instrument_class.__name__):
                self.assertEqual(
                    exporter._preferred_temporality[instrument_class],
                    expected,
                )

    def test_temporality_invalid_env_logs_warning(self):
        with patch.dict(
            "os.environ",
            {OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE: "INVALID"},
        ):
            with self.assertLogs(_LOGGER_NAME, level="WARNING"):
                exporter = self._exporter()
        self.assertEqual(
            exporter._preferred_temporality[Counter],
            AggregationTemporality.CUMULATIVE,
        )

    def test_temporality_constructor_overrides_env(self):
        with patch.dict(
            "os.environ",
            {OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE: "CUMULATIVE"},
        ):
            exporter = self._exporter(
                preferred_temporality={Counter: AggregationTemporality.DELTA}
            )
        self.assertEqual(
            exporter._preferred_temporality[Counter],
            AggregationTemporality.DELTA,
        )


class TestFileMetricExporterAggregation(unittest.TestCase):
    def setUp(self):
        self._stream = io.StringIO()

    def _exporter(self, **kwargs) -> FileMetricExporter:
        return FileMetricExporter(self._stream, **kwargs)

    def test_aggregation_default_is_explicit_bucket(self):
        exporter = self._exporter()
        self.assertIsInstance(
            exporter._preferred_aggregation[Histogram],
            ExplicitBucketHistogramAggregation,
        )

    def test_aggregation_exponential_env(self):
        with patch.dict(
            "os.environ",
            {
                OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION: "base2_exponential_bucket_histogram"
            },
        ):
            exporter = self._exporter()
        self.assertIsInstance(
            exporter._preferred_aggregation[Histogram],
            ExponentialBucketHistogramAggregation,
        )

    def test_aggregation_invalid_env_logs_warning(self):
        with patch.dict(
            "os.environ",
            {
                OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION: "unknown_aggregation"
            },
        ):
            with self.assertLogs(_LOGGER_NAME, level="WARNING"):
                exporter = self._exporter()
        self.assertIsInstance(
            exporter._preferred_aggregation[Histogram],
            ExplicitBucketHistogramAggregation,
        )

    def test_aggregation_constructor_overrides_env(self):
        custom_aggregation = ExponentialBucketHistogramAggregation()
        with patch.dict(
            "os.environ",
            {
                OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION: "explicit_bucket_histogram"
            },
        ):
            exporter = self._exporter(
                preferred_aggregation={Histogram: custom_aggregation}
            )
        self.assertIs(
            exporter._preferred_aggregation[Histogram],
            custom_aggregation,
        )


class TestFileMetricExporterIntegration(unittest.TestCase):
    def setUp(self):
        self._stream = io.StringIO()
        self._file_exporter = FileMetricExporter(self._stream)
        self._in_memory = InMemoryMetricReader()
        self._provider = MeterProvider(
            metric_readers=[
                PeriodicExportingMetricReader(
                    self._file_exporter, export_interval_millis=100_000
                ),
                self._in_memory,
            ]
        )
        self._meter = self._provider.get_meter(__name__)

    def tearDown(self):
        self._provider.shutdown()

    def _metric_names_and_values(
        self, metrics_data
    ) -> dict[str, list[int | float]]:
        result: dict[str, list[int | float]] = {}
        for rm in metrics_data.resource_metrics:
            for sm in rm.scope_metrics:
                for m in sm.metrics:
                    result[m.name] = [
                        getattr(dp, "value", getattr(dp, "sum", None))
                        for dp in m.data.data_points
                    ]
        return result

    def test_counter_matches_in_memory(self):
        counter = self._meter.create_counter("requests")
        counter.add(42)
        self._provider.force_flush()
        metrics_data = self._in_memory.get_metrics_data()

        self.assertIn("requests", self._stream.getvalue())
        in_memory_nv = self._metric_names_and_values(metrics_data)
        self.assertIn("requests", in_memory_nv)
        self.assertEqual(in_memory_nv["requests"], [42])

    def test_histogram_matches_in_memory(self):
        histogram = self._meter.create_histogram("latency")
        histogram.record(1.5)
        histogram.record(3.0)
        self._provider.force_flush()
        metrics_data = self._in_memory.get_metrics_data()

        self.assertIn("latency", self._stream.getvalue())
        in_memory_nv = self._metric_names_and_values(metrics_data)
        self.assertIn("latency", in_memory_nv)
        self.assertEqual(in_memory_nv["latency"], [4.5])

    def test_stream_output_is_valid_json(self):
        counter = self._meter.create_counter("ops")
        counter.add(1)
        self._provider.force_flush()
        for line in self._stream.getvalue().splitlines():
            json.loads(line)
