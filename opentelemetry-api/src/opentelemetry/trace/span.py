import abc
import logging
import types as python_types
import typing

from opentelemetry.trace.status import Status
from opentelemetry.util import types

_logger = logging.getLogger(__name__)


class Span(abc.ABC):
    """A span represents a single operation within a trace."""

    @abc.abstractmethod
    def end(self, end_time: typing.Optional[int] = None) -> None:
        """Sets the current time as the span's end time.

        The span's end time is the wall time at which the operation finished.

        Only the first call to `end` should modify the span, and
        implementations are free to ignore or raise on further calls.
        """

    @abc.abstractmethod
    def get_span_context(self) -> "SpanContext":
        """Gets the span's SpanContext.

        Get an immutable, serializable identifier for this span that can be
        used to create new child spans.

        Returns:
            A :class:`opentelemetry.trace.SpanContext` with a copy of this span's immutable state.
        """

    @abc.abstractmethod
    def set_attribute(self, key: str, value: types.AttributeValue) -> None:
        """Sets an Attribute.

        Sets a single Attribute with the key and value passed as arguments.
        """

    @abc.abstractmethod
    def add_event(
        self,
        name: str,
        attributes: types.Attributes = None,
        timestamp: typing.Optional[int] = None,
    ) -> None:
        """Adds an `Event`.

        Adds a single `Event` with the name and, optionally, a timestamp and
        attributes passed as arguments. Implementations should generate a
        timestamp if the `timestamp` argument is omitted.
        """

    @abc.abstractmethod
    def update_name(self, name: str) -> None:
        """Updates the `Span` name.

        This will override the name provided via :func:`opentelemetry.trace.Tracer.start_span`.

        Upon this update, any sampling behavior based on Span name will depend
        on the implementation.
        """

    @abc.abstractmethod
    def is_recording(self) -> bool:
        """Returns whether this span will be recorded.

        Returns true if this Span is active and recording information like
        events with the add_event operation and attributes using set_attribute.
        """

    @abc.abstractmethod
    def set_status(self, status: Status) -> None:
        """Sets the Status of the Span. If used, this will override the default
        Span status, which is OK.
        """

    @abc.abstractmethod
    def record_exception(self, exception: Exception) -> None:
        """Records an exception as a span event."""

    def __enter__(self) -> "Span":
        """Invoked when `Span` is used as a context manager.

        Returns the `Span` itself.
        """
        return self

    def __exit__(
        self,
        exc_type: typing.Optional[typing.Type[BaseException]],
        exc_val: typing.Optional[BaseException],
        exc_tb: typing.Optional[python_types.TracebackType],
    ) -> None:
        """Ends context manager and calls `end` on the `Span`."""

        self.end()


class TraceFlags(int):
    """A bitmask that represents options specific to the trace.

    The only supported option is the "sampled" flag (``0x01``). If set, this
    flag indicates that the trace may have been sampled upstream.

    See the `W3C Trace Context - Traceparent`_ spec for details.

    .. _W3C Trace Context - Traceparent:
        https://www.w3.org/TR/trace-context/#trace-flags
    """

    DEFAULT = 0x00
    SAMPLED = 0x01

    @classmethod
    def get_default(cls) -> "TraceFlags":
        return cls(cls.DEFAULT)

    @property
    def sampled(self) -> bool:
        return bool(self & TraceFlags.SAMPLED)


DEFAULT_TRACE_OPTIONS = TraceFlags.get_default()


class TraceState(typing.Dict[str, str]):
    """A list of key-value pairs representing vendor-specific trace info.

    Keys and values are strings of up to 256 printable US-ASCII characters.
    Implementations should conform to the `W3C Trace Context - Tracestate`_
    spec, which describes additional restrictions on valid field values.

    .. _W3C Trace Context - Tracestate:
        https://www.w3.org/TR/trace-context/#tracestate-field
    """

    @classmethod
    def get_default(cls) -> "TraceState":
        return cls()


DEFAULT_TRACE_STATE = TraceState.get_default()


class SpanContext(
    typing.Tuple[int, int, bool, "TraceFlags", "TraceState", bool]
):
    """The state of a Span to propagate between processes.

    This class includes the immutable attributes of a :class:`.Span` that must
    be propagated to a span's children and across process boundaries.

    Args:
        trace_id: The ID of the trace that this span belongs to.
        span_id: This span's ID.
        trace_flags: Trace options to propagate.
        trace_state: Tracing-system-specific info to propagate.
        is_remote: True if propagated from a remote parent.
    """

    def __new__(
        cls,
        trace_id: int,
        span_id: int,
        is_remote: bool,
        trace_flags: "TraceFlags" = DEFAULT_TRACE_OPTIONS,
        trace_state: "TraceState" = DEFAULT_TRACE_STATE,
    ) -> "SpanContext":
        if trace_flags is None:
            trace_flags = DEFAULT_TRACE_OPTIONS
        if trace_state is None:
            trace_state = DEFAULT_TRACE_STATE

        is_valid = trace_id != INVALID_TRACE_ID and span_id != INVALID_SPAN_ID

        return tuple.__new__(
            cls,
            (trace_id, span_id, is_remote, trace_flags, trace_state, is_valid),
        )

    @property
    def trace_id(self) -> int:
        return self[0]  # pylint: disable=unsubscriptable-object

    @property
    def span_id(self) -> int:
        return self[1]  # pylint: disable=unsubscriptable-object

    @property
    def is_remote(self) -> bool:
        return self[2]  # pylint: disable=unsubscriptable-object

    @property
    def trace_flags(self) -> "TraceFlags":
        return self[3]  # pylint: disable=unsubscriptable-object

    @property
    def trace_state(self) -> "TraceState":
        return self[4]  # pylint: disable=unsubscriptable-object

    @property
    def is_valid(self) -> bool:
        return self[5]  # pylint: disable=unsubscriptable-object

    def __setattr__(self, *args: str) -> None:
        _logger.debug(
            "Immutable type, ignoring call to set attribute", stack_info=True
        )

    def __delattr__(self, *args: str) -> None:
        _logger.debug(
            "Immutable type, ignoring call to set attribute", stack_info=True
        )

    def __repr__(self) -> str:
        return (
            "{}(trace_id={}, span_id={}, trace_state={!r}, is_remote={})"
        ).format(
            type(self).__name__,
            format_trace_id(self.trace_id),
            format_span_id(self.span_id),
            self.trace_state,
            self.is_remote,
        )


class DefaultSpan(Span):
    """The default Span that is used when no Span implementation is available.

    All operations are no-op except context propagation.
    """

    def __init__(self, context: "SpanContext") -> None:
        self._context = context

    def get_span_context(self) -> "SpanContext":
        return self._context

    def is_recording(self) -> bool:
        return False

    def end(self, end_time: typing.Optional[int] = None) -> None:
        pass

    def set_attribute(self, key: str, value: types.AttributeValue) -> None:
        pass

    def add_event(
        self,
        name: str,
        attributes: types.Attributes = None,
        timestamp: typing.Optional[int] = None,
    ) -> None:
        pass

    def update_name(self, name: str) -> None:
        pass

    def set_status(self, status: Status) -> None:
        pass

    def record_exception(self, exception: Exception) -> None:
        pass


INVALID_SPAN_ID = 0x0000000000000000
INVALID_TRACE_ID = 0x00000000000000000000000000000000
INVALID_SPAN_CONTEXT = SpanContext(
    trace_id=INVALID_TRACE_ID,
    span_id=INVALID_SPAN_ID,
    is_remote=False,
    trace_flags=DEFAULT_TRACE_OPTIONS,
    trace_state=DEFAULT_TRACE_STATE,
)
INVALID_SPAN = DefaultSpan(INVALID_SPAN_CONTEXT)


def format_trace_id(trace_id: int) -> str:
    return "0x{:032x}".format(trace_id)


def format_span_id(span_id: int) -> str:
    return "0x{:016x}".format(span_id)


def get_hexadecimal_trace_id(trace_id: int) -> str:
    return "{:032x}".format(trace_id)


def get_hexadecimal_span_id(span_id: int) -> str:
    return "{:016x}".format(span_id)
