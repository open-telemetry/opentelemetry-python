# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import unittest

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


class TestAttributeNestingDepth(unittest.TestCase):
    def setUp(self):
        self.exporter = InMemorySpanExporter()
        self.provider = TracerProvider(shutdown_on_exit=False)
        self.provider.add_span_processor(SimpleSpanProcessor(self.exporter))
        self.tracer = self.provider.get_tracer(__name__)

    def tearDown(self):
        self.provider.shutdown()

    def test_span_attribute_does_not_raise(self):
        with self.tracer.start_as_current_span("span") as span:
            span.set_attribute("cyclic", _cyclic_list())

        self.assertIsNone(self.exporter.get_finished_spans()[0].attributes["cyclic"])

    def test_span_sibling_attributes_are_preserved(self):
        with self.tracer.start_as_current_span("span") as span:
            span.set_attributes({"good": "kept", "cyclic": _cyclic_list()})

        attributes = self.exporter.get_finished_spans()[0].attributes
        self.assertEqual(attributes["good"], "kept")
        self.assertIsNone(attributes["cyclic"])

    def test_resource_attribute_does_not_raise(self):
        resource = Resource.create({"cyclic": _cyclic_list()})

        self.assertIsNone(resource.attributes["cyclic"])
