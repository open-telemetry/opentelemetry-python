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

import unittest

from opentelemetry import trace as trace_api
from opentelemetry.sdk.trace import TracerProvider, export
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)


class TestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_provider = trace_api.get_tracer_provider()
        result = cls.create_tracer_provider()
        cls.tracer_provider, cls.memory_exporter = result
        trace_api.set_tracer_provider(cls.tracer_provider)

    @classmethod
    def tearDownClass(cls):
        trace_api.set_tracer_provider(cls.original_provider)

    def setUp(self):
        self.memory_exporter.clear()

    def check_span_instrumentation_info(self, span, module):
        self.assertEqual(span.instrumentation_info.name, module.__name__)
        self.assertEqual(span.instrumentation_info.version, module.__version__)

    @staticmethod
    def create_tracer_provider(**kwargs):
        """Helper to create a configured tracer provider.

        Creates and configures a `TracerProvider` with a
        `SimpleExportSpanProcessor` and a `InMemorySpanExporter`.
        All the parameters passed are forwarded to the TracerProvider
        constructor.

        Returns:
            A list with the tracer provider in the first element and the
            memory exporter in the second.
        """
        tracer_provider = TracerProvider(**kwargs)
        memory_exporter = InMemorySpanExporter()
        span_processor = export.SimpleExportSpanProcessor(memory_exporter)
        tracer_provider.add_span_processor(span_processor)

        return tracer_provider, memory_exporter
