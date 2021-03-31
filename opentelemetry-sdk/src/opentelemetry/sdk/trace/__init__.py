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

# pylint: disable=too-many-lines
import abc
import atexit
import concurrent.futures
import json
import logging
import threading
import traceback
from collections import OrderedDict
from contextlib import contextmanager
from os import environ
from types import MappingProxyType, TracebackType
from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    MutableSequence,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
)

from opentelemetry import context as context_api
from opentelemetry import trace as trace_api
from opentelemetry.sdk import util
from opentelemetry.sdk.environment_variables import (
    OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT,
    OTEL_SPAN_EVENT_COUNT_LIMIT,
    OTEL_SPAN_LINK_COUNT_LIMIT,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import sampling
from opentelemetry.sdk.trace.id_generator import IdGenerator, RandomIdGenerator
from opentelemetry.sdk.util import BoundedDict, BoundedList
from opentelemetry.sdk.util.instrumentation import InstrumentationInfo
from opentelemetry.trace import SpanContext
from opentelemetry.trace.propagation import SPAN_KEY
from opentelemetry.trace.status import Status, StatusCode
from opentelemetry.util import types
from opentelemetry.util._time import _time_ns

logger = logging.getLogger(__name__)

SPAN_ATTRIBUTE_COUNT_LIMIT = int(
    environ.get(OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT, 128)
)

_SPAN_EVENT_COUNT_LIMIT = int(environ.get(OTEL_SPAN_EVENT_COUNT_LIMIT, 128))
_SPAN_LINK_COUNT_LIMIT = int(environ.get(OTEL_SPAN_LINK_COUNT_LIMIT, 128))
_VALID_ATTR_VALUE_TYPES = (bool, str, int, float)
# pylint: disable=protected-access
_TRACE_SAMPLER = sampling._get_from_env_or_default()


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
        parent_context: Optional[context_api.Context] = None,
    ) -> None:
        """Called when a :class:`opentelemetry.trace.Span` is started.

        This method is called synchronously on the thread that starts the
        span, therefore it should not block or throw an exception.

        Args:
            span: The :class:`opentelemetry.trace.Span` that just started.
            parent_context: The parent context of the span that just started.
        """

    def on_end(self, span: "ReadableSpan") -> None:
        """Called when a :class:`opentelemetry.trace.Span` is ended.

        This method is called synchronously on the thread that ends the
        span, therefore it should not block or throw an exception.

        Args:
            span: The :class:`opentelemetry.trace.Span` that just ended.
        """

    def shutdown(self) -> None:
        """Called when a :class:`opentelemetry.sdk.trace.Tracer` is shutdown."""

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Export all ended spans to the configured Exporter that have not yet
        been exported.

        Args:
            timeout_millis: The maximum amount of time to wait for spans to be
                exported.

        Returns:
            False if the timeout is exceeded, True otherwise.
        """


# Temporary fix until https://github.com/PyCQA/pylint/issues/4098 is resolved
# pylint:disable=no-member
class SynchronousMultiSpanProcessor(SpanProcessor):
    """Implementation of class:`SpanProcessor` that forwards all received
    events to a list of span processors sequentially.

    The underlying span processors are called in sequential order as they were
    added.
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

    def on_start(
        self,
        span: "Span",
        parent_context: Optional[context_api.Context] = None,
    ) -> None:
        for sp in self._span_processors:
            sp.on_start(span, parent_context=parent_context)

    def on_end(self, span: "ReadableSpan") -> None:
        for sp in self._span_processors:
            sp.on_end(span)

    def shutdown(self) -> None:
        """Sequentially shuts down all underlying span processors."""
        for sp in self._span_processors:
            sp.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Sequentially calls force_flush on all underlying
        :class:`SpanProcessor`

        Args:
            timeout_millis: The maximum amount of time over all span processors
                to wait for spans to be exported. In case the first n span
                processors exceeded the timeout followup span processors will be
                skipped.

        Returns:
            True if all span processors flushed their spans within the
            given timeout, False otherwise.
        """
        deadline_ns = _time_ns() + timeout_millis * 1000000
        for sp in self._span_processors:
            current_time_ns = _time_ns()
            if current_time_ns >= deadline_ns:
                return False

            if not sp.force_flush((deadline_ns - current_time_ns) // 1000000):
                return False

        return True


class ConcurrentMultiSpanProcessor(SpanProcessor):
    """Implementation of :class:`SpanProcessor` that forwards all received
    events to a list of span processors in parallel.

    Calls to the underlying span processors are forwarded in parallel by
    submitting them to a thread pool executor and waiting until each span
    processor finished its work.

    Args:
        num_threads: The number of threads managed by the thread pool executor
            and thus defining how many span processors can work in parallel.
    """

    def __init__(self, num_threads: int = 2):
        # use a tuple to avoid race conditions when adding a new span and
        # iterating through it on "on_start" and "on_end".
        self._span_processors = ()  # type: Tuple[SpanProcessor, ...]
        self._lock = threading.Lock()
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=num_threads
        )

    def add_span_processor(self, span_processor: SpanProcessor) -> None:
        """Adds a SpanProcessor to the list handled by this instance."""
        with self._lock:
            self._span_processors = self._span_processors + (span_processor,)

    def _submit_and_await(
        self,
        func: Callable[[SpanProcessor], Callable[..., None]],
        *args: Any,
        **kwargs: Any
    ):
        futures = []
        for sp in self._span_processors:
            future = self._executor.submit(func(sp), *args, **kwargs)
            futures.append(future)
        for future in futures:
            future.result()

    def on_start(
        self,
        span: "Span",
        parent_context: Optional[context_api.Context] = None,
    ) -> None:
        self._submit_and_await(
            lambda sp: sp.on_start, span, parent_context=parent_context
        )

    def on_end(self, span: "ReadableSpan") -> None:
        self._submit_and_await(lambda sp: sp.on_end, span)

    def shutdown(self) -> None:
        """Shuts down all underlying span processors in parallel."""
        self._submit_and_await(lambda sp: sp.shutdown)

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Calls force_flush on all underlying span processors in parallel.

        Args:
            timeout_millis: The maximum amount of time to wait for spans to be
                exported.

        Returns:
            True if all span processors flushed their spans within the given
            timeout, False otherwise.
        """
        futures = []
        for sp in self._span_processors:  # type: SpanProcessor
            future = self._executor.submit(sp.force_flush, timeout_millis)
            futures.append(future)

        timeout_sec = timeout_millis / 1e3
        done_futures, not_done_futures = concurrent.futures.wait(
            futures, timeout_sec
        )
        if not_done_futures:
            return False

        for future in done_futures:
            if not future.result():
                return False

        return True


class EventBase(abc.ABC):
    def __init__(self, name: str, timestamp: Optional[int] = None) -> None:
        self._name = name
        if timestamp is None:
            self._timestamp = _time_ns()
        else:
            self._timestamp = timestamp

    @property
    def name(self) -> str:
        return self._name

    @property
    def timestamp(self) -> int:
        return self._timestamp

    @property
    @abc.abstractmethod
    def attributes(self) -> types.Attributes:
        pass


class Event(EventBase):
    """A text annotation with a set of attributes.

    Args:
        name: Name of the event.
        attributes: Attributes of the event.
        timestamp: Timestamp of the event. If `None` it will filled
            automatically.
    """

    def __init__(
        self,
        name: str,
        attributes: types.Attributes = None,
        timestamp: Optional[int] = None,
    ) -> None:
        super().__init__(name, timestamp)
        self._attributes = attributes

    @property
    def attributes(self) -> types.Attributes:
        return self._attributes


def _is_valid_attribute_value(value: types.AttributeValue) -> bool:
    """Checks if attribute value is valid.

    An attribute value is valid if it is one of the valid types.
    If the value is a sequence, it is only valid if all items in the sequence:
      - are of the same valid type or None
      - are not a sequence
    """

    if isinstance(value, Sequence):
        if len(value) == 0:
            return True

        sequence_first_valid_type = None
        for element in value:
            if element is None:
                continue
            element_type = type(element)
            if element_type not in _VALID_ATTR_VALUE_TYPES:
                logger.warning(
                    "Invalid type %s in attribute value sequence. Expected one of "
                    "%s or None",
                    element_type.__name__,
                    [
                        valid_type.__name__
                        for valid_type in _VALID_ATTR_VALUE_TYPES
                    ],
                )
                return False
            # The type of the sequence must be homogeneous. The first non-None
            # element determines the type of the sequence
            if sequence_first_valid_type is None:
                sequence_first_valid_type = element_type
            elif not isinstance(element, sequence_first_valid_type):
                logger.warning(
                    "Mixed types %s and %s in attribute value sequence",
                    sequence_first_valid_type.__name__,
                    type(element).__name__,
                )
                return False

    elif not isinstance(value, _VALID_ATTR_VALUE_TYPES):
        logger.warning(
            "Invalid type %s for attribute value. Expected one of %s or a "
            "sequence of those types",
            type(value).__name__,
            [valid_type.__name__ for valid_type in _VALID_ATTR_VALUE_TYPES],
        )
        return False
    return True


def _filter_attribute_values(attributes: types.Attributes):
    if attributes:
        for attr_key, attr_value in list(attributes.items()):
            if _is_valid_attribute_value(attr_value):
                if isinstance(attr_value, MutableSequence):
                    attributes[attr_key] = tuple(attr_value)
            else:
                attributes.pop(attr_key)


def _create_immutable_attributes(attributes):
    return MappingProxyType(attributes.copy() if attributes else {})


def _check_span_ended(func):
    def wrapper(self, *args, **kwargs):
        already_ended = False
        with self._lock:  # pylint: disable=protected-access
            if self._end_time is None:
                func(self, *args, **kwargs)
            else:
                already_ended = True

        if already_ended:
            logger.warning("Tried calling %s on an ended span.", func.__name__)

    return wrapper


class ReadableSpan:
    """Provides read-only access to span attributes"""

    def __init__(
        self,
        name: str = None,
        context: trace_api.SpanContext = None,
        parent: Optional[trace_api.SpanContext] = None,
        resource: Resource = Resource.create({}),
        attributes: types.Attributes = None,
        events: Sequence[Event] = None,
        links: Sequence[trace_api.Link] = (),
        kind: trace_api.SpanKind = trace_api.SpanKind.INTERNAL,
        instrumentation_info: InstrumentationInfo = None,
        status: Status = Status(StatusCode.UNSET),
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> None:
        self._name = name
        self._context = context
        self._kind = kind
        self._instrumentation_info = instrumentation_info
        self._parent = parent
        self._start_time = start_time
        self._end_time = end_time
        self._attributes = attributes
        self._events = events
        self._links = links
        self._resource = resource
        self._status = status

    @property
    def name(self) -> str:
        return self._name

    def get_span_context(self):
        return self._context

    @property
    def context(self):
        return self._context

    @property
    def kind(self) -> trace_api.SpanKind:
        return self._kind

    @property
    def parent(self) -> Optional[trace_api.SpanContext]:
        return self._parent

    @property
    def start_time(self) -> Optional[int]:
        return self._start_time

    @property
    def end_time(self) -> Optional[int]:
        return self._end_time

    @property
    def status(self) -> trace_api.Status:
        return self._status

    @property
    def attributes(self) -> types.Attributes:
        return MappingProxyType(self._attributes)

    @property
    def events(self) -> Sequence[Event]:
        return MappingProxyType(self._events)

    @property
    def links(self) -> Sequence[trace_api.Link]:
        return MappingProxyType(self._links)

    @property
    def resource(self) -> Resource:
        return self._resource

    @property
    def instrumentation_info(self) -> InstrumentationInfo:
        return self._instrumentation_info

    def to_json(self, indent=4):
        parent_id = None
        if self.parent is not None:
            if isinstance(self.parent, Span):
                ctx = self.parent.context
                parent_id = trace_api.format_span_id(ctx.span_id)
            elif isinstance(self.parent, SpanContext):
                parent_id = trace_api.format_span_id(self.parent.span_id)

        start_time = None
        if self._start_time:
            start_time = util.ns_to_iso_str(self._start_time)

        end_time = None
        if self._end_time:
            end_time = util.ns_to_iso_str(self._end_time)

        if self._status is not None:
            status = OrderedDict()
            status["status_code"] = str(self._status.status_code.name)
            if self._status.description:
                status["description"] = self._status.description

        f_span = OrderedDict()

        f_span["name"] = self._name
        f_span["context"] = self._format_context(self._context)
        f_span["kind"] = str(self.kind)
        f_span["parent_id"] = parent_id
        f_span["start_time"] = start_time
        f_span["end_time"] = end_time
        if self._status is not None:
            f_span["status"] = status
        f_span["attributes"] = self._format_attributes(self._attributes)
        f_span["events"] = self._format_events(self._events)
        f_span["links"] = self._format_links(self._links)
        f_span["resource"] = self._resource.attributes

        return json.dumps(f_span, indent=indent)

    @staticmethod
    def _format_context(context):
        x_ctx = OrderedDict()
        x_ctx["trace_id"] = "0x{}".format(
            trace_api.format_trace_id(context.trace_id)
        )
        x_ctx["span_id"] = "0x{}".format(
            trace_api.format_span_id(context.span_id)
        )
        x_ctx["trace_state"] = repr(context.trace_state)
        return x_ctx

    @staticmethod
    def _format_attributes(attributes):
        if isinstance(attributes, BoundedDict):
            return attributes._dict  # pylint: disable=protected-access
        if isinstance(attributes, MappingProxyType):
            return attributes.copy()
        return attributes

    @staticmethod
    def _format_events(events):
        f_events = []
        for event in events:
            f_event = OrderedDict()
            f_event["name"] = event.name
            f_event["timestamp"] = util.ns_to_iso_str(event.timestamp)
            f_event["attributes"] = Span._format_attributes(event.attributes)
            f_events.append(f_event)
        return f_events

    @staticmethod
    def _format_links(links):
        f_links = []
        for link in links:
            f_link = OrderedDict()
            f_link["context"] = Span._format_context(link.context)
            f_link["attributes"] = Span._format_attributes(link.attributes)
            f_links.append(f_link)
        return f_links


class Span(trace_api.Span, ReadableSpan):
    """See `opentelemetry.trace.Span`.

    Users should create `Span` objects via the `Tracer` instead of this
    constructor.

    Args:
        name: The name of the operation this span represents
        context: The immutable span context
        parent: This span's parent's `opentelemetry.trace.SpanContext`, or
            None if this is a root span
        sampler: The sampler used to create this span
        trace_config: TODO
        resource: Entity producing telemetry
        attributes: The span's attributes to be exported
        events: Timestamped events to be exported
        links: Links to other spans to be exported
        span_processor: `SpanProcessor` to invoke when starting and ending
            this `Span`.
    """

    def __new__(cls, *args, **kwargs):
        if cls is Span:
            raise TypeError("Span must be instantiated via a tracer.")
        return super().__new__(cls)

    # pylint: disable=too-many-locals
    def __init__(
        self,
        name: str,
        context: trace_api.SpanContext,
        parent: Optional[trace_api.SpanContext] = None,
        sampler: Optional[sampling.Sampler] = None,
        trace_config: None = None,  # TODO
        resource: Resource = Resource.create({}),
        attributes: types.Attributes = None,
        events: Sequence[Event] = None,
        links: Sequence[trace_api.Link] = (),
        kind: trace_api.SpanKind = trace_api.SpanKind.INTERNAL,
        span_processor: SpanProcessor = SpanProcessor(),
        instrumentation_info: InstrumentationInfo = None,
        record_exception: bool = True,
        set_status_on_exception: bool = True,
    ) -> None:
        super().__init__(
            name=name,
            context=context,
            parent=parent,
            kind=kind,
            resource=resource,
            instrumentation_info=instrumentation_info,
        )
        self._sampler = sampler
        self._trace_config = trace_config
        self._record_exception = record_exception
        self._set_status_on_exception = set_status_on_exception
        self._span_processor = span_processor
        self._lock = threading.Lock()

        _filter_attribute_values(attributes)
        if not attributes:
            self._attributes = self._new_attributes()
        else:
            self._attributes = BoundedDict.from_map(
                SPAN_ATTRIBUTE_COUNT_LIMIT, attributes
            )

        self._events = self._new_events()
        if events:
            for event in events:
                _filter_attribute_values(event.attributes)
                # pylint: disable=protected-access
                event._attributes = _create_immutable_attributes(
                    event.attributes
                )
                self._events.append(event)

        if links is None:
            self._links = self._new_links()
        else:
            self._links = BoundedList.from_seq(_SPAN_LINK_COUNT_LIMIT, links)

    def __repr__(self):
        return '{}(name="{}", context={})'.format(
            type(self).__name__, self._name, self._context
        )

    @staticmethod
    def _new_attributes():
        return BoundedDict(SPAN_ATTRIBUTE_COUNT_LIMIT)

    @staticmethod
    def _new_events():
        return BoundedList(_SPAN_EVENT_COUNT_LIMIT)

    @staticmethod
    def _new_links():
        return BoundedList(_SPAN_LINK_COUNT_LIMIT)

    def get_span_context(self):
        return self._context

    def set_attributes(
        self, attributes: Dict[str, types.AttributeValue]
    ) -> None:
        with self._lock:
            if self._end_time is not None:
                logger.warning("Setting attribute on ended span.")
                return

            for key, value in attributes.items():
                if not _is_valid_attribute_value(value):
                    continue

                if not key:
                    logger.warning("invalid key `%s` (empty or null)", key)
                    continue

                # Freeze mutable sequences defensively
                if isinstance(value, MutableSequence):
                    value = tuple(value)
                if isinstance(value, bytes):
                    try:
                        value = value.decode()
                    except ValueError:
                        logger.warning("Byte attribute could not be decoded.")
                        return
                self._attributes[key] = value

    def set_attribute(self, key: str, value: types.AttributeValue) -> None:
        return self.set_attributes({key: value})

    @_check_span_ended
    def _add_event(self, event: EventBase) -> None:
        self._events.append(event)

    def add_event(
        self,
        name: str,
        attributes: types.Attributes = None,
        timestamp: Optional[int] = None,
    ) -> None:
        _filter_attribute_values(attributes)
        attributes = _create_immutable_attributes(attributes)
        self._add_event(
            Event(
                name=name,
                attributes=attributes,
                timestamp=_time_ns() if timestamp is None else timestamp,
            )
        )

    def _readable_span(self) -> ReadableSpan:
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
        )

    def start(
        self,
        start_time: Optional[int] = None,
        parent_context: Optional[context_api.Context] = None,
    ) -> None:
        with self._lock:
            if self._start_time is not None:
                logger.warning("Calling start() on a started span.")
                return
            self._start_time = (
                start_time if start_time is not None else _time_ns()
            )

        self._span_processor.on_start(self, parent_context=parent_context)

    def end(self, end_time: Optional[int] = None) -> None:
        with self._lock:
            if self._start_time is None:
                raise RuntimeError("Calling end() on a not started span.")
            if self._end_time is not None:
                logger.warning("Calling end() on an ended span.")
                return

            self._end_time = end_time if end_time is not None else _time_ns()

        self._span_processor.on_end(self._readable_span())

    @_check_span_ended
    def update_name(self, name: str) -> None:
        self._name = name

    def is_recording(self) -> bool:
        return self._end_time is None

    @_check_span_ended
    def set_status(self, status: trace_api.Status) -> None:
        self._status = status

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Ends context manager and calls `end` on the `Span`."""
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
                        description="{}: {}".format(
                            exc_type.__name__, exc_val
                        ),
                    )
                )

        super().__exit__(exc_type, exc_val, exc_tb)

    def record_exception(
        self,
        exception: Exception,
        attributes: types.Attributes = None,
        timestamp: Optional[int] = None,
        escaped: bool = False,
    ) -> None:
        """Records an exception as a span event."""
        try:
            stacktrace = traceback.format_exc()
        except Exception:  # pylint: disable=broad-except
            # workaround for python 3.4, format_exc can raise
            # an AttributeError if the __context__ on
            # an exception is None
            stacktrace = "Exception occurred on stacktrace formatting"
        _attributes = {
            "exception.type": exception.__class__.__name__,
            "exception.message": str(exception),
            "exception.stacktrace": stacktrace,
            "exception.escaped": str(escaped),
        }
        if attributes:
            _attributes.update(attributes)
        self.add_event(
            name="exception", attributes=_attributes, timestamp=timestamp
        )


class _Span(Span):
    """Protected implementation of `opentelemetry.trace.Span`.

    This constructor exists to prevent the instantiation of the `Span` class
    by other mechanisms than through the `Tracer`.
    """


class Tracer(trace_api.Tracer):
    """See `opentelemetry.trace.Tracer`."""

    def __init__(
        self,
        sampler: sampling.Sampler,
        resource: Resource,
        span_processor: Union[
            SynchronousMultiSpanProcessor, ConcurrentMultiSpanProcessor
        ],
        id_generator: IdGenerator,
        instrumentation_info: InstrumentationInfo,
    ) -> None:
        self.sampler = sampler
        self.resource = resource
        self.span_processor = span_processor
        self.id_generator = id_generator
        self.instrumentation_info = instrumentation_info

    @contextmanager
    def start_as_current_span(
        self,
        name: str,
        context: Optional[context_api.Context] = None,
        kind: trace_api.SpanKind = trace_api.SpanKind.INTERNAL,
        attributes: types.Attributes = None,
        links: Sequence[trace_api.Link] = (),
        start_time: Optional[int] = None,
        record_exception: bool = True,
        set_status_on_exception: bool = True,
        end_on_exit: bool = True,
    ) -> Iterator[trace_api.Span]:
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
        ) as span_context:
            yield span_context

    def start_span(  # pylint: disable=too-many-locals
        self,
        name: str,
        context: Optional[context_api.Context] = None,
        kind: trace_api.SpanKind = trace_api.SpanKind.INTERNAL,
        attributes: types.Attributes = None,
        links: Sequence[trace_api.Link] = (),
        start_time: Optional[int] = None,
        record_exception: bool = True,
        set_status_on_exception: bool = True,
    ) -> trace_api.Span:

        parent_span_context = trace_api.get_current_span(
            context
        ).get_span_context()

        if parent_span_context is not None and not isinstance(
            parent_span_context, trace_api.SpanContext
        ):
            raise TypeError(
                "parent_span_context must be a SpanContext or None."
            )

        # is_valid determines root span
        if parent_span_context is None or not parent_span_context.is_valid:
            parent_span_context = None
            trace_id = self.id_generator.generate_trace_id()
            trace_flags = None
            trace_state = None
        else:
            trace_id = parent_span_context.trace_id
            trace_flags = parent_span_context.trace_flags
            trace_state = parent_span_context.trace_state

        # The sampler decides whether to create a real or no-op span at the
        # time of span creation. No-op spans do not record events, and are not
        # exported.
        # The sampler may also add attributes to the newly-created span, e.g.
        # to include information about the sampling result.
        sampling_result = self.sampler.should_sample(
            context, trace_id, name, attributes, links, trace_state
        )

        trace_flags = (
            trace_api.TraceFlags(trace_api.TraceFlags.SAMPLED)
            if sampling_result.decision.is_sampled()
            else trace_api.TraceFlags(trace_api.TraceFlags.DEFAULT)
        )
        span_context = trace_api.SpanContext(
            trace_id,
            self.id_generator.generate_span_id(),
            is_remote=False,
            trace_flags=trace_flags,
            trace_state=sampling_result.trace_state,
        )

        # Only record if is_recording() is true
        if sampling_result.decision.is_recording():
            # pylint:disable=protected-access
            span = _Span(
                name=name,
                context=span_context,
                parent=parent_span_context,
                sampler=self.sampler,
                resource=self.resource,
                attributes=sampling_result.attributes.copy(),
                span_processor=self.span_processor,
                kind=kind,
                links=links,
                instrumentation_info=self.instrumentation_info,
                record_exception=record_exception,
                set_status_on_exception=set_status_on_exception,
            )
            span.start(start_time=start_time, parent_context=context)
        else:
            span = trace_api.NonRecordingSpan(context=span_context)
        return span


class TracerProvider(trace_api.TracerProvider):
    """See `opentelemetry.trace.TracerProvider`."""

    def __init__(
        self,
        sampler: sampling.Sampler = _TRACE_SAMPLER,
        resource: Resource = Resource.create({}),
        shutdown_on_exit: bool = True,
        active_span_processor: Union[
            SynchronousMultiSpanProcessor, ConcurrentMultiSpanProcessor
        ] = None,
        id_generator: IdGenerator = None,
    ):
        self._active_span_processor = (
            active_span_processor or SynchronousMultiSpanProcessor()
        )
        if id_generator is None:
            self.id_generator = RandomIdGenerator()
        else:
            self.id_generator = id_generator
        self._resource = resource
        self.sampler = sampler
        self._atexit_handler = None
        if shutdown_on_exit:
            self._atexit_handler = atexit.register(self.shutdown)

    @property
    def resource(self) -> Resource:
        return self._resource

    def get_tracer(
        self,
        instrumenting_module_name: str,
        instrumenting_library_version: str = "",
    ) -> "trace_api.Tracer":
        if not instrumenting_module_name:  # Reject empty strings too.
            instrumenting_module_name = "ERROR:MISSING MODULE NAME"
            logger.error("get_tracer called with missing module name.")
        return Tracer(
            self.sampler,
            self.resource,
            self._active_span_processor,
            self.id_generator,
            InstrumentationInfo(
                instrumenting_module_name, instrumenting_library_version
            ),
        )

    def add_span_processor(self, span_processor: SpanProcessor) -> None:
        """Registers a new :class:`SpanProcessor` for this `TracerProvider`.

        The span processors are invoked in the same order they are registered.
        """

        # no lock here because add_span_processor is thread safe for both
        # SynchronousMultiSpanProcessor and ConcurrentMultiSpanProcessor.
        self._active_span_processor.add_span_processor(span_processor)

    def shutdown(self):
        """Shut down the span processors added to the tracer."""
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

        Args:
            timeout_millis: The maximum amount of time to wait for spans to be
                processed.

        Returns:
            False if the timeout is exceeded, True otherwise.
        """
        return self._active_span_processor.force_flush(timeout_millis)
