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
import typing
from collections import OrderedDict, deque
from contextlib import contextmanager

from opentelemetry import trace as trace_api
from opentelemetry.context import Context
from opentelemetry.sdk import util
from opentelemetry.util import types

logger = logging.getLogger(__name__)

try:
    # pylint: disable=ungrouped-imports
    from collections.abc import MutableMapping
    from collections.abc import Sequence
except ImportError:
    # pylint: disable=no-name-in-module,ungrouped-imports
    from collections import MutableMapping
    from collections import Sequence

MAX_NUM_ATTRIBUTES = 32
MAX_NUM_EVENTS = 128
MAX_NUM_LINKS = 32


class BoundedList(Sequence):
    """An append only list with a fixed max size."""

    def __init__(self, maxlen):
        self.dropped = 0
        self._dq = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def __repr__(self):
        return "{}({}, maxlen={})".format(
            type(self).__name__, list(self._dq), self._dq.maxlen
        )

    def __getitem__(self, index):
        return self._dq[index]

    def __len__(self):
        return len(self._dq)

    def __iter__(self):
        with self._lock:
            return iter(self._dq.copy())

    def append(self, item):
        with self._lock:
            if len(self._dq) == self._dq.maxlen:
                self.dropped += 1
            self._dq.append(item)

    def extend(self, seq):
        with self._lock:
            to_drop = len(seq) + len(self._dq) - self._dq.maxlen
            if to_drop > 0:
                self.dropped += to_drop
            self._dq.extend(seq)

    @classmethod
    def from_seq(cls, maxlen, seq):
        seq = tuple(seq)
        if len(seq) > maxlen:
            raise ValueError
        bounded_list = cls(maxlen)
        # pylint: disable=protected-access
        bounded_list._dq = deque(seq, maxlen=maxlen)
        return bounded_list


class BoundedDict(MutableMapping):
    """A dict with a fixed max capacity."""

    def __init__(self, maxlen):
        if not isinstance(maxlen, int):
            raise ValueError
        if maxlen < 0:
            raise ValueError
        self.maxlen = maxlen
        self.dropped = 0
        self._dict = OrderedDict()
        self._lock = threading.Lock()

    def __repr__(self):
        return "{}({}, maxlen={})".format(
            type(self).__name__, dict(self._dict), self.maxlen
        )

    def __getitem__(self, key):
        return self._dict[key]

    def __setitem__(self, key, value):
        with self._lock:
            if self.maxlen == 0:
                self.dropped += 1
                return

            if key in self._dict:
                del self._dict[key]
            elif len(self._dict) == self.maxlen:
                del self._dict[next(iter(self._dict.keys()))]
                self.dropped += 1
            self._dict[key] = value

    def __delitem__(self, key):
        del self._dict[key]

    def __iter__(self):
        with self._lock:
            return iter(self._dict.copy())

    def __len__(self):
        return len(self._dict)

    @classmethod
    def from_map(cls, maxlen, mapping):
        mapping = OrderedDict(mapping)
        if len(mapping) > maxlen:
            raise ValueError
        bounded_dict = cls(maxlen)
        # pylint: disable=protected-access
        bounded_dict._dict = mapping
        return bounded_dict


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
        self._span_processors = ()
        self._lock = threading.Lock()

    def add_span_processor(self, span_processor: SpanProcessor):
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
        sampler: TODO
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
        context: "trace_api.SpanContext",
        parent: trace_api.ParentSpan = None,
        sampler=None,  # TODO
        trace_config=None,  # TODO
        resource=None,  # TODO
        attributes: types.Attributes = None,  # TODO
        events: typing.Sequence[trace_api.Event] = None,  # TODO
        links: typing.Sequence[trace_api.Link] = None,  # TODO
        kind: trace_api.SpanKind = trace_api.SpanKind.INTERNAL,
        span_processor: SpanProcessor = SpanProcessor(),
    ) -> None:

        self.name = name
        self.context = context
        self.parent = parent
        self.sampler = sampler
        self.trace_config = trace_config
        self.resource = resource
        self.attributes = attributes
        self.events = events
        self.links = links
        self.kind = kind

        self.span_processor = span_processor
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

        self.end_time = None
        self.start_time = None

    def __repr__(self):
        return '{}(name="{}")'.format(type(self).__name__, self.name)

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
        self, name: str, attributes: types.Attributes = None
    ) -> None:
        if attributes is None:
            attributes = Span.empty_attributes
        self.add_lazy_event(trace_api.Event(name, util.time_ns(), attributes))

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

    def add_link(
        self,
        link_target_context: "trace_api.SpanContext",
        attributes: types.Attributes = None,
    ) -> None:
        if attributes is None:
            attributes = Span.empty_attributes
        self.add_lazy_link(trace_api.Link(link_target_context, attributes))

    def add_lazy_link(self, link: "trace_api.Link") -> None:
        with self._lock:
            if not self.is_recording_events():
                return
            has_ended = self.end_time is not None
            if not has_ended:
                if self.links is Span.empty_links:
                    self.links = BoundedList(MAX_NUM_LINKS)
        if has_ended:
            logger.warning("Calling add_link() on an ended span.")
            return
        self.links.append(link)

    def start(self):
        with self._lock:
            if not self.is_recording_events():
                return
            has_started = self.start_time is not None
            if not has_started:
                self.start_time = util.time_ns()
        if has_started:
            logger.warning("Calling start() on a started span.")
            return
        self.span_processor.on_start(self)

    def end(self):
        with self._lock:
            if not self.is_recording_events():
                return
            if self.start_time is None:
                raise RuntimeError("Calling end() on a not started span.")
            has_ended = self.end_time is not None
            if not has_ended:
                self.end_time = util.time_ns()
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


def generate_span_id():
    """Get a new random span ID.

    Returns:
        A random 64-bit int for use as a span ID
    """
    return random.getrandbits(64)


def generate_trace_id():
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

    def __init__(self, name: str = "") -> None:
        slot_name = "current_span"
        if name:
            slot_name = "{}.current_span".format(name)
        self._current_span_slot = Context.register_slot(slot_name)
        self._active_span_processor = MultiSpanProcessor()

    def get_current_span(self):
        """See `opentelemetry.trace.Tracer.get_current_span`."""
        return self._current_span_slot.get()

    @contextmanager
    def start_span(
        self,
        name: str,
        parent: trace_api.ParentSpan = trace_api.Tracer.CURRENT_SPAN,
        kind: trace_api.SpanKind = trace_api.SpanKind.INTERNAL,
    ) -> typing.Iterator["Span"]:
        """See `opentelemetry.trace.Tracer.start_span`."""

        span = self.create_span(name, parent, kind)
        span.start()
        with self.use_span(span, end_on_exit=True) as span:
            yield span

    def create_span(
        self,
        name: str,
        parent: trace_api.ParentSpan = trace_api.Tracer.CURRENT_SPAN,
        kind: trace_api.SpanKind = trace_api.SpanKind.INTERNAL,
    ) -> "Span":
        """See `opentelemetry.trace.Tracer.create_span`."""
        span_id = generate_span_id()
        if parent is Tracer.CURRENT_SPAN:
            parent = self.get_current_span()
        if parent is None:
            context = trace_api.SpanContext(generate_trace_id(), span_id)
        else:
            if isinstance(parent, trace_api.Span):
                parent_context = parent.get_context()
            elif isinstance(parent, trace_api.SpanContext):
                parent_context = parent
            else:
                raise TypeError
            context = trace_api.SpanContext(
                parent_context.trace_id,
                span_id,
                parent_context.trace_options,
                parent_context.trace_state,
            )
        return Span(
            name=name,
            context=context,
            parent=parent,
            span_processor=self._active_span_processor,
            kind=kind,
        )

    @contextmanager
    def use_span(self, span: Span, end_on_exit=False) -> typing.Iterator[Span]:
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
