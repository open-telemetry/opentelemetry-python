# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=too-many-lines
"""Tracing implementation of the OpenTelemetry SDK.

This module holds the concrete types behind the tracing API. A
``TracerProvider`` builds and caches ``Tracer`` instances. A ``Tracer`` asks
its sampler whether a new span should record, and hands the recording ones to
the span processors registered on the provider. A ``Span`` accumulates the
attributes, events, links and status that an exporter later reads back through
``ReadableSpan``.

``SpanLimits`` collects the caps applied while a span records: how many
attributes, events and links it keeps, and how long a string attribute value
may be. Anything over a cap is dropped or truncated, and the counts show up on
the finished span as ``dropped_attributes``, ``dropped_events`` and
``dropped_links``.

Nothing here exports a span. A ``SpanProcessor`` registered with
``TracerProvider.add_span_processor`` is called when a span starts and when it
ends, and the processors in ``opentelemetry.sdk.trace.export`` are the ones
that hand spans to an exporter.
"""

import abc
import atexit
import concurrent.futures
import json
import logging
import os
import threading
import traceback
import typing
import weakref
from collections.abc import (
    Callable,
    Iterator,
    Mapping,
    MutableMapping,
    Sequence,
)
from dataclasses import dataclass
from os import environ
from time import time_ns
from types import MappingProxyType, TracebackType
from typing import (
    Any,
)
from warnings import filterwarnings

from typing_extensions import deprecated

from opentelemetry import context as context_api
from opentelemetry import metrics as metrics_api
from opentelemetry import trace as trace_api
from opentelemetry.attributes import BoundedAttributes
from opentelemetry.sdk import util
from opentelemetry.sdk.environment_variables import (
    OTEL_ATTRIBUTE_COUNT_LIMIT,
    OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT,
    OTEL_EVENT_ATTRIBUTE_COUNT_LIMIT,
    OTEL_LINK_ATTRIBUTE_COUNT_LIMIT,
    OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED,
    OTEL_SDK_DISABLED,
    OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT,
    OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT,
    OTEL_SPAN_EVENT_COUNT_LIMIT,
    OTEL_SPAN_LINK_COUNT_LIMIT,
)
from opentelemetry.sdk.environment_variables._internal import (
    parse_boolean_environment_variable,
)
from opentelemetry.sdk.resources import (
    Resource,
    _get_process_dependent_resource,
)
from opentelemetry.sdk.trace import sampling
from opentelemetry.sdk.trace._tracer_metrics import create_tracer_metrics
from opentelemetry.sdk.trace.id_generator import IdGenerator, RandomIdGenerator
from opentelemetry.sdk.util import BoundedList
from opentelemetry.sdk.util._configurator import RuleBasedConfigurator
from opentelemetry.sdk.util.instrumentation import (
    InstrumentationInfo,
    InstrumentationScope,
)
from opentelemetry.semconv.attributes.exception_attributes import (
    EXCEPTION_ESCAPED,
    EXCEPTION_MESSAGE,
    EXCEPTION_STACKTRACE,
    EXCEPTION_TYPE,
)
from opentelemetry.trace import NoOpTracer, SpanContext
from opentelemetry.trace.status import Status, StatusCode
from opentelemetry.util import types
from opentelemetry.util._decorator import _agnosticcontextmanager

logger = logging.getLogger(__name__)


_DEFAULT_OTEL_ATTRIBUTE_COUNT_LIMIT = 128
_DEFAULT_OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT = 128
_DEFAULT_OTEL_EVENT_ATTRIBUTE_COUNT_LIMIT = 128
_DEFAULT_OTEL_LINK_ATTRIBUTE_COUNT_LIMIT = 128
_DEFAULT_OTEL_SPAN_EVENT_COUNT_LIMIT = 128
_DEFAULT_OTEL_SPAN_LINK_COUNT_LIMIT = 128


_ENV_VALUE_UNSET = ""


class SpanProcessor:
    """Interface which allows hooks for SDK's `Span` start and end method
    invocations.

    Span processors can be registered directly using
    :func:`TracerProvider.add_span_processor` and they are invoked
    in the same order as they were registered.
    """

    def on_start(
        self,
        span: "Span",
        parent_context: context_api.Context | None = None,
    ) -> None:
        """Called when a :class:`opentelemetry.trace.Span` is started.

        This method is called synchronously on the thread that starts the
        span, therefore it should not block or throw an exception.

        Args:
            span: The :class:`opentelemetry.trace.Span` that just started.
            parent_context: The parent context of the span that just started.
        """

    def _on_ending(self, span: "Span") -> None:
        """Called when a :class:`opentelemetry.trace.Span` is ending.

        This method is called synchronously on the thread that ends the
        span, therefore it should not block or throw an exception.

        Args:
            span: The :class:`opentelemetry.trace.Span` that is ending.
        """

    def on_end(self, span: "ReadableSpan") -> None:
        """Called when a :class:`opentelemetry.trace.Span` is ended.

        This method is called synchronously on the thread that ends the
        span, therefore it should not block or throw an exception.

        Args:
            span: The :class:`opentelemetry.trace.Span` that just ended.
        """

    def shutdown(self) -> None:
        """Called when a :class:`opentelemetry.sdk.trace.TracerProvider` is shutdown."""

    def force_flush(self, timeout_millis: int = 30000) -> bool:  # pylint: disable=no-self-use
        """Export all ended spans to the configured Exporter that have not yet
        been exported.

        Args:
            timeout_millis: The maximum amount of time to wait for spans to be
                exported.

        Returns:
            False if the timeout is exceeded, True otherwise.
        """
        return True


# Temporary fix until https://github.com/PyCQA/pylint/issues/4098 is resolved
# pylint:disable=no-member
class SynchronousMultiSpanProcessor(SpanProcessor):
    """Implementation of class:`SpanProcessor` that forwards all received
    events to a list of span processors sequentially.

    The underlying span processors are called in sequential order as they were
    added.
    """

    _span_processors: tuple[SpanProcessor, ...]

    def __init__(self):
        """Build the instance with no span processors registered.

        The constructor takes no arguments. Processors are added afterwards
        with ``add_span_processor``.
        """
        # use a tuple to avoid race conditions when adding a new span and
        # iterating through it on "on_start" and "on_end".
        self._span_processors = ()
        self._lock = threading.Lock()

    def add_span_processor(self, span_processor: SpanProcessor) -> None:
        """Adds a SpanProcessor to the list handled by this instance.

        The processor goes at the end, so it is called after every processor
        already registered. Registering the same processor twice makes it run
        twice for every span.

        Args:
            span_processor: The processor to append to the list this instance
                forwards to.
        """
        with self._lock:
            self._span_processors += (span_processor,)

    def on_start(
        self,
        span: "Span",
        parent_context: context_api.Context | None = None,
    ) -> None:
        """Forward the start of ``span`` to each processor in turn.

        An exception raised by one processor propagates to the thread that
        started the span, and the processors after it are not called.

        Args:
            span: The span that just started.
            parent_context: The context the span was started in, passed on
                unchanged. ``None`` means the current context was used.
        """
        for sp in self._span_processors:
            sp.on_start(span, parent_context=parent_context)

    def _on_ending(self, span: "Span") -> None:
        """Forward the ending of ``span`` to each processor in turn.

        The span is still mutable on this thread while these callbacks run, so
        a processor may add attributes to it. An exception raised by one
        processor is logged with its traceback and swallowed, and the
        processors after it still run.

        Args:
            span: The span whose ``end`` call is in progress.
        """
        for sp in self._span_processors:
            try:
                # pylint: disable=protected-access
                sp._on_ending(span)
            except Exception:  # pylint: disable=broad-exception-caught
                logger.exception("Exception while calling _on_ending on %s.", sp)

    def on_end(self, span: "ReadableSpan") -> None:
        """Forward the ended ``span`` to each processor in turn.

        An exception raised by one processor propagates to the thread that
        ended the span, and the processors after it are not called.

        Args:
            span: The read-only snapshot taken when the span ended. Every
                processor receives the same object.
        """
        for sp in self._span_processors:
            sp.on_end(span)

    def shutdown(self) -> None:
        """Sequentially shuts down all underlying span processors.

        An exception raised by one processor propagates to the caller and the
        processors after it are never shut down.
        """
        for sp in self._span_processors:
            sp.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Sequentially calls force_flush on all underlying
        :class:`SpanProcessor`

        A deadline is computed once, and each processor is given whatever is
        left of it, rounded down to whole milliseconds, so a processor reached
        with less than a millisecond to spare is asked to flush in zero. Once
        the deadline has passed the call returns ``False`` at once, without
        calling the processors that are left.

        Args:
            timeout_millis: The maximum amount of time over all span processors
                to wait for spans to be exported. In case the first n span
                processors exceeded the timeout followup span processors will be
                skipped.

        Returns:
            True if all span processors flushed their spans within the
            given timeout, False otherwise.
        """
        deadline_ns = time_ns() + timeout_millis * 1000000
        all_flushed = True
        for sp in self._span_processors:
            current_time_ns = time_ns()
            if current_time_ns >= deadline_ns:
                return False

            if sp.force_flush((deadline_ns - current_time_ns) // 1000000) is False:
                all_flushed = False

        return all_flushed


class ConcurrentMultiSpanProcessor(SpanProcessor):
    """Implementation of :class:`SpanProcessor` that forwards all received
    events to a list of span processors in parallel.

    Calls to the underlying span processors are forwarded in parallel by
    submitting them to a thread pool executor and waiting until each span
    processor finished its work. The only exception is ``_on_ending``, which
    is called synchronously on the thread ending the span, since that is the
    only thread allowed to mutate the span while it is ending.

    The pool is rebuilt in a child process after a fork, because only the
    forking thread survives and the worker threads inherited with the pool
    would never run anything.

    Args:
        num_threads: The number of threads managed by the thread pool executor
            and thus defining how many span processors can work in parallel.
    """

    _span_processors: tuple[SpanProcessor, ...]

    def __init__(self, num_threads: int = 2):
        """Build the instance and the thread pool it submits work to.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        # use a tuple to avoid race conditions when adding a new span and
        # iterating through it on "on_start" and "on_end".
        self._span_processors = ()
        self._lock = threading.Lock()
        self._init_executor(num_threads)
        if hasattr(os, "register_at_fork"):
            # Only the main thread is kept in forked processed, the executor
            # needs to be re-instantiated to get a fresh pool of threads:
            weak_reinit = weakref.WeakMethod(self._init_executor)

            def _after_in_child() -> None:
                """Rebuild the thread pool in the freshly forked child.

                A fork keeps only the calling thread, so the inherited pool has
                no workers. ``os.register_at_fork`` keeps a strong reference to
                whatever is handed to it, so this closure holds
                ``_init_executor`` of this multi span processor only weakly. A
                multi span processor that has been garbage collected leaves the
                weak reference empty and the handler does nothing.
                """
                reinit = weak_reinit()
                if reinit is not None:
                    reinit(num_threads)

            os.register_at_fork(after_in_child=_after_in_child)

    def _init_executor(self, num_threads: int) -> None:
        """Replace the thread pool with a fresh one of the requested size.

        Called once from the constructor, and again in a child process after a
        fork. The pool being replaced is dropped without being shut down.

        Args:
            num_threads: Number of worker threads the new pool runs.
        """
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=num_threads)

    def add_span_processor(self, span_processor: SpanProcessor) -> None:
        """Adds a SpanProcessor to the list handled by this instance.

        Registering the same processor twice makes it run twice for every span.
        Work is submitted to the pool in registration order, but the processors
        run in parallel, so that order says nothing about which one finishes
        first.

        Args:
            span_processor: The processor to append to the list this instance
                forwards to.
        """
        with self._lock:
            self._span_processors += (span_processor,)

    def _submit_and_await(
        self,
        func: Callable[[SpanProcessor], Callable[..., None]],
        *args: Any,
        **kwargs: Any,
    ):
        """Call one bound method on every processor and wait for all of them.

        Every call is submitted to the thread pool before any result is
        collected, so the processors run concurrently. The first exception
        raised by a processor surfaces here when its result is collected, and
        the results not yet collected are abandoned, though the calls behind
        them still run to completion.

        Args:
            func: Takes a processor and returns the bound method to call on it,
                for example ``lambda sp: sp.on_end``.
            *args: Positional arguments passed to each bound method.
            **kwargs: Keyword arguments passed to each bound method.
        """
        futures = []
        for sp in self._span_processors:
            future = self._executor.submit(func(sp), *args, **kwargs)
            futures.append(future)
        for future in futures:
            future.result()

    def on_start(
        self,
        span: "Span",
        parent_context: context_api.Context | None = None,
    ) -> None:
        """Forward the start of ``span`` to every processor at once.

        The call blocks until every processor has returned, so the thread that
        started the span still waits for the slowest of them.

        Args:
            span: The span that just started.
            parent_context: The context the span was started in, passed on
                unchanged. ``None`` means the current context was used.
        """
        self._submit_and_await(lambda sp: sp.on_start, span, parent_context=parent_context)

    def _on_ending(self, span: "Span") -> None:
        """Forward the ending of ``span`` to each processor in turn.

        This is the one callback that does not go through the thread pool. The
        span is still mutable while it ends, and only the thread ending it may
        mutate it, so a processor that wants to add an attribute has to run
        there. An exception raised by one processor is logged with its
        traceback and swallowed, and the processors after it still run.

        Args:
            span: The span whose ``end`` call is in progress.
        """
        # Unlike the other callbacks, _on_ending runs synchronously on the
        # thread that ends the span: that is the only thread allowed to
        # mutate the span while it is ending.
        for sp in self._span_processors:
            try:
                # pylint: disable=protected-access
                sp._on_ending(span)
            except Exception:  # pylint: disable=broad-exception-caught
                logger.exception("Exception while calling _on_ending on %s.", sp)

    def on_end(self, span: "ReadableSpan") -> None:
        """Forward the ended ``span`` to every processor at once.

        The call blocks until every processor has returned, so the thread that
        ended the span still waits for the slowest of them.

        Args:
            span: The read-only snapshot taken when the span ended. Every
                processor receives the same object.
        """
        self._submit_and_await(lambda sp: sp.on_end, span)

    def shutdown(self) -> None:
        """Shuts down all underlying span processors in parallel.

        The call blocks until every processor has returned. There is no
        timeout: each processor applies its own.
        """
        self._submit_and_await(lambda sp: sp.shutdown)

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Calls force_flush on all underlying span processors in parallel.

        Unlike ``SynchronousMultiSpanProcessor``, this class gives the whole
        budget to every processor rather than dividing it, and waits that long
        for all of them together. A processor that has not finished by then
        makes the call return ``False`` while its flush keeps running in the
        thread pool, unobserved.

        Args:
            timeout_millis: The maximum amount of time to wait for spans to be
                exported.

        Returns:
            True if all span processors flushed their spans within the given
            timeout, False otherwise.
        """
        futures = []
        for sp in self._span_processors:
            future = self._executor.submit(sp.force_flush, timeout_millis)
            futures.append(future)

        timeout_sec = timeout_millis / 1e3
        done_futures, not_done_futures = concurrent.futures.wait(futures, timeout_sec)
        if not_done_futures:
            return False

        for future in done_futures:
            if future.result() is False:
                return False

        return True


class EventBase(abc.ABC):
    """Base class for a named, timestamped annotation on a span.

    The name and the timestamp are stored here and never change afterwards.
    Subclasses decide where the attributes come from by implementing
    ``attributes``. ``Event`` is the only implementation in this package.

    Args:
        name: Name of the event.
        timestamp: Time of the event in nanoseconds since the Unix epoch.
            ``None`` reads the clock as the instance is built.
    """

    def __init__(self, name: str, timestamp: int | None = None) -> None:
        """Build the instance.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        self._name = name
        if timestamp is None:
            self._timestamp = time_ns()
        else:
            self._timestamp = timestamp

    @property
    def name(self) -> str:
        """Name the event was created with.

        Returns:
            The name, exactly as it was passed to the constructor. Nothing in
            this package renames an event after the fact.
        """
        return self._name

    @property
    def timestamp(self) -> int:
        """Time of the event in nanoseconds since the Unix epoch.

        Returns:
            The timestamp given to the constructor, or the clock reading taken
            when the instance was built.
        """
        return self._timestamp

    @property
    @abc.abstractmethod
    def attributes(self) -> types.Attributes:
        """Attributes recorded on the event.

        Returns:
            The attributes, or ``None`` when the event carries none. Callers
            are expected to read the result and not write to it.
        """


class Event(EventBase):
    """A text annotation with a set of attributes. The attributes of an event
    are immutable.

    Args:
        name: Name of the event.
        attributes: Attributes of the event.
        timestamp: Timestamp of the event. If `None` it will filled
            automatically.
        limit: Accepted and ignored, kept so that older callers keep working.
            No cap is applied here. The attribute limit is applied by whoever
            builds the attributes passed in, which for a span event is
            ``Span.add_event``.
    """

    def __init__(
        self,
        name: str,
        attributes: types.Attributes = None,
        timestamp: int | None = None,
        limit: int | None = _DEFAULT_OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT,
    ) -> None:
        """Build the instance.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        super().__init__(name, timestamp)
        self._attributes = attributes

    @property
    def attributes(self) -> types.Attributes:
        """Attributes recorded on the event, exactly as they were passed in.

        ``Span.add_event`` passes an immutable, bounded mapping, so an event
        that reached a span through it is already capped and frozen. An event
        built directly keeps whatever mapping was given, uncapped.

        Returns:
            The attributes, or ``None`` when none were given.
        """
        return self._attributes

    @property
    def dropped_attributes(self) -> int:
        """Number of attributes the attribute limit kept out of this event.

        The count covers keys rejected because the mapping was already full,
        and keys that were neither non-empty strings nor convertible to one.
        Truncating a long string value is not a drop, and neither is replacing
        a value of an unusable type with ``None``, so neither of those shows up
        here.

        Returns:
            The number of dropped attributes, or ``0`` when the attributes
            were not stored in a bounded mapping and therefore nothing could
            have been dropped.
        """
        if isinstance(self._attributes, BoundedAttributes):
            return self._attributes.dropped
        return 0


def _check_span_ended(func):
    """Wrap a span mutator so that it is skipped once the span has ended.

    The wrapper takes the span lock, calls ``func`` only while the span is
    still mutable, and otherwise logs a warning naming ``func`` and leaves the
    span untouched. Whatever ``func`` returns is discarded, so this suits only
    mutators that return ``None``.

    The wrapper does not copy the name, signature or docstring of ``func``, so
    what the API reference shows for a decorated method is the wrapper.

    Args:
        func: The unbound method to wrap. It is called as
            ``func(self, *args, **kwargs)`` with the span lock held.

    Returns:
        The function to use as the body of the decorated method.
    """

    def wrapper(self, *args, **kwargs):
        """Apply this mutation to the span while it is still recording.

        ``_check_span_ended`` gives this body to ``Span.set_status``,
        ``Span.update_name``, ``Span._add_event`` and ``Span._add_link``, so
        the API reference shows this text, and the ``*args`` and ``**kwargs``
        below, in place of the signature and the docstring each of those four
        methods carries in the source. The call is made while the span lock is
        held. On a span that has already ended nothing is applied, and a
        warning naming the method is logged once the lock is released.

        Args:
            *args: The positional arguments of the method being called.
            **kwargs: The keyword arguments of the method being called.
        """
        already_ended = False
        with self._lock:  # pylint: disable=protected-access
            if self._is_mutable():  # pylint: disable=protected-access
                func(self, *args, **kwargs)
            else:
                already_ended = True

        if already_ended:
            logger.warning("Tried calling %s on an ended span.", func.__name__)

    return wrapper


def _is_valid_link(context: SpanContext, attributes: types.Attributes) -> bool:
    """Decide whether a link with this context and attributes is kept.

    A link whose context is valid is always kept. A link whose context is
    invalid is kept only when it carries something else of value, meaning
    attributes or a non-empty trace state. Everything else, a missing context
    included, is rejected, and the caller drops the link without logging.

    Args:
        context: The span context the link points at. A falsy value rejects the
            link outright.
        attributes: Attributes recorded on the link, or ``None``.

    Returns:
        ``True`` when the link should be recorded.
    """
    return bool(context and (context.is_valid or (attributes or context.trace_state)))


class ReadableSpan:
    """Provides read-only access to span attributes.

    Users should NOT be creating these objects directly. `ReadableSpan`s are created as
    a direct result from using the tracing pipeline via the `Tracer`.

    One of these is built by ``Span._readable_span`` when a span ends, and is
    what the ``on_end`` callbacks and the exporters read. It shares the
    containers holding the attributes, the events and the links with the span
    it was taken from rather than copying them, which is safe because the span
    freezes its attributes before handing the snapshot over.

    Args:
        name: Name of the span.
        context: Span context carrying the trace id, the span id, the flags and
            the trace state. ``None`` for a span that was never given one.
        parent: Span context of the parent, or ``None`` for a root span.
        resource: Resource describing the entity that produced the span.
            ``None`` builds one from the configured resource detectors.
        attributes: Attributes recorded on the span, or ``None``.
        events: Events recorded on the span, oldest first.
        links: Links recorded on the span.
        kind: Relationship between this span and its parent.
        instrumentation_info: Deprecated description of the instrumenting
            library. Pass ``instrumentation_scope`` instead.
        status: Status of the operation the span represents. Defaults to a
            status whose code is ``UNSET``.
        start_time: Start of the span in nanoseconds since the Unix epoch, or
            ``None`` for a span that was never started.
        end_time: End of the span in nanoseconds since the Unix epoch, or
            ``None`` for a span that has not ended.
        instrumentation_scope: Name, version, schema URL and attributes of the
            instrumenting library the span came from.
    """

    def __init__(
        self,
        name: str,
        context: trace_api.SpanContext | None = None,
        parent: trace_api.SpanContext | None = None,
        resource: Resource | None = None,
        attributes: types.Attributes = None,
        events: Sequence[Event] = (),
        links: Sequence[trace_api.Link] = (),
        kind: trace_api.SpanKind = trace_api.SpanKind.INTERNAL,
        instrumentation_info: InstrumentationInfo | None = None,
        status: Status = Status(StatusCode.UNSET),
        start_time: int | None = None,
        end_time: int | None = None,
        instrumentation_scope: InstrumentationScope | None = None,
    ) -> None:
        """Build the instance.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        self._name = name
        self._context = context
        self._kind = kind
        self._instrumentation_info = instrumentation_info
        self._instrumentation_scope = instrumentation_scope
        self._parent = parent
        self._start_time = start_time
        self._end_time = end_time
        self._attributes = attributes
        self._events = events
        self._links = links
        if resource is None:
            self._resource = Resource.create({})
        else:
            self._resource = resource
        self._status = status

    @property
    def dropped_attributes(self) -> int:
        """Number of attributes the attribute limit kept out of this span.

        The count covers keys rejected because the span already held as many
        attributes as the limit allows, and keys that were neither non-empty
        strings nor convertible to one. Truncating a long string value is not a
        drop, and neither is replacing a value of an unusable type with
        ``None``, so neither of those shows up here.

        Returns:
            The number of dropped attributes, or ``0`` when the attributes
            were not stored in a bounded mapping, which is the case for a
            ``ReadableSpan`` built directly.
        """
        if isinstance(self._attributes, BoundedAttributes):
            return self._attributes.dropped
        return 0

    @property
    def dropped_events(self) -> int:
        """Number of events the event limit kept out of this span.

        Appending to a full event list discards the oldest event rather than
        the new one, so a span that overflowed keeps its most recent events and
        this count says how many earlier ones were lost.

        Returns:
            The number of dropped events, or ``0`` when the events were not
            stored in a bounded list.
        """
        if isinstance(self._events, BoundedList):
            return self._events.dropped
        return 0

    @property
    def dropped_links(self) -> int:
        """Number of links the link limit kept out of this span.

        As with events, the oldest link is discarded when a full list is
        appended to. Links refused at creation for having neither a valid
        context, attributes nor a trace state were never counted here.

        Returns:
            The number of dropped links, or ``0`` when the links were not
            stored in a bounded list.
        """
        if isinstance(self._links, BoundedList):
            return self._links.dropped
        return 0

    @property
    def name(self) -> str:
        """Name of the span.

        Returns:
            The name the span was created with, or the one last given to
            ``Span.update_name`` before it ended.
        """
        return self._name

    def get_span_context(self) -> trace_api.SpanContext | None:
        """Return the span context, the method form the tracing API declares.

        Returns:
            The same object the ``context`` property returns: the span context
            carrying the trace id, the span id, the flags and the trace state,
            or ``None`` when the span was built without one.
        """
        return self._context

    @property
    def context(self):
        """Span context of this span, also returned by ``get_span_context``.

        Returns:
            The span context, or ``None`` when the span was built without one.
        """
        return self._context

    @property
    def kind(self) -> trace_api.SpanKind:
        """Relationship between this span and its parent.

        Returns:
            The kind asked for when the span was created, which is
            ``SpanKind.INTERNAL`` unless the caller said otherwise. It cannot
            be changed afterwards.
        """
        return self._kind

    @property
    def parent(self) -> trace_api.SpanContext | None:
        """Span context of the span that started this one.

        Returns:
            The parent span context, or ``None`` for a root span.
            ``Tracer.start_span`` records ``None`` both when there was no
            current span and when the current span context was invalid, so
            ``None`` does not mean the caller failed to propagate anything.
        """
        return self._parent

    @property
    def start_time(self) -> int | None:
        """Time the span started, in nanoseconds since the Unix epoch.

        Returns:
            The start timestamp, or ``None`` for a span on which ``start`` was
            never called.
        """
        return self._start_time

    @property
    def end_time(self) -> int | None:
        """Time the span ended, in nanoseconds since the Unix epoch.

        The value is set at the beginning of ``Span.end``, before the
        ``_on_ending`` callbacks run, so a processor reading it from one of
        those callbacks already sees it.

        Returns:
            The end timestamp, or ``None`` while the span has not ended.
        """
        return self._end_time

    @property
    def status(self) -> trace_api.Status:
        """Status of the operation the span represents.

        A span starts out ``UNSET``. ``Span.set_status`` raises it to ``ERROR``
        or to ``OK`` and refuses to lower it again.

        Returns:
            The status, carrying a code and an optional description.
        """
        return self._status

    @property
    def attributes(self) -> types.Attributes:
        """Attributes recorded on the span, behind a read-only view.

        The view wraps the container the span writes into rather than copying
        it, so reading it again after the span records another attribute shows
        the new value. That holds only for a span that already carried at
        least one attribute when the view was taken: an empty container is
        falsy, so a view taken from a span with no attributes wraps a
        throwaway empty mapping and never changes. Reading the property again
        always reports the current attributes either way. An ended span
        records nothing further, which is what makes the view of an ended
        span stable.

        Returns:
            A mapping proxy over the attributes, empty when the span has none.
            Writing through it raises ``TypeError``.
        """
        return MappingProxyType(self._attributes or {})

    @property
    def events(self) -> Sequence[Event]:
        """Events recorded on the span, oldest first.

        A new tuple is built on every access, so what you get is a snapshot
        and a later event never appears in a tuple already taken. The ``Event``
        objects inside it are shared, not copied.

        Returns:
            A tuple of the events the span still holds, which excludes any the
            event limit dropped.
        """
        return tuple(self._events)

    @property
    def links(self) -> Sequence[trace_api.Link]:
        """Links recorded on the span, oldest first.

        A new tuple is built on every access, so what you get is a snapshot.
        Links refused at creation never appear here.

        Returns:
            A tuple of the links the span still holds, which excludes any the
            link limit dropped.
        """
        return tuple(self._links)

    @property
    def resource(self) -> Resource:
        """Resource describing the entity that produced the span.

        A span takes this from its tracer as it is created and keeps that same
        object afterwards, so replacing the resource of the provider does not
        change the resource of a span that already exists.

        Returns:
            The resource. Never ``None``: a span built without one gets
            whatever the configured resource detectors produce.
        """
        return self._resource

    @property
    @deprecated("You should use instrumentation_scope. Deprecated since version 1.11.1.")
    def instrumentation_info(self) -> InstrumentationInfo | None:
        """Deprecated description of the instrumenting library.

        Returns:
            The instrumentation info given at creation, or ``None``. Read
            ``instrumentation_scope`` instead, which carries the same name,
            version and schema URL plus the attributes of the scope.
        """
        return self._instrumentation_info

    @property
    def instrumentation_scope(self) -> InstrumentationScope | None:
        """Scope of the instrumenting library the span came from.

        Returns:
            The scope the tracer was obtained for, carrying its name, version,
            schema URL and attributes, or ``None`` for a span built without
            one.
        """
        return self._instrumentation_scope

    def to_json(self, indent: int | None = 4):
        """Render the span as a JSON document.

        The document holds the name, the context, the kind, the parent span id,
        the start and end times as ISO 8601 strings, the status, the
        attributes, the events, the links and the resource. The instrumentation
        scope and the dropped counts are left out, which makes this a readable
        dump and not a wire format.

        Args:
            indent: Number of spaces to indent each nested level by. ``None``
                produces the compact single-line form.

        Returns:
            The JSON document as a string.
        """
        parent_id = None
        if self.parent is not None:
            parent_id = f"0x{trace_api.format_span_id(self.parent.span_id)}"

        start_time = None
        if self._start_time:
            start_time = util.ns_to_iso_str(self._start_time)

        end_time = None
        if self._end_time:
            end_time = util.ns_to_iso_str(self._end_time)

        status = {
            "status_code": str(self._status.status_code.name),
        }
        if self._status.description:
            status["description"] = self._status.description

        f_span = {
            "name": self._name,
            "context": (self._format_context(self._context) if self._context else None),
            "kind": str(self.kind),
            "parent_id": parent_id,
            "start_time": start_time,
            "end_time": end_time,
            "status": status,
            "attributes": self._format_attributes(self._attributes),
            "events": self._format_events(self._events),
            "links": self._format_links(self._links),
            "resource": json.loads(self.resource.to_json()),
        }

        return json.dumps(f_span, indent=indent)

    @staticmethod
    def _format_context(context: SpanContext) -> dict[str, str]:
        """Render one span context for ``to_json``.

        The trace id and the span id come out as lowercase hexadecimal behind
        an ``0x`` prefix, padded to their full width, and the trace state comes
        out as its ``repr``.

        Args:
            context: The span context to render.

        Returns:
            A dict holding the ``trace_id``, ``span_id`` and ``trace_state``
            keys.
        """
        return {
            "trace_id": f"0x{trace_api.format_trace_id(context.trace_id)}",
            "span_id": f"0x{trace_api.format_span_id(context.span_id)}",
            "trace_state": repr(context.trace_state),
        }

    @staticmethod
    def _format_attributes(
        attributes: types.Attributes,
    ) -> dict[str, Any] | None:
        """Coerce an attribute mapping into something ``json.dumps`` accepts.

        A bounded mapping is copied into a plain dict. A plain dict and
        ``None`` are handed back untouched, so the result is sometimes the very
        object that was passed in.

        Args:
            attributes: The attributes to render, or ``None``.

        Returns:
            A plain dict of the attributes, or ``None`` when there were none.
        """
        if attributes is not None and not isinstance(attributes, dict):
            return dict(attributes)
        return attributes

    @staticmethod
    def _format_events(events: Sequence[Event]) -> list[dict[str, Any]]:
        """Render events for ``to_json``.

        Each timestamp becomes an ISO 8601 string and each attribute mapping is
        flattened into a plain dict. The dropped attribute count of an event is
        left out.

        Args:
            events: The events to render, in the order they should appear.

        Returns:
            A list of dicts holding the ``name``, ``timestamp`` and
            ``attributes`` keys.
        """
        return [
            {
                "name": event.name,
                "timestamp": util.ns_to_iso_str(event.timestamp),
                "attributes": Span._format_attributes(  # pylint: disable=protected-access
                    event.attributes
                ),
            }
            for event in events
        ]

    @staticmethod
    def _format_links(links: Sequence[trace_api.Link]) -> list[dict[str, Any]]:
        """Render links for ``to_json``.

        Each link contributes the span context it points at and its attributes.
        The dropped attribute count of a link is left out.

        Args:
            links: The links to render, in the order they should appear.

        Returns:
            A list of dicts holding the ``context`` and ``attributes`` keys.
        """
        return [
            {
                "context": Span._format_context(  # pylint: disable=protected-access
                    link.context
                ),
                "attributes": Span._format_attributes(  # pylint: disable=protected-access
                    link.attributes
                ),
            }
            for link in links
        ]


class SpanLimits:
    """The limits that should be enforced on recorded data such as events, links, attributes etc.

    This class does not enforce any limits itself. It only provides a way to read limits from env,
    default values and from user provided arguments.

    All limit arguments must be either a non-negative integer, ``None`` or ``SpanLimits.UNSET``.

    - All limit arguments are optional.
    - If a limit argument is not set, the class will try to read its value from the corresponding
      environment variable.
    - If the environment variable is not set, the default value, if any, will be used.

    Limit precedence:

    - If a model specific limit is set, it will be used.
    - Else if the corresponding global limit is set, it will be used.
    - Else if the model specific limit has a default value, the default value will be used.
    - Else if the global limit has a default value, the default value will be used.

    Passing ``SpanLimits.UNSET`` for a limit removes it, so that nothing is
    capped. An environment variable set to the empty string, or to whitespace
    alone, has the same effect. A negative number raises ``ValueError`` out of
    the constructor instead of being ignored, and so does an environment
    variable whose value does not parse as an integer. A limit argument is
    never parsed and never type checked, so one that cannot be compared with
    an integer, a string for instance, raises ``TypeError`` from that
    comparison, and a float is accepted and stored as it is.

    ``max_attributes`` is the exception to both of those. When it resolves to
    no limit, whether because ``UNSET`` was passed or because the environment
    variable was empty, 128 is stored instead, so the global attribute limit
    can never be removed. The three specific attribute limits fall back on 128
    in the same case, so removing the global limit does not remove them either.
    A span applies the three specific limits, never this one: ``max_attributes``
    only ever acts as their default.

    Args:
        max_attributes: Maximum number of attributes that can be added to a span, event, and link.
            Environment variable: OTEL_ATTRIBUTE_COUNT_LIMIT
            Default: 128
        max_events: Maximum number of events that can be added to a Span.
            Environment variable: OTEL_SPAN_EVENT_COUNT_LIMIT
            Default: 128
        max_links: Maximum number of links that can be added to a Span.
            Environment variable: OTEL_SPAN_LINK_COUNT_LIMIT
            Default: 128
        max_span_attributes: Maximum number of attributes that can be added to a Span.
            Environment variable: OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT
            Default: the global attribute limit, 128 when that is unset too.
        max_event_attributes: Maximum number of attributes that can be added to an Event.
            Environment variable: OTEL_EVENT_ATTRIBUTE_COUNT_LIMIT
            Default: the global attribute limit, 128 when that is unset too.
        max_link_attributes: Maximum number of attributes that can be added to a Link.
            Environment variable: OTEL_LINK_ATTRIBUTE_COUNT_LIMIT
            Default: the global attribute limit, 128 when that is unset too.
        max_attribute_length: Maximum length an attribute value can have. Values longer than
            the specified length will be truncated.
            Environment variable: OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT
            Default: no limit, so values are never truncated.
        max_span_attribute_length: Maximum length a span attribute value can have. Values longer than
            the specified length will be truncated.
            Environment variable: OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT
            Default: whatever ``max_attribute_length`` resolved to.
    """

    UNSET = -1

    def __init__(
        self,
        max_attributes: int | None = None,
        max_events: int | None = None,
        max_links: int | None = None,
        max_span_attributes: int | None = None,
        max_event_attributes: int | None = None,
        max_link_attributes: int | None = None,
        max_attribute_length: int | None = None,
        max_span_attribute_length: int | None = None,
    ):
        """Resolve each limit from the arguments, the environment and defaults.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders. The resolution happens once, here, so
        changing an environment variable afterwards has no effect on an
        instance that already exists.

        Raises:
            ValueError: If an argument or the environment variable backing it
                is negative, or if the environment variable does not parse as
                an integer. The message names the environment variable even
                when the offending value came from the argument.
            TypeError: If an argument cannot be compared with an integer, a
                string for instance. Arguments are never parsed, so one of the
                wrong type reaches that comparison unconverted.
        """
        # span events and links count
        self.max_events = self._from_env_if_absent(
            max_events,
            OTEL_SPAN_EVENT_COUNT_LIMIT,
            _DEFAULT_OTEL_SPAN_EVENT_COUNT_LIMIT,
        )
        self.max_links = self._from_env_if_absent(
            max_links,
            OTEL_SPAN_LINK_COUNT_LIMIT,
            _DEFAULT_OTEL_SPAN_LINK_COUNT_LIMIT,
        )

        # attribute count
        global_max_attributes = self._from_env_if_absent(max_attributes, OTEL_ATTRIBUTE_COUNT_LIMIT)
        self.max_attributes = (
            global_max_attributes if global_max_attributes is not None else _DEFAULT_OTEL_ATTRIBUTE_COUNT_LIMIT
        )

        self.max_span_attributes = self._from_env_if_absent(
            max_span_attributes,
            OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT,
            (global_max_attributes if global_max_attributes is not None else _DEFAULT_OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT),
        )
        self.max_event_attributes = self._from_env_if_absent(
            max_event_attributes,
            OTEL_EVENT_ATTRIBUTE_COUNT_LIMIT,
            (global_max_attributes if global_max_attributes is not None else _DEFAULT_OTEL_EVENT_ATTRIBUTE_COUNT_LIMIT),
        )
        self.max_link_attributes = self._from_env_if_absent(
            max_link_attributes,
            OTEL_LINK_ATTRIBUTE_COUNT_LIMIT,
            (global_max_attributes if global_max_attributes is not None else _DEFAULT_OTEL_LINK_ATTRIBUTE_COUNT_LIMIT),
        )

        # attribute length
        self.max_attribute_length = self._from_env_if_absent(
            max_attribute_length,
            OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT,
        )
        self.max_span_attribute_length = self._from_env_if_absent(
            max_span_attribute_length,
            OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT,
            # use global attribute length limit as default
            self.max_attribute_length,
        )

    def __repr__(self):
        """Render every resolved limit on one line.

        ``max_span_attribute_length`` is the one limit left out.

        Returns:
            A string naming the class and the limits it resolved to, where
            ``None`` means that limit caps nothing.
        """
        return f"{type(self).__name__}(max_span_attributes={self.max_span_attributes}, max_events_attributes={self.max_event_attributes}, max_link_attributes={self.max_link_attributes}, max_attributes={self.max_attributes}, max_events={self.max_events}, max_links={self.max_links}, max_attribute_length={self.max_attribute_length})"

    @classmethod
    def _from_env_if_absent(cls, value: int | None, env_var: str, default: int | None = None) -> int | None:
        """Resolve one limit from the argument, the environment or the default.

        An argument equal to ``UNSET`` wins over everything and removes the
        limit. Any other argument is used as given. Only when no argument was
        passed is ``env_var`` read, and only when it is absent from the
        environment is ``default`` used. An environment variable present but
        empty, or whitespace alone, also removes the limit, which is not the
        same as being absent.

        Args:
            value: The limit the caller asked for, ``None`` when the caller
                said nothing, or ``UNSET`` to remove the limit.
            env_var: Name of the environment variable to read when ``value``
                is ``None``. Its value is stripped and lowercased before being
                parsed.
            default: What to return when ``value`` is ``None`` and ``env_var``
                is absent from the environment. ``None`` means no limit.

        Returns:
            The resolved limit, or ``None`` when nothing should be capped.

        Raises:
            ValueError: If the resolved value is negative, or if the
                environment variable does not parse as an integer. The message
                names ``env_var`` in both cases, including when the offending
                value came from ``value``.
            TypeError: If ``value`` is neither ``None`` nor ``UNSET`` and
                cannot be compared with an integer, a string for instance.
                Only the environment variable is ever parsed, so a ``value``
                of the wrong type reaches the comparison unconverted.
        """
        if value == cls.UNSET:
            return None

        err_msg = "{} must be a non-negative integer but got {}"

        # if no value is provided for the limit, try to load it from env
        if value is None:
            # return default value if env var is not set
            if env_var not in environ:
                return default

            str_value = environ.get(env_var, "").strip().lower()
            if str_value == _ENV_VALUE_UNSET:
                return None

            try:
                value = int(str_value)
            except ValueError:
                raise ValueError(err_msg.format(env_var, str_value))

        if value < 0:
            raise ValueError(err_msg.format(env_var, value))
        return value


_UnsetLimits = SpanLimits(
    max_attributes=SpanLimits.UNSET,
    max_events=SpanLimits.UNSET,
    max_links=SpanLimits.UNSET,
    max_span_attributes=SpanLimits.UNSET,
    max_event_attributes=SpanLimits.UNSET,
    max_link_attributes=SpanLimits.UNSET,
    max_attribute_length=SpanLimits.UNSET,
    max_span_attribute_length=SpanLimits.UNSET,
)

# not removed for backward compat. please use SpanLimits instead.
SPAN_ATTRIBUTE_COUNT_LIMIT = SpanLimits._from_env_if_absent(  # pylint: disable=protected-access
    None,
    OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT,
    _DEFAULT_OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT,
)


class Span(trace_api.Span, ReadableSpan):
    """See `opentelemetry.trace.Span`.

    Users should create `Span` objects via the `Tracer` instead of this
    constructor.

    The attributes, the events and the links given here are copied into bounded
    containers as the span is built, so the limits apply to them as they do to
    anything recorded later. The attributes of each event and of each link are
    replaced in place with an immutable copy, which changes the ``Event`` and
    ``Link`` objects the caller passed in.

    Args:
        name: The name of the operation this span represents
        context: The immutable span context
        parent: This span's parent's `opentelemetry.trace.SpanContext`, or
            None if this is a root span
        sampler: The sampler used to create this span
        trace_config:  Unused. Originally intended for trace-level configuration
            from the OpenTelemetry protocol, but the upstream ``TraceConfig``
            proto was removed. Retained for backwards compatibility.
        resource: Entity producing telemetry
        attributes: The span's attributes to be exported
        events: Timestamped events to be exported
        links: Links to other spans to be exported
        span_processor: `SpanProcessor` to invoke when starting and ending
            this `Span`.
        limits: `SpanLimits` instance that was passed to the `TracerProvider`
        kind: Relationship between this span and its parent
        instrumentation_info: Deprecated description of the instrumenting
            library. Pass ``instrumentation_scope`` instead
        record_exception: Whether leaving a ``with`` block over this span by
            raising records the exception as an event on it. Only consulted by
            ``__exit__``, so it does nothing for a span that is ended by hand
        set_status_on_exception: Whether leaving a ``with`` block over this
            span by raising sets its status to ``ERROR``. Only consulted by
            ``__exit__``
        instrumentation_scope: Name, version, schema URL and attributes of the
            instrumenting library this span came from
        record_end_metrics: Called once, with no arguments, at the start of
            ``end``, to decrement the count of live spans. A tracer always
            passes a callable, one that does nothing when the internal SDK
            metrics are switched off. ``None`` counts nothing at all and is
            what a span built outside a tracer gets
    """

    def __new__(cls, *args, **kwargs):
        """Build an instance of a subclass and refuse to build a bare ``Span``.

        ``Tracer.start_span`` creates ``_Span``, the only subclass this package
        defines. Creating a ``Span`` directly is the mistake this guards
        against.

        Args:
            *args: Accepted so that the constructor arguments may be passed
                positionally. They are discarded here.
            **kwargs: Accepted so that the constructor arguments may be passed
                by keyword. They are discarded here.

        Returns:
            The new instance, before ``__init__`` has run on it.

        Raises:
            TypeError: If the class being instantiated is ``Span`` itself.
        """
        if cls is Span:
            raise TypeError("Span must be instantiated via a tracer.")
        return super().__new__(cls)

    # pylint: disable=too-many-locals
    def __init__(
        self,
        name: str,
        context: trace_api.SpanContext,
        parent: trace_api.SpanContext | None = None,
        sampler: sampling.Sampler | None = None,
        trace_config: None = None,
        resource: Resource | None = None,
        attributes: types.Attributes = None,
        events: Sequence[Event] | None = None,
        links: Sequence[trace_api.Link] = (),
        kind: trace_api.SpanKind = trace_api.SpanKind.INTERNAL,
        span_processor: SpanProcessor = SpanProcessor(),
        instrumentation_info: InstrumentationInfo | None = None,
        record_exception: bool = True,
        set_status_on_exception: bool = True,
        limits=_UnsetLimits,
        instrumentation_scope: InstrumentationScope | None = None,
        *,
        record_end_metrics: Callable[[], None] | None = None,
    ) -> None:
        """Build the span, without starting it.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders. The span has no start time until
        ``start`` is called, and ``end`` on a span that was never started
        raises.
        """
        if resource is None:
            resource = Resource.create({})
        super().__init__(
            name=name,
            context=context,
            parent=parent,
            kind=kind,
            resource=resource,
            instrumentation_info=instrumentation_info,
            instrumentation_scope=instrumentation_scope,
        )
        self._sampler = sampler
        self._trace_config = trace_config
        self._record_exception = record_exception
        self._set_status_on_exception = set_status_on_exception
        self._span_processor = span_processor
        self._limits = limits
        self._lock = threading.Lock()
        # Identifier of the thread running end() while the _on_ending
        # callbacks execute: the end timestamp is already set, but the span
        # must remain mutable from that thread until the callbacks return.
        self._ending_thread: int | None = None
        self._attributes = BoundedAttributes(
            self._limits.max_span_attributes,
            attributes,
            immutable=False,
            max_value_len=self._limits.max_span_attribute_length,
        )
        self._events = self._new_events()
        if events:
            for event in events:
                # Immutable set to true so attributes cannot be added or removed after creation.
                event._attributes = BoundedAttributes(
                    self._limits.max_event_attributes,
                    event.attributes,
                    max_value_len=self._limits.max_attribute_length,
                    immutable=True,
                )
                self._events.append(event)

        self._links = self._new_links(links)

        self._record_end_metrics = record_end_metrics

    def __repr__(self):
        """Render the span as its type, its name and its span context.

        The attributes, events, links, status and timings are left out, so two
        spans that differ only in what they recorded print the same.

        Returns:
            A string of the form ``_Span(name="...", context=...)``, naming the
            concrete subclass rather than ``Span``.
        """
        return f'{type(self).__name__}(name="{self._name}", context={self._context})'

    def _new_events(self):
        """Build the empty container the span appends events to.

        Returns:
            A bounded list capped at ``max_events``. Appending to it once it is
            full discards the oldest event and raises the dropped count.
        """
        return BoundedList(self._limits.max_events)

    def _new_links(self, links: Sequence[trace_api.Link]):
        """Build the link container, seeded with the links worth keeping.

        A link that is falsy, or that has neither a valid context, attributes
        nor a trace state, is left out without a word. The attributes of each
        link that survives are replaced in place with an immutable, bounded
        copy, which mutates the ``Link`` object the caller passed in.

        Args:
            links: Links given to the constructor. An empty sequence, which is
                the usual case, skips the filtering and produces an empty
                container.

        Returns:
            A bounded list capped at ``max_links``. When more links survive the
            filtering than the cap allows, the oldest are dropped.
        """
        if not links:
            return BoundedList(self._limits.max_links)

        valid_links = []
        for link in links:
            if link and _is_valid_link(link.context, link.attributes):
                # Immutable set to true so attributes cannot be added or removed after creation.
                # pylint: disable=protected-access
                link._attributes = BoundedAttributes(
                    self._limits.max_link_attributes,
                    link.attributes,
                    max_value_len=self._limits.max_attribute_length,
                    immutable=True,
                )
                valid_links.append(link)

        return BoundedList.from_seq(self._limits.max_links, valid_links)

    def get_span_context(self) -> trace_api.SpanContext:
        """Return the span context, which a span built by a tracer always has.

        Returns:
            The span context the tracer assigned at creation. The cast only
            narrows the type the base class declares to one that cannot be
            ``None``; no check is performed at runtime.
        """
        return typing.cast(trace_api.SpanContext, self._context)

    def set_attributes(self, attributes: Mapping[str, types.AnyValue]) -> None:
        """Record several attributes in one pass.

        A key that is already present is overwritten and moves to the end of
        the insertion order, so it does not count against the attribute limit a
        second time. Once the span holds as many attributes as the limit
        allows, further new keys are dropped and counted in
        ``dropped_attributes``, and a warning is logged for the first drop
        only. On a span that has ended the call logs a warning and records
        nothing.

        Args:
            attributes: Mapping of attribute name to value. A string value
                longer than the configured limit is truncated, and a value of a
                type that cannot be used as an attribute is replaced with
                ``None`` rather than dropped.
        """
        with self._lock:
            if not self._is_mutable():
                logger.warning("Setting attribute on ended span.")
                return

            self._attributes._set_items(attributes)  # pylint: disable=protected-access

    def set_attribute(self, key: str, value: types.AnyValue) -> None:
        """Record a single attribute.

        A key that is already present is overwritten and moves to the end of
        the insertion order. Once the span holds as many attributes as the
        limit allows, a new key is dropped and counted in
        ``dropped_attributes``. On a span that has ended the call logs a
        warning and records nothing.

        Args:
            key: Attribute name. Anything that is not a non-empty string is
                rejected with a warning and counted as dropped.
            value: Attribute value. A string longer than the configured limit
                is truncated, which is not counted as a drop.
        """
        with self._lock:
            if not self._is_mutable():
                logger.warning("Setting attribute on ended span.")
                return

            self._attributes[key] = value

    @_check_span_ended
    def _add_event(self, event: EventBase) -> None:
        """Append an already built event to the span.

        The decorator takes the span lock and skips the append, with a warning,
        once the span has ended. The event is stored as it arrives: no limit is
        applied to its attributes here, so the caller has to have applied one.

        Args:
            event: The event to append. Appending to a full event list discards
                the oldest event and raises ``dropped_events``.
        """
        self._events.append(event)

    def add_event(
        self,
        name: str,
        attributes: types.Attributes = None,
        timestamp: int | None = None,
    ) -> None:
        """Record a timestamped annotation on the span.

        The attributes are capped at ``max_event_attributes`` and frozen before
        the event is built, so nothing can change them afterwards. The value
        length applied to them is the global ``max_attribute_length`` and not
        the span specific one. On a span that has ended the call logs a warning
        and records nothing.

        Args:
            name: Name of the event. It is recorded as given, with no length
                limit applied.
            attributes: Attributes of the event, or ``None`` for none.
            timestamp: Time of the event in nanoseconds since the Unix epoch.
                ``None`` reads the clock as the ``Event`` is built, which is
                after the attributes have been capped and frozen.
        """
        # Immutable set to true so attributes cannot be added or removed after creation.
        attributes = BoundedAttributes(
            self._limits.max_event_attributes,
            attributes,
            max_value_len=self._limits.max_attribute_length,
            immutable=True,
        )
        self._add_event(
            Event(
                name=name,
                attributes=attributes,
                timestamp=timestamp,
            )
        )

    @_check_span_ended
    def _add_link(self, link: trace_api.Link) -> None:
        """Append an already built link to the span.

        The decorator takes the span lock and skips the append, with a warning,
        once the span has ended. No validation and no attribute limit are
        applied here, so the caller has to have applied both.

        Args:
            link: The link to append. Appending to a full link list discards
                the oldest link and raises ``dropped_links``.
        """
        self._links.append(link)

    def add_link(
        self,
        context: SpanContext,
        attributes: types.Attributes = None,
    ) -> None:
        """Record a link from this span to another one.

        A link whose context is invalid is kept only when it carries
        attributes or a trace state. Otherwise the call returns having recorded
        nothing and logged nothing, which makes a mistyped context hard to
        notice. The attributes are capped at ``max_link_attributes`` and
        frozen. On a span that has ended the call logs a warning and records
        nothing.

        Args:
            context: Span context of the span being linked to.
            attributes: Attributes of the link, or ``None`` for none. They
                count towards whether an invalid context is kept.
        """
        if not _is_valid_link(context, attributes):
            return
        # Immutable set to true so attributes cannot be added or removed after creation.
        attributes = BoundedAttributes(
            self._limits.max_link_attributes,
            attributes,
            max_value_len=self._limits.max_attribute_length,
            immutable=True,
        )
        self._add_link(
            trace_api.Link(
                context=context,
                attributes=attributes,
            )
        )

    def _readable_span(self) -> ReadableSpan:
        """Take the read-only snapshot handed to the ``on_end`` callbacks.

        The containers holding the attributes, the events and the links are
        shared with this span rather than copied, which is safe because ``end``
        freezes the attributes before calling this. Nothing is read under the
        span lock.

        Returns:
            A ``ReadableSpan`` carrying the current name, context, parent,
            resource, kind, status, timings and instrumentation scope.
        """
        return ReadableSpan(
            name=self._name,
            context=self._context,
            parent=self._parent,
            resource=self._resource,
            attributes=self._attributes,
            events=self._events,
            links=self._links,
            kind=self.kind,
            status=self._status,
            start_time=self._start_time,
            end_time=self._end_time,
            instrumentation_info=self._instrumentation_info,
            instrumentation_scope=self._instrumentation_scope,
        )

    def start(
        self,
        start_time: int | None = None,
        parent_context: context_api.Context | None = None,
    ) -> None:
        """Record the start time and run the ``on_start`` callbacks.

        A second call logs a warning and does nothing, so neither the start
        time nor the callbacks are repeated. The callbacks run on the calling
        thread with the span lock released, and an exception from one of them
        propagates to the caller, leaving the span started and the remaining
        callbacks uncalled.

        Args:
            start_time: Start of the span in nanoseconds since the Unix epoch.
                ``None`` reads the clock now.
            parent_context: Context the span was started in, handed to the
                processors unchanged. ``None`` means the current context.
        """
        with self._lock:
            if self._start_time is not None:
                logger.warning("Calling start() on a started span.")
                return
            self._start_time = start_time if start_time is not None else time_ns()

        self._span_processor.on_start(self, parent_context=parent_context)

    def end(self, end_time: int | None = None) -> None:
        """Record the end time of the span and run the end callbacks.

        The end time is taken first. The metrics callback and then the
        ``_on_ending`` callbacks run next, and throughout those the span stays
        mutable for this one thread, so a processor can still add an attribute
        to it. The attributes are frozen once they return, whether or not they
        raised, and only then is the read-only snapshot handed to the
        ``on_end`` callbacks. An exception out of the metrics callback or out
        of ``_on_ending`` therefore leaves a span that is ended and frozen but
        was never delivered to ``on_end``.

        A second call logs a warning and changes nothing, so the end time and
        the callbacks are not repeated.

        Args:
            end_time: End of the span in nanoseconds since the Unix epoch.
                ``None`` reads the clock now. No check is made that it is later
                than the start time.

        Raises:
            RuntimeError: If ``start`` was never called on this span.
        """
        with self._lock:
            if self._start_time is None:
                raise RuntimeError("Calling end() on a not started span.")
            if self._end_time is not None:
                logger.warning("Calling end() on an ended span.")
                return

            self._ending_thread = threading.get_ident()
            self._end_time = end_time if end_time is not None else time_ns()

        # The span must remain mutable from this thread while the _on_ending
        # callbacks run; it becomes immutable once they have returned.
        # pylint: disable=protected-access
        try:
            if self._record_end_metrics:
                self._record_end_metrics()
            self._span_processor._on_ending(self)
        finally:
            with self._lock:
                self._ending_thread = None
                self._attributes._immutable = True
        self._span_processor.on_end(self._readable_span())

    @_check_span_ended
    def update_name(self, name: str) -> None:
        """Replace the name of the span.

        On a span that has ended the call logs a warning and leaves the name
        alone. A span processor that renames spans has to do it from
        ``_on_ending``, since by ``on_end`` the span is no longer mutable.

        Args:
            name: The new name, recorded as given with no length limit
                applied.
        """
        self._name = name

    def _is_mutable(self) -> bool:
        """Say whether the span still accepts changes.

        A span is mutable until its end time is recorded, and then stays
        mutable for the single thread that is inside ``end`` running the
        ``_on_ending`` callbacks. Callers are expected to hold the span lock,
        since the answer can change under them otherwise.

        Returns:
            ``True`` while the span still accepts changes.
        """
        return self._end_time is None or self._ending_thread == threading.get_ident()

    def is_recording(self) -> bool:
        """Say whether anything recorded on the span would still be kept.

        The answer is read without the span lock, so it can be stale by the
        time the caller acts on it: another thread may end the span in between.

        Returns:
            ``True`` while the span accepts changes, which lasts until ``end``
            has run its ``_on_ending`` callbacks.
        """
        # Unlike the mutators, this check is deliberately not taken under
        # self._lock: it does not modify the span, and the answer can become
        # stale as soon as it is returned anyway, since another thread may
        # end the span right after this call.
        return self._is_mutable()

    @_check_span_ended
    def set_status(
        self,
        status: Status | StatusCode,
        description: str | None = None,
    ) -> None:
        """Set the status of the operation the span represents.

        The new status is recorded only when it outranks the one already there,
        which ``_accepts_status`` decides. An argument that is neither a
        ``Status`` nor a ``StatusCode`` is ignored without a word. On a span
        that has ended the call logs a warning and changes nothing.

        Args:
            status: Either a ready made ``Status``, or a ``StatusCode`` to be
                paired with ``description``.
            description: Message to attach. Used only when ``status`` is a
                ``StatusCode``; passing it alongside a ``Status`` logs a
                warning and drops the message.
        """
        if isinstance(status, Status):
            if description is not None:
                logger.warning(
                    "Description %s ignored. Use either `Status` or `(StatusCode, Description)`",
                    description,
                )
            new_status = status
        elif isinstance(status, StatusCode):
            new_status = Status(status, description)
        else:
            return

        if self._accepts_status(new_status):
            self._status = new_status

    def _accepts_status(self, new_status: Status) -> bool:
        """Decide whether ``new_status`` may replace the status already recorded.

        The codes are totally ordered, ``Ok > Error > Unset``, an attempt to set
        ``Unset`` is ignored, and ``Ok`` is final. Once those two are handled, a
        differing code always outranks the one recorded. A repeat of the same code
        gets through only when it fills in a description that is still missing,
        and an empty description counts as missing.

        Args:
            new_status: The status ``set_status`` was asked to record.

        Returns:
            ``True`` when the recorded status should be replaced by
            ``new_status``.
        """
        if new_status.status_code is StatusCode.UNSET:
            return False

        current = self._status
        if current is None:
            return True
        if current.status_code is StatusCode.OK:
            return False

        # An empty description is equivalent to an absent one.
        return current.status_code is not new_status.status_code or (
            not current.description and bool(new_status.description)
        )

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Ends context manager and calls `end` on the `Span`.

        This runs when the span itself is used as a context manager, as in
        ``with tracer.start_span("name") as span:``. It is not what
        ``start_as_current_span`` goes through: that one uses
        ``opentelemetry.trace.use_span``, which does its own recording and
        then ends the span directly.

        When the block is left by raising and the span is still recording, the
        exception is recorded as an event with ``exception.escaped`` set to
        ``True``, unless the span was built with ``record_exception`` false,
        and the status is set to ``ERROR`` with the type and message of the
        exception as its description, unless the span was built with
        ``set_status_on_exception`` false. Any ``BaseException`` counts here,
        including ``KeyboardInterrupt`` and ``GeneratorExit``, which is wider
        than what ``use_span`` records. The span is ended either way and the
        exception is left to propagate.

        Args:
            exc_type: Type of the exception leaving the block, or ``None``.
                Unused.
            exc_val: The exception leaving the block, or ``None`` when the
                block finished normally. This is the value the method keys off.
            exc_tb: Traceback of the exception, or ``None``. Unused: the
                traceback is read off the exception itself.
        """
        if exc_val is not None and self.is_recording():
            # Record the exception as an event
            # pylint:disable=protected-access
            if self._record_exception:
                self.record_exception(exception=exc_val, escaped=True)
            # Records status if span is used as context manager
            # i.e. with tracer.start_span() as span:
            if self._set_status_on_exception:
                self.set_status(
                    Status(
                        status_code=StatusCode.ERROR,
                        description=(f"{type(exc_val).__name__}: {exc_val}"),
                    )
                )

        super().__exit__(exc_type, exc_val, exc_tb)

    def record_exception(
        self,
        exception: BaseException,
        attributes: types.Attributes = None,
        timestamp: int | None = None,
        escaped: bool = False,
    ) -> None:
        """Records an exception as a span event.

        The event is named ``exception`` and carries the type, the message and
        the formatted traceback of the exception. The type is qualified with
        its module unless the module is ``builtins``. The status of the span is
        left alone, so recording an exception does not by itself mark the span
        as failed. The event goes through ``add_event``, so the event limit
        applies to it and a span that has ended records nothing and logs a
        warning.

        Args:
            exception: The exception to record. The traceback is read off the
                exception, and one that was never raised has none, which
                yields a one-line trace holding only the type and the message.
            attributes: Extra attributes for the event, or ``None``. A key that
                collides with one of the four exception attributes replaces it.
            timestamp: Time of the event in nanoseconds since the Unix epoch.
                ``None`` reads the clock now.
            escaped: Recorded as the ``exception.escaped`` attribute, as the
                string ``"True"`` or ``"False"``. ``True`` says the exception
                ended the span by escaping its scope.
        """
        stacktrace = "".join(traceback.format_exception(exception))
        module = type(exception).__module__
        qualname = type(exception).__qualname__
        exception_type = f"{module}.{qualname}" if module and module != "builtins" else qualname
        _attributes: MutableMapping[str, types.AnyValue] = {
            EXCEPTION_TYPE: exception_type,
            EXCEPTION_MESSAGE: str(exception),
            EXCEPTION_STACKTRACE: stacktrace,
            EXCEPTION_ESCAPED: str(escaped),
        }
        if attributes:
            _attributes.update(attributes)
        self.add_event(name="exception", attributes=_attributes, timestamp=timestamp)


class _Span(Span):
    """Protected implementation of `opentelemetry.trace.Span`.

    This constructor exists to prevent the instantiation of the `Span` class
    by other mechanisms than through the `Tracer`.
    """


@dataclass
class _TracerConfig:
    """Settings a ``TracerProvider`` applies to each ``Tracer`` it hands out.

    A provider computes one of these per instrumentation scope when it creates
    a tracer, and replaces the one a tracer holds whenever its configurator
    changes.

    Args:
        is_enabled: Whether the tracer records anything. A disabled tracer
            returns a non-recording span from every ``start_span`` call and
            never consults its sampler.
    """

    is_enabled: bool

    @classmethod
    def default(cls):
        """Build the configuration a tracer gets when no rule matches it.

        Returns:
            A configuration that leaves the tracer enabled.
        """
        return cls(is_enabled=True)


class Tracer(trace_api.Tracer):
    """See `opentelemetry.trace.Tracer`.

    Obtain one from ``TracerProvider.get_tracer`` rather than building it
    directly. A tracer holds everything ``start_span`` needs: the sampler that
    decides whether a span records, the processors that are told when it starts
    and ends, and the limits applied while it records.

    Args:
        sampler: Decides, for each new span, whether it records and whether it
            is sampled. It may also add attributes and replace the trace state.
        resource: Resource attached to every span this tracer creates.
        span_processor: Told when a span of this tracer starts and ends. This
            is the multi processor held by the provider, so processors
            registered after the tracer was created are picked up as well.
        id_generator: Produces the trace ids and span ids of new spans.
        instrumentation_info: Deprecated description of the instrumenting
            library, recorded on spans for backwards compatibility.
        span_limits: Caps applied to the attributes, events and links of every
            span this tracer creates.
        instrumentation_scope: Scope recorded on every span this tracer
            creates.
        meter_provider: Provider for the internal SDK metrics. ``None`` reads
            the global meter provider as the tracer is built.
        _tracer_config: Configuration to start with. ``None`` leaves the tracer
            enabled. The provider replaces it when its configurator changes.
    """

    def __init__(
        self,
        sampler: sampling.Sampler,
        resource: Resource,
        span_processor: SynchronousMultiSpanProcessor | ConcurrentMultiSpanProcessor,
        id_generator: IdGenerator,
        instrumentation_info: InstrumentationInfo,
        span_limits: SpanLimits,
        instrumentation_scope: InstrumentationScope,
        *,
        meter_provider: metrics_api.MeterProvider | None = None,
        _tracer_config: _TracerConfig | None = None,
    ) -> None:
        """Build the tracer and its internal metric instruments.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders. Whether the internal instruments
        record anything is read once here, from
        ``OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED``.
        """
        self.sampler = sampler
        self.resource = resource
        self.span_processor = span_processor
        self.id_generator = id_generator
        self.instrumentation_info = instrumentation_info
        self._span_limits = span_limits
        self._instrumentation_scope = instrumentation_scope
        self._tracer_config = _tracer_config or _TracerConfig.default()

        meter_provider = meter_provider or metrics_api.get_meter_provider()
        self._tracer_metrics = create_tracer_metrics(
            meter_provider,
            parse_boolean_environment_variable(OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED),
        )

    def _set_tracer_config(self, tracer_config: _TracerConfig):
        """Replace the configuration this tracer consults.

        Called by ``TracerProvider._set_tracer_configurator`` for every tracer
        it has already handed out, which is how disabling reaches tracers that
        callers are still holding. Spans already started are unaffected.

        Args:
            tracer_config: The configuration to consult from now on.
        """
        self._tracer_config = tracer_config

    def _set_resource(self, resource: Resource) -> None:
        """Replace the resource attached to spans created from now on.

        Called by ``TracerProvider._update_resource``, which is how the new
        process attributes reach later spans after a fork. Spans that already
        exist keep the resource they were given.

        Args:
            resource: The resource to attach from now on.
        """
        self.resource = resource

    def _is_enabled(self) -> bool:
        """If the tracer is not enabled, start_span will create a NonRecordingSpan

        Returns:
            ``True`` while the configuration the provider last applied leaves
            this tracer enabled.
        """
        return self._tracer_config.is_enabled

    @_agnosticcontextmanager  # pylint: disable=protected-access
    def start_as_current_span(
        self,
        name: str,
        context: context_api.Context | None = None,
        kind: trace_api.SpanKind = trace_api.SpanKind.INTERNAL,
        attributes: types.Attributes = None,
        links: Sequence[trace_api.Link] | None = (),
        start_time: int | None = None,
        record_exception: bool = True,
        set_status_on_exception: bool = True,
        end_on_exit: bool = True,
    ) -> Iterator[trace_api.Span]:
        """Start a span and make it current for the duration of the block.

        The span is started before the block runs and, with ``end_on_exit``
        left true, ended when the block is left, however it is left. An
        exception escaping the block is recorded on the span and sets its
        status to ``ERROR``, both subject to the flags below, and is then
        re-raised. Only exceptions deriving from ``Exception`` are treated that
        way: a ``BaseException`` such as ``GeneratorExit`` passes through
        without being recorded.

        The returned object also works as a function decorator. An async
        function decorated with it is awaited inside the span, so the span
        covers the whole coroutine and not only its first suspension.

        Args:
            name: Name of the span.
            context: Context to take the parent span from. ``None`` uses the
                current context.
            kind: Relationship between this span and its parent.
            attributes: Attributes to record on the span at creation. They are
                also handed to the sampler.
            links: Links to record on the span. ``None`` is treated as empty.
            start_time: Start of the span in nanoseconds since the Unix epoch.
                ``None`` reads the clock now.
            record_exception: Whether an exception escaping the block is
                recorded on the span as an event.
            set_status_on_exception: Whether an exception escaping the block
                sets the status of the span to ``ERROR``. A status recorded by
                hand beforehand survives, unless it was an ``ERROR`` with no
                description, which the one built here fills in.
            end_on_exit: Whether leaving the block ends the span. Pass
                ``False`` to end it yourself later.

        Yields:
            The span, already started and already current.
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
        with trace_api.use_span(
            span,
            end_on_exit=end_on_exit,
            record_exception=record_exception,
            set_status_on_exception=set_status_on_exception,
        ) as span:
            yield span

    def start_span(  # pylint: disable=too-many-locals
        self,
        name: str,
        context: context_api.Context | None = None,
        kind: trace_api.SpanKind = trace_api.SpanKind.INTERNAL,
        attributes: types.Attributes = None,
        links: Sequence[trace_api.Link] | None = (),
        start_time: int | None = None,
        record_exception: bool = True,
        set_status_on_exception: bool = True,
    ) -> trace_api.Span:
        """Create a span and start it, leaving the current context untouched.

        The parent is the span context of the current span of ``context``. The
        sampler is then asked about the new span, with that parent, the trace
        id, the name, the kind, the attributes and the links. A decision that
        does not record produces a non-recording span, which carries the span
        context onwards for propagation and records nothing. A decision that
        records produces a span that is started here, so its ``on_start``
        callbacks have already run by the time this returns.

        A disabled tracer skips all of that and returns a non-recording span
        wrapping the parent span context, which may be ``None``.

        The new span takes the trace id of a valid parent and a fresh one
        otherwise. Attributes the sampler added and the trace state it returned
        both end up on the new span.

        Args:
            name: Name of the span.
            context: Context to take the parent span from. ``None`` uses the
                current context.
            kind: Relationship between this span and its parent.
            attributes: Attributes to record on the span at creation. They are
                handed to the sampler, and what reaches the span is what the
                sampler returned, which may differ.
            links: Links to record on the span. ``None`` is treated as empty.
            start_time: Start of the span in nanoseconds since the Unix epoch.
                ``None`` reads the clock now.
            record_exception: Whether an exception escaping a ``with`` block
                over the returned span is recorded on it as an event.
            set_status_on_exception: Whether an exception escaping a ``with``
                block over the returned span sets its status to ``ERROR``.

        Returns:
            The new span, already started. Ending it is left to the caller.

        Raises:
            TypeError: If the current span of ``context`` returns something
                that is neither a span context nor ``None``.
        """
        links = links or ()
        parent_span_context = trace_api.get_current_span(context).get_span_context()

        if parent_span_context is not None and not isinstance(parent_span_context, trace_api.SpanContext):
            raise TypeError("parent_span_context must be a SpanContext or None.")

        if not self._is_enabled():
            return trace_api.NonRecordingSpan(context=parent_span_context)

        # is_valid determines root span
        if parent_span_context is None or not parent_span_context.is_valid:
            parent_span_context = None
            trace_id = self.id_generator.generate_trace_id()
        else:
            trace_id = parent_span_context.trace_id

        # The sampler decides whether to create a real or no-op span at the
        # time of span creation. No-op spans do not record events, and are not
        # exported.
        # The sampler may also add attributes to the newly-created span, e.g.
        # to include information about the sampling result.
        # The sampler may also modify the parent span context's tracestate
        sampling_result = self.sampler.should_sample(context, trace_id, name, kind, attributes, links)

        trace_flags = (
            trace_api.TraceFlags(trace_api.TraceFlags.SAMPLED)
            if sampling_result.decision.is_sampled()
            else trace_api.TraceFlags(trace_api.TraceFlags.DEFAULT)
        )

        if parent_span_context is None:
            random_trace_id = self.id_generator.is_trace_id_random()
        else:
            random_trace_id = parent_span_context.trace_flags.random_trace_id

        if random_trace_id:
            trace_flags = trace_api.TraceFlags(trace_flags | trace_api.TraceFlags.RANDOM_TRACE_ID)

        span_context = trace_api.SpanContext(
            trace_id,
            self.id_generator.generate_span_id(),
            is_remote=False,
            trace_flags=trace_flags,
            trace_state=sampling_result.trace_state,
        )

        record_end_metrics = self._tracer_metrics.start_span(parent_span_context, sampling_result.decision)

        # Only record if is_recording() is true
        if sampling_result.decision.is_recording():
            # pylint:disable=protected-access
            span = _Span(
                name=name,
                context=span_context,
                parent=parent_span_context,
                sampler=self.sampler,
                resource=self.resource,
                attributes=sampling_result.attributes,
                span_processor=self.span_processor,
                kind=kind,
                links=links,
                instrumentation_info=self.instrumentation_info,
                record_exception=record_exception,
                set_status_on_exception=set_status_on_exception,
                limits=self._span_limits,
                instrumentation_scope=self._instrumentation_scope,
                record_end_metrics=record_end_metrics,
            )
            span.start(start_time=start_time, parent_context=context)
        else:
            span = trace_api.NonRecordingSpan(context=span_context)
        return span


_TracerConfiguratorT = Callable[[InstrumentationScope], _TracerConfig]
_RuleBasedTracerConfigurator = RuleBasedConfigurator[_TracerConfig]


def _default_tracer_configurator(
    tracer_scope: InstrumentationScope,
) -> _TracerConfig:
    """Default Tracer Configurator implementation

    In order to update Tracers configs you need to call
    TracerProvider._set_tracer_configurator with a function
    implementing this interface returning a Tracer Config.

    Args:
        tracer_scope: Scope of the tracer being configured. It is matched
            against an empty list of rules here, so it has no effect on the
            result.

    Returns:
        The default configuration, which leaves the tracer enabled.
    """
    return _RuleBasedTracerConfigurator(
        rules=[],
        default_config=_TracerConfig.default(),
    )(tracer_scope)


def _disable_tracer_configurator(
    tracer_scope: InstrumentationScope,
) -> _TracerConfig:
    """Configure every tracer as disabled, whatever its scope.

    Handing this to ``TracerProvider._set_tracer_configurator`` switches
    tracing off for the tracers already handed out as well as for the ones
    created later.

    Args:
        tracer_scope: Scope of the tracer being configured. It is matched
            against an empty list of rules here, so it has no effect on the
            result.

    Returns:
        A configuration whose ``is_enabled`` is ``False``.
    """
    return _RuleBasedTracerConfigurator(
        rules=[],
        default_config=_TracerConfig(is_enabled=False),
    )(tracer_scope)


class TracerProvider(trace_api.TracerProvider):
    """See `opentelemetry.trace.TracerProvider`.

    One provider owns the sampler, the resource, the id generator, the span
    limits and the registered span processors, and hands all of them to every
    tracer it creates. Tracers are cached per instrumentation scope, so asking
    twice for the same name, version, schema URL and attributes gives back the
    same tracer.

    Setting ``OTEL_SDK_DISABLED`` to ``true`` makes ``get_tracer`` return the
    no-op tracer of the API, and then none of what the provider holds is ever
    used. The variable is read once, as the provider is built.

    Args:
        sampler: Decides which spans record and which are sampled. ``None``
            reads the sampler out of the environment.
        resource: Resource attached to every span. ``None`` builds one from
            the configured resource detectors.
        shutdown_on_exit: Whether to register ``shutdown`` with ``atexit``, so
            that the processors get a chance to flush as the interpreter exits.
        active_span_processor: The multi processor that registered processors
            are added to. ``None`` builds a ``SynchronousMultiSpanProcessor``.
            Pass a ``ConcurrentMultiSpanProcessor`` to have the processors run
            in parallel instead.
        id_generator: Produces trace ids and span ids. ``None`` builds a
            ``RandomIdGenerator``.
        span_limits: Caps applied while a span records. ``None`` builds limits
            from the environment and the defaults.
        meter_provider: Provider for the internal SDK metrics, passed to every
            tracer. ``None`` makes each tracer read the global meter provider
            as it is created.
        _tracer_configurator: Maps an instrumentation scope to the
            configuration its tracer starts with. ``None`` leaves every tracer
            enabled.
    """

    def __init__(
        self,
        sampler: sampling.Sampler | None = None,
        resource: Resource | None = None,
        shutdown_on_exit: bool = True,
        active_span_processor: SynchronousMultiSpanProcessor | ConcurrentMultiSpanProcessor | None = None,
        id_generator: IdGenerator | None = None,
        span_limits: SpanLimits | None = None,
        *,
        meter_provider: metrics_api.MeterProvider | None = None,
        _tracer_configurator: _TracerConfiguratorT | None = None,
    ) -> None:
        """Build the provider and register its fork and exit hooks.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders. The hook registered with
        ``os.register_at_fork`` holds only a weak reference to this provider,
        so the hook does not keep this provider alive. ``os.register_at_fork``
        has no matching unregister call, so the hook stays registered for the
        life of the process and does nothing once the provider has been
        garbage collected.
        """
        self._active_span_processor = active_span_processor or SynchronousMultiSpanProcessor()
        if id_generator is None:
            self.id_generator = RandomIdGenerator()
        else:
            self.id_generator = id_generator
        if resource is None:
            self._resource = Resource.create({})
        else:
            self._resource = resource
        if not sampler:
            sampler = sampling._get_from_env_or_default()
        self.sampler = sampler
        self._span_limits = span_limits or SpanLimits()
        disabled = environ.get(OTEL_SDK_DISABLED, "")
        self._disabled = disabled.lower().strip() == "true"
        self._atexit_handler = None
        self._meter_provider = meter_provider

        if shutdown_on_exit:
            self._atexit_handler = atexit.register(self.shutdown)

        self._tracer_configurator = _tracer_configurator or _default_tracer_configurator
        self._tracers_lock = threading.Lock()
        self._tracers: dict[InstrumentationScope, Tracer] = {}
        if hasattr(os, "register_at_fork"):
            weak_at_fork = weakref.WeakMethod(self._handle_fork)

            def _after_in_child() -> None:
                """Run the provider's fork handler in the freshly forked child.

                ``os.register_at_fork`` keeps a strong reference to whatever is handed
                to it, so this closure holds the provider only weakly. A provider that
                has been garbage collected leaves the weak reference empty and the
                handler does nothing.
                """
                if at_fork := weak_at_fork():
                    at_fork()

            os.register_at_fork(after_in_child=_after_in_child)

    def _handle_fork(self) -> None:
        """Repair the provider in a child process after a fork.

        The tracers lock is replaced, since a lock inherited while another
        thread held it would never be released in the child. The attributes
        that depend on the process, its id among them, are then merged into the
        resource of the provider and pushed to the tracers already created.
        """
        self._tracers_lock = threading.Lock()
        self._update_resource(_get_process_dependent_resource())

    def _set_tracer_configurator(self, *, tracer_configurator: _TracerConfiguratorT):
        """This is the function used to update the TracerProvider TracerConfigurator

        Setting a new TracerConfigurator for a TracerProvider will update the
        TracerConfig of all Tracers create by this TracerProvider.

        A configurator that raises while being applied to one scope is logged
        and that tracer keeps the default configuration, which leaves it
        enabled.

        Args:
            tracer_configurator: Maps an instrumentation scope to the
                configuration its tracer should use. It is called once for
                every tracer that already exists, and once for each tracer
                created afterwards.
        """
        self._tracer_configurator = tracer_configurator
        with self._tracers_lock:
            for instrumentation_scope, tracer in self._tracers.items():
                tracer_config = self._apply_tracer_configurator(instrumentation_scope)
                # pylint: disable-next=protected-access
                tracer._set_tracer_config(tracer_config)

    @property
    def resource(self) -> Resource:
        """Resource attached to the spans of every tracer from this provider.

        Returns:
            The resource. It is replaced by a merged one after a fork, so a
            caller holding the result from before the fork holds a resource
            that is now out of date.
        """
        return self._resource

    def _update_resource(self, resource: Resource) -> None:
        """Merge ``resource`` into the provider resource and tell the tracers.

        The attributes of ``resource`` win where the two disagree. Tracers
        created later pick the merged resource up on their own, and spans that
        already exist keep the resource object they were given.

        Args:
            resource: Resource whose attributes take precedence over the ones
                already held.
        """
        with self._tracers_lock:
            self._resource = self._resource.merge(resource)
            for tracer in self._tracers.values():
                tracer._set_resource(self._resource)  # pylint: disable=protected-access

    def _apply_tracer_configurator(self, instrumentation_scope: InstrumentationScope):
        """Ask the configurator for the configuration of one scope.

        A configurator that raises is logged with its traceback and does not
        stop the tracer from being created or reconfigured.

        Args:
            instrumentation_scope: Scope of the tracer being configured.

        Returns:
            What the configurator returned, or the default configuration when
            it raised.
        """
        try:
            return self._tracer_configurator(instrumentation_scope)
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception(
                "Failed to create a Tracer Config for %s, using default Tracer config",
                instrumentation_scope,
            )
            return _TracerConfig.default()

    def get_tracer(
        self,
        instrumenting_module_name: str,
        instrumenting_library_version: str | None = None,
        schema_url: str | None = None,
        attributes: types.Attributes = None,
    ) -> "trace_api.Tracer":
        """Return the tracer for an instrumentation scope, building it once.

        Tracers are cached on the four values that make up the scope, so
        repeated calls with the same arguments give back the same object and
        the configurator runs only the first time. A module name that is empty
        or missing is logged as an error and replaced with the empty string,
        which means every caller making that mistake shares one tracer.

        Args:
            instrumenting_module_name: Name of the instrumenting library, for
                example ``opentelemetry.instrumentation.requests``.
            instrumenting_library_version: Version of the instrumenting
                library. ``None`` is stored as the empty string.
            schema_url: URL of the semantic conventions schema the scope emits
                against, or ``None``.
            attributes: Attributes of the scope, recorded next to its name and
                version. They are part of the cache key.

        Returns:
            A tracer for that scope, or the no-op tracer of the API when
            ``OTEL_SDK_DISABLED`` was ``true`` as this provider was built.
        """
        if self._disabled:
            return NoOpTracer()
        if not instrumenting_module_name:  # Reject empty strings too.
            instrumenting_module_name = ""
            logger.error("get_tracer called with missing module name.")
        if instrumenting_library_version is None:
            instrumenting_library_version = ""

        filterwarnings(
            "ignore",
            message=(r"You should use InstrumentationScope. Deprecated since version 1.11.1."),
            category=DeprecationWarning,
            module="opentelemetry.sdk.trace",
        )

        instrumentation_info = InstrumentationInfo(
            instrumenting_module_name,
            instrumenting_library_version,
            schema_url,
        )

        instrumentation_scope = InstrumentationScope(
            instrumenting_module_name,
            instrumenting_library_version,
            schema_url,
            attributes,
        )

        with self._tracers_lock:
            if instrumentation_scope in self._tracers:
                return self._tracers[instrumentation_scope]

            tracer_config = self._apply_tracer_configurator(instrumentation_scope)
            tracer = Tracer(
                self.sampler,
                self.resource,
                self._active_span_processor,
                self.id_generator,
                instrumentation_info,
                self._span_limits,
                instrumentation_scope,
                meter_provider=self._meter_provider,
                _tracer_config=tracer_config,
            )
            self._tracers[instrumentation_scope] = tracer

        return tracer

    def add_span_processor(self, span_processor: SpanProcessor) -> None:
        """Registers a new :class:`SpanProcessor` for this `TracerProvider`.

        The span processors are invoked in the same order they are registered,
        unless the provider was built with a ``ConcurrentMultiSpanProcessor``,
        which runs them in parallel. A processor registered after a tracer was
        created still sees the spans of that tracer, since the tracer holds the
        multi processor rather than a list of its own.

        Args:
            span_processor: The processor to register. Registering the same
                one twice makes it run twice for every span.
        """

        # no lock here because add_span_processor is thread safe for both
        # SynchronousMultiSpanProcessor and ConcurrentMultiSpanProcessor.
        self._active_span_processor.add_span_processor(span_processor)

    def shutdown(self) -> None:
        """Shut down the span processors added to the tracer provider.

        There is no timeout to hand out here: each processor applies whatever
        bound it has of its own. The ``atexit`` hook is unregistered
        afterwards, so calling this twice reaches the processors twice and only
        the first call unregisters. Spans started after this are still created
        and still ended; the processors are simply no longer in a position to
        export them.
        """
        self._active_span_processor.shutdown()
        if self._atexit_handler is not None:
            atexit.unregister(self._atexit_handler)
            self._atexit_handler = None

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Requests the active span processor to process all spans that have not
        yet been processed.

        By default force flush is called sequentially on all added span
        processors. This means that span processors further back in the list
        have less time to flush their spans.
        To have span processors flush their spans in parallel it is possible to
        initialize the tracer provider with an instance of
        `ConcurrentMultiSpanProcessor` at the cost of using multiple threads.

        A ``False`` result says that at least one processor did not finish
        within the budget, or that the budget ran out before a later processor
        was reached at all. It does not say which spans were exported and which
        were not, and the processors that were skipped are not flushed.

        Args:
            timeout_millis: The maximum amount of time to wait for spans to be
                processed.

        Returns:
            False if the timeout is exceeded, True otherwise.
        """
        return self._active_span_processor.force_flush(timeout_millis)
