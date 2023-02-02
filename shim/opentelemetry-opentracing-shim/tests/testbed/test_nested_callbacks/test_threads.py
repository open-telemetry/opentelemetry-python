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

from concurrent.futures import ThreadPoolExecutor

# pylint: disable=import-error
from ..otel_ot_shim_tracer import MockTracer
from ..testcase import OpenTelemetryTestCase
from ..utils import await_until


class TestThreads(OpenTelemetryTestCase):
    def setUp(self):  # pylint: disable=invalid-name
        self.tracer = MockTracer()
        self.executor = ThreadPoolExecutor(max_workers=3)

    def tearDown(self):  # pylint: disable=invalid-name
        self.executor.shutdown(False)

    def test_main(self):
        # Start a Span and let the callback-chain
        # finish it when the task is done
        with self.tracer.start_active_span("one", finish_on_close=False):
            self.submit()

        # Cannot shutdown the executor and wait for the callbacks
        # to be run, as in such case only the first will be executed,
        # and the rest will get canceled.
        await_until(lambda: len(self.tracer.finished_spans()) == 1, 5)

        spans = self.tracer.finished_spans()
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].name, "one")

        for idx in range(1, 4):
            self.assertEqual(
                spans[0].attributes.get(f"key{idx}", None), str(idx)
            )

    def submit(self):
        span = self.tracer.scope_manager.active.span

        def task1():
            with self.tracer.scope_manager.activate(span, False):
                span.set_tag("key1", "1")

                def task2():
                    with self.tracer.scope_manager.activate(span, False):
                        span.set_tag("key2", "2")

                        def task3():
                            with self.tracer.scope_manager.activate(
                                span, True
                            ):
                                span.set_tag("key3", "3")

                        self.executor.submit(task3)

                self.executor.submit(task2)

        self.executor.submit(task1)
