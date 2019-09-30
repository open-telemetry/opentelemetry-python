# Copyright 2019, OpenTelemetry Authors
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

import time
import unittest
from unittest import mock

from opentelemetry import trace as trace_api
from opentelemetry.sdk import trace
from opentelemetry.sdk.trace import export


class MySpanExporter(export.SpanExporter):
    """Very simple span exporter used for testing."""

    def __init__(self, destination, max_export_batch_size=None):
        self.destination = destination
        self.max_export_batch_size = max_export_batch_size

    def export(self, spans: trace.Span) -> export.SpanExportResult:
        if (
            self.max_export_batch_size is not None
            and len(spans) > self.max_export_batch_size
        ):
            raise ValueError("Batch is too big")
        self.destination.extend(span.name for span in spans)
        return export.SpanExportResult.SUCCESS


class TestSimpleExportSpanProcessor(unittest.TestCase):
    def test_simple_span_processor(self):
        tracer = trace.Tracer()

        spans_names_list = []

        my_exporter = MySpanExporter(destination=spans_names_list)
        span_processor = export.SimpleExportSpanProcessor(my_exporter)
        tracer.add_span_processor(span_processor)

        with tracer.start_span("foo"):
            with tracer.start_span("bar"):
                with tracer.start_span("xxx"):
                    pass

        self.assertListEqual(["xxx", "bar", "foo"], spans_names_list)


def _create_start_and_end_span(name, span_processor):
    span = trace.Span(
        name,
        mock.Mock(spec=trace_api.SpanContext),
        span_processor=span_processor,
    )
    span.start()
    span.end()


class TestBatchExportSpanProcessor(unittest.TestCase):
    def test_batch_span_processor(self):
        spans_names_list = []

        my_exporter = MySpanExporter(destination=spans_names_list)
        span_processor = export.BatchExportSpanProcessor(my_exporter)

        span_names = ["xxx", "bar", "foo"]

        for name in span_names:
            _create_start_and_end_span(name, span_processor)

        span_processor.shutdown()
        self.assertListEqual(span_names, spans_names_list)

    def test_batch_span_processor_lossless(self):
        """Test that no spans are lost when sending max_queue_size spans"""
        spans_names_list = []

        my_exporter = MySpanExporter(
            destination=spans_names_list, max_export_batch_size=128
        )
        span_processor = export.BatchExportSpanProcessor(
            my_exporter, max_queue_size=512, max_export_batch_size=128
        )

        for _ in range(512):
            _create_start_and_end_span("foo", span_processor)

        span_processor.shutdown()
        self.assertEqual(len(spans_names_list), 512)

    def test_batch_span_processor_many_spans(self):
        """Test that no spans are lost when sending many spans"""
        spans_names_list = []

        my_exporter = MySpanExporter(
            destination=spans_names_list, max_export_batch_size=128
        )
        span_processor = export.BatchExportSpanProcessor(
            my_exporter,
            max_queue_size=256,
            max_export_batch_size=64,
            schedule_delay_millis=100,
        )

        for _ in range(4):
            for _ in range(256):
                _create_start_and_end_span("foo", span_processor)

            time.sleep(0.05)  # give some time for the exporter to upload spans

        span_processor.shutdown()
        self.assertEqual(len(spans_names_list), 1024)

    def test_batch_span_processor_scheduled_delay(self):
        """Test that spans are exported each schedule_delay_millis"""
        spans_names_list = []

        my_exporter = MySpanExporter(destination=spans_names_list)
        span_processor = export.BatchExportSpanProcessor(
            my_exporter, schedule_delay_millis=50
        )

        # create single span
        _create_start_and_end_span("foo", span_processor)

        time.sleep(0.05 + 0.02)
        # span should be already exported
        self.assertEqual(len(spans_names_list), 1)

        span_processor.shutdown()

    def test_batch_span_processor_parameters(self):
        # zero max_queue_size
        self.assertRaises(
            ValueError, export.BatchExportSpanProcessor, None, max_queue_size=0
        )

        # negative max_queue_size
        self.assertRaises(
            ValueError,
            export.BatchExportSpanProcessor,
            None,
            max_queue_size=-500,
        )

        # zero schedule_delay_millis
        self.assertRaises(
            ValueError,
            export.BatchExportSpanProcessor,
            None,
            schedule_delay_millis=0,
        )

        # negative schedule_delay_millis
        self.assertRaises(
            ValueError,
            export.BatchExportSpanProcessor,
            None,
            schedule_delay_millis=-500,
        )

        # zero max_export_batch_size
        self.assertRaises(
            ValueError,
            export.BatchExportSpanProcessor,
            None,
            max_export_batch_size=0,
        )

        # negative max_export_batch_size
        self.assertRaises(
            ValueError,
            export.BatchExportSpanProcessor,
            None,
            max_export_batch_size=-500,
        )

        # max_export_batch_size > max_queue_size:
        self.assertRaises(
            ValueError,
            export.BatchExportSpanProcessor,
            None,
            max_queue_size=256,
            max_export_batch_size=512,
        )
