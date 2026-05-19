# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import sys
import threading
import unittest
from collections.abc import Callable
from functools import partial
from typing import TypeVar
from unittest.mock import Mock

ReturnT = TypeVar("ReturnT")


class MockFunc:
    """A thread safe mock function

    Use this as part of your mock if you want to count calls across multiple
    threads.
    """

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.call_count = 0
        self.mock = Mock()

    def __call__(self, *args, **kwargs):
        with self.lock:
            self.call_count += 1
        return self.mock


class ConcurrencyTestBase(unittest.TestCase):
    """Test base class/mixin for tests of concurrent code

    This test class calls ``sys.setswitchinterval(1e-12)`` to try to create more
    contention while running tests that use many threads. It also provides
    ``run_with_many_threads`` to run some test code in many threads
    concurrently.
    """

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
    ) -> list[ReturnT]:
        """Util to run ``func_to_test`` in ``num_threads`` concurrently"""

        barrier = threading.Barrier(num_threads)
        results: list[ReturnT | None] = [None] * num_threads

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
