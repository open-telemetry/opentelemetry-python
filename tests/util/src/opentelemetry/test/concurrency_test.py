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
from typing import Callable, List, Optional, TypeVar
from unittest.mock import Mock

ReturnT = TypeVar("ReturnT")


# Can't use Mock directly because its call count is not thread safe
class MockFunc:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.call_count = 0
        self.mock = Mock()

    def __call__(self, *args, **kwargs):
        with self.lock:
            self.call_count += 1
        return self.mock


class ConcurrencyTestBase(unittest.TestCase):
    orig_switch_interval = sys.getswitchinterval()

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        # switch threads more often to increase chance of contention
        sys.setswitchinterval(1e-12)

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        sys.setswitchinterval(cls.orig_switch_interval)

    @staticmethod
    def run_with_many_threads(
        func_to_test: Callable[[], ReturnT],
        num_threads: int = 100,
    ) -> List[ReturnT]:
        barrier = threading.Barrier(num_threads)
        results: List[Optional[ReturnT]] = [None] * num_threads

        def thread_start(idx: int) -> None:
            nonlocal results
            # Get all threads here before releasing them to create contention
            barrier.wait()
            results[idx] = func_to_test()

        threads = [
            threading.Thread(target=partial(thread_start, i))
            for i in range(num_threads)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        return results  # type: ignore
