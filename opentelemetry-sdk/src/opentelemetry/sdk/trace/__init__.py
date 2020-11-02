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


import abc
import atexit
import concurrent.futures
import json
import logging
import threading
import traceback
from collections import OrderedDict
from contextlib import contextmanager
from types import MappingProxyType, TracebackType
from typing import (
    Any,
    Callable,
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
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import sampling
from opentelemetry.sdk.util import BoundedDict, BoundedList
from opentelemetry.sdk.util.instrumentation import InstrumentationInfo
from opentelemetry.trace import SpanContext
from opentelemetry.trace.propagation import SPAN_KEY
from opentelemetry.trace.status import (
    EXCEPTION_STATUS_FIELD,
    Status,
    StatusCode,
)
from opentelemetry.util import time_ns, types

logger = logging.getLogger(__name__)

MAX_NUM_ATTRIBUTES = 1000
MAX_NUM_EVENTS = 1000
MAX_NUM_LINKS = 1000
VALID_ATTR_VALUE_TYPES = (bool, str, int, float)


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

    def on_end(self, span: "Span") -> None:
        """Called when a :class:`opentelemetry.trace.Span` is ended.

        This method is called synchronously on the thread that ends the
        span, therefore it should not block or throw an exception.

        Args:
            span: The :class:`opentelemetry.trace.Span` that just ended.
        """

    def shutdown(self) -> None:
        """Called when a :class:`opentelemetry.sdk.trace.Tracer` is shutdown.
        """

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Export all ended spans to the configured Exporter that have not yet
        been exported.

        Args:
            timeout_millis: The maximum amount of time to wait for spans to be
                exported.

        Returns:
            False if the timeout is exceeded, True otherwise.
        """


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

    def on_end(self, span: "Span") -> None:
        for sp in self._span_processors:
            sp.on_end(span)

    def shutdown(self) -> None:
        """Sequentially shuts down all underlying span processors.
        """
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
        deadline_ns = time_ns() + timeout_millis * 1000000
        for sp in self._span_processors:
            current_time_ns = time_ns()
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

    def on_end(self, span: "Span") -> None:
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
            self._timestamp = time_ns()
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
            if element_type not in VALID_ATTR_VALUE_TYPES:
                logger.warning(
                    "Invalid type %s in attribute value sequence. Expected one of "
                    "%s or None",
                    element_type.__name__,
                    [
                        valid_type.__name__
                        for valid_type in VALID_ATTR_VALUE_TYPES
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

    elif not isinstance(value, VALID_ATTR_VALUE_TYPES):
        logger.warning(
            "Invalid type %s for attribute value. Expected one of %s or a "
            "sequence of those types",
            type(value).__name__,
            [valid_type.__name__ for valid_type in VALID_ATTR_VALUE_TYPES],
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
            if self.end_time is None:
                func(self, *args, **kwargs)
            else:
                already_ended = True

        if already_ended:
            logger.warning("Tried calling %s on an ended span.", func.__name__)

    return wrapper


class Span(trace_api.Span):
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

    def __init__(
        self,
        name: str,
        context: trace_api.SpanContext,
        parent: Optional[trace_api.SpanContext] = None,
        sampler: Optional[sampling.Sampler] = None,
        trace_config: None = None,  # TODO
        resource: Resource = Resource.create({}),
        attributes: types.Attributes = None,  # TODO
        events: Sequence[Event] = None,  # TODO
        links: Sequence[trace_api.Link] = (),
        kind: trace_api.SpanKind = trace_api.SpanKind.INTERNAL,
        span_processor: SpanProcessor = SpanProcessor(),
        instrumentation_info: InstrumentationInfo = None,
        set_status_on_exception: bool = True,
    ) -> None:

        self.name = name
        self.context = context
        self.parent = parent
        self.sampler = sampler
        self.trace_config = trace_config
        self.resource = resource
        self.kind = kind
        self._set_status_on_exception = set_status_on_exception

        self.span_processor = span_processor
        self.status = Status(StatusCode.UNSET)
        self._lock = threading.Lock()

        _filter_attribute_values(attributes)
        if not attributes:
            self.attributes = self._new_attributes()
        else:
            self.attributes = BoundedDict.from_map(
                MAX_NUM_ATTRIBUTES, attributes
            )

        self.events = self._new_events()
        if events:
            for event in events:
                _filter_attribute_values(event.attributes)
                # pylint: disable=protected-access
                event._attributes = _create_immutable_attributes(
                    event.attributes
                )
                self.events.append(event)

        if links is None:
            self.links = self._new_links()
        else:
            self.links = BoundedList.from_seq(MAX_NUM_LINKS, links)

        self._end_time = None  # type: Optional[int]
        self._start_time = None  # type: Optional[int]
        self.instrumentation_info = instrumentation_info

    @property
    def start_time(self):
        return self._start_time

    @property
    def end_time(self):
        return self._end_time

    def __repr__(self):
        return '{}(name="{}", context={})'.format(
            type(self).__name__, self.name, self.context
        )

    @staticmethod
    def _new_attributes():
        return BoundedDict(MAX_NUM_ATTRIBUTES)

    @staticmethod
    def _new_events():
        return BoundedList(MAX_NUM_EVENTS)

    @staticmethod
    def _new_links():
        return BoundedList(MAX_NUM_LINKS)

    @staticmethod
    def _format_context(context):
        x_ctx = OrderedDict()
        x_ctx["trace_id"] = trace_api.format_trace_id(context.trace_id)
        x_ctx["span_id"] = trace_api.format_span_id(context.span_id)
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

    def to_json(self, indent=4):
        parent_id = None
        if self.parent is not None:
            if isinstance(self.parent, Span):
                ctx = self.parent.context
                parent_id = trace_api.format_span_id(ctx.span_id)
            elif isinstance(self.parent, SpanContext):
                parent_id = trace_api.format_span_id(self.parent.span_id)

        start_time = None
        if self.start_time:
            start_time = util.ns_to_iso_str(self.start_time)

        end_time = None
        if self.end_time:
            end_time = util.ns_to_iso_str(self.end_time)

        if self.status is not None:
            status = OrderedDict()
            status["status_code"] = str(self.status.status_code.name)
            if self.status.description:
                status["description"] = self.status.description

        f_span = OrderedDict()

        f_span["name"] = self.name
        f_span["context"] = self._format_context(self.context)
        f_span["kind"] = str(self.kind)
        f_span["parent_id"] = parent_id
        f_span["start_time"] = start_time
        f_span["end_time"] = end_time
        if self.status is not None:
            f_span["status"] = status
        f_span["attributes"] = self._format_attributes(self.attributes)
        f_span["events"] = self._format_events(self.events)
        f_span["links"] = self._format_links(self.links)
        f_span["resource"] = self.resource.attributes

        return json.dumps(f_span, indent=indent)

    def get_span_context(self):
        return self.context

    def set_attribute(self, key: str, value: types.AttributeValue) -> None:
        if not _is_valid_attribute_value(value):
            return

        if not key:
            logger.warning("invalid key (empty or null)")
            return

        with self._lock:
            if self.end_time is not None:
                logger.warning("Setting attribute on ended span.")
                return

            # Freeze mutable sequences defensively
            if isinstance(value, MutableSequence):
                value = tuple(value)
            if isinstance(value, bytes):
                try:
                    value = value.decode()
                except ValueError:
                    logger.warning("Byte attribute could not be decoded.")
                    return
            self.attributes[key] = value

    @_check_span_ended
    def _add_event(self, event: EventBase) -> None:
        self.events.append(event)

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
                timestamp=time_ns() if timestamp is None else timestamp,
            )
        )

    def start(
        self,
        start_time: Optional[int] = None,
        parent_context: Optional[context_api.Context] = None,
    ) -> None:
        with self._lock:
            if self.start_time is not None:
                logger.warning("Calling start() on a started span.")
                return
            self._start_time = (
                start_time if start_time is not None else time_ns()
            )

        self.span_processor.on_start(self, parent_context=parent_context)

    def end(self, end_time: Optional[int] = None) -> None:
        with self._lock:
            if self.start_time is None:
                raise RuntimeError("Calling end() on a not started span.")
            if self.end_time is not None:
                logger.warning("Calling end() on an ended span.")
                return

            self._end_time = end_time if end_time is not None else time_ns()

        self.span_processor.on_end(self)

    @_check_span_ended
    def update_name(self, name: str) -> None:
        self.name = name

    def is_recording(self) -> bool:
        return self._end_time is None

    @_check_span_ended
    def set_status(self, status: trace_api.Status) -> None:
        self.status = status

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Ends context manager and calls `end` on the `Span`."""
        # Records status if span is used as context manager
        # i.e. with tracer.start_span() as span:
        # TODO: Record exception
        if (
            self.status.status_code is StatusCode.UNSET
            and self._set_status_on_exception
            and exc_val is not None
        ):
            self.set_status(
                Status(
                    status_code=StatusCode.ERROR,
                    description="{}: {}".format(exc_type.__name__, exc_val),
                )
            )

        super().__exit__(exc_type, exc_val, exc_tb)

    def record_exception(self, exception: Exception) -> None:
        """Records an exception as a span event."""
        try:
            stacktrace = traceback.format_exc()
        except Exception:  # pylint: disable=broad-except
            # workaround for python 3.4, format_exc can raise
            # an AttributeError if the __context__ on
            # an exception is None
            stacktrace = "Exception occurred on stacktrace formatting"

        self.add_event(
            name="exception",
            attributes={
                "exception.type": exception.__class__.__name__,
                "exception.message": str(exception),
                "exception.stacktrace": stacktrace,
            },
        )


class _Span(Span):
    """Protected implementation of `opentelemetry.trace.Span`.

    This constructor should only be used internally.
    """


class Tracer(trace_api.Tracer):
    """See `opentelemetry.trace.Tracer`.
    """

    def __init__(
        self,
        sampler: sampling.Sampler,
        resource: Resource,
        span_processor: Union[
            SynchronousMultiSpanProcessor, ConcurrentMultiSpanProcessor
        ],
        ids_generator: trace_api.IdsGenerator,
        instrumentation_info: InstrumentationInfo,
    ) -> None:
        self.sampler = sampler
        self.resource = resource
        self.span_processor = span_processor
        self.ids_generator = ids_generator
        self.instrumentation_info = instrumentation_info

    def start_as_current_span(
        self,
        name: str,
        context: Optional[context_api.Context] = None,
        kind: trace_api.SpanKind = trace_api.SpanKind.INTERNAL,
        attributes: types.Attributes = None,
        links: Sequence[trace_api.Link] = (),
        record_exception: bool = True,
    ) -> Iterator[trace_api.Span]:
        span = self.start_span(name, context, kind, attributes, links)
        return self.use_span(
            span, end_on_exit=True, record_exception=record_exception
        )

    def start_span(  # pylint: disable=too-many-locals
        self,
        name: str,
        context: Optional[context_api.Context] = None,
        kind: trace_api.SpanKind = trace_api.SpanKind.INTERNAL,
        attributes: types.Attributes = None,
        links: Sequence[trace_api.Link] = (),
        start_time: Optional[int] = None,
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
            trace_id = self.ids_generator.generate_trace_id()
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
            context, trace_id, name, attributes, links,
        )

        trace_flags = (
            trace_api.TraceFlags(trace_api.TraceFlags.SAMPLED)
            if sampling_result.decision.is_sampled()
            else trace_api.TraceFlags(trace_api.TraceFlags.DEFAULT)
        )
        span_context = trace_api.SpanContext(
            trace_id,
            self.ids_generator.generate_span_id(),
            is_remote=False,
            trace_flags=trace_flags,
            trace_state=trace_state,
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
                set_status_on_exception=set_status_on_exception,
            )
            span.start(start_time=start_time, parent_context=context)
        else:
            span = trace_api.DefaultSpan(context=span_context)
        return span

    @contextmanager
    def use_span(
        self,
        span: trace_api.Span,
        end_on_exit: bool = False,
        record_exception: bool = True,
    ) -> Iterator[trace_api.Span]:
        try:
            token = context_api.attach(context_api.set_value(SPAN_KEY, span))
            try:
                yield span
            finally:
                context_api.detach(token)

        except Exception as error:  # pylint: disable=broad-except
            # pylint:disable=protected-access
            if isinstance(span, Span):
                if record_exception:
                    span.record_exception(error)

                # Records status if use_span is used
                # i.e. with tracer.start_as_current_span() as span:
                if (
                    span.status.status_code is StatusCode.UNSET
                    and span._set_status_on_exception
                ):
                    span.set_status(
                        Status(
                            status_code=getattr(
                                error,
                                EXCEPTION_STATUS_FIELD,
                                StatusCode.ERROR,
                            ),
                            description="{}: {}".format(
                                type(error).__name__, error
                            ),
                        )
                    )
            raise

        finally:
            if end_on_exit:
                span.end()


class TracerProvider(trace_api.TracerProvider):
    def __init__(
        self,
        sampler: sampling.Sampler = sampling.DEFAULT_ON,
        resource: Resource = Resource.create({}),
        shutdown_on_exit: bool = True,
        active_span_processor: Union[
            SynchronousMultiSpanProcessor, ConcurrentMultiSpanProcessor
        ] = None,
        ids_generator: trace_api.IdsGenerator = None,
    ):
        self._active_span_processor = (
            active_span_processor or SynchronousMultiSpanProcessor()
        )
        if ids_generator is None:
            self.ids_generator = trace_api.RandomIdsGenerator()
        else:
            self.ids_generator = ids_generator
        self.resource = resource
        self.sampler = sampler
        self._atexit_handler = None
        if shutdown_on_exit:
            self._atexit_handler = atexit.register(self.shutdown)

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
            self.ids_generator,
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
