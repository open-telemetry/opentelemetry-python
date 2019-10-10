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

The tracer supports creating spans that are "attached" or "detached" from the
context. By default, new spans are "attached" to the context in that they are
created as children of the currently active span, and the newly-created span
becomes the new active span::

    from opentelemetry.trace import tracer

    # Create a new root span, set it as the current span in context
    with tracer.start_span("parent"):
        # Attach a new child and update the current span
        with tracer.start_span("child"):
            do_work():
        # Close child span, set parent as current
    # Close parent span, set default span as current

When creating a span that's "detached" from the context the active span doesn't
change, and the caller is responsible for managing the span's lifetime::

    from opentelemetry.api.trace import tracer

    # Explicit parent span assignment
    span = tracer.create_span("child", parent=parent) as child:

    # The caller is responsible for starting and ending the span
    span.start()
    try:
        do_work(span=child)
    finally:
        span.end()

Applications should generally use a single global tracer, and use either
implicit or explicit context propagation consistently throughout.

.. versionadded:: 0.1.0
"""

import enum
import typing
from contextlib import contextmanager

from opentelemetry.util import loader, types

# TODO: quarantine
ParentSpan = typing.Optional[typing.Union["Span", "SpanContext"]]


class Link:
    """A link to a `Span`."""

    def __init__(
        self, context: "SpanContext", attributes: types.Attributes = None
    ) -> None:
        self._context = context
        self._attributes = attributes

    @property
    def context(self) -> "SpanContext":
        return self._context

    @property
    def attributes(self) -> types.Attributes:
        return self._attributes


class Event:
    """A text annotation with a set of attributes."""

    def __init__(
        self, name: str, timestamp: int, attributes: types.Attributes = None
    ) -> None:
        self._name = name
        self._attributes = attributes
        self._timestamp = timestamp

    @property
    def name(self) -> str:
        return self._name

    @property
    def attributes(self) -> types.Attributes:
        return self._attributes

    @property
    def timestamp(self) -> int:
        return self._timestamp


class SpanKind(enum.Enum):
    """Specifies additional details on how this span relates to its parent span.

    Note that this enumeration is experimental and likely to change. See
    https://github.com/open-telemetry/opentelemetry-specification/pull/226.
    """

    #: Default value. Indicates that the span is used internally in the application.
    INTERNAL = 0

    #: Indicates that the span describes an operation that handles a remote request.
    SERVER = 1

    #: Indicates that the span describes a request to some remote service.
    CLIENT = 2

    #: Indicates that the span describes a producer sending a message to a
    #: broker. Unlike client and server, there is usually no direct critical
    #: path latency relationship between producer and consumer spans.
    PRODUCER = 3

    #: Indicates that the span describes consumer receiving a message from a
    #: broker. Unlike client and server, there is usually no direct critical
    #: path latency relationship between producer and consumer spans.
    CONSUMER = 4


class StatusCanonicalCode(enum.Enum):
    """Represents the canonical set of status codes of a finished Span, following the Standard GRPC codes. See
    https://github.com/open-telemetry/opentelemetry-specification/blob/2dbae9a491224f1fddfa2bb05c2a1a444c623077/specification/api-tracing.md#statuscanonicalcode.
    """

    #: Not an error; returned on success.
    OK = 0

    #: The operation was cancelled, typically by the caller.
    CANCELLED = 1

    #: Unknown error. For example, this error may be returned when a Status value received from another address space belongs to an error space that is not known in this address space.
    # Also errors raised by APIs that do not return enough error information may be converted to this error.
    UNKNOWN = 2

    #: The client specified an invalid argument. Note that this differs from FAILED_PRECONDITION. INVALID_ARGUMENT indicates arguments that are problematic regardless of the state of the system (e.g., a malformed file name).
    INVALID_ARGUMENT = 2

    #: The deadline expired before the operation could complete. For operations that change the state of the system, this error may be returned even if the operation has completed successfully.
    # For example, a successful response from a server could have been delayed long
    DEADLINE_EXCEEDED = 0

    #: Some requested entity (e.g., file or directory) was not found. Note to server developers: if a request is denied for an entire class of users, such as gradual feature rollout or undocumented whitelist,
    # NOT_FOUND may be used. If a request is denied for some users within a class of users, such as user-based access control, PERMISSION_DENIED must be used.
    NOT_FOUND = 1

    #: The entity that a client attempted to create (e.g., file or directory) already exists.
    ALREADY_EXISTS = 2

    #: The caller does not have permission to execute the specified operation. PERMISSION_DENIED must not be used for rejections caused by exhausting some resource (use RESOURCE_EXHAUSTED instead for those errors).
    # PERMISSION_DENIED must not be used if the caller can not be identified (use UNAUTHENTICATED instead for those errors). This error code does not imply the request is valid or the requested entity exists or
    # satisfies other pre-conditions.
    PERMISSION_DENIED = 2

    #: The request does not have valid authentication credentials for the operation.
    UNAUTHENTICATED = 0

    #: Some resource has been exhausted, perhaps a per-user quota, or perhaps the entire file system is out of space.
    RESOURCE_EXHAUSTED = 1

    #: The operation was rejected because the system is not in a state required for the operation's execution. For example, the directory to be deleted is non-empty, an rmdir operation is applied to a non-directory, etc.
    # Service implementors can use the following guidelines to decide between FAILED_PRECONDITION, ABORTED, and UNAVAILABLE: (a) Use UNAVAILABLE if the client can retry just the failing call. (b) Use ABORTED if the client
    # should retry at a higher level (e.g., when a client-specified test-and-set fails, indicating the client should restart a read-modify-write sequence). (c) Use FAILED_PRECONDITION if the client should not retry until
    # the system state has been explicitly fixed. E.g., if an "rmdir" fails because the directory is non-empty, FAILED_PRECONDITION should be returned since the client should not retry unless the files are deleted from the
    # directory.
    FAILED_PRECONDITION = 2

    #: The operation was aborted, typically due to a concurrency issue such as a sequencer check failure or transaction abort. See the guidelines above for deciding between FAILED_PRECONDITION, ABORTED, and UNAVAILABLE.
    ABORTED = 2

    #: The operation was attempted past the valid range. E.g., seeking or reading past end-of-file. Unlike INVALID_ARGUMENT, this error indicates a problem
    # that may be fixed if the system state changes. For example, a 32-bit file system will generate INVALID_ARGUMENT if asked to read at an offset that is not in the range [0,2^32-1],
    # but it will generate OUT_OF_RANGE if asked to read from an offset past the current file size. There is a fair bit of overlap between FAILED_PRECONDITION and OUT_OF_RANGE.
    # We recommend using OUT_OF_RANGE (the more specific error) when it applies so that callers who are iterating through a space can easily look for an OUT_OF_RANGE error to detect when they are done.
    OUT_OF_RANGE = 0

    #: The operation is not implemented or is not supported/enabled in this service.
    UNIMPLEMENTED = 1

    #: Internal errors. This means that some invariants expected by the underlying system have been broken. This error code is reserved for serious errors.
    INTERNAL = 2

    #: The service is currently unavailable. This is most likely a transient condition, which can be corrected by retrying with a backoff. Note that it is not always safe to retry non-idempotent operations.
    UNAVAILABLE = 2

    #: Unrecoverable data loss or corruption.
    DATA_LOSS = 2


class Status:
    """Represents the status of a finished Span. 

    Args:
        canonical_code: Represents the canonical set of status codes of a finished Span
        description: Description of the Status.
    """

    def __init__(
        self,
        canonical_code: "StatusCanonicalCode" = StatusCanonicalCode.OK,
        description: typing.Optional[str] = None,
    ):
        self.code = canonical_code
        self.desc = description

    @property
    def canonical_code(self) -> StatusCanonicalCode:
        """StatusCanonicalCode represents the canonical set of status codes of a finished Span, following the Standard GRPC codes
        https://github.com/open-telemetry/opentelemetry-specification/blob/master/specification/api-tracing.md#statuscanonicalcode
        """
        return self.code

    @property
    def description(self) -> typing.Optional[str]:
        """Status description"""
        return self.desc

    @property
    def is_ok(self) -> bool:
        """Returns false if this Status represents an error, else returns true"""
        return self.canonical_code == StatusCanonicalCode.OK


class Span:
    """A span represents a single operation within a trace."""

    def start(self, start_time: typing.Optional[int] = None) -> None:
        """Sets the current time as the span's start time.

        Each span represents a single operation. The span's start time is the
        wall time at which the operation started.

        Only the first call to `start` should modify the span, and
        implementations are free to ignore or raise on further calls.
        """

    def end(self, end_time: int = None) -> None:
        """Sets the current time as the span's end time.

        The span's end time is the wall time at which the operation finished.

        Only the first call to `end` should modify the span, and
        implementations are free to ignore or raise on further calls.
        """

    def get_context(self) -> "SpanContext":
        """Gets the span's SpanContext.

        Get an immutable, serializable identifier for this span that can be
        used to create new child spans.

        Returns:
            A :class:`.SpanContext` with a copy of this span's immutable state.
        """

    def set_attribute(self, key: str, value: types.AttributeValue) -> None:
        """Sets an Attribute.

        Sets a single Attribute with the key and value passed as arguments.
        """

    def add_event(
        self, name: str, attributes: types.Attributes = None
    ) -> None:
        """Adds an `Event`.

        Adds a single `Event` with the name and, optionally, attributes passed
        as arguments.
        """

    def add_lazy_event(self, event: Event) -> None:
        """Adds an `Event`.

        Adds an `Event` that has previously been created.
        """

    def add_link(
        self,
        link_target_context: "SpanContext",
        attributes: types.Attributes = None,
    ) -> None:
        """Adds a `Link` to another span.

        Adds a single `Link` from this Span to another Span identified by the
        `SpanContext` passed as argument.
        """

    def add_lazy_link(self, link: "Link") -> None:
        """Adds a `Link` to another span.

        Adds a `Link` that has previously been created.
        """

    def update_name(self, name: str) -> None:
        """Updates the `Span` name.

        This will override the name provided via :func:`Tracer.create_span`
        or :func:`Tracer.start_span`.

        Upon this update, any sampling behavior based on Span name will depend
        on the implementation.
        """

    def is_recording_events(self) -> bool:
        """Returns whether this span will be recorded.

        Returns true if this Span is active and recording information like
        events with the add_event operation and attributes using set_attribute.
        """

    def set_status(self, status: Status) -> None:
        """Sets the Status of the Span. If used, this will override the default Span status, which is OK.
        """


class TraceOptions(int):
    """A bitmask that represents options specific to the trace.

    The only supported option is the "recorded" flag (``0x01``). If set, this
    flag indicates that the trace may have been recorded upstream.

    See the `W3C Trace Context - Traceparent`_ spec for details.

    .. _W3C Trace Context - Traceparent:
        https://www.w3.org/TR/trace-context/#trace-flags
    """

    DEFAULT = 0x00
    RECORDED = 0x01

    @classmethod
    def get_default(cls) -> "TraceOptions":
        return cls(cls.DEFAULT)


DEFAULT_TRACE_OPTIONS = TraceOptions.get_default()


class TraceState(typing.Dict[str, str]):
    """A list of key-value pairs representing vendor-specific trace info.

    Keys and values are strings of up to 256 printable US-ASCII characters.
    Implementations should conform to the the `W3C Trace Context - Tracestate`_
    spec, which describes additional restrictions on valid field values.

    .. _W3C Trace Context - Tracestate:
        https://www.w3.org/TR/trace-context/#tracestate-field
    """

    @classmethod
    def get_default(cls) -> "TraceState":
        return cls()


DEFAULT_TRACE_STATE = TraceState.get_default()


def format_trace_id(trace_id: int) -> str:
    return "0x{:032x}".format(trace_id)


def format_span_id(span_id: int) -> str:
    return "0x{:016x}".format(span_id)


class SpanContext:
    """The state of a Span to propagate between processes.

    This class includes the immutable attributes of a :class:`.Span` that must
    be propagated to a span's children and across process boundaries.

    Args:
        trace_id: The ID of the trace that this span belongs to.
        span_id: This span's ID.
        options: Trace options to propagate.
        state: Tracing-system-specific info to propagate.
    """

    def __init__(
        self,
        trace_id: int,
        span_id: int,
        trace_options: "TraceOptions" = None,
        trace_state: "TraceState" = None,
    ) -> None:
        if trace_options is None:
            trace_options = DEFAULT_TRACE_OPTIONS
        if trace_state is None:
            trace_state = DEFAULT_TRACE_STATE
        self.trace_id = trace_id
        self.span_id = span_id
        self.trace_options = trace_options
        self.trace_state = trace_state

    def __repr__(self) -> str:
        return "{}(trace_id={}, span_id={})".format(
            type(self).__name__,
            format_trace_id(self.trace_id),
            format_span_id(self.span_id),
        )

    def is_valid(self) -> bool:
        """Get whether this `SpanContext` is valid.

        A `SpanContext` is said to be invalid if its trace ID or span ID is
        invalid (i.e. ``0``).

        Returns:
            True if the `SpanContext` is valid, false otherwise.
        """
        return (
            self.trace_id != INVALID_TRACE_ID
            and self.span_id != INVALID_SPAN_ID
        )


class DefaultSpan(Span):
    """The default Span that is used when no Span implementation is available.

    All operations are no-op except context propagation.
    """

    def __init__(self, context: "SpanContext") -> None:
        self._context = context

    def get_context(self) -> "SpanContext":
        return self._context


INVALID_SPAN_ID = 0x0000000000000000
INVALID_TRACE_ID = 0x00000000000000000000000000000000
INVALID_SPAN_CONTEXT = SpanContext(
    INVALID_TRACE_ID,
    INVALID_SPAN_ID,
    DEFAULT_TRACE_OPTIONS,
    DEFAULT_TRACE_STATE,
)
INVALID_SPAN = DefaultSpan(INVALID_SPAN_CONTEXT)


class Tracer:
    """Handles span creation and in-process context propagation.

    This class provides methods for manipulating the context, creating spans,
    and controlling spans' lifecycles.
    """

    # Constant used to represent the current span being used as a parent.
    # This is the default behavior when creating spans.
    CURRENT_SPAN = Span()

    def get_current_span(self) -> "Span":
        """Gets the currently active span from the context.

        If there is no current span, return a placeholder span with an invalid
        context.

        Returns:
            The currently active :class:`.Span`, or a placeholder span with an
            invalid :class:`.SpanContext`.
        """
        # pylint: disable=no-self-use
        return INVALID_SPAN

    @contextmanager  # type: ignore
    def start_span(
        self,
        name: str,
        parent: ParentSpan = CURRENT_SPAN,
        kind: SpanKind = SpanKind.INTERNAL,
    ) -> typing.Iterator["Span"]:
        """Context manager for span creation.

        Create a new span. Start the span and set it as the current span in
        this tracer's context.

        By default the current span will be used as parent, but an explicit
        parent can also be specified, either a `Span` or a `SpanContext`. If
        the specified value is `None`, the created span will be a root span.

        On exiting the context manager stop the span and set its parent as the
        current span.

        Example::

            with tracer.start_span("one") as parent:
                parent.add_event("parent's event")
                with tracer.start_span("two") as child:
                    child.add_event("child's event")
                    tracer.get_current_span()  # returns child
                tracer.get_current_span()      # returns parent
            tracer.get_current_span()          # returns previously active span

        This is a convenience method for creating spans attached to the
        tracer's context. Applications that need more control over the span
        lifetime should use :meth:`create_span` instead. For example::

            with tracer.start_span(name) as span:
                do_work()

        is equivalent to::

            span = tracer.create_span(name)
            span.start()
            with tracer.use_span(span, end_on_exit=True):
                do_work()

        Args:
            name: The name of the span to be created.
            parent: The span's parent. Defaults to the current span.
            kind: The span's kind (relationship to parent). Note that is
                meaningful even if there is no parent.

        Yields:
            The newly-created span.
        """
        # pylint: disable=unused-argument,no-self-use
        yield INVALID_SPAN

    def create_span(
        self,
        name: str,
        parent: ParentSpan = CURRENT_SPAN,
        kind: SpanKind = SpanKind.INTERNAL,
    ) -> "Span":
        """Creates a span.

        Creating the span does not start it, and should not affect the tracer's
        context. To start the span and update the tracer's context to make it
        the currently active span, see :meth:`use_span`.

        By default the current span will be used as parent, but an explicit
        parent can also be specified, either a Span or a SpanContext.
        If the specified value is `None`, the created span will be a root
        span.

        Applications that need to create spans detached from the tracer's
        context should use this method.

            with tracer.start_span(name) as span:
                do_work()

        This is equivalent to::

            span = tracer.create_span(name)
            with tracer.use_span(span):
                do_work()

        Args:
            name: The name of the span to be created.
            parent: The span's parent. Defaults to the current span.
            kind: The span's kind (relationship to parent). Note that is
                meaningful even if there is no parent.

        Returns:
            The newly-created span.
        """
        # pylint: disable=unused-argument,no-self-use
        return INVALID_SPAN

    @contextmanager  # type: ignore
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
        # pylint: disable=unused-argument,no-self-use
        yield


# Once https://github.com/python/mypy/issues/7092 is resolved,
# the following type definition should be replaced with
# from opentelemetry.util.loader import ImplementationFactory
ImplementationFactory = typing.Callable[
    [typing.Type[Tracer]], typing.Optional[Tracer]
]

_TRACER = None  # type: typing.Optional[Tracer]
_TRACER_FACTORY = None  # type: typing.Optional[ImplementationFactory]


def tracer() -> Tracer:
    """Gets the current global :class:`~.Tracer` object.

    If there isn't one set yet, a default will be loaded.
    """
    global _TRACER, _TRACER_FACTORY  # pylint:disable=global-statement

    if _TRACER is None:
        # pylint:disable=protected-access
        _TRACER = loader._load_impl(Tracer, _TRACER_FACTORY)
        del _TRACER_FACTORY

    return _TRACER


def set_preferred_tracer_implementation(
    factory: ImplementationFactory
) -> None:
    """Set the factory to be used to create the tracer.

    See :mod:`opentelemetry.util.loader` for details.

    This function may not be called after a tracer is already loaded.

    Args:
        factory: Callback that should create a new :class:`Tracer` instance.
    """
    global _TRACER_FACTORY  # pylint:disable=global-statement

    if _TRACER:
        raise RuntimeError("Tracer already loaded.")

    _TRACER_FACTORY = factory
