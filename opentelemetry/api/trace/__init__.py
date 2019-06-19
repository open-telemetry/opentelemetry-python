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

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator


class Tracer(object):
    """Handles span creation and in-process context propagation.

    This class provides methods for manipulating the context, creating spans,
    and controlling spans' lifecycles.
    """

    def get_current_span(self) -> Span:
        """Gets the currently active span from the context.

        If there is no current span, return a placeholder span with an invalid
        context.

        Returns:
            The currently active :class:`.Span`, or a placeholder span with an
            invalid :class:`.SpanContext`.
        """
        raise NotImplementedError


    @contextmanager
    def start_span(self, name: str, parent: Span) -> Iterator[Span]:
        """Context manager for span creation.

        Create a new child of the current span, or create a root span if no
        current span exists. Start the span and set it as the current span in
        this tracer's context.

        On exiting the context manager stop the span and set its parent as the
        current span.

        Example::

            with tracer.start_span("one") as parent:
                parent.add_event("parent's event")
                with tracer.start_span("two") as child:
                    child.add_event("child's event")
                    tracer.get_current_span()  # returns child
                tracer.get_current_span()      # returns parent
            tracer.get_current_span()          # returns the previously active span

        This is a convenience method for creating spans attached to the
        tracer's context. Applications that need more control over the span
        lifetime should use :meth:`create_span` instead. For example::

            with tracer.start_span(name) as span:
                do_work()

        is equivalent to::

            span = tracer.create_span(name, parent=tracer.get_current_span())
            with tracer.use_span(span):
                do_work()

        Args:
            name: The name of the span to be created.
            parent: The span's parent.

        Yields:
            The newly-created span.
        """
        raise NotImplementedError

    def create_span(self, name: str, parent: Span) -> Span:
        """Creates a new child span of the given parent.

        Creating the span does not start it, and should not affect the tracer's
        context. To start the span and update the tracer's context to make it
        the currently active span, see :meth:`use_span`.

        Applications that need to explicitly set spans' parents or create spans
        detached from the tracer's context should use this method.

            with tracer.start_span(name) as span:
                do_work()

        This is equivalent to::

            span = tracer.create_span(name, parent=tracer.get_current_span())
            with tracer.use_span(span):
                do_work()

        Args:
            name: The name of the span to be created.
            parent: The span's parent.

        Returns:
            The newly-created span.
        """
        raise NotImplementedError

    @contextmanager
    def use_span(self, span: Span) -> Iterator[None]:
        """Context manager for controlling a span's lifetime.

        Start the given span and set it as the current span in this tracer's
        context.

        On exiting the context manager stop the span and set its parent as the
        current span.

        Args:
            span: The span to start and make current.
        """
        raise NotImplementedError


class Span(object):
    """A span represents a single operation within a trace."""

    def start(self) -> None:
        """Sets the current time as the span's start time.

        Each span represents a single operation. The span's start time is the
        wall time at which the operation started.

        Only the first call to ``start`` should modify the span, and
        implementations are free to ignore or raise on further calls.
        """
        raise NotImplementedError

    def end(self) -> None:
        """Sets the current time as the span's end time.

        The span's end time is the wall time at which the operation finished.

        Only the first call to ``end`` should modify the span, and
        implementations are free to ignore or raise on further calls.
        """
        raise NotImplementedError

    def get_context(self) -> SpanContext:
        """Gets the span's SpanContext.

        Get an immutable, serializable identifier for this span that can be
        used to create new child spans.

        Returns:
            A :class:`.SpanContext` with a copy of this span's immutable state.
        """
        raise NotImplementedError


class SpanContext(object):
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
                 trace_id: str,
                 span_id: str,
                 options: TraceOptions,
                 state: TraceState) -> None:
        pass


# TODO
class TraceOptions(int):
    pass


# TODO
class TraceState(dict):
    pass
