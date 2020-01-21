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

from .base_context import Context


def current() -> Context:
    return _CONTEXT.current()


def new_context() -> Context:
    try:
        from .async_context import (  # pylint: disable=import-outside-toplevel
            AsyncRuntimeContext,
        )

        context = AsyncRuntimeContext()  # type: Context
    except ImportError:
        from .thread_local_context import (  # pylint: disable=import-outside-toplevel
            ThreadLocalRuntimeContext,
        )

        context = ThreadLocalRuntimeContext()  # type: Context
    return context


def merge_context_correlation(source: Context, dest: Context) -> Context:
    return dest.merge(source)


_CONTEXT = new_context()
