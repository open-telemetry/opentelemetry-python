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


from collections import OrderedDict
from collections import deque
from collections import namedtuple
from contextlib import contextmanager
import random
import threading
import typing

from opentelemetry import trace as trace_api
from opentelemetry import types
from opentelemetry.context import Context
from opentelemetry.sdk import util

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
        return ("{}({}, maxlen={})"
                .format(
                    type(self).__name__,
                    list(self._dq),
                    self._dq.maxlen
                ))

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
        return ("{}({}, maxlen={})"
                .format(
                    type(self).__name__,
                    dict(self._dict),
                    self.maxlen
                ))

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


Event = namedtuple('Event', ('name', 'attributes'))

Link = namedtuple('Link', ('context', 'attributes'))


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
    """

    # Initialize these lazily assuming most spans won't have them.
    empty_attributes = BoundedDict(MAX_NUM_ATTRIBUTES)
    empty_events = BoundedList(MAX_NUM_EVENTS)
    empty_links = BoundedList(MAX_NUM_LINKS)

    def __init__(self: 'Span',
                 name: str,
                 context: 'trace_api.SpanContext',
                 parent: trace_api.ParentSpan = None,
                 sampler=None,  # TODO
                 trace_config=None,  # TODO
                 resource=None,  # TODO
                 attributes: types.Attributes = None,  # TODO
                 events: typing.Sequence[Event] = None,  # TODO
                 links: typing.Sequence[Link] = None,  # TODO
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

        if attributes is None:
            self.attributes = Span.empty_attributes
        else:
            self.attributes = BoundedDict.from_map(
                MAX_NUM_ATTRIBUTES, attributes)

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
        return ('{}(name="{}")'
                .format(
                    type(self).__name__,
                    self.name
                ))

    def get_context(self):
        return self.context

    def set_attribute(self: 'Span',
                      key: str,
                      value: 'types.AttributeValue'
                      ) -> None:
        if self.attributes is Span.empty_attributes:
            self.attributes = BoundedDict(MAX_NUM_ATTRIBUTES)
        self.attributes[key] = value

    def add_event(self: 'Span',
                  name: str,
                  attributes: 'types.Attributes',
                  ) -> None:
        if self.events is Span.empty_events:
            self.events = BoundedList(MAX_NUM_EVENTS)
        self.events.append(Event(name, attributes))

    def add_link(self: 'Span',
                 context: 'trace_api.SpanContext',
                 attributes: 'types.Attributes',
                 ) -> None:
        if self.links is Span.empty_links:
            self.links = BoundedList(MAX_NUM_LINKS)
        self.links.append(Link(context, attributes))

    def start(self):
        if self.start_time is None:
            self.start_time = util.time_ns()

    def end(self):
        if self.end_time is None:
            self.end_time = util.time_ns()


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

    def __init__(self,
                 name: str = ''
                 ) -> None:
        slot_name = 'current_span'
        if name:
            slot_name = '{}.current_span'.format(name)
        self._current_span_slot = Context.register_slot(slot_name)

    def get_current_span(self):
        """See `opentelemetry.trace.Tracer.get_current_span`."""
        return self._current_span_slot.get()

    @contextmanager
    def start_span(self,
                   name: str,
                   parent: trace_api.ParentSpan = trace_api.Tracer.CURRENT_SPAN
                   ) -> typing.Iterator['Span']:
        """See `opentelemetry.trace.Tracer.start_span`."""
        with self.use_span(self.create_span(name, parent)) as span:
            yield span

    def create_span(self,
                    name: str,
                    parent: trace_api.ParentSpan =
                    trace_api.Tracer.CURRENT_SPAN
                    ) -> 'Span':
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
                parent_context.trace_state)
        return Span(name=name, context=context, parent=parent)

    @contextmanager
    def use_span(self, span: 'Span') -> typing.Iterator['Span']:
        """See `opentelemetry.trace.Tracer.use_span`."""
        span.start()
        span_snapshot = self._current_span_slot.get()
        self._current_span_slot.set(span)
        try:
            yield span
        finally:
            self._current_span_slot.set(span_snapshot)
            span.end()


tracer = Tracer()  # pylint: disable=invalid-name
