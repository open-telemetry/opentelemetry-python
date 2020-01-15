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

import concurrent.futures
import contextvars
import unittest
from multiprocessing.dummy import Pool as ThreadPool

from opentelemetry.context import Context, merge_context_correlation
from opentelemetry.sdk import trace
from opentelemetry.sdk.trace import export
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)


def do_work():
    Context.set_value("say-something", "bar")


class TestContext(unittest.TestCase):
    spans = [
        "test_span1",
        "test_span2",
        "test_span3",
        "test_span4",
        "test_span5",
    ]

    def do_some_work(self, name):
        with self.tracer.start_as_current_span(name):
            pass

    def setUp(self):
        self.tracer_source = trace.TracerSource()
        self.tracer = self.tracer_source.get_tracer(__name__)
        self.memory_exporter = InMemorySpanExporter()
        span_processor = export.SimpleExportSpanProcessor(self.memory_exporter)
        self.tracer_source.add_span_processor(span_processor)

    def test_context(self):
        self.assertIsNone(Context.value("say-something"))
        empty_context = Context.current()
        Context.set_value("say-something", "foo")
        self.assertEqual(Context.value("say-something"), "foo")
        second_context = Context.current()

        do_work()
        self.assertEqual(Context.value("say-something"), "bar")
        third_context = Context.current()

        self.assertIsNone(empty_context.get("say-something"))
        self.assertEqual(second_context.get("say-something"), "foo")
        self.assertEqual(third_context.get("say-something"), "bar")

    def test_merge(self):
        Context.set_value("name", "first")
        Context.set_value("somebool", True)
        Context.set_value("key", "value")
        Context.set_value("otherkey", "othervalue")
        src_ctx = Context.current()

        Context.set_value("name", "second")
        Context.set_value("somebool", False)
        Context.set_value("anotherkey", "anothervalue")
        dst_ctx = Context.current()

        Context.set_current(merge_context_correlation(src_ctx, dst_ctx))
        self.assertEqual(Context.current().get("name"), "first")
        self.assertTrue(Context.current().get("somebool"))
        self.assertEqual(Context.current().get("key"), "value")
        self.assertEqual(Context.current().get("otherkey"), "othervalue")
        self.assertEqual(Context.current().get("anotherkey"), "anothervalue")

    def test_propagation(self):
        pass

    def test_with_futures(self):
        with self.tracer.start_as_current_span("futures_test"):
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=5
            ) as executor:
                # Start the load operations
                for span in self.spans:
                    executor.submit(
                        contextvars.copy_context().run,
                        self.do_some_work,
                        span,
                    )

        span_list = self.memory_exporter.get_finished_spans()
        spans_names_list = [span.name for span in span_list]
        self.assertListEqual(
            [
                "test_span1",
                "test_span2",
                "test_span3",
                "test_span4",
                "test_span5",
                "futures_test",
            ],
            spans_names_list,
        )

    def test_with_threads(self):
        with self.tracer.start_as_current_span("threads_test"):
            pool = ThreadPool(5)  # create a thread pool
            pool.map(
                Context.with_current_context(self.do_some_work), self.spans,
            )
            pool.close()
            pool.join()
        span_list = self.memory_exporter.get_finished_spans()
        spans_names_list = [span.name for span in span_list]
        self.assertListEqual(
            [
                "test_span1",
                "test_span2",
                "test_span3",
                "test_span4",
                "test_span5",
                "threads_test",
            ],
            spans_names_list,
        )
