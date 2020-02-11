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

import asyncio
import unittest
from unittest.mock import patch

from opentelemetry import context as context_api
from opentelemetry.sdk import trace
from opentelemetry.sdk.context.contextvars_context import (
    ContextVarsRuntimeContext,
)
from opentelemetry.sdk.trace import export
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

try:
    import contextvars  # pylint: disable=unused-import
except ImportError:
    raise unittest.SkipTest("contextvars not available")


_SPAN_NAMES = [
    "test_span1",
    "test_span2",
    "test_span3",
    "test_span4",
    "test_span5",
]


def stop_loop_when(loop, cond_func, timeout=5.0):
    """Registers a periodic callback that stops the loop when cond_func() == True.
    Compatible with both Tornado and asyncio.
    """
    if cond_func() or timeout <= 0.0:
        loop.stop()
        return

    timeout -= 0.1
    loop.call_later(0.1, stop_loop_when, loop, cond_func, timeout)


def do_work() -> None:
    context_api.set_current(context_api.set_value("say-something", "bar"))


class TestAsyncio(unittest.TestCase):
    @asyncio.coroutine
    def task(self, name):
        with self.tracer.start_as_current_span(name):
            context_api.set_value("say-something", "bar")

    def submit_another_task(self, name):
        self.loop.create_task(self.task(name))

    def setUp(self):
        self.previous_context = context_api.get_current()
        context_api.set_current(context_api.Context())
        self.tracer_source = trace.TracerSource()
        self.tracer = self.tracer_source.get_tracer(__name__)
        self.memory_exporter = InMemorySpanExporter()
        span_processor = export.SimpleExportSpanProcessor(self.memory_exporter)
        self.tracer_source.add_span_processor(span_processor)
        self.loop = asyncio.get_event_loop()

    def tearDown(self):
        context_api.set_current(self.previous_context)

    @patch(
        "opentelemetry.context._CONTEXT_RUNTIME", ContextVarsRuntimeContext()
    )
    def test_with_asyncio(self):
        with self.tracer.start_as_current_span("asyncio_test"):
            for name in _SPAN_NAMES:
                self.submit_another_task(name)

            stop_loop_when(
                self.loop,
                lambda: len(self.memory_exporter.get_finished_spans()) >= 5,
                timeout=5.0,
            )
            self.loop.run_forever()
        span_list = self.memory_exporter.get_finished_spans()
        span_names_list = [span.name for span in span_list]
        expected = [
            "test_span1",
            "test_span2",
            "test_span3",
            "test_span4",
            "test_span5",
            "asyncio_test",
        ]
        self.assertCountEqual(span_names_list, expected)
        span_names_list.sort()
        expected.sort()
        self.assertListEqual(span_names_list, expected)
        expected_parent = next(
            span for span in span_list if span.name == "asyncio_test"
        )
        for span in span_list:
            if span is expected_parent:
                continue
            self.assertEqual(span.parent, expected_parent)


class TestContextVarsContext(unittest.TestCase):
    def setUp(self):
        self.previous_context = context_api.get_current()

    def tearDown(self):
        context_api.set_current(self.previous_context)

    @patch(
        "opentelemetry.context._CONTEXT_RUNTIME", ContextVarsRuntimeContext()
    )
    def test_context(self):
        self.assertIsNone(context_api.get_value("say-something"))
        empty_context = context_api.get_current()
        second_context = context_api.set_value("say-something", "foo")
        self.assertEqual(second_context.get_value("say-something"), "foo")

        do_work()
        self.assertEqual(context_api.get_value("say-something"), "bar")
        third_context = context_api.get_current()

        self.assertIsNone(empty_context.get_value("say-something"))
        self.assertEqual(second_context.get_value("say-something"), "foo")
        self.assertEqual(third_context.get_value("say-something"), "bar")

    @patch(
        "opentelemetry.context._CONTEXT_RUNTIME", ContextVarsRuntimeContext()
    )
    def test_set_value(self):
        first = context_api.set_value("a", "yyy")
        second = context_api.set_value("a", "zzz")
        third = context_api.set_value("a", "---", first)
        self.assertEqual("yyy", context_api.get_value("a", context=first))
        self.assertEqual("zzz", context_api.get_value("a", context=second))
        self.assertEqual("---", context_api.get_value("a", context=third))
        self.assertEqual(None, context_api.get_value("a"))
