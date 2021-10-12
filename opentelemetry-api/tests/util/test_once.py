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

from opentelemetry.test.concurrency_test import ConcurrencyTestBase, MockFunc
from opentelemetry.util._once import Once


class TestOnce(ConcurrencyTestBase):
    def test_once_single_thread(self):
        once_func = MockFunc()
        once = Once()

        self.assertEqual(once_func.call_count, 0)

        # first call should run
        called = once.do_once(once_func)
        self.assertTrue(called)
        self.assertEqual(once_func.call_count, 1)

        # subsequent calls do nothing
        called = once.do_once(once_func)
        self.assertFalse(called)
        self.assertEqual(once_func.call_count, 1)

    def test_once_many_threads(self):
        once_func = MockFunc()
        once = Once()

        def run_concurrently() -> bool:
            return once.do_once(once_func)

        results = self.run_with_many_threads(run_concurrently, num_threads=100)

        self.assertEqual(once_func.call_count, 1)

        # check that only one of the threads got True
        self.assertEqual(results.count(True), 1)
