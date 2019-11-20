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


import logging
import random
import threading
from contextlib import contextmanager
from typing import Iterator, Optional, Sequence, Tuple

from opentelemetry import trace as trace_api
from opentelemetry.context import Context
from opentelemetry.sdk import util
from opentelemetry.sdk.util import BoundedDict, BoundedList
from opentelemetry.trace import sampling
from opentelemetry.util import time_ns, types

logger = logging.getLogger(__name__)

MAX_NUM_ATTRIBUTES = 32
MAX_NUM_EVENTS = 128
MAX_NUM_LINKS = 32


class SpanProcessor:
    """Interface which allows hooks for SDK's `Span`s start and end method
    invocations.

    Span processors can be registered directly using
    :func:`~Tracer:add_span_processor` and they are invoked in the same order
    as they were registered.
    """

    def on_start(self, span: "Span") -> None:
        """Called when a :class:`Span` is started.

        This method is called synchronously on the thread that starts the
        span, therefore it should not block or throw an exception.

        Args:
            span: The :class:`Span` that just started.
        """

    def on_end(self, span: "Span") -> None:
        """Called when a :class:`Span` is ended.

        This method is called synchronously on the thread that ends the
        span, therefore it should not block or throw an exception.

        Args:
            span: The :class:`Span` that just ended.
        """

    def shutdown(self) -> None:
        """Called when a :class:`Tracer` is shutdown."""


class MultiSpanProcessor(SpanProcessor):
    """Implementation of :class:`SpanProcessor` that forwards all received
    events to a list of `SpanProcessor`.
    """

    def __init__(self):
        # use a tuple to avoid race conditions when adding a new span and
        # iterating through it on "on_start" and "on_end".
        self._span_processors = ()  # type: Tuple[SpanProcessor, ...]
        self._lock = threading.Lock()

    def add_span_processor(self, span_processor: SpanProcessor) -> None:
        """Adds a SpanProcessor to the list handled by this instance."""
        with self._lock:
            self._span_processors = self._span_processors + (span_processor,)

    def on_start(self, span: "Span") -> None:
        for sp in self._span_processors:
            sp.on_start(span)

    def on_end(self, span: "Span") -> None:
        for sp in self._span_processors:
            sp.on_end(span)

    def shutdown(self) -> None:
        for sp in self._span_processors:
            sp.shutdown()


class Span(trace_api.Span):
    """See `opentelemetry.trace.Span`.

    Users should create `Span`s via the `Tracer` instead of this constructor.

    Args:
        name: The name of the operation this span represents
        context: The immutable span context
        parent: This span's parent, may be a `SpanContext` if the parent is
            remote, null if this is a root span
        sampler: The sampler used to create this span
        trace_config: TODO
        resource: TODO
        attributes: The span's attributes to be exported
        events: Timestamped events to be exported
        links: Links to other spans to be exported
        span_processor: `SpanProcessor` to invoke when starting and ending
            this `Span`.
    """

    # Initialize these lazily assuming most spans won't have them.
    empty_attributes = BoundedDict(MAX_NUM_ATTRIBUTES)
    empty_events = BoundedList(MAX_NUM_EVENTS)
    empty_links = BoundedList(MAX_NUM_LINKS)

    def __init__(
        self,
        name: str,
        context: trace_api.SpanContext,
        parent: trace_api.ParentSpan = None,
        sampler: Optional[sampling.Sampler] = None,
        trace_config: None = None,  # TODO
        resource: None = None,  # TODO
        attributes: types.Attributes = None,  # TODO
        events: Sequence[trace_api.Event] = None,  # TODO
        links: Sequence[trace_api.Link] = (),
        kind: trace_api.SpanKind = trace_api.SpanKind.INTERNAL,
        span_processor: SpanProcessor = SpanProcessor(),
    ) -> None:

        self.name = name
        self.context = context
        self.parent = parent
        self.sampler = sampler
        self.trace_config = trace_config
        self.resource = resource
        self.kind = kind

        self.span_processor = span_processor
        self.status = trace_api.Status()
        self._lock = threading.Lock()

        if attributes is None:
            self.attributes = Span.empty_attributes
        else:
            self.attributes = BoundedDict.from_map(
                MAX_NUM_ATTRIBUTES, attributes
            )

        if events is None:
            self.events = Span.empty_events
        else:
            self.events = BoundedList.from_seq(MAX_NUM_EVENTS, events)

        if links is None:
            self.links = Span.empty_links
        else:
            self.links = BoundedList.from_seq(MAX_NUM_LINKS, links)

        self.end_time = None  # type: Optional[int]
        self.start_time = None  # type: Optional[int]

    def __repr__(self):
        return '{}(name="{}", context={})'.format(
            type(self).__name__, self.name, self.context
        )

    def __str__(self):
        return '{}(name="{}", context={}, kind={}, parent={}, start_time={}, end_time={})'.format(
            type(self).__name__,
            self.name,
            self.context,
            self.kind,
            repr(self.parent),
            util.ns_to_iso_str(self.start_time) if self.start_time else "None",
            util.ns_to_iso_str(self.end_time) if self.end_time else "None",
        )

    def get_context(self):
        return self.context

    def set_attribute(self, key: str, value: types.AttributeValue) -> None:
        with self._lock:
            if not self.is_recording_events():
                return
            has_ended = self.end_time is not None
            if not has_ended:
                if self.attributes is Span.empty_attributes:
                    self.attributes = BoundedDict(MAX_NUM_ATTRIBUTES)
        if has_ended:
            logger.warning("Setting attribute on ended span.")
            return
        self.attributes[key] = value

    def add_event(
        self,
        name: str,
        attributes: types.Attributes = None,
        timestamp: int = None,
    ) -> None:
        self.add_lazy_event(
            trace_api.Event(
                name,
                Span.empty_attributes if attributes is None else attributes,
                time_ns() if timestamp is None else timestamp,
            )
        )

    def add_lazy_event(self, event: trace_api.Event) -> None:
        with self._lock:
            if not self.is_recording_events():
                return
            has_ended = self.end_time is not None
            if not has_ended:
                if self.events is Span.empty_events:
                    self.events = BoundedList(MAX_NUM_EVENTS)
        if has_ended:
            logger.warning("Calling add_event() on an ended span.")
            return
        self.events.append(event)

    def start(self, start_time: Optional[int] = None) -> None:
        with self._lock:
            if not self.is_recording_events():
                return
            has_started = self.start_time is not None
            if not has_started:
                self.start_time = (
                    start_time if start_time is not None else time_ns()
                )
        if has_started:
            logger.warning("Calling start() on a started span.")
            return
        self.span_processor.on_start(self)

    def end(self, end_time: int = None) -> None:
        with self._lock:
            if not self.is_recording_events():
                return
            if self.start_time is None:
                raise RuntimeError("Calling end() on a not started span.")
            has_ended = self.end_time is not None
            if not has_ended:
                self.end_time = end_time if end_time is not None else time_ns()
        if has_ended:
            logger.warning("Calling end() on an ended span.")
            return

        self.span_processor.on_end(self)

    def update_name(self, name: str) -> None:
        with self._lock:
            has_ended = self.end_time is not None
        if has_ended:
            logger.warning("Calling update_name() on an ended span.")
            return
        self.name = name

    def is_recording_events(self) -> bool:
        return True

    def set_status(self, status: trace_api.Status) -> None:
        with self._lock:
            has_ended = self.end_time is not None
        if has_ended:
            logger.warning("Calling set_status() on an ended span.")
            return
        self.status = status


def generate_span_id() -> int:
    """Get a new random span ID.
    Returns:
        A random 64-bit int for use as a span ID
    """
    return random.getrandbits(64)


def generate_trace_id() -> int:
    """Get a new random trace ID.
    Returns:
        A random 128-bit int for use as a trace ID
    """
    return random.getrandbits(128)


class Tracer(trace_api.Tracer):
    """See `opentelemetry.trace.Tracer`.

    Args:
        name: The name of the tracer.
    """

    def __init__(
        self,
        name: str = "",
        sampler: sampling.Sampler = trace_api.sampling.ALWAYS_ON,
    ) -> None:
        slot_name = "current_span"
        if name:
            slot_name = "{}.current_span".format(name)
        self._current_span_slot = Context.register_slot(slot_name)
        self._active_span_processor = MultiSpanProcessor()
        self.sampler = sampler

    def get_current_span(self):
        """See `opentelemetry.trace.Tracer.get_current_span`."""
        return self._current_span_slot.get()

    def start_span(
        self,
        name: str,
        parent: trace_api.ParentSpan = trace_api.Tracer.CURRENT_SPAN,
        kind: trace_api.SpanKind = trace_api.SpanKind.INTERNAL,
        attributes: Optional[types.Attributes] = None,
        links: Sequence[trace_api.Link] = (),
    ) -> "Span":
        """See `opentelemetry.trace.Tracer.start_span`."""

        span = self.create_span(name, parent, kind, attributes, links)
        span.start()
        return span

    def start_as_current_span(
        self,
        name: str,
        parent: trace_api.ParentSpan = trace_api.Tracer.CURRENT_SPAN,
        kind: trace_api.SpanKind = trace_api.SpanKind.INTERNAL,
        attributes: Optional[types.Attributes] = None,
        links: Sequence[trace_api.Link] = (),
    ) -> Iterator[trace_api.Span]:
        """See `opentelemetry.trace.Tracer.start_as_current_span`."""

        span = self.start_span(name, parent, kind, attributes, links)
        return self.use_span(span, end_on_exit=True)

    def create_span(
        self,
        name: str,
        parent: trace_api.ParentSpan = trace_api.Tracer.CURRENT_SPAN,
        kind: trace_api.SpanKind = trace_api.SpanKind.INTERNAL,
        attributes: Optional[types.Attributes] = None,
        links: Sequence[trace_api.Link] = (),
    ) -> "trace_api.Span":
        """See `opentelemetry.trace.Tracer.create_span`.

        If `parent` is null the new span will be created as a root span, i.e. a
        span with no parent context. By default, the new span will be created
        as a child of the current span in this tracer's context, or as a root
        span if no current span exists.
        """
        span_id = generate_span_id()

        if parent is Tracer.CURRENT_SPAN:
            parent = self.get_current_span()

        parent_context = parent
        if isinstance(parent_context, trace_api.Span):
            parent_context = parent.get_context()

        if parent_context is not None and not isinstance(
            parent_context, trace_api.SpanContext
        ):
            raise TypeError

        if parent_context is None or not parent_context.is_valid():
            parent = parent_context = None
            trace_id = generate_trace_id()
            trace_options = None
            trace_state = None
        else:
            trace_id = parent_context.trace_id
            trace_options = parent_context.trace_options
            trace_state = parent_context.trace_state

        context = trace_api.SpanContext(
            trace_id, span_id, trace_options, trace_state
        )

        # The sampler decides whether to create a real or no-op span at the
        # time of span creation. No-op spans do not record events, and are not
        # exported.
        # The sampler may also add attributes to the newly-created span, e.g.
        # to include information about the sampling decision.
        sampling_decision = self.sampler.should_sample(
            parent_context,
            context.trace_id,
            context.span_id,
            name,
            attributes,
            links,
        )

        if sampling_decision.sampled:
            if attributes is None:
                span_attributes = sampling_decision.attributes
            else:
                # apply sampling decision attributes after initial attributes
                span_attributes = attributes.copy()
                span_attributes.update(sampling_decision.attributes)
            return Span(
                name=name,
                context=context,
                parent=parent,
                sampler=self.sampler,
                attributes=span_attributes,
                span_processor=self._active_span_processor,
                kind=kind,
                links=links,
            )

        return trace_api.DefaultSpan(context=context)

    @contextmanager
    def use_span(
        self, span: trace_api.Span, end_on_exit: bool = False
    ) -> Iterator[trace_api.Span]:
        """See `opentelemetry.trace.Tracer.use_span`."""
        try:
            span_snapshot = self._current_span_slot.get()
            self._current_span_slot.set(span)
            try:
                yield span
            finally:
                self._current_span_slot.set(span_snapshot)
        finally:
            if end_on_exit:
                span.end()

    def add_span_processor(self, span_processor: SpanProcessor) -> None:
        """Registers a new :class:`SpanProcessor` for this `Tracer`.

        The span processors are invoked in the same order they are registered.
        """

        # no lock here because MultiSpanProcessor.add_span_processor is
        # thread safe
        self._active_span_processor.add_span_processor(span_processor)


tracer = Tracer()
