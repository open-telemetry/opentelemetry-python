# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import unittest
from contextlib import contextmanager

from opentelemetry import trace as trace_api
from opentelemetry.sdk.trace import TracerProvider, export
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from opentelemetry.test.globals_test import reset_trace_globals


class TestBase(unittest.TestCase):
    # pylint: disable=C0103

    @classmethod
    def setUpClass(cls):
        result = cls.create_tracer_provider()
        cls.tracer_provider, cls.memory_exporter = result
        # This is done because set_tracer_provider cannot override the
        # current tracer provider.
        reset_trace_globals()
        trace_api.set_tracer_provider(cls.tracer_provider)

    @classmethod
    def tearDownClass(cls):
        # This is done because set_tracer_provider cannot override the
        # current tracer provider.
        reset_trace_globals()

    def setUp(self):
        self.memory_exporter.clear()

    def get_finished_spans(self):
        return FinishedTestSpans(
            self, self.memory_exporter.get_finished_spans()
        )

    def assertEqualSpanInstrumentationInfo(self, span, module):
        self.assertEqual(span.instrumentation_info.name, module.__name__)
        self.assertEqual(span.instrumentation_info.version, module.__version__)

    def assertSpanHasAttributes(self, span, attributes):
        for key, val in attributes.items():
            self.assertIn(key, span.attributes)
            self.assertEqual(val, span.attributes[key])

    def sorted_spans(self, spans):  # pylint: disable=R0201
        """
        Sorts spans by span creation time.

        Note: This method should not be used to sort spans in a deterministic way as the
        order depends on timing precision provided by the platform.
        """
        return sorted(
            spans,
            key=lambda s: s._start_time,  # pylint: disable=W0212
            reverse=True,
        )

    @staticmethod
    def create_tracer_provider(**kwargs):
        """Helper to create a configured tracer provider.

        Creates and configures a `TracerProvider` with a
        `SimpleSpanProcessor` and a `InMemorySpanExporter`.
        All the parameters passed are forwarded to the TracerProvider
        constructor.

        Returns:
            A list with the tracer provider in the first element and the
            in-memory span exporter in the second.
        """
        tracer_provider = TracerProvider(**kwargs)
        memory_exporter = InMemorySpanExporter()
        span_processor = export.SimpleSpanProcessor(memory_exporter)
        tracer_provider.add_span_processor(span_processor)

        return tracer_provider, memory_exporter

    @staticmethod
    @contextmanager
    def disable_logging(highest_level=logging.CRITICAL):
        logging.disable(highest_level)

        try:
            yield
        finally:
            logging.disable(logging.NOTSET)


class FinishedTestSpans(list):
    def __init__(self, test, spans):
        super().__init__(spans)
        self.test = test

    def by_name(self, name):
        for span in self:
            if span.name == name:
                return span
        self.test.fail(f"Did not find span with name {name}")
        return None

    def by_attr(self, key, value):
        for span in self:
            if span.attributes.get(key) == value:
                return span
        self.test.fail(f"Did not find span with attrs {key}={value}")
        return None
