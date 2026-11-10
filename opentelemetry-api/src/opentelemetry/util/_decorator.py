# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Context manager that also decorates coroutine functions correctly.

:func:`_agnosticcontextmanager` replaces :func:`contextlib.contextmanager` for
the helpers that both wrap a block and decorate a function, such as
``Tracer.start_as_current_span``. Decorating a coroutine function with the
standard decorator closes the block when the coroutine object is created
rather than when it finishes, which reports a near-zero duration. The manager
here awaits the coroutine inside the block instead.
"""

import contextlib
import functools
import inspect
from collections.abc import Callable, Iterator
from typing import Generic, ParamSpec, TypeVar

V = TypeVar("V")
R = TypeVar("R")  # Return type
Pargs = TypeVar("Pargs")  # Generic type for arguments
Pkwargs = TypeVar("Pkwargs")  # Generic type for arguments
P = ParamSpec("P")  # Generic type for all arguments


class _AgnosticContextManager(
    contextlib._GeneratorContextManager[R],
    Generic[R],
):  # pylint: disable=protected-access
    """Context manager that can decorate both async and sync functions.

    This is an overridden version of the contextlib._GeneratorContextManager
    class that will decorate async functions with an async context manager
    to end the span AFTER the entire async function coroutine finishes.

    Else it will report near zero spans durations for async functions.

    We are overriding the contextlib._GeneratorContextManager class as
    reimplementing it is a lot of code to maintain and this class (even if it's
    marked as protected) doesn't seems like to be evolving a lot.

    For more information, see:
    https://github.com/open-telemetry/opentelemetry-python/pull/3633
    """

    def __enter__(self) -> R:
        """Enter the context and return the value the generator yielded.

        This overrides the inherited method so that the declared return type is
        ``R`` rather than :data:`~typing.Any`.

        Returns:
            The value yielded by the wrapped generator, for example the span
            started by ``Tracer.start_as_current_span``.

        Raises:
            RuntimeError: If the wrapped generator returned without yielding.
        """
        del self.args, self.kwds, self.func  # type: ignore
        try:
            return next(self.gen)  # type: ignore
        except StopIteration:
            raise RuntimeError("generator didn't yield") from None

    def __call__(self, func: V) -> V:  # pyright: ignore [reportIncompatibleMethodOverride]
        """Decorate ``func`` so each call runs inside a fresh context.

        A coroutine function is wrapped so that the context closes once the
        coroutine finishes rather than once it is created. Any other callable
        is handed to the inherited implementation.

        Args:
            func: The callable to decorate. Both a coroutine function and an
                ordinary function are accepted.

        Returns:
            A wrapper around ``func`` with the same signature.
        """
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)  # type: ignore
            async def async_wrapper(*args: Pargs, **kwargs: Pkwargs) -> R:  # pyright: ignore [reportInvalidTypeVarUse]
                """Await the coroutine with a fresh context manager entered.

                Args:
                    *args: Positional arguments forwarded to the coroutine.
                    **kwargs: Keyword arguments forwarded to the coroutine.

                Returns:
                    Whatever the coroutine returns.
                """
                with self._recreate_cm():  # type: ignore
                    return await func(*args, **kwargs)  # type: ignore

            return async_wrapper  # type: ignore
        return super().__call__(func)  # type: ignore


def _agnosticcontextmanager(
    func: "Callable[P, Iterator[R]]",
) -> "Callable[P, _AgnosticContextManager[R]]":
    """Turn a generator function into a context manager and a decorator.

    This behaves like :func:`contextlib.contextmanager`, except that the
    returned object decorates a coroutine function correctly. See
    :class:`_AgnosticContextManager`.

    Args:
        func: A generator function yielding exactly once. The value it yields
            becomes the result of the ``with`` statement.

    Returns:
        A callable with the same signature as ``func`` that returns an
        :class:`_AgnosticContextManager` usable as a context manager or as a
        decorator.
    """

    @functools.wraps(func)
    def helper(*args: Pargs, **kwargs: Pkwargs) -> _AgnosticContextManager[R]:  # pyright: ignore [reportInvalidTypeVarUse]
        """Build the context manager for one call of the wrapped function.

        Args:
            *args: Positional arguments forwarded to the generator function.
            **kwargs: Keyword arguments forwarded to the generator function.

        Returns:
            A context manager bound to this particular set of arguments.
        """
        return _AgnosticContextManager(func, args, kwargs)  # pyright: ignore [reportArgumentType]

    # Ignoring the type to keep the original signature of the function
    return helper  # type: ignore[return-value]
