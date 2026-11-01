# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Runtime context backed by :mod:`contextvars`.

This is the only runtime context implementation shipped with the API. Storing
the current :class:`~opentelemetry.context.Context` in a
:class:`~contextvars.ContextVar` gives each thread and each task its own view,
so a span started in one task does not become current in another. A generator
is not included: a generator runs in the context of whoever resumes it, so a
value the generator attaches stays visible to its caller.
"""

from __future__ import annotations

from contextvars import ContextVar, Token

from opentelemetry.context.context import Context, _RuntimeContext


class ContextVarsRuntimeContext(_RuntimeContext):
    """An implementation of the RuntimeContext interface which wraps ContextVar under
    the hood. This is the preferred implementation for usage with Python 3.5+
    """

    _CONTEXT_KEY = "current_context"

    def __init__(self) -> None:
        """Create the backing :class:`~contextvars.ContextVar`.

        The variable starts out holding an empty
        :class:`~opentelemetry.context.Context`.
        """
        self._current_context = ContextVar(self._CONTEXT_KEY, default=Context())

    def attach(self, context: Context) -> Token[Context]:
        """Sets the current `Context` object. Returns a
        token that can be used to reset to the previous `Context`.

        Args:
            context: The Context to set.

        Returns:
            A token to pass to :meth:`detach` to restore the context that was
            current before this call.
        """
        return self._current_context.set(context)

    def get_current(self) -> Context:
        """Returns the current `Context` object.

        Returns:
            The context attached to the current execution, or an empty
            :class:`~opentelemetry.context.Context` when nothing has been
            attached.
        """
        return self._current_context.get()

    def detach(self, token: Token[Context]) -> None:
        """Resets Context to a previous value

        Args:
            token: A reference to a previous Context.

        Raises:
            ValueError: When ``token`` came from a different
                :class:`ContextVarsRuntimeContext` instance, since each one
                owns its own :class:`~contextvars.ContextVar`.
            RuntimeError: When ``token`` has already been passed to this
                method once.
        """
        self._current_context.reset(token)


__all__ = ["ContextVarsRuntimeContext"]
