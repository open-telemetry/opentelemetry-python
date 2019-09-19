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

import unittest

from opentelemetry.sdk import trace
from opentelemetry.sdk.trace import export


class TestSimpleExportSpanProcessor(unittest.TestCase):
    def test_simple_span_processor(self):
        class MySpanExporter(export.SpanExporter):
            def __init__(self, destination):
                self.destination = destination

            def export(self, spans: trace.Span) -> export.SpanExportResult:
                self.destination.extend(span.name for span in spans)
                return export.SpanExportResult.SUCCESS

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


class TestBatchExportSpanProcessor(unittest.TestCase):
    def test_batch_span_processor(self):
        class MySpanExporter(export.SpanExporter):
            def __init__(self, destination):
                self.destination = destination

            def export(self, spans: trace.Span) -> export.SpanExportResult:
                self.destination.extend(span.name for span in spans)
                return export.SpanExportResult.SUCCESS

        tracer = trace.Tracer()

        spans_names_list = []

        my_exporter = MySpanExporter(destination=spans_names_list)
        span_processor = export.BatchExportSpanProcessor(my_exporter)
        tracer.add_span_processor(span_processor)

        with tracer.start_span("foo"):
            with tracer.start_span("bar"):
                with tracer.start_span("xxx"):
                    pass

        # call shutdown on specific span processor
        # TODO: this call is missing in the tracer
        span_processor.shutdown()
        self.assertListEqual(["xxx", "bar", "foo"], spans_names_list)

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
