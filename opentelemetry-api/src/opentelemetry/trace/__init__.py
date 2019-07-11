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
The OpenTelemetry tracing API describes the classes used to generate
distributed traces.

The :class:`.Tracer` class controls access to the execution context, and
manages span creation. Each operation in a trace is represented by a
:class:`.Span`, which records the start, end time, and metadata associated with
the operation.

This module provides abstract (i.e. unimplemented) classes required for
tracing, and a concrete no-op ``BlankSpan`` that allows applications to use the
API package alone without a supporting implementation.

The tracer supports creating spans that are "attached" or "detached" from the
context. By default, new spans are "attached" to the context in that they are
created as children of the currently active span, and the newly-created span
becomes the new active span::

    # TODO (#15): which module holds the global tracer?
    from opentelemetry.api.trace import tracer

    # Create a new root span, set it as the current span in context
    with tracer.start_span("parent"):
        # Attach a new child and update the current span
        with tracer.start_span("child"):
            do_work():
        # Close child span, set parent as current
    # Close parent span, set default span as current

When creating a span that's "detached" from the context the active span doesn't
change, and the caller is responsible for managing the span's lifetime::

    from opentelemetry.api.trace import tracer

    # Explicit parent span assignment
    span = tracer.create_span("child", parent=parent) as child:

    # The caller is responsible for starting and ending the span
    span.start()
    try:
        do_work(span=child)
    finally:
        span.end()

Applications should generally use a single global tracer, and use either
implicit or explicit context propagation consistently throughout.

.. versionadded:: 0.1.0
"""

from contextlib import contextmanager
import typing
from opentelemetry import loader


class Span:
    """A span represents a single operation within a trace."""

    def start(self) -> None:
        """Sets the current time as the span's start time.

        Each span represents a single operation. The span's start time is the
        wall time at which the operation started.

        Only the first call to `start` should modify the span, and
        implementations are free to ignore or raise on further calls.
        """

    def end(self) -> None:
        """Sets the current time as the span's end time.

        The span's end time is the wall time at which the operation finished.

        Only the first call to `end` should modify the span, and
        implementations are free to ignore or raise on further calls.
        """

    def get_context(self) -> 'SpanContext':
        """Gets the span's SpanContext.

        Get an immutable, serializable identifier for this span that can be
        used to create new child spans.

        Returns:
            A :class:`.SpanContext` with a copy of this span's immutable state.
        """


class TraceOptions(int):
    """A bitmask that represents options specific to the trace.

    The only supported option is the "recorded" flag (``0x01``). If set, this
    flag indicates that the trace may have been recorded upstream.

    See the `W3C Trace Context - Traceparent`_ spec for details.

    .. _W3C Trace Context - Traceparent:
        https://www.w3.org/TR/trace-context/#trace-flags
    """
    DEFAULT = 0x00
    RECORDED = 0x01

    @classmethod
    def get_default(cls) -> 'TraceOptions':
        return cls(cls.DEFAULT)


DEFAULT_TRACEOPTIONS = TraceOptions.get_default()


class TraceState(typing.Dict[str, str]):
    """A list of key-value pairs that carries system-specific config.

    Keys are strings of up to 256 characters containing only lowercase letters
    ``a-z``, digits ``0-9``, underscores ``_``, dashes ``-``, asterisks ``*``,
    and forward slashes ``/``.

    Values are strings of up to 256 printable ASCII RFC0020 characters (i.e.,
    the range ``0x20`` to ``0x7E``) except comma ``,`` and equals sign ``=``.

    See the `W3C Trace Context - Tracestate`_ spec for details.

    .. _W3C Trace Context - Tracestate:
        https://www.w3.org/TR/trace-context/#tracestate-field
    """

    @classmethod
    def get_default(cls) -> 'TraceState':
        return cls()


DEFAULT_TRACESTATE = TraceState.get_default()


class SpanContext:
    """The state of a Span to propagate between processes.

    This class includes the immutable attributes of a :class:`.Span` that must
    be propagated to a span's children and across process boundaries.

    Args:
        trace_id: The ID of the trace that this span belongs to.
        span_id: This span's ID.
        options: Trace options to propagate.
        state: Tracing-system-specific info to propagate.
    """

    def __init__(self,
                 trace_id: int,
                 span_id: int,
                 options: 'TraceOptions',
                 state: 'TraceState') -> None:
        self.trace_id = trace_id
        self.span_id = span_id
        self.options = options
        self.state = state

    def is_valid(self) -> bool:
        """Get whether this `SpanContext` is valid.

        A `SpanContext` is said to be invalid if its trace ID or span ID is
        invalid (i.e. ``0``).

        Returns:
            True if the `SpanContext` is valid, false otherwise.
        """


INVALID_SPAN_ID = 0
INVALID_TRACE_ID = 0
INVALID_SPAN_CONTEXT = SpanContext(INVALID_TRACE_ID, INVALID_SPAN_ID,
                                   DEFAULT_TRACEOPTIONS, DEFAULT_TRACESTATE)


class Tracer:
    """Handles span creation and in-process context propagation.

    This class provides methods for manipulating the context, creating spans,
    and controlling spans' lifecycles.
    """

    # Constant used to represent the current span being used as a parent.
    # This is the default behavior when creating spans.
    CURRENT_SPAN = Span()

    def get_current_span(self) -> 'Span':
        """Gets the currently active span from the context.

        If there is no current span, return a placeholder span with an invalid
        context.

        Returns:
            The currently active :class:`.Span`, or a placeholder span with an
            invalid :class:`.SpanContext`.
        """

    @contextmanager  # type: ignore
    def start_span(self,
                   name: str,
                   parent: typing.Union['Span', 'SpanContext'] = CURRENT_SPAN
                   ) -> typing.Iterator['Span']:
        """Context manager for span creation.

        Create a new span. Start the span and set it as the current span in
        this tracer's context.

        By default the current span will be used as parent, but an explicit
        parent can also be specified, either a `Span` or a `SpanContext`. If
        the specified value is `None`, the created span will be a root span.

        On exiting the context manager stop the span and set its parent as the
        current span.

        Example::

            with tracer.start_span("one") as parent:
                parent.add_event("parent's event")
                with tracer.start_span("two") as child:
                    child.add_event("child's event")
                    tracer.get_current_span()  # returns child
                tracer.get_current_span()      # returns parent
            tracer.get_current_span()          # returns previously active span

        This is a convenience method for creating spans attached to the
        tracer's context. Applications that need more control over the span
        lifetime should use :meth:`create_span` instead. For example::

            with tracer.start_span(name) as span:
                do_work()

        is equivalent to::

            span = tracer.create_span(name)
            with tracer.use_span(span):
                do_work()

        Args:
            name: The name of the span to be created.
            parent: The span's parent. Defaults to the current span.

        Yields:
            The newly-created span.
        """

    def create_span(self,
                    name: str,
                    parent: typing.Union['Span', 'SpanContext'] = CURRENT_SPAN
                    ) -> 'Span':
        """Creates a span.

        Creating the span does not start it, and should not affect the tracer's
        context. To start the span and update the tracer's context to make it
        the currently active span, see :meth:`use_span`.

        By default the current span will be used as parent, but an explicit
        parent can also be specified, either a Span or a SpanContext.
        If the specified value is `None`, the created span will be a root
        span.

        Applications that need to create spans detached from the tracer's
        context should use this method.

            with tracer.start_span(name) as span:
                do_work()

        This is equivalent to::

            span = tracer.create_span(name)
            with tracer.use_span(span):
                do_work()

        Args:
            name: The name of the span to be created.
            parent: The span's parent. Defaults to the current span.

        Returns:
            The newly-created span.
        """

    @contextmanager  # type: ignore
    def use_span(self, span: 'Span') -> typing.Iterator[None]:
        """Context manager for controlling a span's lifetime.

        Start the given span and set it as the current span in this tracer's
        context.

        On exiting the context manager stop the span and set its parent as the
        current span.

        Args:
            span: The span to start and make current.
        """


_TRACER: typing.Optional[Tracer] = None
_TRACER_FACTORY: typing.Optional[
    typing.Callable[[typing.Type[Tracer]], typing.Optional[Tracer]]] = None


def tracer() -> Tracer:
    """Gets the current global :class:`~.Tracer` object.

    If there isn't one set yet, a default will be loaded.
    """
    global _TRACER, _TRACER_FACTORY  # pylint:disable=global-statement

    if _TRACER is None:
        # pylint:disable=protected-access
        _TRACER = loader._load_impl(Tracer, _TRACER_FACTORY)
        del _TRACER_FACTORY

    return _TRACER


def set_preferred_tracer_implementation(
        factory: typing.Callable[
            [typing.Type[Tracer]], typing.Optional[Tracer]]
        ) -> None:
    """Set the factory to be used to create the tracer.

    See :mod:`opentelemetry.loader` for details.

    This function may not be called after a tracer is already loaded.

    Args:
        factory: Callback that should create a new :class:`Tracer` instance.
    """
    global _TRACER_FACTORY  # pylint:disable=global-statement

    if _TRACER:
        raise RuntimeError("Tracer already loaded.")

    _TRACER_FACTORY = factory
