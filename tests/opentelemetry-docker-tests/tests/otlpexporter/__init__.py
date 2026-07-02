# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import math
import unittest
from abc import ABC, abstractmethod

from opentelemetry._logs import SeverityNumber
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import (
    LogRecordExporter,
    SimpleLogRecordProcessor,
)
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
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter
from opentelemetry.test._otlp_test_server import OtlpProtoTestServer
from opentelemetry.trace import Link, SpanContext, StatusCode, TraceFlags


def _attrs_to_dict(attributes) -> dict:
    result = {}
    for kv in attributes:
        which = kv.value.WhichOneof("value")
        if which == "string_value":
            result[kv.key] = kv.value.string_value
        elif which == "int_value":
            result[kv.key] = kv.value.int_value
        elif which == "double_value":
            result[kv.key] = kv.value.double_value
        elif which == "bool_value":
            result[kv.key] = kv.value.bool_value
    return result


class TracesExporterTestsBase(ABC, unittest.TestCase):
    __test__ = False

    _server: OtlpProtoTestServer

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._server = OtlpProtoTestServer(host="0.0.0.0", port=4319).start()

    @classmethod
    def tearDownClass(cls):
        cls._server.stop()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self._tracer_provider = TracerProvider()
        self._tracer_provider.add_span_processor(
            SimpleSpanProcessor(self.build_exporter())
        )
        self._tracer = self._tracer_provider.get_tracer(__name__)
        self._server.clear()

    def tearDown(self):
        self._tracer_provider.shutdown()
        super().tearDown()

    @abstractmethod
    def build_exporter(self) -> SpanExporter: ...

    def test_simple_span_name(self):
        with self._tracer.start_as_current_span("my-span"):
            pass

        recorded = self._server.get_span(timeout=5.0)
        self.assertEqual(recorded.span.name, "my-span")

    def test_span_attributes(self):
        with self._tracer.start_as_current_span(
            "attrs-span",
            attributes={
                "str_key": "hello",
                "int_key": 42,
                "float_key": 3.14,
                "bool_key": True,
            },
        ):
            pass

        recorded = self._server.get_span(timeout=5.0)
        attrs = _attrs_to_dict(recorded.span.attributes)
        self.assertEqual(attrs["str_key"], "hello")
        self.assertEqual(attrs["int_key"], 42)
        self.assertAlmostEqual(attrs["float_key"], 3.14, places=5)
        self.assertEqual(attrs["bool_key"], True)

    def test_nested_spans_parent_child(self):
        with self._tracer.start_as_current_span("foo"):
            with self._tracer.start_as_current_span("bar"):
                with self._tracer.start_as_current_span("baz"):
                    pass

        spans = {
            r.span.name: r.span
            for r in self._server.get_spans(count=3, timeout=10.0)
        }
        self.assertIn("foo", spans)
        self.assertIn("bar", spans)
        self.assertIn("baz", spans)
        self.assertEqual(spans["baz"].parent_span_id, spans["bar"].span_id)
        self.assertEqual(spans["bar"].parent_span_id, spans["foo"].span_id)
        self.assertEqual(spans["foo"].parent_span_id, b"")

    def test_span_with_event(self):
        with self._tracer.start_as_current_span("event-span") as span:
            span.add_event("my-event", {"event_key": "event_val"})

        recorded = self._server.get_span(timeout=5.0)
        self.assertEqual(len(recorded.span.events), 1)
        event = recorded.span.events[0]
        self.assertEqual(event.name, "my-event")
        self.assertEqual(
            _attrs_to_dict(event.attributes), {"event_key": "event_val"}
        )

    def test_span_with_link(self):
        link_trace_id = 0x000000000000000000000000DEADBEEF
        link_span_id = 0x00000000DEADBEF0
        link_context = SpanContext(
            trace_id=link_trace_id,
            span_id=link_span_id,
            is_remote=True,
            trace_flags=TraceFlags(0x01),
        )
        with self._tracer.start_as_current_span(
            "linked-span", links=[Link(link_context)]
        ):
            pass

        recorded = self._server.get_span(timeout=5.0)
        self.assertEqual(len(recorded.span.links), 1)
        link = recorded.span.links[0]
        self.assertEqual(link.trace_id, link_trace_id.to_bytes(16, "big"))
        self.assertEqual(link.span_id, link_span_id.to_bytes(8, "big"))

    def test_span_status_ok(self):
        with self._tracer.start_as_current_span("ok-span") as span:
            span.set_status(StatusCode.OK)

        recorded = self._server.get_span(timeout=5.0)
        self.assertEqual(recorded.span.status.code, 1)

    def test_span_status_error(self):
        with self._tracer.start_as_current_span("error-span") as span:
            span.set_status(StatusCode.ERROR, "something went wrong")

        recorded = self._server.get_span(timeout=5.0)
        self.assertEqual(recorded.span.status.code, 2)
        self.assertEqual(recorded.span.status.message, "something went wrong")


class MetricsExporterTestsBase(ABC, unittest.TestCase):
    __test__ = False

    _server: OtlpProtoTestServer

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._server = OtlpProtoTestServer(host="0.0.0.0", port=4319).start()

    @classmethod
    def tearDownClass(cls):
        cls._server.stop()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self._reader = PeriodicExportingMetricReader(
            self.build_exporter(),
            export_interval_millis=math.inf,
        )
        self._meter_provider = MeterProvider(
            metric_readers=[self._reader],
            resource=Resource.create({"service.name": "test-service"}),
        )
        self._meter = self._meter_provider.get_meter(__name__)
        self._server.clear()

    def tearDown(self):
        self._meter_provider.shutdown()
        super().tearDown()

    @abstractmethod
    def build_exporter(self) -> MetricExporter: ...

    def test_sum_counter(self):
        counter = self._meter.create_counter("test.counter", unit="requests")
        counter.add(3, {"status": "ok"})
        counter.add(7, {"status": "ok"})
        counter.add(5, {"status": "error"})
        self._reader.force_flush(timeout_millis=5000)

        recorded = self._server.wait_for_metric(
            name="test.counter", timeout=5.0
        )
        self.assertEqual(recorded.metric.name, "test.counter")
        self.assertEqual(recorded.metric.unit, "requests")
        self.assertTrue(recorded.metric.HasField("sum"))
        self.assertTrue(recorded.metric.sum.is_monotonic)
        dps = {
            tuple(sorted(_attrs_to_dict(dp.attributes).items())): dp
            for dp in recorded.metric.sum.data_points
        }
        self.assertEqual(dps[(("status", "ok"),)].as_int, 10)
        self.assertEqual(dps[(("status", "error"),)].as_int, 5)

    def test_sum_up_down_counter(self):
        counter = self._meter.create_up_down_counter("test.up_down_counter")
        counter.add(10)
        counter.add(-3)
        self._reader.force_flush(timeout_millis=5000)

        recorded = self._server.wait_for_metric(
            name="test.up_down_counter", timeout=5.0
        )
        self.assertTrue(recorded.metric.HasField("sum"))
        self.assertFalse(recorded.metric.sum.is_monotonic)
        self.assertEqual(recorded.metric.sum.data_points[0].as_int, 7)

    def test_gauge(self):
        gauge = self._meter.create_gauge("test.gauge")
        gauge.set(42, {"status": "active"})
        self._reader.force_flush(timeout_millis=5000)

        recorded = self._server.wait_for_metric(name="test.gauge", timeout=5.0)
        self.assertTrue(recorded.metric.HasField("gauge"))
        self.assertEqual(recorded.metric.gauge.data_points[0].as_int, 42)

    def test_explicit_bucket_histogram(self):
        histogram = self._meter.create_histogram("test.histogram")
        histogram.record(5)
        histogram.record(15)
        histogram.record(150)
        self._reader.force_flush(timeout_millis=5000)

        recorded = self._server.wait_for_metric(
            name="test.histogram", timeout=5.0
        )
        self.assertTrue(recorded.metric.HasField("histogram"))
        dp = recorded.metric.histogram.data_points[0]
        self.assertEqual(dp.count, 3)
        self.assertAlmostEqual(dp.sum, 170.0)
        self.assertGreater(len(dp.bucket_counts), 0)
        self.assertGreater(len(dp.explicit_bounds), 0)

    def test_exponential_histogram(self):
        reader = PeriodicExportingMetricReader(
            self.build_exporter(),
            export_interval_millis=math.inf,
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

        recorded = self._server.wait_for_metric(
            name="test.exp.histogram", timeout=5.0
        )
        self.assertTrue(recorded.metric.HasField("exponential_histogram"))
        dp = recorded.metric.exponential_histogram.data_points[0]
        self.assertEqual(dp.count, 3)
        self.assertAlmostEqual(dp.sum, 7.0)
        self.assertGreater(len(dp.positive.bucket_counts), 0)

        meter_provider.shutdown()

    def test_metric_data_point_attributes(self):
        counter = self._meter.create_counter("test.attrs.counter")
        counter.add(1, {"str_key": "hello", "int_key": 42})
        self._reader.force_flush(timeout_millis=5000)

        recorded = self._server.wait_for_metric(
            name="test.attrs.counter", timeout=5.0
        )
        attrs = _attrs_to_dict(recorded.metric.sum.data_points[0].attributes)
        self.assertEqual(attrs["str_key"], "hello")
        self.assertEqual(attrs["int_key"], 42)

    def test_scope_attributes(self):
        meter = self._meter_provider.get_meter(
            "test.scope",
            version="1.0.0",
            attributes={"scope.key": "scope.val"},
        )
        counter = meter.create_counter("scope.counter")
        counter.add(1)
        self._reader.force_flush(timeout_millis=5000)

        recorded = self._server.wait_for_metric(
            name="scope.counter", timeout=5.0
        )
        self.assertEqual(recorded.scope.name, "test.scope")
        self.assertEqual(recorded.scope.version, "1.0.0")
        self.assertEqual(
            _attrs_to_dict(recorded.scope.attributes)["scope.key"], "scope.val"
        )

    def test_resource_attributes(self):
        counter = self._meter.create_counter("resource.counter")
        counter.add(1)
        self._reader.force_flush(timeout_millis=5000)

        recorded = self._server.wait_for_metric(
            name="resource.counter", timeout=5.0
        )
        resource_attrs = _attrs_to_dict(recorded.resource.attributes)
        self.assertEqual(resource_attrs["service.name"], "test-service")


class LogsExporterTestsBase(ABC, unittest.TestCase):
    __test__ = False

    _server: OtlpProtoTestServer

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._server = OtlpProtoTestServer(host="0.0.0.0", port=4319).start()

    @classmethod
    def tearDownClass(cls):
        cls._server.stop()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self._logger_provider = LoggerProvider(
            resource=Resource.create({"service.name": "test-service"}),
        )
        self._logger_provider.add_log_record_processor(
            SimpleLogRecordProcessor(self.build_exporter())
        )
        self._logger = self._logger_provider.get_logger(__name__)
        self._server.clear()

    def tearDown(self):
        self._logger_provider.shutdown()
        super().tearDown()

    @abstractmethod
    def build_exporter(self) -> LogRecordExporter: ...

    def test_log_body(self):
        self._logger.emit(
            body="hello world", severity_number=SeverityNumber.INFO
        )

        recorded = self._server.get_log_record(timeout=5.0)
        self.assertEqual(recorded.log_record.body.string_value, "hello world")

    def test_log_severity_number(self):
        self._logger.emit(
            severity_number=SeverityNumber.ERROR, body="error occurred"
        )

        recorded = self._server.get_log_record(timeout=5.0)
        self.assertEqual(
            recorded.log_record.severity_number, SeverityNumber.ERROR.value
        )

    def test_log_severity_text(self):
        self._logger.emit(
            severity_number=SeverityNumber.WARN,
            severity_text="WARN",
            body="warning",
        )

        recorded = self._server.get_log_record(timeout=5.0)
        self.assertEqual(recorded.log_record.severity_text, "WARN")

    def test_log_attributes(self):
        self._logger.emit(
            body="attrs test",
            severity_number=SeverityNumber.INFO,
            attributes={
                "str_key": "hello",
                "int_key": 42,
                "float_key": 3.14,
                "bool_key": True,
            },
        )

        recorded = self._server.get_log_record(timeout=5.0)
        attrs = _attrs_to_dict(recorded.log_record.attributes)
        self.assertEqual(attrs["str_key"], "hello")
        self.assertEqual(attrs["int_key"], 42)
        self.assertAlmostEqual(attrs["float_key"], 3.14, places=5)
        self.assertEqual(attrs["bool_key"], True)

    def test_scope_attributes(self):
        logger = self._logger_provider.get_logger(
            "test.scope",
            version="1.0.0",
            attributes={"scope.key": "scope.val"},
        )
        logger.emit(body="scope test", severity_number=SeverityNumber.INFO)

        recorded = self._server.get_log_record(timeout=5.0)
        self.assertEqual(recorded.scope.name, "test.scope")
        self.assertEqual(recorded.scope.version, "1.0.0")
        self.assertEqual(
            _attrs_to_dict(recorded.scope.attributes)["scope.key"], "scope.val"
        )

    def test_resource_attributes(self):
        self._logger.emit(
            body="resource test", severity_number=SeverityNumber.INFO
        )

        recorded = self._server.get_log_record(timeout=5.0)
        resource_attrs = _attrs_to_dict(recorded.resource.attributes)
        self.assertEqual(resource_attrs["service.name"], "test-service")
