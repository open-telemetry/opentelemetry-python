# Copyright 2019, OpenTelemetry Authors
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
import typing
from contextvars import ContextVar
from copy import copy
from sys import version_info

from opentelemetry.context.context import Context

if (3, 5, 3) <= version_info < (3, 7):
    import aiocontextvars  # pylint:disable=unused-import

elif (3, 4) < version_info <= (3, 5, 2):

    # This is copied and pasted from:
    # https://github.com/fantix/aiocontextvars/issues/88#issuecomment-522276290

    import asyncio
    import asyncio.coroutines
    import asyncio.futures
    import concurrent.futures

    if not hasattr(asyncio, "_get_running_loop"):
        # noinspection PyCompatibility
        # pylint:disable=protected-access
        import asyncio.events
        from threading import local as threading_local

        if not hasattr(asyncio.events, "_get_running_loop"):

            class _RunningLoop(threading_local):
                _loop = None

            _running_loop = _RunningLoop()

            def _get_running_loop():
                return _running_loop._loop

            def set_running_loop(loop):  # noqa: F811
                _running_loop._loop = loop

            def _get_event_loop():
                current_loop = _get_running_loop()
                if current_loop is not None:
                    return current_loop
                return asyncio.events.get_event_loop_policy().get_event_loop()

            asyncio.events.get_event_loop = _get_event_loop
            asyncio.events._get_running_loop = _get_running_loop
            asyncio.events._set_running_loop = set_running_loop

        asyncio._get_running_loop = asyncio.events._get_running_loop
        asyncio._set_running_loop = asyncio.events._set_running_loop

    # It needs only to be imported to activate the patching of the contextvars
    # backport (see the comment in setup.py)
    # noinspection PyUnresolvedReferences
    import aiocontextvars

    def _run_coroutine_threadsafe(coro, loop):
        """
        Patch to create task in the same thread instead of in the callback.
        This ensures that contextvars get copied. Python 3.7 copies contextvars
        without this.
        """
        if not asyncio.coroutines.iscoroutine(coro):
            raise TypeError("A coroutine object is required")
        future = concurrent.futures.Future()
        task = asyncio.ensure_future(coro, loop=loop)

        def callback() -> None:
            try:
                # noinspection PyProtectedMember,PyUnresolvedReferences
                # pylint:disable=protected-access
                asyncio.futures._chain_future(task, future)
            except Exception as exc:
                if future.set_running_or_notify_cancel():
                    future.set_exception(exc)
                raise

        loop.call_soon_threadsafe(callback)
        return future

    asyncio.run_coroutine_threadsafe = _run_coroutine_threadsafe


class ContextVarsContext(Context):
    def __init__(self) -> None:
        self._contextvars = {}  # type: typing.Dict[str, ContextVar[object]]

    def set_value(self, key: str, value: "object") -> None:
        """Set a value in this context"""
        if key not in self._contextvars.keys():
            self._contextvars[key] = ContextVar(key)

        self._contextvars[key].set(value)

    def get_value(self, key: str) -> "object":
        """Get a value from this context"""
        if key in self._contextvars:
            try:
                return self._contextvars[key].get()
            except LookupError:
                pass
        return None

    def remove_value(self, key: str) -> None:
        """Remove a value from this context"""
        if key in self._contextvars.keys():
            self._contextvars.pop(key)

    def copy(self) -> Context:
        """Return a copy of this context"""

        context_copy = ContextVarsContext()

        for key, value in self._contextvars.items():
            context_copy.set_value(key, copy(value))

        return context_copy


__all__ = ["ContextVarsContext"]
