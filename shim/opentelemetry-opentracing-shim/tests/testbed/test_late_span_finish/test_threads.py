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

import time
from concurrent.futures import ThreadPoolExecutor

# pylint: disable=import-error
from ..otel_ot_shim_tracer import MockTracer
from ..testcase import OpenTelemetryTestCase


class TestThreads(OpenTelemetryTestCase):
    def setUp(self):  # pylint: disable=invalid-name
        self.tracer = MockTracer()
        self.executor = ThreadPoolExecutor(max_workers=3)

    def test_main(self):
        # Create a Span and use it as (explicit) parent of a pair of subtasks.
        parent_span = self.tracer.start_span("parent")
        self.submit_subtasks(parent_span)

        # Wait for the threadpool to be done.
        self.executor.shutdown(True)

        # Late-finish the parent Span now.
        parent_span.finish()

        spans = self.tracer.finished_spans()
        self.assertEqual(len(spans), 3)
        self.assertNamesEqual(spans, ["task1", "task2", "parent"])

        for idx in range(2):
            self.assertSameTrace(spans[idx], spans[-1])
            self.assertIsChildOf(spans[idx], spans[-1])
            self.assertTrue(spans[idx].end_time <= spans[-1].end_time)

    # Fire away a few subtasks, passing a parent Span whose lifetime
    # is not tied at all to the children.
    def submit_subtasks(self, parent_span):
        def task(name, interval):
            with self.tracer.scope_manager.activate(parent_span, False):
                with self.tracer.start_active_span(name):
                    time.sleep(interval)

        self.executor.submit(task, "task1", 0.1)
        self.executor.submit(task, "task2", 0.3)
