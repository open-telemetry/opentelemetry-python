# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""The immutable context mapping and the runtime that stores it.

A :class:`Context` carries the values that travel with the current execution,
such as the active span and the current baggage. It is a read-only
:class:`dict`, so adding a value produces a new :class:`Context` rather than
changing the existing one, which is what makes a context safe to share between
concurrent tasks.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextvars import Token


class Context(dict[str, object]):
    """An immutable mapping from context key to value.

    Every mutating method of :class:`dict` is overridden to raise
    :exc:`ValueError`. Build a new :class:`Context` with
    :func:`opentelemetry.context.set_value` instead of modifying one in place,
    and read from it with :func:`opentelemetry.context.get_value`.
    """

    def __setitem__(self, key: str, value: object) -> None:
        """Reject assignment of a single key.

        Args:
            key: The context key that would have been set.
            value: The value that would have been stored.

        Raises:
            ValueError: Always, because a context is immutable.
        """
        raise ValueError

    def __delitem__(self, key: str) -> None:
        """Reject deletion of a single key.

        Args:
            key: The context key that would have been removed.

        Raises:
            ValueError: Always, because a context is immutable.
        """
        raise ValueError

    def setdefault(self, key: str, default: object = None) -> object:
        """Reject insertion of a default value.

        Args:
            key: The context key that would have been looked up.
            default: The value that would have been stored if ``key`` were
                absent.

        Returns:
            Never returns.

        Raises:
            ValueError: Always, because a context is immutable.
        """
        raise ValueError

    def pop(self, key: str, *args: object) -> object:
        """Reject removal of a key.

        Args:
            key: The context key that would have been removed.
            *args: An optional default to return when ``key`` is absent, as
                accepted by :meth:`dict.pop`.

        Returns:
            Never returns.

        Raises:
            ValueError: Always, because a context is immutable.
        """
        raise ValueError

    def popitem(self) -> tuple[str, object]:
        """Reject removal of an arbitrary pair.

        Returns:
            Never returns.

        Raises:
            ValueError: Always, because a context is immutable.
        """
        raise ValueError

    def clear(self) -> None:
        """Reject removal of every key.

        Raises:
            ValueError: Always, because a context is immutable.
        """
        raise ValueError

    def update(self, *args: object, **kwargs: object) -> None:
        """Reject a bulk update.

        Args:
            *args: A mapping or iterable of pairs, as accepted by
                :meth:`dict.update`.
            **kwargs: Further pairs that would have been stored.

        Raises:
            ValueError: Always, because a context is immutable.
        """
        raise ValueError

    def __ior__(self, other: object) -> Context:
        """Reject an in-place merge with ``other``.

        Args:
            other: The mapping that would have been merged in.

        Returns:
            Never returns.

        Raises:
            ValueError: Always, because a context is immutable.
        """
        raise ValueError


class _RuntimeContext(ABC):
    """The RuntimeContext interface provides a wrapper for the different
    mechanisms that are used to propagate context in Python.
    Implementations can be made available via entry_points and
    selected through environment variables.
    """

    @abstractmethod
    def attach(self, context: Context) -> Token[Context]:
        """Sets the current `Context` object. Returns a
        token that can be used to reset to the previous `Context`.

        Args:
            context: The Context to set.

        Returns:
            A token to pass to :meth:`detach` to restore the context that was
            current before this call.
        """

    @abstractmethod
    def get_current(self) -> Context:
        """Returns the current `Context` object.

        Returns:
            The context attached to the current execution, or an empty
            :class:`Context` when nothing has been attached.
        """

    @abstractmethod
    def detach(self, token: Token[Context]) -> None:
        """Resets Context to a previous value

        Args:
            token: A reference to a previous Context.
        """


__all__ = ["Context"]
