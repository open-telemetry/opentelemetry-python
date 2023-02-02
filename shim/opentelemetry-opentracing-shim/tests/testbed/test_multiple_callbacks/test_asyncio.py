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
import random

# pylint: disable=import-error
from ..otel_ot_shim_tracer import MockTracer
from ..testcase import OpenTelemetryTestCase
from ..utils import get_logger, stop_loop_when

random.seed()
logger = get_logger(__name__)


class TestAsyncio(OpenTelemetryTestCase):
    def setUp(self):  # pylint: disable=invalid-name
        self.tracer = MockTracer()
        self.loop = asyncio.get_event_loop()

    def test_main(self):
        # Need to run within a Task, as the scope manager depends
        # on Task.current_task()
        async def main_task():
            with self.tracer.start_active_span("parent"):
                tasks = self.submit_callbacks()
                await asyncio.gather(*tasks)

        self.loop.create_task(main_task())

        stop_loop_when(
            self.loop,
            lambda: len(self.tracer.finished_spans()) >= 4,
            timeout=5.0,
        )
        self.loop.run_forever()

        spans = self.tracer.finished_spans()
        self.assertEqual(len(spans), 4)
        self.assertNamesEqual(spans, ["task", "task", "task", "parent"])

        for idx in range(3):
            self.assertSameTrace(spans[idx], spans[-1])
            self.assertIsChildOf(spans[idx], spans[-1])

    async def task(self, interval, parent_span):
        logger.info("Starting task")

        with self.tracer.scope_manager.activate(parent_span, False):
            with self.tracer.start_active_span("task"):
                await asyncio.sleep(interval)

    def submit_callbacks(self):
        parent_span = self.tracer.scope_manager.active.span
        tasks = []
        for _ in range(3):
            interval = 0.1 + random.randint(200, 500) * 0.001
            task = self.loop.create_task(self.task(interval, parent_span))
            tasks.append(task)

        return tasks
