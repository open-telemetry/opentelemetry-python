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

import asyncio
import contextlib
import functools
from typing import (
    Any,
    Awaitable,
    Callable,
    Coroutine,
    ParamSpec,
    TypeVar,
    cast,
    ParamSpecKwargs,
    ParamSpecArgs,
)

P = ParamSpec("P")
R = TypeVar("R")
A = ParamSpecArgs("ARGS")
K = ParamSpecKwargs("KWARGS")

class _AgnosticContextManager(
    contextlib.AbstractContextManager,
    contextlib.ContextDecorator,
):
    """A reimplementation of contextlib._GeneratorContextManager that supports decorating async functions.

    All credit goes to the CPython team for the original implementation.
    https://github.com/python/cpython/blob/3.12/Lib/contextlib.py
    """

    def __init__(self, func: Callable[P, R], args: A, kwds: K) -> None:
        """https://github.com/python/cpython/blob/3.12/Lib/contextlib.py#L104"""
        self.gen = func(*args, **kwds)
        self.func, self.args, self.kwds = func, args, kwds
        doc = getattr(func, "__doc__", None)
        if doc is None:
            doc = type(self).__doc__
        self.__doc__ = doc

    def _recreate_cm(self) -> "_AgnosticContextManager":
        """https://github.com/python/cpython/blob/3.12/Lib/contextlib.py#L122C9-L122C21"""
        return self.__class__(self.func, self.args, self.kwds)

    def __enter__(self):
        """https://github.com/python/cpython/blob/3.12/Lib/contextlib.py#L132"""
        del self.args, self.kwds, self.func
        try:
            return next(self.gen)
        except StopIteration:
            raise RuntimeError("generator didn't yield") from None

    def __exit__(self, typ, value, traceback):
        """https://github.com/python/cpython/blob/3.12/Lib/contextlib.py#L141"""
        if typ is None:
            try:
                next(self.gen)
            except StopIteration:
                return False
            raise RuntimeError("generator didn't stop")
        if value is None:
            value = typ()
        try:
            self.gen.throw(typ, value, traceback)
        except StopIteration as exc:
            return exc is not value
        except RuntimeError as exc:
            if exc is value:
                exc.__traceback__ = traceback
                return False
            if isinstance(value, StopIteration) and exc.__cause__ is value:
                exc.__traceback__ = traceback
                return False
            raise
        except BaseException as exc:
            if exc is not value:
                raise
            exc.__traceback__ = traceback
            return False
        raise RuntimeError("generator didn't stop after throw()")

    def __call__(self, func):
        """Mixing contextlib.ContextDecorator.__call__ and contextlib.AsyncContextDecorator.__call__

        https://github.com/python/cpython/blob/3.12/Lib/contextlib.py#L77
        https://github.com/python/cpython/blob/3.12/Lib/contextlib.py#L93
        """
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                with self._recreate_cm():
                    return await func(*args, **kwargs)

            return async_wrapper

        @functools.wraps(func)
        def wrapper(*args: list[Any], **kwargs: dict[str, Any]) -> Any:
            with self._recreate_cm():
                return func(*args, **kwargs)

        return wrapper


def _agnosticcontextmanager(func: Callable[P, R]) -> Callable[P, R]:
    @functools.wraps(func)
    def helper(*args, **kwds) -> Callable[P, R]:
        return _AgnosticContextManager(func, args, kwds)

    return helper
