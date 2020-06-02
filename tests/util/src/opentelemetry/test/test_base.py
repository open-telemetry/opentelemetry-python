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

from opentelemetry import metrics as metrics_api
from opentelemetry import trace as trace_api
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export.in_memory_metrics_exporter import (
    InMemoryMetricsExporter,
)
from opentelemetry.sdk.trace import TracerProvider, export
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)


class TestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_tracer_provider = trace_api.get_tracer_provider()
        result = cls.create_tracer_provider()
        cls.tracer_provider, cls.memory_exporter = result
        trace_api.set_tracer_provider(cls.tracer_provider)
        cls.original_meter_provider = metrics_api.get_meter_provider()
        result = cls.create_meter_provider()
        cls.meter_provider, cls.memory_metrics_exporter = result
        metrics_api.set_meter_provider(cls.meter_provider)

    @classmethod
    def tearDownClass(cls):
        trace_api.set_tracer_provider(cls.original_tracer_provider)
        metrics_api.set_meter_provider(cls.original_meter_provider)

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
            in-memory span exporter in the second.
        """
        tracer_provider = TracerProvider(**kwargs)
        memory_exporter = InMemorySpanExporter()
        span_processor = export.SimpleExportSpanProcessor(memory_exporter)
        tracer_provider.add_span_processor(span_processor)

        return tracer_provider, memory_exporter

    @staticmethod
    def create_meter_provider(**kwargs):
        """Helper to create a configured meter provider

        Creates a `MeterProvider` and an `InMemoryMetricsExporter`.

        Returns:
            A list with the meter provider in the first element and the
            in-memory metrics exporter in the second
        """
        meter_provider = MeterProvider(**kwargs)
        memory_exporter = InMemoryMetricsExporter()
        return meter_provider, memory_exporter

    @staticmethod
    @contextmanager
    def disable_logging(highest_level=logging.CRITICAL):
        logging.disable(highest_level)

        try:
            yield
        finally:
            logging.disable(logging.NOTSET)
