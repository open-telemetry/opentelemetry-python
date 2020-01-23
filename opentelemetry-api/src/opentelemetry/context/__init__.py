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

import threading
import typing
from contextlib import contextmanager

from .base_context import Context, Slot

try:
    from .async_context import (
        AsyncRuntimeContext,
        ContextVarSlot,
    )

    _context_class = AsyncRuntimeContext  # pylint: disable=invalid-name
    _slot_class = ContextVarSlot  # pylint: disable=invalid-name
except ImportError:
    from .thread_local_context import (
        ThreadLocalRuntimeContext,
        ThreadLocalSlot,
    )

    _context_class = ThreadLocalRuntimeContext  # pylint: disable=invalid-name
    _slot_class = ThreadLocalSlot  # pylint: disable=invalid-name

_slots = {}  # type: typing.Dict[str, 'Slot']
_lock = threading.Lock()


def _register_slot(name: str, default: "object" = None) -> Slot:
    """Register a context slot with an optional default value.

    :type name: str
    :param name: The name of the context slot.

    :type default: object
    :param name: The default value of the slot, can be a value or lambda.

    :returns: The registered slot.
    """
    with _lock:
        if name not in _slots:
            _slots[name] = _slot_class(name, default)  # type: Slot
        return _slots[name]


def set_value(
    name: str, val: "object", context: typing.Optional[Context] = None,
) -> Context:
    """
    To record the local state of a cross-cutting concern, the
    Context API provides a function which takes a context, a
    key, and a value as input, and returns an updated context
    which contains the new value.

    Args:
        name: name of the entry to set
        value: value of the entry to set
        context: a context to copy, if None, the current context is used
    """
    # Function inside the module that performs the action on the current context
    # or in the passsed one based on the context object
    if context:
        ret = Context()
        ret.snapshot = dict((n, v) for n, v in context.snapshot.items())
        ret.snapshot[name] = val
        return ret

    # update value on current context:
    slot = _register_slot(name)
    slot.set(val)
    return current()


def value(name: str, context: Context = None) -> typing.Optional["object"]:
    """
    To access the local state of an concern, the Context API
    provides a function which takes a context and a key as input,
    and returns a value.

    Args:
        name: name of the entry to retrieve
        context: a context from which to retrieve the value, if None, the current context is used
    """
    if context:
        return context.value(name)

    # get context from current context
    if name in _slots:
        return _slots[name].get()
    return None


def current() -> Context:
    """
    To access the context associated with program execution,
    the Context API provides a function which takes no arguments
    and returns a Context.
    """
    ret = Context()
    for key, slot in _slots.items():
        ret.snapshot[key] = slot.get()

    return ret


def set_current(context: Context) -> None:
    """
    To associate a context with program execution, the Context
    API provides a function which takes a Context.
    """
    _slots.clear()  # remove current data

    for key, val in context.snapshot.items():
        slot = _register_slot(key)
        slot.set(val)


@contextmanager
def use(**kwargs: typing.Dict[str, object]) -> typing.Iterator[None]:
    snapshot = current()
    for key in kwargs:
        set_value(key, kwargs[key])
    yield
    set_current(snapshot)


def new_context() -> Context:
    return _context_class()


def merge_context_correlation(source: Context, dest: Context) -> Context:
    ret = Context()

    for key in dest.snapshot:
        ret.snapshot[key] = dest.snapshot[key]

    for key in source.snapshot:
        ret.snapshot[key] = source.snapshot[key]
    return ret
