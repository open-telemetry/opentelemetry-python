# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

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
            do_work()
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
from collections.abc import Iterator, Sequence
from enum import Enum
from logging import getLogger
from typing import cast

from typing_extensions import deprecated

from opentelemetry import context as context_api
from opentelemetry.attributes import BoundedAttributes
from opentelemetry.context.context import Context
from opentelemetry.environment_variables import OTEL_PYTHON_TRACER_PROVIDER
from opentelemetry.trace.propagation import (
    _SPAN_KEY,
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
from opentelemetry.util._decorator import _agnosticcontextmanager
from opentelemetry.util._once import Once
from opentelemetry.util._providers import _load_provider

logger = getLogger(__name__)


class _LinkBase(ABC):
    """The span context half of a link, shared by every link implementation.

    A link associates one span with another that is causally related but is
    not its parent, for example the spans of the messages gathered into a
    batch.

    Args:
        context: The span context of the span to link to.
    """

    def __init__(self, context: "SpanContext") -> None:
        """Store the context of the span being linked to.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        self._context = context

    @property
    def context(self) -> "SpanContext":
        """The context of the span being linked to.

        Returns:
            The span context this link was built with.
        """
        return self._context

    @property
    @abstractmethod
    def attributes(self) -> types.Attributes:
        """The attributes describing this link.

        Returns:
            The link attributes, or ``None`` when the link carries none.
        """


class Link(_LinkBase):
    """A link to a `Span`. The attributes of a Link are immutable.

    Args:
        context: `SpanContext` of the `Span` to link to.
        attributes: Link's attributes.
    """

    def __init__(
        self,
        context: "SpanContext",
        attributes: types.Attributes = None,
    ) -> None:
        """Build the link.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        super().__init__(context)
        self._attributes = attributes

    @property
    def attributes(self) -> types.Attributes:
        """The attributes describing this link.

        Returns:
            The link attributes, or ``None`` when the link carries none.
        """
        return self._attributes

    @property
    def dropped_attributes(self) -> int:
        """How many attributes were discarded for exceeding the limits.

        Returns:
            The count reported by the underlying
            :class:`~opentelemetry.attributes.BoundedAttributes`, or ``0``
            when the attributes are a plain mapping with no limit applied.
        """
        if isinstance(self._attributes, BoundedAttributes):
            return self._attributes.dropped
        return 0


_Links = Sequence[Link] | None


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
    """The entry point of the tracing API, which hands out tracers.

    An application configures one provider, usually by installing an SDK, and
    every library obtains its own :class:`Tracer` from it through
    :meth:`get_tracer`.
    """

    @abstractmethod
    def get_tracer(
        self,
        instrumenting_module_name: str,
        instrumenting_library_version: str | None = None,
        schema_url: str | None = None,
        attributes: types.Attributes = None,
    ) -> "Tracer":
        """Returns a `Tracer` for use by the given instrumentation library.

        For any two calls it is undefined whether the same or different
        `Tracer` instances are returned, even for different library names.

        This function may return different `Tracer` types (e.g. a no-op tracer
        vs.  a functional tracer).

        Args:
            instrumenting_module_name: The uniquely identifiable name for instrumentation
                scope, such as instrumentation library, package, module or class name.
                ``__name__`` should be avoided as this can result in
                different tracer names if the tracers are in different files.
                It is better to use a fixed string that can be imported where
                needed and used consistently as the name of the tracer.

                This should *not* be the name of the module that is
                instrumented but the name of the module doing the instrumentation.
                E.g., instead of ``"requests"``, use
                ``"opentelemetry.instrumentation.requests"``.

            instrumenting_library_version: Optional. The version string of the
                instrumenting library.  Usually this should be the same as
                ``importlib.metadata.version(instrumenting_library_name)``.

            schema_url: Optional. Specifies the Schema URL of the emitted telemetry.
            attributes: Optional. Specifies the attributes of the emitted telemetry.

        Returns:
            A `Tracer` bound to the given instrumentation scope.
        """


class NoOpTracerProvider(TracerProvider):
    """The default TracerProvider, used when no implementation is available.

    All operations are no-op.
    """

    def get_tracer(
        self,
        instrumenting_module_name: str,
        instrumenting_library_version: str | None = None,
        schema_url: str | None = None,
        attributes: types.Attributes = None,
    ) -> "Tracer":
        """Return a tracer that creates only non-recording spans.

        Args:
            instrumenting_module_name: The uniquely identifiable name for the
                instrumentation scope, not the name of the module being
                instrumented.
            instrumenting_library_version: The version string of the
                instrumenting library.
            schema_url: The Schema URL of the emitted telemetry.
            attributes: The instrumentation scope attributes to associate with
                emitted telemetry.

        Returns:
            A :class:`NoOpTracer`. The scope arguments are accepted and
            ignored.
        """
        # pylint:disable=no-self-use,unused-argument
        return NoOpTracer()


@deprecated("You should use NoOpTracerProvider. Deprecated since version 1.9.0.")
class _DefaultTracerProvider(NoOpTracerProvider):
    """The default TracerProvider, used when no implementation is available.

    All operations are no-op.
    """


class ProxyTracerProvider(TracerProvider):
    """The provider returned before a real one has been set globally.

    Every tracer this tracer provider hands out before a real tracer provider
    is set is a :class:`ProxyTracer`, which creates non-recording spans and
    switches to the real tracer provider as soon as
    :func:`set_tracer_provider` installs one. Every tracer handed out after
    that call comes from the real tracer provider directly. This is what lets
    a library call :func:`get_tracer` at import time, before the application
    configures the SDK.
    """

    def get_tracer(
        self,
        instrumenting_module_name: str,
        instrumenting_library_version: str | None = None,
        schema_url: str | None = None,
        attributes: types.Attributes = None,
    ) -> "Tracer":
        """Return a tracer bound to the real provider once one exists.

        Args:
            instrumenting_module_name: The uniquely identifiable name for the
                instrumentation scope, not the name of the module being
                instrumented.
            instrumenting_library_version: The version string of the
                instrumenting library.
            schema_url: The Schema URL of the emitted telemetry.
            attributes: The instrumentation scope attributes to associate with
                emitted telemetry.

        Returns:
            A tracer from the global provider when one has been set, and a
            :class:`ProxyTracer` carrying the given scope otherwise.
        """
        if _TRACER_PROVIDER:
            return _TRACER_PROVIDER.get_tracer(
                instrumenting_module_name,
                instrumenting_library_version,
                schema_url,
                attributes,
            )
        return ProxyTracer(
            instrumenting_module_name,
            instrumenting_library_version,
            schema_url,
            attributes,
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
        context: Context | None = None,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: types.Attributes = None,
        links: _Links = None,
        start_time: int | None = None,
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
                in a with/context manager. Defines whether the span status will
                be automatically set to ERROR when an uncaught exception is
                raised in the span with block. The span status won't be set by
                this mechanism if it was previously set manually.

        Returns:
            The newly-created span.
        """

    @_agnosticcontextmanager
    @abstractmethod
    def start_as_current_span(
        self,
        name: str,
        context: Context | None = None,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: types.Attributes = None,
        links: _Links = None,
        start_time: int | None = None,
        record_exception: bool = True,
        set_status_on_exception: bool = True,
        end_on_exit: bool = True,
    ) -> Iterator["Span"]:
        """Context manager for creating a new span and set it
        as the current span in this tracer's context.

        Exiting the context manager will call the span's end method,
        as well as return the current span to its previous value by
        returning to the previous context.

        Example::

            with tracer.start_as_current_span("one") as parent:
                parent.add_event("parent's event")
                with tracer.start_as_current_span("two") as child:
                    child.add_event("child's event")
                    trace.get_current_span()  # returns child
                trace.get_current_span()  # returns parent
            trace.get_current_span()  # returns previously active span

        This is a convenience method for creating spans attached to the
        tracer's context. Applications that need more control over the span
        lifetime should use :meth:`start_span` instead. For example::

            with tracer.start_as_current_span(name) as span:
                do_work()

        is equivalent to::

            span = tracer.start_span(name)
            with opentelemetry.trace.use_span(span, end_on_exit=True):
                do_work()

        This can also be used as a decorator::

            @tracer.start_as_current_span("name")
            def function(): ...


            function()

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
                in a with/context manager. Defines whether the span status will
                be automatically set to ERROR when an uncaught exception is
                raised in the span with block. The span status won't be set by
                this mechanism if it was previously set manually.
            end_on_exit: Whether to end the span automatically when leaving the
                context manager.

        Yields:
            The newly-created span.
        """


class ProxyTracer(Tracer):
    """A tracer that stands in until a real provider is set globally.

    Every span it creates is a :class:`~opentelemetry.trace.NonRecordingSpan` while no
    :class:`TracerProvider` has been installed. Once one is, the proxy
    resolves a real tracer for its instrumentation scope, caches it, and
    forwards everything from then on.

    Args:
        instrumenting_module_name: The uniquely identifiable name for the
            instrumentation scope.
        instrumenting_library_version: The version string of the
            instrumenting library.
        schema_url: The Schema URL of the emitted telemetry.
        attributes: The instrumentation scope attributes to associate with
            emitted telemetry.
    """

    # pylint: disable=W0222,signature-differs
    def __init__(
        self,
        instrumenting_module_name: str,
        instrumenting_library_version: str | None = None,
        schema_url: str | None = None,
        attributes: types.Attributes = None,
    ):
        """Record what to ask the global provider for once it exists.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        self._instrumenting_module_name = instrumenting_module_name
        self._instrumenting_library_version = instrumenting_library_version
        self._schema_url = schema_url
        self._attributes = attributes
        self._real_tracer: Tracer | None = None
        self._noop_tracer = NoOpTracer()

    @property
    def _tracer(self) -> Tracer:
        """Return the tracer to delegate to, resolving it on first use.

        Returns:
            The tracer obtained from the global :class:`TracerProvider` once
            one is set, cached thereafter. A :class:`NoOpTracer` until then,
            built once and returned on every call, which the proxy never
            adopts as its real tracer, so a later provider is still picked up.
        """
        if self._real_tracer:
            return self._real_tracer

        if _TRACER_PROVIDER:
            self._real_tracer = _TRACER_PROVIDER.get_tracer(
                self._instrumenting_module_name,
                self._instrumenting_library_version,
                self._schema_url,
                self._attributes,
            )
            return self._real_tracer
        return self._noop_tracer

    def start_span(self, *args, **kwargs) -> Span:  # type: ignore
        """Start a span through the real tracer once one is available.

        Args:
            *args: Positional arguments forwarded to
                :meth:`Tracer.start_span`.
            **kwargs: Keyword arguments forwarded to
                :meth:`Tracer.start_span`.

        Returns:
            The span the delegate created, which is a
            :class:`~opentelemetry.trace.NonRecordingSpan` while no provider has been set.
        """
        return self._tracer.start_span(*args, **kwargs)  # type: ignore

    @_agnosticcontextmanager  # type: ignore
    def start_as_current_span(self, *args, **kwargs) -> Iterator[Span]:
        """Start a span and make it current, through the real tracer.

        Args:
            *args: Positional arguments forwarded to
                :meth:`Tracer.start_as_current_span`.
            **kwargs: Keyword arguments forwarded to
                :meth:`Tracer.start_as_current_span`.

        Yields:
            The span the delegate created, which is a
            :class:`~opentelemetry.trace.NonRecordingSpan` while no provider has been set.
        """
        with self._tracer.start_as_current_span(*args, **kwargs) as span:  # type: ignore
            yield span


class NoOpTracer(Tracer):
    """The default Tracer, used when no Tracer implementation is available.

    All operations are no-op.
    """

    def start_span(
        self,
        name: str,
        context: Context | None = None,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: types.Attributes = None,
        links: _Links = None,
        start_time: int | None = None,
        record_exception: bool = True,
        set_status_on_exception: bool = True,
    ) -> "Span":
        """Return a non-recording span, creating no telemetry.

        ``context`` is the only argument that has an effect. Every other one
        is accepted so that the signature matches :meth:`Tracer.start_span`,
        and discarded, because a non-recording span holds nothing but a span
        context.

        Args:
            name: Ignored.
            context: The Context to read the current span from. Defaults to
                the current context.
            kind: Ignored.
            attributes: Ignored.
            links: Ignored.
            start_time: Ignored.
            record_exception: Ignored.
            set_status_on_exception: Ignored.

        Returns:
            The current span when it is already a
            :class:`~opentelemetry.trace.NonRecordingSpan`, so the trace context is preserved.
            Otherwise a new :class:`~opentelemetry.trace.NonRecordingSpan` carrying the current
            span context, or :data:`INVALID_SPAN` when that context is not
            usable.
        """
        current_span = get_current_span(context)
        if isinstance(current_span, NonRecordingSpan):
            return current_span
        parent_span_context = current_span.get_span_context()
        if parent_span_context is not None and not isinstance(parent_span_context, SpanContext):
            logger.warning(
                "Invalid span context for %s: %s",
                current_span,
                parent_span_context,
            )
            return INVALID_SPAN

        return NonRecordingSpan(context=parent_span_context)

    @_agnosticcontextmanager
    def start_as_current_span(
        self,
        name: str,
        context: Context | None = None,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: types.Attributes = None,
        links: _Links = None,
        start_time: int | None = None,
        record_exception: bool = True,
        set_status_on_exception: bool = True,
        end_on_exit: bool = True,
    ) -> Iterator["Span"]:
        """Make a non-recording span current for the duration of the block.

        ``context`` is the only argument that changes what happens. The rest
        are accepted so that the signature matches
        :meth:`Tracer.start_as_current_span`, and the three passed on to
        :func:`use_span` change nothing there, because a non-recording span is
        never recording and discards the call to :meth:`Span.end`.

        Args:
            name: Ignored.
            context: The Context to read the current span from. Defaults to
                the current context.
            kind: Ignored.
            attributes: Ignored.
            links: Ignored.
            start_time: Ignored.
            record_exception: Passed on to :func:`use_span`, which records
                nothing on a non-recording span.
            set_status_on_exception: Passed on to :func:`use_span`, which sets
                no status on a non-recording span.
            end_on_exit: Passed on to :func:`use_span`, whose call to
                :meth:`Span.end` a non-recording span discards.

        Yields:
            A :class:`~opentelemetry.trace.NonRecordingSpan`, which records nothing set on it but
            keeps the trace context current so propagation still works.
        """
        span = self.start_span(
            name=name,
            context=context,
            kind=kind,
            attributes=attributes,
            links=links,
            start_time=start_time,
            record_exception=record_exception,
            set_status_on_exception=set_status_on_exception,
        )
        with use_span(
            span,
            end_on_exit=end_on_exit,
            record_exception=record_exception,
            set_status_on_exception=set_status_on_exception,
        ) as span:
            yield span


@deprecated("You should use NoOpTracer. Deprecated since version 1.9.0.")
class _DefaultTracer(NoOpTracer):
    """The default Tracer, used when no Tracer implementation is available.

    All operations are no-op.
    """


_TRACER_PROVIDER_SET_ONCE = Once()
_TRACER_PROVIDER: TracerProvider | None = None
_PROXY_TRACER_PROVIDER = ProxyTracerProvider()


def get_tracer(
    instrumenting_module_name: str,
    instrumenting_library_version: str | None = None,
    tracer_provider: TracerProvider | None = None,
    schema_url: str | None = None,
    attributes: types.Attributes = None,
) -> "Tracer":
    """Returns a `Tracer` for use by the given instrumentation library.

    This function is a convenience wrapper for
    opentelemetry.trace.TracerProvider.get_tracer.

    If tracer_provider is omitted the current configured one is used.

    Args:
        instrumenting_module_name: The uniquely identifiable name for the
            instrumentation scope, not the name of the module being
            instrumented.
        instrumenting_library_version: The version string of the instrumenting
            library.
        tracer_provider: The provider to obtain the tracer from. Defaults to
            the globally configured one.
        schema_url: The Schema URL of the emitted telemetry.
        attributes: The instrumentation scope attributes to associate with
            emitted telemetry.

    Returns:
        A `Tracer` bound to the given instrumentation scope.
    """
    if tracer_provider is None:
        tracer_provider = get_tracer_provider()
    return tracer_provider.get_tracer(
        instrumenting_module_name,
        instrumenting_library_version,
        schema_url,
        attributes,
    )


def _set_tracer_provider(tracer_provider: TracerProvider, log: bool) -> None:
    """Install the global provider, at most once per process.

    Args:
        tracer_provider: The provider to install.
        log: Whether to log a warning when a provider is already installed and
            this call therefore has no effect.
    """

    def set_tp() -> None:
        """Assign the global provider. Called at most once."""
        global _TRACER_PROVIDER  # pylint: disable=global-statement
        _TRACER_PROVIDER = tracer_provider

    did_set = _TRACER_PROVIDER_SET_ONCE.do_once(set_tp)

    if log and not did_set:
        logger.warning("Overriding of current TracerProvider is not allowed")


def set_tracer_provider(tracer_provider: TracerProvider) -> None:
    """Sets the current global :class:`~.TracerProvider` object.

    This can only be done once, a warning will be logged if any further attempt
    is made.

    Args:
        tracer_provider: The provider to install globally.
    """
    _set_tracer_provider(tracer_provider, log=True)


def get_tracer_provider() -> TracerProvider:
    """Gets the current global :class:`~.TracerProvider` object.

    Returns:
        The provider set by :func:`set_tracer_provider`, or the one named by
        the ``OTEL_PYTHON_TRACER_PROVIDER`` environment variable. When neither
        is present, a ``ProxyTracerProvider`` is returned, which starts
        delegating as soon as a provider is set.

    Raises:
        Exception: Whatever loading the entry point named by the environment
            variable raised, since ``_load_provider`` logs it and re-raises. A
            name that matches no installed entry point surfaces as
            :exc:`StopIteration`.
    """
    if _TRACER_PROVIDER is None:
        # if a global tracer provider has not been set either via code or env
        # vars, return a proxy tracer provider
        if OTEL_PYTHON_TRACER_PROVIDER not in os.environ:
            return _PROXY_TRACER_PROVIDER

        tracer_provider: TracerProvider = _load_provider(OTEL_PYTHON_TRACER_PROVIDER, "tracer_provider")
        _set_tracer_provider(tracer_provider, log=False)
    # _TRACER_PROVIDER will have been set by one thread
    return cast("TracerProvider", _TRACER_PROVIDER)


@_agnosticcontextmanager
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
            in a with/context manager. Defines whether the span status will
            be automatically set to ERROR when an uncaught exception is
            raised in the span with block. The span status won't be set by
            this mechanism if it was previously set manually.

    Yields:
        The span passed in, now current for the duration of the block.

    Raises:
        Exception: Re-raises whatever the block raised, after recording it on
            the span when the span is recording and ``record_exception`` is
            true. An exception inheriting directly from :exc:`BaseException`,
            such as :exc:`GeneratorExit`, passes through without being
            recorded, because it does not signal an error.
    """
    try:
        token = context_api.attach(context_api.set_value(_SPAN_KEY, span))
        try:
            yield span
        finally:
            context_api.detach(token)

    # Record only exceptions that inherit Exception class but not BaseException, because
    # classes that directly inherit BaseException are not technically errors, e.g. GeneratorExit.
    # See https://github.com/open-telemetry/opentelemetry-python/issues/4484
    except Exception as exc:  # pylint: disable=broad-exception-caught
        if isinstance(span, Span) and span.is_recording():
            # Record the exception as an event
            if record_exception:
                span.record_exception(exc)

            # Set status in case exception was raised
            if set_status_on_exception:
                span.set_status(
                    Status(
                        status_code=StatusCode.ERROR,
                        description=f"{type(exc).__name__}: {exc}",
                    )
                )

        # This causes parent spans to set their status to ERROR and to record
        # an exception as an event if a child span raises an exception even if
        # such child span was started with both record_exception and
        # set_status_on_exception attributes set to False.
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
    "Link",
    "NonRecordingSpan",
    "Span",
    "SpanContext",
    "SpanKind",
    "Status",
    "StatusCode",
    "TraceFlags",
    "TraceState",
    "Tracer",
    "TracerProvider",
    "format_span_id",
    "format_trace_id",
    "get_current_span",
    "get_tracer",
    "get_tracer_provider",
    "set_span_in_context",
    "set_tracer_provider",
    "use_span",
]
