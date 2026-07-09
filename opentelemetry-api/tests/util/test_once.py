# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry.test.concurrency_test import ConcurrencyTestBase, MockFunc
from opentelemetry.util._once import Once


class TestOnce(ConcurrencyTestBase):
    def test_once_single_thread(self):
        once_func = MockFunc()
        once = Once()

        self.assertEqual(once_func.call_count, 0)

        # first call should run
        called = once.do_once(once_func)  # type: ignore[reportArgumentType]
        self.assertTrue(called)
        self.assertEqual(once_func.call_count, 1)

        # subsequent calls do nothing
        called = once.do_once(once_func)  # type: ignore[reportArgumentType]
        self.assertFalse(called)
        self.assertEqual(once_func.call_count, 1)

    def test_once_many_threads(self):
        once_func = MockFunc()
        once = Once()

        def run_concurrently() -> bool:
            return once.do_once(once_func)  # type: ignore[reportArgumentType]

        results = self.run_with_many_threads(run_concurrently, num_threads=100)

        self.assertEqual(once_func.call_count, 1)

        # check that only one of the threads got True
        self.assertEqual(results.count(True), 1)
