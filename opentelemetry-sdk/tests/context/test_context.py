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
from multiprocessing.dummy import Pool as ThreadPool

import unittest

from opentelemetry import trace as trace_api
from opentelemetry.sdk import trace
from opentelemetry.sdk.trace import export
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from opentelemetry.context import Context, merge_context_correlation
from opentelemetry.trace import tracer_source


class TestContext(unittest.TestCase):
    URLS = [
        "test_span1",
        "test_span2",
        "test_span3",
        "test_span4",
        "test_span5",
    ]

    def do_some_work(self, name):
        # try:
        with self.tracer.start_as_current_span(name) as span:
            pass
        # except Exception as err:
        #     print(err)

    def setUp(self):
        self.tracer_source = trace.TracerSource()
        self.tracer = self.tracer_source.get_tracer(__name__)
        self.memory_exporter = InMemorySpanExporter()
        span_processor = export.SimpleExportSpanProcessor(self.memory_exporter)
        self.tracer_source.add_span_processor(span_processor)

    def do_work(self):
        Context.set_value("say-something", "bar")

    def test_context(self):
        assert Context.value("say-something") is None
        empty_context = Context.current()
        Context.set_value("say-something", "foo")
        assert Context.value("say-something") == "foo"
        second_context = Context.current()

        self.do_work()
        assert Context.value("say-something") == "bar"
        third_context = Context.current()

        assert empty_context.get("say-something") is None
        assert second_context.get("say-something") == "foo"
        assert third_context.get("say-something") == "bar"

    def test_merge(self):
        self.maxDiff = None
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
        self.assertEqual(Context.current().contents.get("name"), "first")
        self.assertTrue(Context.current().contents.get("somebool"))
        self.assertEqual(Context.current().contents.get("key"), "value")
        self.assertEqual(
            Context.current().contents.get("otherkey"), "othervalue"
        )
        self.assertEqual(
            Context.current().contents.get("anotherkey"), "anothervalue"
        )

    def test_propagation(self):
        pass

    def test_with_futures(self):
        with self.tracer.start_as_current_span("futures_test"):
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=5
            ) as executor:
                # Start the load operations and mark each future with its URL
                future_to_url = {
                    executor.submit(
                        contextvars.copy_context().run, self.do_some_work, url,
                    ): url
                    for url in self.URLS
                }
                for future in concurrent.futures.as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        data = future.result()
                    except Exception as exc:
                        print("%r generated an exception: %s" % (url, exc))
                    else:
                        data_len = 0
                        if data:
                            data_len = len(data)
                        print("%r page is %d bytes" % (url, data_len))

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
                Context.with_current_context(self.do_some_work), self.URLS,
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
