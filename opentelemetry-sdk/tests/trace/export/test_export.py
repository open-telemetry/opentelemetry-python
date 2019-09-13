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
