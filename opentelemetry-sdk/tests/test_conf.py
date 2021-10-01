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

from opentelemetry import trace
from opentelemetry.sdk.conf import configure_tracing
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SpanExporter,
    SpanProcessor,
)


class CustomTracerProvider(TracerProvider):
    pass


class CustomSpanProcessor(SpanProcessor):
    def __init__(self, exporter):
        self.span_exporter = exporter


class CustomSpanExporter(SpanExporter):
    pass


class TestConf(unittest.TestCase):
    # pylint: disable=protected-access

    def setUp(self):
        self._original_provider = trace._TRACER_PROVIDER
        return super().setUp()

    def tearDown(self) -> None:
        trace._TRACER_PROVIDER = self._original_provider
        return super().tearDown()

    def assertConfiguredProcessorAndExporter(  # pylint: disable=C0103
        self, processor, expected_processor_class, expected_exporter_class
    ):
        self.assertIsInstance(processor, expected_processor_class)
        self.assertIsInstance(processor.span_exporter, expected_exporter_class)

    def test_configure_tracing_default(self):
        provider = configure_tracing()
        self.assertIsInstance(provider, TracerProvider)
        self.assertIs(provider, trace.get_tracer_provider())

        self.assertEqual(
            len(provider._active_span_processor._span_processors), 1
        )
        processor = provider._active_span_processor._span_processors[0]
        self.assertConfiguredProcessorAndExporter(
            processor, BatchSpanProcessor, ConsoleSpanExporter
        )

    def test_configure_tracing_non_global(self):
        configure_tracing(set_global=False)
        self.assertIsNone(trace._TRACER_PROVIDER)

    def test_configure_tracing_custom_components(self):
        provider = configure_tracing(
            CustomTracerProvider, [CustomSpanProcessor], [CustomSpanExporter]
        )
        self.assertIsInstance(provider, TracerProvider)
        self.assertIs(provider, trace.get_tracer_provider())

        self.assertEqual(
            len(provider._active_span_processor._span_processors), 1
        )
        processor = provider._active_span_processor._span_processors[0]
        self.assertConfiguredProcessorAndExporter(
            processor, CustomSpanProcessor, CustomSpanExporter
        )

    def test_configure_tracing_multiple_components(self):
        provider = configure_tracing(
            CustomTracerProvider,
            [CustomSpanProcessor, BatchSpanProcessor],
            [CustomSpanExporter, ConsoleSpanExporter],
        )
        self.assertIsInstance(provider, TracerProvider)
        self.assertIs(provider, trace.get_tracer_provider())

        self.assertEqual(
            len(provider._active_span_processor._span_processors), 4
        )
        processors = provider._active_span_processor._span_processors
        self.assertConfiguredProcessorAndExporter(
            processors[0], CustomSpanProcessor, CustomSpanExporter
        )
        self.assertConfiguredProcessorAndExporter(
            processors[1], BatchSpanProcessor, CustomSpanExporter
        )
        self.assertConfiguredProcessorAndExporter(
            processors[2], CustomSpanProcessor, ConsoleSpanExporter
        )
        self.assertConfiguredProcessorAndExporter(
            processors[3], BatchSpanProcessor, ConsoleSpanExporter
        )
