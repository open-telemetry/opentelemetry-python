# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import io
import os
import sys
import tempfile
import unittest
from typing import IO
from unittest.mock import Mock

from opentelemetry.exporter.otlp.json.common.metrics_encoder import (
    encode_metrics,
)
from opentelemetry.exporter.otlp.json.file._internal import _format_line
from opentelemetry.exporter.otlp.json.file.metric_exporter import (
    FileMetricExporter,
)
from opentelemetry.metrics import Observation
from opentelemetry.proto_json.metrics.v1.metrics import (
    ResourceMetrics as OtlpResourceMetrics,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics._internal.export import MetricExportResult
from opentelemetry.sdk.metrics._internal.point import (
    MetricsData,
    ResourceMetrics,
    ScopeMetrics,
)
from opentelemetry.sdk.metrics.export import (
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.test.metrictestutil import _generate_gauge, _generate_sum

_LOGGER_NAME = "opentelemetry.exporter.otlp.json.file.metric_exporter"


class _CapturingMetricExporter(FileMetricExporter):
    def __init__(self, *, stream: IO[str]) -> None:
        super().__init__(stream=stream)
        self.last_metrics_data: MetricsData | None = None

    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> MetricExportResult:
        self.last_metrics_data = metrics_data
        return super().export(
            metrics_data, timeout_millis=timeout_millis, **kwargs
        )


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
        self._exporter = FileMetricExporter(stream=self._stream)

    def test_export_metrics(self):
        result = self._exporter.export(_make_metrics_data())
        self.assertEqual(result, MetricExportResult.SUCCESS)
        lines = self._stream.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        rm = OtlpResourceMetrics.from_json(lines[0])
        # pylint: disable-next=unsubscriptable-object
        self.assertEqual(rm.scope_metrics[0].metrics[0].name, "requests")

    # pylint: disable-next=no-self-use
    def test_stream_flushed_after_export(self):
        mock_stream = Mock()
        exporter = FileMetricExporter(stream=mock_stream)
        exporter.export(_make_metrics_data())
        mock_stream.flush.assert_called_once()

    def test_export_multiple_resource_metrics(self):
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
        names = {
            OtlpResourceMetrics.from_json(line)  # pylint: disable=unsubscriptable-object
            .scope_metrics[0]
            .metrics[0]
            .name
            for line in lines
        }
        self.assertEqual(names, {"counter_a", "gauge_b"})

    def test_export_after_shutdown(self):
        self._exporter.shutdown()
        with self.assertLogs(_LOGGER_NAME, level="WARNING"):
            result = self._exporter.export(_make_metrics_data())
        self.assertEqual(result, MetricExportResult.FAILURE)
        self.assertEqual(self._stream.getvalue(), "")

    def test_shutdown_idempotent(self):
        self._exporter.shutdown()
        with self.assertLogs(_LOGGER_NAME, level="WARNING"):
            self._exporter.shutdown()

    def test_force_flush_returns_true(self):
        self.assertTrue(self._exporter.force_flush())

    def test_export_stream_error(self):
        mock_stream = Mock()
        mock_stream.writelines.side_effect = OSError("disk full")
        exporter = FileMetricExporter(stream=mock_stream)
        with self.assertLogs(_LOGGER_NAME, level="ERROR"):
            result = exporter.export(_make_metrics_data())
        self.assertEqual(result, MetricExportResult.FAILURE)

    def test_export_with_path(self):
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            path = os.path.join(tmp_dir_name, "output.jsonl")
            exporter = FileMetricExporter(path)
            exporter.export(_make_metrics_data())
            exporter.shutdown()
            with open(path, encoding="utf-8") as fh:
                rm = OtlpResourceMetrics.from_json(fh.read().splitlines()[0])
            # pylint: disable-next=unsubscriptable-object
            self.assertEqual(rm.scope_metrics[0].metrics[0].name, "requests")

    def test_path_and_stream_raises(self):
        with self.assertRaises(ValueError):
            FileMetricExporter("output.jsonl", stream=self._stream)  # type: ignore

    def test_default_stream_is_stdout(self):
        exporter = FileMetricExporter()
        # pylint: disable-next=protected-access
        self.assertIs(exporter._stream, sys.stdout)


class TestFileMetricExporterRoundTrip(unittest.TestCase):
    def setUp(self):
        self._stream = io.StringIO()
        self._exporter = _CapturingMetricExporter(stream=self._stream)
        self._provider = MeterProvider(
            metric_readers=[
                PeriodicExportingMetricReader(
                    self._exporter, export_interval_millis=100_000
                ),
            ]
        )
        self._meter = self._provider.get_meter(__name__)

    def tearDown(self):
        self._provider.shutdown()

    def _expected(self) -> str:
        return "".join(
            _format_line(rm.to_dict())
            for rm in encode_metrics(  # pylint: disable=not-an-iterable
                self._exporter.last_metrics_data  # type: ignore
            ).resource_metrics
        )

    def test_synchronous_instruments_match_in_memory(self):
        self._meter.create_counter("req.count").add(10)
        self._meter.create_up_down_counter("queue.depth").add(-3)
        self._meter.create_histogram("req.duration").record(1.5)
        self._meter.create_gauge("cpu.temp").set(72.0)
        self._provider.force_flush()
        self.assertEqual(self._stream.getvalue(), self._expected())

    def test_observable_instruments_match_in_memory(self):
        self._meter.create_observable_counter(
            "obs.req.count", callbacks=[lambda _: [Observation(20)]]
        )
        self._meter.create_observable_up_down_counter(
            "obs.queue.depth", callbacks=[lambda _: [Observation(-7)]]
        )
        self._meter.create_observable_gauge(
            "obs.cpu.temp", callbacks=[lambda _: [Observation(55.5)]]
        )
        self._provider.force_flush()
        self.assertEqual(self._stream.getvalue(), self._expected())
