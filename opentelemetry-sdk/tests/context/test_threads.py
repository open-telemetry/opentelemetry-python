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
from multiprocessing.dummy import Pool as ThreadPool

from opentelemetry import context
from opentelemetry.sdk import trace
from opentelemetry.sdk.context.threadlocal_context import ThreadLocalContext
from opentelemetry.sdk.trace import export
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)


class TestThreads(unittest.TestCase):
    span_names = [
        "test_span1",
        "test_span2",
        "test_span3",
        "test_span4",
        "test_span5",
    ]

    def do_work(self, name="default"):
        with self.tracer.start_as_current_span(name):
            context.set_value("say-something", "bar")

    def setUp(self):
        self.previous_context = context.get_current()
        context.set_current(ThreadLocalContext())
        self.tracer_source = trace.TracerSource()
        self.tracer = self.tracer_source.get_tracer(__name__)
        self.memory_exporter = InMemorySpanExporter()
        span_processor = export.SimpleExportSpanProcessor(self.memory_exporter)
        self.tracer_source.add_span_processor(span_processor)

    def tearDown(self):
        context.set_current(self.previous_context)

    def test_with_threads(self):
        with self.tracer.start_as_current_span("threads_test"):
            pool = ThreadPool(5)  # create a thread pool
            pool.map(
                context.with_current_context(self.do_work), self.span_names
            )
            pool.close()
            pool.join()
        span_list = self.memory_exporter.get_finished_spans()
        span_names_list = [span.name for span in span_list]
        expected = [
            "test_span1",
            "test_span2",
            "test_span3",
            "test_span4",
            "test_span5",
            "threads_test",
        ]
        self.assertCountEqual(span_names_list, expected)
        span_names_list.sort()
        expected.sort()
        self.assertListEqual(span_names_list, expected)
        expected_parent = next(
            span for span in span_list if span.name == "threads_test"
        )
        # FIXME
        for span in span_list:
            if span is expected_parent:
                continue
            self.assertEqual(span.parent, expected_parent)
