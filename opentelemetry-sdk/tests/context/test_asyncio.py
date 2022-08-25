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

import asyncio
import unittest
from unittest.mock import patch

from opentelemetry import context
from opentelemetry.context.contextvars_context import ContextVarsRuntimeContext
from opentelemetry.sdk import trace
from opentelemetry.sdk.trace import export
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

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


class TestAsyncio(unittest.TestCase):
    async def task(self, name):
        with self.tracer.start_as_current_span(name):
            context.set_value("say", "bar")

    def submit_another_task(self, name):
        self.loop.create_task(self.task(name))

    def setUp(self):
        self.token = context.attach(context.Context())
        self.tracer_provider = trace.TracerProvider()
        self.tracer = self.tracer_provider.get_tracer(__name__)
        self.memory_exporter = InMemorySpanExporter()
        span_processor = export.SimpleSpanProcessor(self.memory_exporter)
        self.tracer_provider.add_span_processor(span_processor)
        self.loop = asyncio.get_event_loop()

    def tearDown(self):
        context.detach(self.token)

    @patch(
        "opentelemetry.context._RUNTIME_CONTEXT", ContextVarsRuntimeContext()
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
            self.assertEqual(span.parent, expected_parent.context)
