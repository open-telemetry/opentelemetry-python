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
tracing, and a concrete no-op :class:`.DefaultSpan` that allows applications
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

    # Explicit parent span assignment
    child = tracer.start_span("child", parent=parent)

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

__all__ = [
    "DEFAULT_TRACE_OPTIONS",
    "DEFAULT_TRACE_STATE",
    "INVALID_SPAN",
    "INVALID_SPAN_CONTEXT",
    "INVALID_SPAN_ID",
    "INVALID_TRACE_ID",
    "DefaultSpan",
    "DefaultTracer",
    "DefaultTracerProvider",
    "LazyLink",
    "Link",
    "LinkBase",
    "ParentSpan",
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
]

import abc
import enum
import types as python_types
import typing
from contextlib import contextmanager
from logging import getLogger

from opentelemetry.configuration import Configuration
from opentelemetry.trace.propagation import (
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
    DefaultSpan,
    Span,
    SpanContext,
    TraceFlags,
    TraceState,
    format_span_id,
    format_trace_id,
)
from opentelemetry.trace.status import Status
from opentelemetry.util import _load_trace_provider, types

logger = getLogger(__name__)

# TODO: quarantine
ParentSpan = typing.Optional[typing.Union["Span", "SpanContext"]]


class LinkBase(abc.ABC):
    def __init__(self, context: "SpanContext") -> None:
        self._context = context

    @property
    def context(self) -> "SpanContext":
        return self._context

    @property
    @abc.abstractmethod
    def attributes(self) -> types.Attributes:
        pass


class Link(LinkBase):
    """A link to a `Span`.

    Args:
        context: `SpanContext` of the `Span` to link to.
        attributes: Link's attributes.
    """

    def __init__(
        self, context: "SpanContext", attributes: types.Attributes = None,
    ) -> None:
        super().__init__(context)
        self._attributes = attributes

    @property
    def attributes(self) -> types.Attributes:
        return self._attributes


class LazyLink(LinkBase):
    """A lazy link to a `Span`.

    Args:
        context: `SpanContext` of the `Span` to link to.
        link_formatter: Callable object that returns the attributes of the
            Link.
    """

    def __init__(
        self,
        context: "SpanContext",
        link_formatter: types.AttributesFormatter,
    ) -> None:
        super().__init__(context)
        self._link_formatter = link_formatter

    @property
    def attributes(self) -> types.Attributes:
        return self._link_formatter()


class SpanKind(enum.Enum):
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


class TracerProvider(abc.ABC):
    @abc.abstractmethod
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
                ``"opentelemetry.ext.requests"``.

            instrumenting_library_version: Optional. The version string of the
                instrumenting library.  Usually this should be the same as
                ``pkg_resources.get_distribution(instrumenting_library_name).version``.
        """


class DefaultTracerProvider(TracerProvider):
    """The default TracerProvider, used when no implementation is available.

    All operations are no-op.
    """

    def get_tracer(
        self,
        instrumenting_module_name: str,
        instrumenting_library_version: str = "",
    ) -> "Tracer":
        # pylint:disable=no-self-use,unused-argument
        return DefaultTracer()


class Tracer(abc.ABC):
    """Handles span creation and in-process context propagation.

    This class provides methods for manipulating the context, creating spans,
    and controlling spans' lifecycles.
    """

    # Constant used to represent the current span being used as a parent.
    # This is the default behavior when creating spans.
    CURRENT_SPAN = DefaultSpan(INVALID_SPAN_CONTEXT)

    @abc.abstractmethod
    def start_span(
        self,
        name: str,
        parent: ParentSpan = CURRENT_SPAN,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: typing.Optional[types.Attributes] = None,
        links: typing.Sequence[Link] = (),
        start_time: typing.Optional[int] = None,
        set_status_on_exception: bool = True,
    ) -> "Span":
        """Starts a span.

        Create a new span. Start the span without setting it as the current
        span in this tracer's context.

        By default the current span will be used as parent, but an explicit
        parent can also be specified, either a `Span` or a `opentelemetry.trace.SpanContext`. If
        the specified value is `None`, the created span will be a root span.

        The span can be used as context manager. On exiting, the span will be
        ended.

        Example::

            # trace.get_current_span() will be used as the implicit parent.
            # If none is found, the created span will be a root instance.
            with tracer.start_span("one") as child:
                child.add_event("child's event")

        Applications that need to set the newly created span as the current
        instance should use :meth:`start_as_current_span` instead.

        Args:
            name: The name of the span to be created.
            parent: The span's parent. Defaults to the current span.
            kind: The span's kind (relationship to parent). Note that is
                meaningful even if there is no parent.
            attributes: The span's attributes.
            links: Links span to other spans
            start_time: Sets the start time of a span
            set_status_on_exception: Only relevant if the returned span is used
                in a with/context manager. Defines wether the span status will
                be automatically set to UNKNOWN when an uncaught exception is
                raised in the span with block. The span status won't be set by
                this mechanism if it was previousy set manually.

        Returns:
            The newly-created span.
        """

    @contextmanager  # type: ignore
    @abc.abstractmethod
    def start_as_current_span(
        self,
        name: str,
        parent: ParentSpan = CURRENT_SPAN,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: typing.Optional[types.Attributes] = None,
        links: typing.Sequence[Link] = (),
    ) -> typing.Iterator["Span"]:
        """Context manager for creating a new span and set it
        as the current span in this tracer's context.

        On exiting the context manager stops the span and set its parent as the
        current span.

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
            with tracer.use_span(span, end_on_exit=True):
                do_work()

        Args:
            name: The name of the span to be created.
            parent: The span's parent. Defaults to the current span.
            kind: The span's kind (relationship to parent). Note that is
                meaningful even if there is no parent.
            attributes: The span's attributes.
            links: Links span to other spans

        Yields:
            The newly-created span.
        """

    @contextmanager  # type: ignore
    @abc.abstractmethod
    def use_span(
        self, span: "Span", end_on_exit: bool = False
    ) -> typing.Iterator[None]:
        """Context manager for controlling a span's lifetime.

        Set the given span as the current span in this tracer's context.

        On exiting the context manager set the span that was previously active
        as the current span (this is usually but not necessarily the parent of
        the given span). If ``end_on_exit`` is ``True``, then the span is also
        ended when exiting the context manager.

        Args:
            span: The span to start and make current.
            end_on_exit: Whether to end the span automatically when leaving the
                context manager.
        """


class DefaultTracer(Tracer):
    """The default Tracer, used when no Tracer implementation is available.

    All operations are no-op.
    """

    def start_span(
        self,
        name: str,
        parent: ParentSpan = Tracer.CURRENT_SPAN,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: typing.Optional[types.Attributes] = None,
        links: typing.Sequence[Link] = (),
        start_time: typing.Optional[int] = None,
        set_status_on_exception: bool = True,
    ) -> "Span":
        # pylint: disable=unused-argument,no-self-use
        return INVALID_SPAN

    @contextmanager  # type: ignore
    def start_as_current_span(
        self,
        name: str,
        parent: ParentSpan = Tracer.CURRENT_SPAN,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: typing.Optional[types.Attributes] = None,
        links: typing.Sequence[Link] = (),
    ) -> typing.Iterator["Span"]:
        # pylint: disable=unused-argument,no-self-use
        yield INVALID_SPAN

    @contextmanager  # type: ignore
    def use_span(
        self, span: "Span", end_on_exit: bool = False
    ) -> typing.Iterator[None]:
        # pylint: disable=unused-argument,no-self-use
        yield


_TRACER_PROVIDER = None


def get_tracer(
    instrumenting_module_name: str,
    instrumenting_library_version: str = "",
    tracer_provider: typing.Optional[TracerProvider] = None,
) -> "Tracer":
    """Returns a `Tracer` for use by the given instrumentation library.

    This function is a convenience wrapper for
    opentelemetry.trace.TracerProvider.get_tracer.

    If tracer_provider is ommited the current configured one is used.
    """
    if tracer_provider is None:
        tracer_provider = get_tracer_provider()
    return tracer_provider.get_tracer(
        instrumenting_module_name, instrumenting_library_version
    )


def set_tracer_provider(tracer_provider: TracerProvider) -> None:
    """Sets the current global :class:`~.TracerProvider` object."""
    global _TRACER_PROVIDER  # pylint: disable=global-statement
    _TRACER_PROVIDER = tracer_provider


def get_tracer_provider() -> TracerProvider:
    """Gets the current global :class:`~.TracerProvider` object."""
    global _TRACER_PROVIDER  # pylint: disable=global-statement

    if _TRACER_PROVIDER is None:
        _TRACER_PROVIDER = _load_trace_provider("tracer_provider")

    return _TRACER_PROVIDER
