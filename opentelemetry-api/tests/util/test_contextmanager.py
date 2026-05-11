# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import asyncio
import unittest
from collections.abc import Callable, Iterator

from opentelemetry.util._decorator import _agnosticcontextmanager


@_agnosticcontextmanager
def cm() -> Iterator[int]:
    yield 3


@_agnosticcontextmanager
def cm_call_when_done(f: Callable[[], None]) -> Iterator[int]:
    yield 3
    f()


class TestContextManager(unittest.TestCase):
    def test_sync_with(self):
        with cm() as val:
            self.assertEqual(val, 3)

    def test_decorate_sync_func(self):
        @cm()
        def sync_func(a: str) -> str:
            return a + a

        res = sync_func("a")
        self.assertEqual(res, "aa")

    def test_decorate_async_func(self):
        # Test that a universal context manager decorating an async function runs it's cleanup
        # code after the entire async function coroutine finishes. This silently fails when
        # using the normal @contextmanager decorator, which runs it's __exit__() after the
        # un-started coroutine is returned.
        #
        # To see this behavior, change cm_call_when_done() to
        # be decorated with @contextmanager.

        events = []

        @cm_call_when_done(lambda: events.append("cm_done"))
        async def async_func(a: str) -> str:
            events.append("start_async_func")
            await asyncio.sleep(0)
            events.append("finish_sleep")
            return a + a

        res = asyncio.run(async_func("a"))
        self.assertEqual(res, "aa")
        self.assertEqual(
            events, ["start_async_func", "finish_sleep", "cm_done"]
        )
