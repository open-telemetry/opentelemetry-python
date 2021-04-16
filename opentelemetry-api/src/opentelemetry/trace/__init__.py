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

"""
The OpenTelemetry tracing API describes the classes used to generate
distributed traces.

The :class:`.Tracer` class controls access to the execution context, and
manages span creation. Each operation in a trace is represented by a
:class:`.Span`, which records the start, end time, and metadata associated with
the operation.

This module provides abstract (i.e. unimplemented) classes required for
tracing, and a concrete no-op :class:`.NonRecordingSpan` that allows applications
to use the API package alone without a supporting implementation.

To get a tracer, you need to provide the package name from which you are
calling the tracer APIs to OpenTelemetry by calling `TracerProvider.get_tracer`
with the calling module name and the version of your package.

The tracer supports creating spans that are "attached" or "detached" from the
context. New spans are "attached" to the context in that they are
created as children of the currently active span, and the newly-created span
can optionally become the new active span::

    from opentelemetry import trace

    tracer = trace.get_tracer(__name__)

    # Create a new root span, set it as the current span in context
    with tracer.start_as_current_span("parent"):
        # Attach a new child and update the current span
        with tracer.start_as_current_span("child"):
            do_work():
        # Close child span, set parent as current
    # Close parent span, set default span as current

When creating a span that's "detached" from the context the active span doesn't
change, and the caller is responsible for managing the span's lifetime::

    # Explicit parent span assignment is done via the Context
    from opentelemetry.trace import set_span_in_context

    context = set_span_in_context(parent)
    child = tracer.start_span("child", context=context)

    try:
        do_work(span=child)
    finally:
        child.end()

Applications should generally use a single global TracerProvider, and use
either implicit or explicit context propagation consistently throughout.

.. versionadded:: 0.1.0
.. versionchanged:: 0.3.0
    `TracerProvider` was introduced and the global ``tracer`` getter was
    replaced by ``tracer_provider``.
.. versionchanged:: 0.5.0
    ``tracer_provider`` was replaced by `get_tracer_provider`,
    ``set_preferred_tracer_provider_implementation`` was replaced by
    `set_tracer_provider`.
"""


import os
from abc import ABC, abstractmethod
from contextlib import contextmanager
from enum import Enum
from logging import getLogger
from typing import Iterator, Optional, Sequence, cast

from opentelemetry import context as context_api
from opentelemetry.context.context import Context
from opentelemetry.environment_variables import OTEL_PYTHON_TRACER_PROVIDER
from opentelemetry.trace.propagation import (
    SPAN_KEY,
    get_current_span,
    set_span_in_context,
)
from opentelemetry.trace.span import (
    DEFAULT_TRACE_OPTIONS,
    DEFAULT_TRACE_STATE,
    INVALID_SPAN,
    INVALID_SPAN_CONTEXT,
    INVALID_SPAN_ID,
    INVALID_TRACE_ID,
    NonRecordingSpan,
    Span,
    SpanContext,
    TraceFlags,
    TraceState,
    format_span_id,
    format_trace_id,
)
from opentelemetry.trace.status import Status, StatusCode
from opentelemetry.util import types
from opentelemetry.util._providers import _load_provider

logger = getLogger(__name__)


class _LinkBase(ABC):
    def __init__(self, context: "SpanContext") -> None:
        self._context = context

    @property
    def context(self) -> "SpanContext":
        return self._context

    @property
    @abstractmethod
    def attributes(self) -> types.Attributes:
        pass


class Link(_LinkBase):
    """A link to a `Span`.

    Args:
        context: `SpanContext` of the `Span` to link to.
        attributes: Link's attributes.
    """

    def __init__(
        self,
        context: "SpanContext",
        attributes: types.Attributes = None,
    ) -> None:
        super().__init__(context)
        self._attributes = attributes

    @property
    def attributes(self) -> types.Attributes:
        return self._attributes


_Links = Optional[Sequence[Link]]


class SpanKind(Enum):
    """Specifies additional details on how this span relates to its parent span.

    Note that this enumeration is experimental and likely to change. See
    https://github.com/open-telemetry/opentelemetry-specification/pull/226.
    """

    #: Default value. Indicates that the span is used internally in the
    # application.
    INTERNAL = 0

    #: Indicates that the span describes an operation that handles a remote
    # request.
    SERVER = 1

    #: Indicates that the span describes a request to some remote service.
    CLIENT = 2

    #: Indicates that the span describes a producer sending a message to a
    #: broker. Unlike client and server, there is usually no direct critical
    #: path latency relationship between producer and consumer spans.
    PRODUCER = 3

    #: Indicates that the span describes a consumer receiving a message from a
    #: broker. Unlike client and server, there is usually no direct critical
    #: path latency relationship between producer and consumer spans.
    CONSUMER = 4


class TracerProvider(ABC):
    @abstractmethod
    def get_tracer(
        self,
        instrumenting_module_name: str,
        instrumenting_library_version: str = "",
    ) -> "Tracer":
        """Returns a `Tracer` for use by the given instrumentation library.

        For any two calls it is undefined whether the same or different
        `Tracer` instances are returned, even for different library names.

        This function may return different `Tracer` types (e.g. a no-op tracer
        vs.  a functional tracer).

        Args:
            instrumenting_module_name: The name of the instrumenting module
                (usually just ``__name__``).

                This should *not* be the name of the module that is
                instrumented but the name of the module doing the instrumentation.
                E.g., instead of ``"requests"``, use
                ``"opentelemetry.instrumentation.requests"``.

            instrumenting_library_version: Optional. The version string of the
                instrumenting library.  Usually this should be the same as
                ``pkg_resources.get_distribution(instrumenting_library_name).version``.
        """


class _DefaultTracerProvider(TracerProvider):
    """The default TracerProvider, used when no implementation is available.

    All operations are no-op.
    """

    def get_tracer(
        self,
        instrumenting_module_name: str,
        instrumenting_library_version: str = "",
    ) -> "Tracer":
        # pylint:disable=no-self-use,unused-argument
        return _DefaultTracer()


class ProxyTracerProvider(TracerProvider):
    def get_tracer(
        self,
        instrumenting_module_name: str,
        instrumenting_library_version: str = "",
    ) -> "Tracer":
        if _TRACER_PROVIDER:
            return _TRACER_PROVIDER.get_tracer(
                instrumenting_module_name, instrumenting_library_version
            )
        return ProxyTracer(
            instrumenting_module_name, instrumenting_library_version
        )


class Tracer(ABC):
    """Handles span creation and in-process context propagation.

    This class provides methods for manipulating the context, creating spans,
    and controlling spans' lifecycles.
    """

    @abstractmethod
    def start_span(
        self,
        name: str,
        context: Optional[Context] = None,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: types.Attributes = None,
        links: _Links = None,
        start_time: Optional[int] = None,
        record_exception: bool = True,
        set_status_on_exception: bool = True,
    ) -> "Span":
        """Starts a span.

        Create a new span. Start the span without setting it as the current
        span in the context. To start the span and use the context in a single
        method, see :meth:`start_as_current_span`.

        By default the current span in the context will be used as parent, but an
        explicit context can also be specified, by passing in a `Context` containing
        a current `Span`. If there is no current span in the global `Context` or in
        the specified context, the created span will be a root span.

        The span can be used as a context manager. On exiting the context manager,
        the span's end() method will be called.

        Example::

            # trace.get_current_span() will be used as the implicit parent.
            # If none is found, the created span will be a root instance.
            with tracer.start_span("one") as child:
                child.add_event("child's event")

        Args:
            name: The name of the span to be created.
            context: An optional Context containing the span's parent. Defaults to the
                global context.
            kind: The span's kind (relationship to parent). Note that is
                meaningful even if there is no parent.
            attributes: The span's attributes.
            links: Links span to other spans
            start_time: Sets the start time of a span
            record_exception: Whether to record any exceptions raised within the
                context as error event on the span.
            set_status_on_exception: Only relevant if the returned span is used
                in a with/context manager. Defines wether the span status will
                be automatically set to ERROR when an uncaught exception is
                raised in the span with block. The span status won't be set by
                this mechanism if it was previously set manually.

        Returns:
            The newly-created span.
        """

    @contextmanager  # type: ignore
    @abstractmethod
    def start_as_current_span(
        self,
        name: str,
        context: Optional[Context] = None,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: types.Attributes = None,
        links: _Links = None,
        start_time: Optional[int] = None,
        record_exception: bool = True,
        set_status_on_exception: bool = True,
        end_on_exit: bool = True,
    ) -> Iterator["Span"]:
        """Context manager for creating a new span and set it
        as the current span in this tracer's context.

        Exiting the context manager will call the span's end method,
        as well as return the current span to it's previous value by
        returning to the previous context.

        Example::

            with tracer.start_as_current_span("one") as parent:
                parent.add_event("parent's event")
                with trace.start_as_current_span("two") as child:
                    child.add_event("child's event")
                    trace.get_current_span()  # returns child
                trace.get_current_span()      # returns parent
            trace.get_current_span()          # returns previously active span

        This is a convenience method for creating spans attached to the
        tracer's context. Applications that need more control over the span
        lifetime should use :meth:`start_span` instead. For example::

            with tracer.start_as_current_span(name) as span:
                do_work()

        is equivalent to::

            span = tracer.start_span(name)
            with opentelemetry.trace.use_span(span, end_on_exit=True):
                do_work()

        Args:
            name: The name of the span to be created.
            context: An optional Context containing the span's parent. Defaults to the
                global context.
            kind: The span's kind (relationship to parent). Note that is
                meaningful even if there is no parent.
            attributes: The span's attributes.
            links: Links span to other spans
            start_time: Sets the start time of a span
            record_exception: Whether to record any exceptions raised within the
                context as error event on the span.
            set_status_on_exception: Only relevant if the returned span is used
                in a with/context manager. Defines wether the span status will
                be automatically set to ERROR when an uncaught exception is
                raised in the span with block. The span status won't be set by
                this mechanism if it was previously set manually.
            end_on_exit: Whether to end the span automatically when leaving the
                context manager.

        Yields:
            The newly-created span.
        """


class ProxyTracer(Tracer):
    # pylint: disable=W0222,signature-differs
    def __init__(
        self,
        instrumenting_module_name: str,
        instrumenting_library_version: str,
    ):
        self._instrumenting_module_name = instrumenting_module_name
        self._instrumenting_library_version = instrumenting_library_version
        self._real_tracer: Optional[Tracer] = None
        self._noop_tracer = _DefaultTracer()

    @property
    def _tracer(self) -> Tracer:
        if self._real_tracer:
            return self._real_tracer

        if _TRACER_PROVIDER:
            self._real_tracer = _TRACER_PROVIDER.get_tracer(
                self._instrumenting_module_name,
                self._instrumenting_library_version,
            )
            return self._real_tracer
        return self._noop_tracer

    def start_span(self, *args, **kwargs) -> Span:  # type: ignore
        return self._tracer.start_span(*args, **kwargs)  # type: ignore

    def start_as_current_span(self, *args, **kwargs) -> Span:  # type: ignore
        return self._tracer.start_as_current_span(*args, **kwargs)  # type: ignore


class _DefaultTracer(Tracer):
    """The default Tracer, used when no Tracer implementation is available.

    All operations are no-op.
    """

    def start_span(
        self,
        name: str,
        context: Optional[Context] = None,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: types.Attributes = None,
        links: _Links = None,
        start_time: Optional[int] = None,
        record_exception: bool = True,
        set_status_on_exception: bool = True,
    ) -> "Span":
        # pylint: disable=unused-argument,no-self-use
        return INVALID_SPAN

    @contextmanager  # type: ignore
    def start_as_current_span(
        self,
        name: str,
        context: Optional[Context] = None,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: types.Attributes = None,
        links: _Links = None,
        start_time: Optional[int] = None,
        record_exception: bool = True,
        set_status_on_exception: bool = True,
        end_on_exit: bool = True,
    ) -> Iterator["Span"]:
        # pylint: disable=unused-argument,no-self-use
        yield INVALID_SPAN


_TRACER_PROVIDER = None
_PROXY_TRACER_PROVIDER = None


def get_tracer(
    instrumenting_module_name: str,
    instrumenting_library_version: str = "",
    tracer_provider: Optional[TracerProvider] = None,
) -> "Tracer":
    """Returns a `Tracer` for use by the given instrumentation library.

    This function is a convenience wrapper for
    opentelemetry.trace.TracerProvider.get_tracer.

    If tracer_provider is omitted the current configured one is used.
    """
    if tracer_provider is None:
        tracer_provider = get_tracer_provider()
    return tracer_provider.get_tracer(
        instrumenting_module_name, instrumenting_library_version
    )


def set_tracer_provider(tracer_provider: TracerProvider) -> None:
    """Sets the current global :class:`~.TracerProvider` object.

    This can only be done once, a warning will be logged if any furter attempt
    is made.
    """
    global _TRACER_PROVIDER  # pylint: disable=global-statement

    if _TRACER_PROVIDER is not None:
        logger.warning("Overriding of current TracerProvider is not allowed")
        return

    _TRACER_PROVIDER = tracer_provider


def get_tracer_provider() -> TracerProvider:
    """Gets the current global :class:`~.TracerProvider` object."""
    # pylint: disable=global-statement
    global _TRACER_PROVIDER
    global _PROXY_TRACER_PROVIDER

    if _TRACER_PROVIDER is None:
        # if a global tracer provider has not been set either via code or env
        # vars, return a proxy tracer provider
        if OTEL_PYTHON_TRACER_PROVIDER not in os.environ:
            if not _PROXY_TRACER_PROVIDER:
                _PROXY_TRACER_PROVIDER = ProxyTracerProvider()
            return _PROXY_TRACER_PROVIDER

        _TRACER_PROVIDER = cast(  # type: ignore
            "TracerProvider",
            _load_provider(OTEL_PYTHON_TRACER_PROVIDER, "tracer_provider"),
        )
    return _TRACER_PROVIDER


@contextmanager  # type: ignore
def use_span(
    span: Span,
    end_on_exit: bool = False,
    record_exception: bool = True,
    set_status_on_exception: bool = True,
) -> Iterator[Span]:
    """Takes a non-active span and activates it in the current context.

    Args:
        span: The span that should be activated in the current context.
        end_on_exit: Whether to end the span automatically when leaving the
            context manager scope.
        record_exception: Whether to record any exceptions raised within the
            context as error event on the span.
        set_status_on_exception: Only relevant if the returned span is used
            in a with/context manager. Defines wether the span status will
            be automatically set to ERROR when an uncaught exception is
            raised in the span with block. The span status won't be set by
            this mechanism if it was previously set manually.
    """
    try:
        token = context_api.attach(context_api.set_value(SPAN_KEY, span))
        try:
            yield span
        finally:
            context_api.detach(token)

    except Exception as exc:  # pylint: disable=broad-except
        if isinstance(span, Span) and span.is_recording():
            # Record the exception as an event
            if record_exception:
                span.record_exception(exc)

            # Set status in case exception was raised
            if set_status_on_exception:
                span.set_status(
                    Status(
                        status_code=StatusCode.ERROR,
                        description="{}: {}".format(type(exc).__name__, exc),
                    )
                )
        raise

    finally:
        if end_on_exit:
            span.end()


__all__ = [
    "DEFAULT_TRACE_OPTIONS",
    "DEFAULT_TRACE_STATE",
    "INVALID_SPAN",
    "INVALID_SPAN_CONTEXT",
    "INVALID_SPAN_ID",
    "INVALID_TRACE_ID",
    "NonRecordingSpan",
    "Link",
    "Span",
    "SpanContext",
    "SpanKind",
    "TraceFlags",
    "TraceState",
    "TracerProvider",
    "Tracer",
    "format_span_id",
    "format_trace_id",
    "get_current_span",
    "get_tracer",
    "get_tracer_provider",
    "set_tracer_provider",
    "set_span_in_context",
    "use_span",
    "Status",
    "StatusCode",
]
