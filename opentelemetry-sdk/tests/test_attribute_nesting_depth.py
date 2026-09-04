# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Telemetry calls must never raise into the instrumented application.

`AnyValue` allows arbitrarily nested Sequence/Mapping attribute values, so a
user handing the SDK a self-referential structure must not blow the stack.
"""

import unittest

from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import (
    InMemoryLogExporter,
    SimpleLogRecordProcessor,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)


def _cyclic_list():
    value = [1, 2]
    value.append(value)
    return value


def _cyclic_dict():
    value = {"a": 1}
    value["self"] = value
    return value


class TestAttributeNestingDepthDoesNotRaise(unittest.TestCase):
    def setUp(self):
        self.exporter = InMemorySpanExporter()
        self.tracer_provider = TracerProvider(shutdown_on_exit=False)
        self.tracer_provider.add_span_processor(SimpleSpanProcessor(self.exporter))
        self.tracer = self.tracer_provider.get_tracer(__name__)

    def test_set_attribute_with_cyclic_sequence(self):
        with self.tracer.start_as_current_span("span") as span:
            span.set_attribute("cyclic", _cyclic_list())
        self.assertIsNone(self.exporter.get_finished_spans()[0].attributes["cyclic"])

    def test_set_attribute_with_cyclic_mapping(self):
        with self.tracer.start_as_current_span("span") as span:
            span.set_attribute("cyclic", _cyclic_dict())
        self.assertIsNone(self.exporter.get_finished_spans()[0].attributes["cyclic"])

    def test_set_attributes_keeps_sibling_attributes(self):
        """One unusable value must not discard the attributes beside it."""
        with self.tracer.start_as_current_span("span") as span:
            span.set_attributes({"good": "kept", "cyclic": _cyclic_list()})
        attributes = self.exporter.get_finished_spans()[0].attributes
        self.assertEqual(attributes["good"], "kept")
        self.assertIsNone(attributes["cyclic"])

    def test_add_event_with_cyclic_value(self):
        with self.tracer.start_as_current_span("span") as span:
            span.add_event("event", {"cyclic": _cyclic_list()})
        event = self.exporter.get_finished_spans()[0].events[0]
        self.assertIsNone(event.attributes["cyclic"])

    def test_resource_create_with_cyclic_value(self):
        resource = Resource.create({"cyclic": _cyclic_list()})
        self.assertIsNone(resource.attributes["cyclic"])

    def test_counter_add_with_cyclic_value(self):
        reader = InMemoryMetricReader()
        meter_provider = MeterProvider(metric_readers=[reader])
        meter_provider.get_meter(__name__).create_counter("counter").add(1, {"cyclic": _cyclic_list()})
        metrics_data = reader.get_metrics_data()
        data_point = metrics_data.resource_metrics[0].scope_metrics[0].metrics[0].data.data_points[0]
        self.assertIsNone(dict(data_point.attributes)["cyclic"])
        meter_provider.shutdown()

    def test_logger_emit_with_cyclic_value(self):
        exporter = InMemoryLogExporter()
        logger_provider = LoggerProvider(shutdown_on_exit=False)
        logger_provider.add_log_record_processor(SimpleLogRecordProcessor(exporter))
        logger_provider.get_logger(__name__).emit(
            body="body", attributes={"cyclic": _cyclic_list()}
        )
        record = exporter.get_finished_logs()[0].log_record
        self.assertIsNone(dict(record.attributes)["cyclic"])
        logger_provider.shutdown()

    def tearDown(self):
        self.tracer_provider.shutdown()
