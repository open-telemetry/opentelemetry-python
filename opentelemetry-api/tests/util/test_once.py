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

import sys
import threading
import unittest
from functools import partial

from opentelemetry.util._once import Once


# Can't use Mock because its call count is not thread safe
class MockFunc:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.call_count = 0

    def __call__(self) -> None:
        with self.lock:
            self.call_count += 1


class TestOnce(unittest.TestCase):
    orig_switch_interval = sys.getswitchinterval()

    @classmethod
    def setUpClass(cls) -> None:
        # switch threads more often to increase chance of contention
        sys.setswitchinterval(1e-12)

    @classmethod
    def tearDownClass(cls) -> None:
        sys.setswitchinterval(cls.orig_switch_interval)

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
        num_threads = 100
        once_func = MockFunc()
        once = Once()
        barrier = threading.Barrier(num_threads)
        results = [False] * num_threads

        def thread_start(idx: int) -> None:
            nonlocal results
            # Get all threads here before releasing them to create contention
            barrier.wait()
            called = once.do_once(once_func)
            if called:
                print(f"\t\tCalled {called}")
            results[idx] = called

        threads = [
            threading.Thread(target=partial(thread_start, i))
            for i in range(num_threads)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(once_func.call_count, 1)

        # check that only one of the threads got True
        self.assertEqual(results.count(True), 1)
