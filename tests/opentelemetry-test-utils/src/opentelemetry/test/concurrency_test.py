# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Helpers for tests that have to provoke a race rather than wait for one.

A data race in code guarded by a lock shows up only when two threads reach the
guarded region at the same moment, which a test cannot arrange by starting
threads and hoping. The two pieces here arrange it: ``run_with_many_threads``
holds every thread at a barrier and releases them together, and
``ConcurrencyTestBase`` shortens the interpreter's thread switch interval for
the duration of the test class so that a switch is likely to land inside the
guarded region.

Neither makes a race certain. A test built on them fails intermittently when
the code under test is broken, which is enough to catch a regression over many
runs and is not enough to prove a single run correct.
"""

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
        """Build the lock, the call counter and the mock to hand back.

        ``call_count`` starts at zero and is the number this class exists to
        make reliable. ``mock`` is the object ``__call__`` returns and is never
        called here. ``lock`` guards ``call_count`` and nothing else.
        """
        self.lock = threading.Lock()
        self.call_count = 0
        self.mock = Mock()

    def __call__(self, *args, **kwargs):
        """Count this call and return the shared ``Mock``.

        ``self.mock`` is returned but never called here, so its own
        ``call_count`` counts what callers did with the returned object and not
        calls to this ``MockFunc``. Assert on ``call_count``, which is the only
        count of the latter and the only one taken under the lock.

        Args:
            *args: Accepted and discarded, so any call signature works.
            **kwargs: Accepted and discarded for the same reason.

        Returns:
            The same ``Mock`` instance on every call, so a test can assert on
            what the caller did with the returned value.
        """
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
        """Shorten the interpreter thread switch interval for this class.

        The interval is process-wide, so every test running in the same
        interpreter is slowed while this class runs. ``tearDownClass`` puts the
        original value back.
        """
        super().setUpClass()
        # switch threads more often to increase chance of contention
        sys.setswitchinterval(1e-12)

    @classmethod
    def tearDownClass(cls) -> None:
        """Restore the thread switch interval read when this module was imported.

        ``orig_switch_interval`` is a class attribute evaluated at import time,
        so the value restored is the one in force before any test ran, not the
        one in force when ``setUpClass`` was called.
        """
        super().tearDownClass()
        sys.setswitchinterval(cls.orig_switch_interval)

    @staticmethod
    def run_with_many_threads(
        func_to_test: Callable[[], ReturnT],
        num_threads: int = 100,
    ) -> list[ReturnT]:
        """Util to run ``func_to_test`` in ``num_threads`` concurrently

        Every thread is started, then held at a barrier until all of them have
        arrived, then released at once. Holding them is what makes the calls
        overlap: without it the first threads would finish before the last ones
        started.

        Args:
            func_to_test: Called once per thread, with no arguments. It has to
                be safe to call concurrently with itself, since testing that is
                the point. An exception it raises propagates out of the thread
                and is printed by ``threading.excepthook`` rather than failing
                the test, and that thread then leaves ``None`` in its slot of
                the result list.
            num_threads: How many threads to run, which is also the number of
                calls and the size of the returned list. The barrier is sized to
                this number, so every thread has to arrive before any proceeds.

        Returns:
            A list of the return values, where position ``i`` holds the value
            returned by the ``i``-th thread. The order is the order the threads
            were created in, not the order they finished in.
        """

        barrier = threading.Barrier(num_threads)
        results: list[ReturnT | None] = [None] * num_threads

        def thread_start(idx: int) -> None:
            """Wait for every other thread, then call the function under test.

            Args:
                idx: Position in the result list to store the return value at.
                    Each thread gets its own, so the threads write to disjoint
                    slots and the list needs no lock.
            """
            nonlocal results
            # Get all threads here before releasing them to create contention
            barrier.wait()
            results[idx] = func_to_test()

        threads = [threading.Thread(target=partial(thread_start, i)) for i in range(num_threads)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        return results  # type: ignore
