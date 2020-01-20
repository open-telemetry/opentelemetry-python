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


"""
The OpenTelemetry context module provides abstraction layer on top of
thread-local storage and contextvars. The long term direction is to switch to
contextvars provided by the Python runtime library.

A global object ``Context`` is provided to access all the context related
functionalities::

    >>> from opentelemetry.context import Context
    >>> Context.foo = 1
    >>> Context.foo = 2
    >>> Context.foo
    2

When explicit thread is used, a helper function
``Context.with_current_context`` can be used to carry the context across
threads::

    from threading import Thread
    from opentelemetry.context import Context

    def work(name):
        print('Entering worker:', Context)
        Context.operation_id = name
        print('Exiting worker:', Context)

    if __name__ == '__main__':
        print('Main thread:', Context)
        Context.operation_id = 'main'

        print('Main thread:', Context)

        # by default context is not propagated to worker thread
        thread = Thread(target=work, args=('foo',))
        thread.start()
        thread.join()

        print('Main thread:', Context)

        # user can propagate context explicitly
        thread = Thread(
            target=Context.with_current_context(work),
            args=('bar',),
        )
        thread.start()
        thread.join()

        print('Main thread:', Context)

Here goes another example using thread pool::

    import time
    import threading

    from multiprocessing.dummy import Pool as ThreadPool
    from opentelemetry.context import Context

    _console_lock = threading.Lock()

    def println(msg):
        with _console_lock:
            print(msg)

    def work(name):
        println('Entering worker[{}]: {}'.format(name, Context))
        Context.operation_id = name
        time.sleep(0.01)
        println('Exiting worker[{}]: {}'.format(name, Context))

    if __name__ == "__main__":
        println('Main thread: {}'.format(Context))
        Context.operation_id = 'main'
        pool = ThreadPool(2)  # create a thread pool with 2 threads
        pool.map(Context.with_current_context(work), [
            'bear',
            'cat',
            'dog',
            'horse',
            'rabbit',
        ])
        pool.close()
        pool.join()
        println('Main thread: {}'.format(Context))

Here goes a simple demo of how async could work in Python 3.7+::

    import asyncio

    from opentelemetry.context import Context

    class Span(object):
        def __init__(self, name):
            self.name = name
            self.parent = Context.current_span

        def __repr__(self):
            return ('{}(name={}, parent={})'
                    .format(
                        type(self).__name__,
                        self.name,
                        self.parent,
                    ))

        async def __aenter__(self):
            Context.current_span = self

        async def __aexit__(self, exc_type, exc, tb):
            Context.current_span = self.parent

    async def main():
        print(Context)
        async with Span('foo'):
            print(Context)
            await asyncio.sleep(0.1)
            async with Span('bar'):
                print(Context)
                await asyncio.sleep(0.1)
            print(Context)
            await asyncio.sleep(0.1)
        print(Context)

    if __name__ == '__main__':
        asyncio.run(main())
"""

import typing
from contextlib import contextmanager

from .base_context import BaseRuntimeContext

__all__ = ["Context"]

try:
    from .async_context import AsyncRuntimeContext

    _CONTEXT = AsyncRuntimeContext()  # type: BaseRuntimeContext
except ImportError:
    from .thread_local_context import ThreadLocalRuntimeContext

    _CONTEXT = ThreadLocalRuntimeContext()


class Context:
    def __init__(self) -> None:
        self.snapshot = {}

    def get(self, key: str) -> typing.Optional["object"]:
        return self.snapshot.get(key)

    @classmethod
    def value(
        cls, key: str, context: typing.Optional["Context"] = None
    ) -> typing.Optional["object"]:
        """
        To access the local state of an concern, the Context API
        provides a function which takes a context and a key as input,
        and returns a value.
        """
        if context:
            return context.get(key)

        if cls.current():
            return cls.current().get(key)
        return None

    @classmethod
    def set_value(cls, key: str, value: "object") -> "Context":
        """
        To record the local state of a cross-cutting concern, the
        Context API provides a function which takes a context, a
        key, and a value as input, and returns an updated context
        which contains the new value.

        Args:
            key:
            value:
        """
        setattr(_CONTEXT, key, value)
        return cls.current()

    @classmethod
    def current(cls) -> "Context":
        """
        To access the context associated with program execution,
        the Context API provides a function which takes no arguments
        and returns a Context.
        """
        context = Context()
        context.snapshot = _CONTEXT.snapshot()
        return context

    @classmethod
    def set_current(cls, context: "Context") -> None:
        """
        To associate a context with program execution, the Context
        API provides a function which takes a Context.
        """
        _CONTEXT.apply(context.snapshot)

    @classmethod
    @contextmanager
    def use(cls, **kwargs: typing.Dict[str, object]) -> typing.Iterator[None]:
        snapshot = Context.current()
        for key in kwargs:
            _CONTEXT[key] = kwargs[key]
        yield
        Context.set_current(snapshot)

    @classmethod
    def suppress_instrumentation(cls) -> "object":
        return _CONTEXT.suppress_instrumentation

    @classmethod
    def with_current_context(
        cls, func: typing.Callable[..., "object"]
    ) -> typing.Callable[..., "object"]:
        """Capture the current context and apply it to the provided func.
        """

        caller_context = _CONTEXT.snapshot()

        def call_with_current_context(
            *args: "object", **kwargs: "object"
        ) -> "object":
            try:
                backup_context = _CONTEXT.snapshot()
                _CONTEXT.apply(caller_context)
                return func(*args, **kwargs)
            finally:
                _CONTEXT.apply(backup_context)

        return call_with_current_context

    def apply(self, ctx: "Context") -> None:
        for key in ctx.snapshot:
            self.snapshot[key] = ctx.snapshot[key]


def merge_context_correlation(source: Context, dest: Context) -> Context:
    dest.apply(source)
    return dest
