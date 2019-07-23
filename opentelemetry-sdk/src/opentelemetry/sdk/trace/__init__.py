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
import threading
import typing

from opentelemetry import trace as trace_api
from opentelemetry.sdk import util

try:
    from collections.abc import MutableMapping
    from collections.abc import Sequence
except ImportError:
    from collections import MutableMapping
    from collections import Sequence


MAX_NUM_ATTRIBUTES = 32
MAX_NUM_ANNOTATIONS = 32
MAX_NUM_EVENTS = 128
MAX_NUM_LINKS = 32

AttributeValue = typing.Union[str, bool, float]


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
        return iter(self._dq)

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
        bounded_list._dq = deque(seq, maxlen=maxlen)
        return bounded_list


class BoundedDict(MutableMapping):
    """A dict with a fixed max capacity."""
    def __init__(self, maxlen):
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
            if key in self._dict:
                del self._dict[key]
            elif len(self._dict) == self.maxlen:
                del self._dict[next(iter(self._dict.keys()))]
                self.dropped += 1
            self._dict[key] = value

    def __delitem__(self, key):
        del self._dict[key]

    def __iter__(self):
        return iter(self._dict)

    def __len__(self):
        return len(self._dict)

    @classmethod
    def from_map(cls, maxlen, mapping):
        mapping = OrderedDict(mapping)
        if len(mapping) > maxlen:
            raise ValueError
        bounded_dict = cls(maxlen)
        bounded_dict._dict = mapping
        return bounded_dict


class SpanContext(trace_api.SpanContext):
    """See `opentelemetry.trace.SpanContext`."""

    def is_valid(self) -> bool:
        return (self.trace_id == trace_api.INVALID_TRACE_ID or
                self.span_id == trace_api.INVALID_SPAN_ID)


Event = namedtuple('Event', ('name', 'attributes'))

Link = namedtuple('Link', ('context', 'attributes'))


class Span(trace_api.Span):
    def __init__(self: 'Span',
                 name: str,
                 context: 'SpanContext',
                 # TODO: span processor
                 parent: typing.Union['Span', 'SpanContext'] = None,
                 root: bool = False,
                 sampler=None,  # TODO
                 trace_config=None,  # TraceConfig TODO
                 resource=None,  # Resource TODO
                 # TODO: is_recording
                 attributes=None,  # type TODO
                 events=None,  # type TODO
                 links=None,  # type TODO
                 ) -> None:
        """See `opentelemetry.trace.Span`."""
        if root:
            if parent is not None:
                raise ValueError("Root span can't have a parent")

        self.name = name
        self.context = context
        self.parent = parent
        self.root = root
        self.sampler = sampler
        self.trace_config = trace_config
        self.resource = resource
        self.attributes = attributes
        self.events = events
        self.links = links

        if attributes is None:
            self.attributes = BoundedDict(MAX_NUM_ATTRIBUTES)
        else:
            self.attributes = BoundedDict.from_map(
                MAX_NUM_ATTRIBUTES, attributes)

        if events is None:
            self.events = BoundedList(MAX_NUM_EVENTS)
        else:
            self.events = BoundedList.from_seq(MAX_NUM_EVENTS, events)

        if links is None:
            self.links = BoundedList(MAX_NUM_LINKS)
        else:
            self.links = BoundedList.from_seq(MAX_NUM_LINKS, links)

        self.end_time = None
        self.start_time = None

    def set_attribute(self: 'Span',
                      key: str,
                      value: 'AttributeValue'
                      ) -> None:
        self.attributes[key] = value

    def add_event(self: 'Span',
                  name: str,
                  attributes: typing.Dict[str, 'AttributeValue']
                  ) -> None:
        self.events.append(Event(name, attributes))

    def add_link(self: 'Span',
                 context: 'SpanContext',
                 attributes: typing.Dict[str, 'AttributeValue'],
                 ) -> None:
        self.links.append(Link(context, attributes))

    def start(self):
        if self.end_time is None:
            self.start_time = util.time_ns()

    def end(self):
        if self.end_time is None:
            self.end_time = util.time_ns()


class Tracer(trace_api.Tracer):
    pass
