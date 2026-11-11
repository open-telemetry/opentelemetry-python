# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import abc
import atexit
import base64
import concurrent.futures
import json
import logging
import os
import threading
import traceback
import warnings
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from os import environ
from threading import Lock
from time import time_ns
from types import NoneType
from typing import (  # noqa
    Any,
    Tuple,
    Union,
    cast,
    overload,
)
from weakref import WeakMethod, WeakSet

from typing_extensions import deprecated

from opentelemetry._logs import Logger as APILogger
from opentelemetry._logs import LoggerProvider as APILoggerProvider
from opentelemetry._logs import (
    LogRecord,
    NoOpLogger,
    SeverityNumber,
    get_logger,
    get_logger_provider,
)
from opentelemetry.attributes import BoundedAttributes
from opentelemetry.context import get_current
from opentelemetry.context.context import Context
from opentelemetry.metrics import MeterProvider, get_meter_provider
from opentelemetry.sdk._logs._internal._exceptions import (
    _copy_log_record_with_exception,
    _create_log_record_with_exception,
    _set_log_record_exception_attributes,
)
from opentelemetry.sdk._logs._internal._logger_metrics import (
    LoggerMetricsT,
    create_logger_metrics,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_ATTRIBUTE_COUNT_LIMIT,
    OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT,
    OTEL_LOGRECORD_ATTRIBUTE_COUNT_LIMIT,
    OTEL_LOGRECORD_ATTRIBUTE_VALUE_LENGTH_LIMIT,
    OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED,
    OTEL_SDK_DISABLED,
)
from opentelemetry.sdk.environment_variables._internal import (
    parse_boolean_environment_variable,
)
from opentelemetry.sdk.resources import (
    Resource,
    _get_process_dependent_resource,
)
from opentelemetry.sdk.util import ns_to_iso_str
from opentelemetry.sdk.util._configurator import RuleBasedConfigurator
from opentelemetry.sdk.util.instrumentation import (
    InstrumentationScope,
)
from opentelemetry.semconv.attributes import (
    code_attributes,
    exception_attributes,
)
from opentelemetry.trace import (
    format_span_id,
    format_trace_id,
)
from opentelemetry.util.types import AnyValue, Attributes

# pylint: disable=too-many-lines


_DEFAULT_OTEL_ATTRIBUTE_COUNT_LIMIT = 128
_ENV_VALUE_UNSET = ""

_logger = logging.getLogger(__name__)


class BytesEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, bytes):
            return base64.b64encode(o).decode()
        return super().default(o)


class LogRecordDroppedAttributesWarning(UserWarning):
    """Custom warning to indicate dropped log attributes due to limits.

    This class is used to filter and handle these specific warnings separately
    from other warnings, ensuring that they are only shown once without
    interfering with default user warnings.
    """


warnings.simplefilter("once", LogRecordDroppedAttributesWarning)


@deprecated(
    "Use LogRecordDroppedAttributesWarning. Since logs are not stable yet this WILL be removed in future releases."
)
class LogDroppedAttributesWarning(LogRecordDroppedAttributesWarning):
    """Deprecated alias of ``LogRecordDroppedAttributesWarning``."""


class LogRecordLimits:
    """This class is based on a SpanLimits class in the Tracing module.

    This class represents the limits that should be enforced on recorded data such as events, links, attributes etc.

    This class does not enforce any limits itself. It only provides a way to read limits from env,
    default values and from user provided arguments.

    All limit arguments must be either a non-negative integer, ``None`` or ``LogRecordLimits.UNSET``.

    - All limit arguments are optional.
    - If a limit argument is not set, the class will try to read its value from the corresponding
      environment variable.
    - If the environment variable is not set, the default value, if any, will be used.

    Limit precedence:

    - If a model specific limit is set, it will be used.
    - Else if the corresponding global limit is set, it will be used.
    - Else if the model specific limit has a default value, the default value will be used.
    - Else if the global limit has a default value, the default value will be used.

    Args:
        max_attributes: Maximum number of attributes that can be added to a log record (global fallback).
            Environment variable: ``OTEL_ATTRIBUTE_COUNT_LIMIT``
            Default: {_DEFAULT_OTEL_ATTRIBUTE_COUNT_LIMIT}
        max_attribute_length: Maximum length an attribute value can have (global fallback). Values
            longer than the specified length will be truncated.
        max_log_record_attributes: Maximum number of attributes that can be added to a log record.
            Environment variable: ``OTEL_LOGRECORD_ATTRIBUTE_COUNT_LIMIT``
            Falls back to ``max_attributes`` when unset.
        max_log_record_attribute_length: Maximum length a log record attribute value can have.
            Environment variable: ``OTEL_LOGRECORD_ATTRIBUTE_VALUE_LENGTH_LIMIT``
            Falls back to ``max_attribute_length`` when unset.

    Only the two log record specific values are ever applied to a record.
    ``ReadWriteLogRecord.__post_init__`` reads
    ``max_log_record_attributes`` and ``max_log_record_attribute_length``;
    ``max_attributes`` and ``max_attribute_length`` exist to supply their
    fallbacks and are not consulted again afterwards. The four resolved values
    are plain instance attributes, and changing one after construction has no
    effect on a record already built.

    Reaching the count limit drops attributes: once a record holds
    ``max_log_record_attributes`` keys, a further new key is discarded, while
    assigning to a key the record already has still works. Reaching the length
    limit truncates instead: a string value longer than
    ``max_log_record_attribute_length`` is cut to that many characters and the
    attribute is kept. Only the drops are counted, by
    ``ReadWriteLogRecord.dropped_attributes``. A truncation is reported through
    the logger of ``opentelemetry.attributes`` and leaves no mark on the record
    itself, so a consumer cannot tell a truncated value from a short one.

    A limit of ``None`` means unlimited. A count limit of zero drops every
    attribute, and a length limit of zero truncates every string value to the
    empty string.

    Raises:
        ValueError: If a limit is negative, or if an environment variable that
            had to be consulted does not parse as an integer.
    """

    UNSET = -1

    def __init__(
        self,
        max_attributes: int | None = None,
        max_attribute_length: int | None = None,
        max_log_record_attributes: int | None = None,
        max_log_record_attribute_length: int | None = None,
    ):
        # global attribute count
        global_max_attributes = self._from_env_if_absent(max_attributes, OTEL_ATTRIBUTE_COUNT_LIMIT)
        self.max_attributes = (
            global_max_attributes if global_max_attributes is not None else _DEFAULT_OTEL_ATTRIBUTE_COUNT_LIMIT
        )

        # global attribute length
        self.max_attribute_length = self._from_env_if_absent(
            max_attribute_length,
            OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT,
        )

        self.max_log_record_attributes = self._from_env_if_absent(
            max_log_record_attributes,
            OTEL_LOGRECORD_ATTRIBUTE_COUNT_LIMIT,
            default=self.max_attributes,
        )

        self.max_log_record_attribute_length = self._from_env_if_absent(
            max_log_record_attribute_length,
            OTEL_LOGRECORD_ATTRIBUTE_VALUE_LENGTH_LIMIT,
            default=self.max_attribute_length,
        )

    def __repr__(self):
        return (
            f"{type(self).__name__}("
            f"max_attributes={self.max_attributes}, "
            f"max_attribute_length={self.max_attribute_length}, "
            f"max_log_record_attributes={self.max_log_record_attributes}, "
            f"max_log_record_attribute_length={self.max_log_record_attribute_length})"
        )

    @classmethod
    def _from_env_if_absent(cls, value: int | None, env_var: str, default: int | None = None) -> int | None:
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


@deprecated("Use LogRecordLimits. Since logs are not stable yet this WILL be removed in future releases.")
class LogLimits(LogRecordLimits):
    """Deprecated alias of ``LogRecordLimits``."""


@dataclass(frozen=True, slots=True)
class ReadableLogRecord:
    """Readable LogRecord should be kept exactly in-sync with ReadWriteLogRecord, only difference is the frozen=True param.

    Args:
        log_record: The API record carrying the timestamps, the severity, the
            body, the attributes and the trace correlation.
        resource: The resource of the ``LoggerProvider`` the record came from.
        instrumentation_scope: The scope of the ``Logger`` that emitted the
            record, or ``None`` when none was supplied.
        limits: The limits that were applied when the record was built, kept so
            that a consumer can tell what shaped the attributes. ``None`` means
            no limits travelled with the record, which does not mean none were
            applied.
    """

    log_record: LogRecord
    resource: Resource
    instrumentation_scope: InstrumentationScope | None = None
    limits: LogRecordLimits | None = None

    @property
    def dropped_attributes(self) -> int:
        """Count the attributes the limits refused to keep.

        Returns:
            How many attributes were discarded while the record was being
            built: keys refused because the record already held
            ``max_log_record_attributes`` of them, and keys refused for being
            empty or not a string. A value truncated for exceeding
            ``max_log_record_attribute_length`` is not counted, because the
            attribute itself was kept. Zero when the attribute mapping is not a
            ``BoundedAttributes``, which is the case for a record built by hand
            rather than by ``ReadWriteLogRecord``, and which means the count is
            unknown rather than known to be zero.
        """
        if isinstance(self.log_record.attributes, BoundedAttributes):
            return self.log_record.attributes.dropped
        return 0

    def to_json(self, indent: int | None = 4) -> str:
        """Serialise the record to the JSON form the console exporter writes.

        Args:
            indent: Spaces per nesting level. ``None`` produces the compact
                form, which puts the whole record on one line and is what a
                line-oriented consumer wants.

        Returns:
            The JSON text, with no trailing newline. The console exporter adds
            the line separator itself.
        """
        return json.dumps(
            {
                "body": self.log_record.body,
                "severity_number": self.log_record.severity_number.value
                if self.log_record.severity_number is not None
                else None,
                "severity_text": self.log_record.severity_text,
                "attributes": (dict(self.log_record.attributes) if bool(self.log_record.attributes) else None),
                "dropped_attributes": self.dropped_attributes,
                "timestamp": ns_to_iso_str(self.log_record.timestamp)
                if self.log_record.timestamp is not None
                else None,
                "observed_timestamp": ns_to_iso_str(self.log_record.observed_timestamp),
                "trace_id": (
                    f"0x{format_trace_id(self.log_record.trace_id)}" if self.log_record.trace_id is not None else ""
                ),
                "span_id": (
                    f"0x{format_span_id(self.log_record.span_id)}" if self.log_record.span_id is not None else ""
                ),
                "trace_flags": self.log_record.trace_flags,
                "resource": json.loads(self.resource.to_json()),
                "event_name": self.log_record.event_name if self.log_record.event_name else "",
            },
            indent=indent,
            cls=BytesEncoder,
        )


@dataclass(slots=True)
class ReadWriteLogRecord:
    """A ReadWriteLogRecord instance represents an event being logged.
    ReadWriteLogRecord instances are created and emitted via `Logger`
    every time something is logged. They contain all the information
    pertinent to the event being logged.

    Args:
        log_record: The API record carrying the timestamps, the severity, the
            body, the attributes and the trace correlation. It is stored by
            reference and its ``attributes`` is replaced during construction,
            so the caller's record is changed too.
        resource: The resource to attach. The default is
            ``Resource.create({})``, evaluated once at class definition time
            and shared by every instance that does not pass one. It is not an
            empty resource: the default detectors run, so it carries the
            ``telemetry.sdk.*``, ``service.name`` and ``service.instance.id``
            attributes.
        instrumentation_scope: The scope of the ``Logger`` that emitted the
            record, or ``None`` when none was supplied.
        limits: The limits to apply to the attributes. The default is a fresh
            ``LogRecordLimits``, built per instance, which reads the
            environment at that moment.
    """

    log_record: LogRecord
    resource: Resource | None = Resource.create({})
    instrumentation_scope: InstrumentationScope | None = None
    limits: LogRecordLimits = field(default_factory=LogRecordLimits)

    def __post_init__(self):
        self.log_record.attributes = BoundedAttributes(
            maxlen=self.limits.max_log_record_attributes,
            attributes=self.log_record.attributes if self.log_record.attributes else None,
            immutable=False,
            max_value_len=self.limits.max_log_record_attribute_length,
            extended_attributes=True,
        )
        if self.dropped_attributes > 0:
            warnings.warn(
                "Log record attributes were dropped due to limits",
                LogRecordDroppedAttributesWarning,
                stacklevel=2,
            )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ReadWriteLogRecord):
            return NotImplemented
        return (
            self.log_record == other.log_record
            and self.resource == other.resource
            and self.instrumentation_scope == other.instrumentation_scope
            and self.limits == other.limits
        )

    @property
    def dropped_attributes(self) -> int:
        """Count the attributes the limits refused to keep.

        Returns:
            How many attributes were discarded, counting keys refused because
            the record already held ``limits.max_log_record_attributes`` of
            them and keys refused for being empty or not a string. A value
            truncated for exceeding
            ``limits.max_log_record_attribute_length`` is not counted,
            because the attribute itself was kept. Zero when the
            attribute mapping is not a ``BoundedAttributes``, which happens
            only if something replaced the mapping after construction.
        """
        if isinstance(self.log_record.attributes, BoundedAttributes):
            return self.log_record.attributes.dropped
        return 0

    @classmethod
    def _from_api_log_record(
        cls,
        *,
        record: LogRecord,
        resource: Resource,
        instrumentation_scope: InstrumentationScope | None = None,
        limits: LogRecordLimits | None = None,
    ) -> ReadWriteLogRecord:
        return cls(
            log_record=record,
            resource=resource,
            instrumentation_scope=instrumentation_scope,
            **({} if limits is None else {"limits": limits}),
        )


class LogRecordProcessor(abc.ABC):
    """Interface to hook the log record emitting action.

    Log processors can be registered directly using
    :func:`LoggerProvider.add_log_record_processor` and they are invoked
    in the same order as they were registered.

    Implementers of custom log processors should be aware of the following:

    Error Handling
    --------------
    According to the OpenTelemetry error handling principles, the SDK should
    not throw unhandled exceptions at runtime. When implementing a custom
    ``LogRecordProcessor``, it is the **processor's responsibility** to handle
    any exceptions that may be raised by the exporter's ``export()`` method.

    The ``LogRecordExporter.export()`` method may raise exceptions (e.g.,
    network errors, timeouts). If these exceptions are not caught, they will
    propagate up and potentially crash the application.

    Custom processor implementations should wrap exporter calls in a
    try/except block. See ``SimpleLogRecordProcessor`` for a reference
    implementation::

        def on_emit(self, log_record: ReadWriteLogRecord):
            try:
                self._exporter.export((log_record,))
            except Exception:  # pylint: disable=broad-exception-caught
                logger.exception("Exception while exporting logs.")

    The ``BatchLogRecordProcessor`` handles this implicitly since export
    operations occur in a background thread where exceptions cannot bubble
    up to the caller.
    """

    @abc.abstractmethod
    def on_emit(self, log_record: ReadWriteLogRecord) -> None:
        """Emits the ``ReadWriteLogRecord``.

        Implementers should handle any exceptions raised during log processing
        to prevent application crashes. See the class docstring for details
        on error handling expectations.

        Args:
            log_record: The record to process. Its attributes already have the
                limits applied, and its ``resource`` may be ``None`` for a
                record not built by ``Logger.emit``.
        """

    def enabled(  # pylint: disable=no-self-use,unused-argument
        self,
        *,
        context: Context | None = None,
        instrumentation_scope: InstrumentationScope | None = None,
        severity_number: SeverityNumber | None = None,
        event_name: str | None = None,
    ) -> bool:
        """Returns whether this processor would emit a record for the given arguments.

        Processors that support filtering MAY override this method. The default
        implementation returns ``True``.

        Args:
            context: The context the record would carry, or ``None`` when the
                caller has none and the current context would be used.
            instrumentation_scope: The scope of the emitting ``Logger``, or
                ``None`` when it has none.
            severity_number: The severity the record would carry, or ``None``
                when it is unset. Filtering by level is the usual reason to
                override this method.
            event_name: The event name the record would carry, or ``None`` for
                an unnamed record.

        Returns:
            ``True`` when the record is worth building. The base implementation
            ignores all four arguments and always answers ``True``.
        """
        return True

    @abc.abstractmethod
    def shutdown(self) -> None:
        """Called when a :class:`opentelemetry.sdk._logs.Logger` is shutdown"""

    @abc.abstractmethod
    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Export all the received logs to the configured Exporter that have not yet
        been exported.

        Args:
            timeout_millis: The maximum amount of time to wait for logs to be
                exported.

        Returns:
            False if the timeout is exceeded, True otherwise.
        """


# Temporary fix until https://github.com/PyCQA/pylint/issues/4098 is resolved
# pylint:disable=no-member
class SynchronousMultiLogRecordProcessor(LogRecordProcessor):
    """Implementation of class:`LogRecordProcessor` that forwards all received
    events to a list of log processors sequentially.

    The underlying log processors are called in sequential order as they were
    added.
    """

    def __init__(self) -> None:
        # use a tuple to avoid race conditions when adding a new log and
        # iterating through it on "emit".
        self._log_record_processors = ()  # type: tuple[LogRecordProcessor, ...]
        self._lock = threading.Lock()

    def add_log_record_processor(self, log_record_processor: LogRecordProcessor) -> None:
        """Adds a Logprocessor to the list of log processors handled by this instance

        Args:
            log_record_processor: The processor to add. It takes its place at
                the end, and processors run in the order they were added.
        """
        with self._lock:
            self._log_record_processors += (log_record_processor,)

    def on_emit(self, log_record: ReadWriteLogRecord) -> None:
        """Hand the record to each processor in turn, on the calling thread.

        Args:
            log_record: The record to forward.
        """
        for lp in self._log_record_processors:
            lp.on_emit(log_record)

    def enabled(
        self,
        *,
        context: Context | None = None,
        instrumentation_scope: InstrumentationScope | None = None,
        severity_number: SeverityNumber | None = None,
        event_name: str | None = None,
    ) -> bool:
        """Ask each processor in turn whether it wants such a record.

        Args:
            context: The context the record would carry, or ``None``.
            instrumentation_scope: The scope of the emitting ``Logger``, or
                ``None``.
            severity_number: The severity the record would carry, or ``None``.
            event_name: The event name the record would carry, or ``None``.

        Returns:
            ``True`` as soon as one processor answers ``True``, which leaves
            the rest unasked. ``False`` when every processor declines, and also
            ``False`` when no processor has been registered, so a provider with
            an empty processor list discards everything emitted through it.
        """
        for lp in self._log_record_processors:
            if lp.enabled(
                context=context,
                instrumentation_scope=instrumentation_scope,
                severity_number=severity_number,
                event_name=event_name,
            ):
                return True
        return False

    def shutdown(self) -> None:
        """Shutdown the log processors one by one"""
        for lp in self._log_record_processors:
            lp.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush the log processors one by one

        Args:
            timeout_millis: The maximum amount of time to wait for logs to be
                exported. If the first n log processors exceeded the timeout
                then remaining log processors will not be flushed.

        Returns:
            True if all the log processors flushes the logs within timeout,
            False otherwise.
        """
        deadline_ns = time_ns() + timeout_millis * 1000000
        all_flushed = True
        for lp in self._log_record_processors:
            current_ts = time_ns()
            if current_ts >= deadline_ns:
                return False

            if lp.force_flush((deadline_ns - current_ts) // 1000000) is False:
                all_flushed = False

        return all_flushed


class ConcurrentMultiLogRecordProcessor(LogRecordProcessor):
    """Implementation of :class:`LogRecordProcessor` that forwards all received
    events to a list of log processors in parallel.

    Calls to the underlying log processors are forwarded in parallel by
    submitting them to a thread pool executor and waiting until each log
    processor finished its work.

    Args:
        max_workers: The number of threads managed by the thread pool executor
            and thus defining how many log processors can work in parallel.
    """

    def __init__(self, max_workers: int = 2) -> None:
        # use a tuple to avoid race conditions when adding a new log and
        # iterating through it on "emit".
        self._log_record_processors = ()  # type: tuple[LogRecordProcessor, ...]
        self._lock = threading.Lock()
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

    def add_log_record_processor(self, log_record_processor: LogRecordProcessor) -> None:
        """Add a processor to the set this instance drives.

        Args:
            log_record_processor: The processor to add.
        """
        with self._lock:
            self._log_record_processors += (log_record_processor,)

    def _submit_and_wait(
        self,
        func: Callable[[LogRecordProcessor], Callable[..., None]],
        *args: Any,
        **kwargs: Any,
    ):
        futures = []
        for lp in self._log_record_processors:
            future = self._executor.submit(func(lp), *args, **kwargs)
            futures.append(future)
        for future in futures:
            future.result()

    def on_emit(self, log_record: ReadWriteLogRecord) -> None:
        """Hand the record to every processor at once and wait for all of them.

        Args:
            log_record: The record to forward.
        """
        self._submit_and_wait(lambda lp: lp.on_emit, log_record)

    def enabled(
        self,
        *,
        context: Context | None = None,
        instrumentation_scope: InstrumentationScope | None = None,
        severity_number: SeverityNumber | None = None,
        event_name: str | None = None,
    ) -> bool:
        """Ask each processor in turn whether it wants such a record.

        Args:
            context: The context the record would carry, or ``None``.
            instrumentation_scope: The scope of the emitting ``Logger``, or
                ``None``.
            severity_number: The severity the record would carry, or ``None``.
            event_name: The event name the record would carry, or ``None``.

        Returns:
            ``True`` as soon as one processor answers ``True``, which leaves
            the rest unasked. ``False`` when every processor declines, and also
            ``False`` when no processor has been registered, so a provider with
            an empty processor list discards everything emitted through it.
        """
        for lp in self._log_record_processors:
            if lp.enabled(
                context=context,
                instrumentation_scope=instrumentation_scope,
                severity_number=severity_number,
                event_name=event_name,
            ):
                return True
        return False

    def shutdown(self) -> None:
        """Shut every processor down at once and wait for all of them."""
        self._submit_and_wait(lambda lp: lp.shutdown)

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush the log processors in parallel.

        Args:
            timeout_millis: The maximum amount of time to wait for logs to be
                exported.

        Returns:
            True if all the log processors flushes the logs within timeout,
            False otherwise.
        """
        futures = []
        for lp in self._log_record_processors:
            future = self._executor.submit(lp.force_flush, timeout_millis)
            futures.append(future)

        done_futures, not_done_futures = concurrent.futures.wait(futures, timeout_millis / 1e3)

        if not_done_futures:
            return False

        for future in done_futures:
            if future.result() is False:
                return False

        return True


# skip natural LogRecord attributes
# http://docs.python.org/library/logging.html#logrecord-attributes
_RESERVED_ATTRS = frozenset(
    (
        "asctime",
        "args",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "getMessage",
        "message",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    )
)


class LoggingHandler(logging.Handler):
    """A handler class which writes logging records, in OTLP format, to
    a network destination or file. Supports signals from the `logging` module.
    https://docs.python.org/3/library/logging.html

    Args:
        level: The lowest level this handler accepts, as a ``logging`` level
            number. ``logging.NOTSET``, the default, accepts whatever the
            logger it is attached to passed on.
        logger_provider: The provider to obtain a ``Logger`` from, one per
            ``record.name``. ``None`` reads the globally configured provider
            once, at construction, so configuring the global provider
            afterwards does not reach a handler already built.
    """

    def __init__(
        self,
        level: int = logging.NOTSET,
        logger_provider: APILoggerProvider | None = None,
    ) -> None:
        super().__init__(level=level)
        self._logger_provider = logger_provider or get_logger_provider()

        warnings.warn(
            "`LoggingHandler` in `opentelemetry-sdk` is deprecated. Use the "
            "handler from `opentelemetry-instrumentation-logging` instead.",
            DeprecationWarning,
        )

    @staticmethod
    def _get_attributes(record: logging.LogRecord) -> Attributes:
        attributes = {k: v for k, v in vars(record).items() if k not in _RESERVED_ATTRS}

        # Add standard code attributes for logs.
        attributes[code_attributes.CODE_FILE_PATH] = record.pathname
        attributes[code_attributes.CODE_FUNCTION_NAME] = record.funcName
        attributes[code_attributes.CODE_LINE_NUMBER] = record.lineno

        if record.exc_info:
            exctype, value, tb = record.exc_info
            if exctype is not None:
                attributes[exception_attributes.EXCEPTION_TYPE] = exctype.__name__
            if value is not None and value.args:
                attributes[exception_attributes.EXCEPTION_MESSAGE] = str(value.args[0])
            if tb is not None:
                # https://opentelemetry.io/docs/specs/semconv/exceptions/exceptions-spans/#stacktrace-representation
                attributes[exception_attributes.EXCEPTION_STACKTRACE] = "".join(
                    traceback.format_exception(*record.exc_info)
                )
        return attributes

    def _translate(self, record: logging.LogRecord) -> LogRecord:
        timestamp = int(record.created * 1e9)
        observered_timestamp = time_ns()
        attributes = self._get_attributes(record)
        severity_number = std_to_otel(record.levelno)
        if self.formatter:
            body = self.format(record)
        else:
            # `record.getMessage()` uses `record.msg` as a template to format
            # `record.args` into. There is a special case in `record.getMessage()`
            # where it will only attempt formatting if args are provided,
            # otherwise, it just stringifies `record.msg`.
            #
            # Since the OTLP body field has a type of 'any' and the logging module
            # is sometimes used in such a way that objects incorrectly end up
            # set as record.msg, in those cases we would like to bypass
            # `record.getMessage()` completely and set the body to the object
            # itself instead of its string representation.
            # For more background, see: https://github.com/open-telemetry/opentelemetry-python/pull/4216
            if not record.args and not isinstance(record.msg, str):
                #  if record.msg is not a value we can export, cast it to string
                # TODO: https://github.com/open-telemetry/opentelemetry-python/issues/5304 - do something better
                # than just casting to a string.
                if not isinstance(
                    record.msg,
                    (
                        NoneType,
                        bool,
                        bytes,
                        int,
                        float,
                        str,
                        Sequence,
                        Mapping,
                    ),
                ):
                    body = str(record.msg)
                else:
                    body = record.msg
            else:
                body = record.getMessage()

        # Map Python log level names to OTel severity text as defined in
        # https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/logs/data-model.md#displaying-severity
        # Python "WARNING" -> OTel "WARN" (see #3548)
        # Python "CRITICAL" -> OTel "FATAL" (see #4984)
        _python_to_otel_severity_text = {
            "WARNING": "WARN",
            "CRITICAL": "FATAL",
        }
        level_name = _python_to_otel_severity_text.get(record.levelname, record.levelname)

        return LogRecord(
            timestamp=timestamp,
            observed_timestamp=observered_timestamp,
            context=get_current() or None,
            severity_text=level_name,
            severity_number=severity_number,
            body=body,
            attributes=attributes,
        )

    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a record. Skip emitting if logger is NoOp.

        The record is translated to OTel format, and then sent across the pipeline.

        Args:
            record: The ``logging.LogRecord`` to emit. It is not modified.
        """
        logger = get_logger(record.name, logger_provider=self._logger_provider)
        if not isinstance(logger, NoOpLogger):
            logger.emit(self._translate(record))

    def flush(self) -> None:
        """
        Flushes the logging output. Skip flushing if logging_provider has no force_flush method.
        """
        if hasattr(self._logger_provider, "force_flush") and callable(
            self._logger_provider.force_flush  # type: ignore[reportAttributeAccessIssue]
        ):
            # This is done in a separate thread to avoid a potential deadlock, for
            # details see https://github.com/open-telemetry/opentelemetry-python/pull/4636.
            thread = threading.Thread(target=self._logger_provider.force_flush)  # type: ignore[reportAttributeAccessIssue]
            thread.start()


@dataclass
class _LoggerConfig:
    is_enabled: bool = True

    @classmethod
    def default(cls) -> _LoggerConfig:
        return _LoggerConfig()


class Logger(APILogger):
    """SDK implementation of the logs API ``Logger``.

    Args:
        resource: The resource attached to every record this logger emits. It
            is replaced in place when the provider's resource changes, for
            instance after a fork.
        multi_log_record_processor: The provider's multiplexer, shared with
            every other logger of the same provider. Emitting goes through it,
            never to a processor directly.
        instrumentation_scope: The scope identifying the library that logs
            through this logger. It is what a configurator matches on.
        logger_metrics: Where the count of created records is reported.
        log_record_limits: The limits applied to the attributes of every record
            this logger builds. ``None`` builds a fresh ``LogRecordLimits``,
            which reads the environment at that moment.
        _logger_config: The enabled switch for this scope, produced by the
            provider's configurator. Replaced by the provider when the
            configurator is changed.
    """

    def __init__(
        self,
        resource: Resource,
        multi_log_record_processor: SynchronousMultiLogRecordProcessor | ConcurrentMultiLogRecordProcessor,
        instrumentation_scope: InstrumentationScope,
        *,
        logger_metrics: LoggerMetricsT,
        log_record_limits: LogRecordLimits | None = None,
        _logger_config: _LoggerConfig,
    ):
        super().__init__(
            instrumentation_scope.name,
            instrumentation_scope.version,
            instrumentation_scope.schema_url,
            instrumentation_scope.attributes,
        )
        self._resource = resource
        self._multi_log_record_processor = multi_log_record_processor
        self._instrumentation_scope = instrumentation_scope
        self._logger_metrics = logger_metrics
        self._logger_config = _logger_config
        self._log_record_limits = log_record_limits or LogRecordLimits()

    def enabled(
        self,
        *,
        context: Context | None = None,
        severity_number: SeverityNumber | None = None,
        event_name: str | None = None,
    ) -> bool:
        """Report whether such a record would reach any processor.

        Args:
            context: The context the record would carry, or ``None`` when the
                current context would be used.
            severity_number: The severity the record would carry, or ``None``.
            event_name: The event name the record would carry, or ``None``.

        Returns:
            ``False`` when a configurator disabled this logger's scope, or when
            every registered processor declines, which includes the case of no
            processor being registered at all. ``True`` otherwise.

            The instrumentation scope passed to the processors is this logger's
            own, which differs from what ``emit`` asks when it is handed a
            ``ReadWriteLogRecord`` that carries a scope of its own.
        """
        if not self._logger_config.is_enabled:
            return False
        return self._multi_log_record_processor.enabled(
            context=context,
            instrumentation_scope=self._instrumentation_scope,
            severity_number=severity_number,
            event_name=event_name,
        )

    def _set_logger_config(self, logger_config: _LoggerConfig) -> None:
        self._logger_config = logger_config

    def _set_resource(self, resource: Resource) -> None:
        self._resource = resource

    @property
    def instrumentation_scope(self):
        """The scope this logger was created for.

        Returns:
            The ``InstrumentationScope`` the provider built from the name,
            version, schema URL and attributes passed to ``get_logger``. It is
            fixed for the life of the logger, and it is what a configurator
            matches on.
        """
        return self._instrumentation_scope

    @property
    def resource(self):
        """The resource attached to records this logger emits.

        Returns:
            The provider's resource as of now. Reading it again after a fork
            returns a different object, because the provider merges the child
            process's identity in and pushes the result here.
        """
        return self._resource

    # pylint: disable=arguments-differ
    def emit(
        self,
        record: LogRecord | None = None,
        *,
        timestamp: int | None = None,
        observed_timestamp: int | None = None,
        context: Context | None = None,
        severity_number: SeverityNumber | None = None,
        severity_text: str | None = None,
        body: AnyValue | None = None,
        attributes: Attributes = None,
        event_name: str | None = None,
        exception: BaseException | None = None,
    ) -> None:
        """Emits the :class:`ReadWriteLogRecord` by setting instrumentation scope
        and forwarding to the processor.

        Args:
            record: A ready-made record, either an API ``LogRecord`` or a
                ``ReadWriteLogRecord``. ``None`` selects the keyword argument
                form.
            timestamp: When the event happened, in nanoseconds since the Unix
                epoch. ``None`` leaves it unset.
            observed_timestamp: When the SDK saw the event, in nanoseconds
                since the Unix epoch. ``None`` fills in the current time.
            context: The context supplying the trace correlation. ``None`` uses
                the current context.
            severity_number: The severity, or ``None`` to leave it unset.
            severity_text: The severity label of the originating logging
                system, or ``None``.
            body: The payload of the event. Any attribute value type is
                accepted, including a mapping or a sequence.
            attributes: Attributes to attach, before the limits are applied. A
                key given here survives even when it collides with one of the
                derived ``exception.*`` attributes.
            event_name: The name identifying the class of event, or ``None``
                for an unnamed record.
            exception: An exception to render into ``exception.type``,
                ``exception.message`` and ``exception.stacktrace``. ``None``
                adds none of them.
        """
        if not self._logger_config.is_enabled:
            return
        self._logger_metrics.emit_log()
        instrumentation_scope = self._instrumentation_scope
        if record is not None:
            if isinstance(record, ReadWriteLogRecord):
                instrumentation_scope = record.instrumentation_scope
                api_record = record.log_record
            else:
                api_record = record
            context = api_record.context
            severity_number = api_record.severity_number
            event_name = api_record.event_name
        else:
            context = context or get_current()
        # Skip building the record when no processor would accept it.
        if not self._multi_log_record_processor.enabled(
            context=context,
            instrumentation_scope=instrumentation_scope,
            severity_number=severity_number,
            event_name=event_name,
        ):
            return
        # If a record is provided, use it directly
        if record is not None:
            if not isinstance(record, ReadWriteLogRecord):
                if record.exception is not None:
                    record = _copy_log_record_with_exception(record)
                # pylint:disable=protected-access
                writable_record = ReadWriteLogRecord._from_api_log_record(
                    record=record,
                    resource=self._resource,
                    instrumentation_scope=self._instrumentation_scope,
                    limits=self._log_record_limits,
                )
            else:
                _set_log_record_exception_attributes(record.log_record)
                writable_record = record
        else:
            # Create a record from individual parameters
            log_record = _create_log_record_with_exception(
                timestamp=timestamp,
                observed_timestamp=observed_timestamp,
                context=context,
                severity_number=severity_number,
                severity_text=severity_text,
                body=body,
                attributes=attributes,
                event_name=event_name,
                exception=exception,
            )
            # pylint:disable=protected-access
            writable_record = ReadWriteLogRecord._from_api_log_record(
                record=log_record,
                resource=self._resource,
                instrumentation_scope=self._instrumentation_scope,
                limits=self._log_record_limits,
            )

        self._multi_log_record_processor.on_emit(writable_record)


_LoggerConfiguratorT = Callable[[InstrumentationScope], _LoggerConfig]
_RuleBasedLoggerConfigurator = RuleBasedConfigurator[_LoggerConfig]


def _default_logger_configurator(
    _logger_scope: InstrumentationScope,
) -> _LoggerConfig:
    return _LoggerConfig.default()


def _disable_logger_configurator(
    _logger_scope: InstrumentationScope,
) -> _LoggerConfig:
    return _LoggerConfig(is_enabled=False)


class LoggerProvider(APILoggerProvider):
    """SDK implementation of the logs API ``LoggerProvider``.

    Args:
        resource: The resource attached to every record. ``None`` builds an
            empty one, which still picks up the default resource detectors.
        shutdown_on_exit: Whether to register ``shutdown`` with ``atexit``, so
            that a program that ends without shutting down still flushes.
            ``False`` leaves flushing entirely to the caller.
        multi_log_record_processor: The multiplexer that holds the registered
            processors. ``None`` builds a ``SynchronousMultiLogRecordProcessor``,
            which runs them one after another. Pass a
            ``ConcurrentMultiLogRecordProcessor`` to run them in parallel.
        meter_provider: Provider for the SDK's own counters about logging.
            ``None`` uses the globally configured meter provider. Nothing is
            recorded at all unless
            ``OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED`` is set to true.
        log_record_limits: The attribute limits applied to every record.
            ``None`` builds a fresh ``LogRecordLimits``, which reads the
            environment at that moment.
        _logger_configurator: Decides, per instrumentation scope, whether its
            logger emits. ``None`` enables every scope. It is called once per
            logger created and again for every outstanding logger whenever a
            new configurator is installed, so it has to return quickly.
    """

    def __init__(
        self,
        resource: Resource | None = None,
        shutdown_on_exit: bool = True,
        multi_log_record_processor: SynchronousMultiLogRecordProcessor
        | ConcurrentMultiLogRecordProcessor
        | None = None,
        *,
        meter_provider: MeterProvider | None = None,
        log_record_limits: LogRecordLimits | None = None,
        _logger_configurator: _LoggerConfiguratorT | None = None,
    ):
        if resource is None:
            self._resource = Resource.create({})
        else:
            self._resource = resource
        self._multi_log_record_processor = multi_log_record_processor or SynchronousMultiLogRecordProcessor()
        self._logger_metrics = create_logger_metrics(
            meter_provider or get_meter_provider(),
            parse_boolean_environment_variable(OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED),
        )
        disabled = environ.get(OTEL_SDK_DISABLED, "")
        self._disabled = disabled.lower().strip() == "true"
        self._logger_configurator = _logger_configurator or _default_logger_configurator
        self._log_record_limits = log_record_limits or LogRecordLimits()
        self._at_exit_handler = None
        if shutdown_on_exit:
            self._at_exit_handler = atexit.register(self.shutdown)
        self._logger_cache = {}
        self._logger_cache_lock = Lock()
        self._active_loggers: WeakSet[Logger] = WeakSet()
        self._active_loggers_lock = Lock()
        if hasattr(os, "register_at_fork"):
            weak_at_fork = WeakMethod(self._handle_fork)

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
        self._logger_cache_lock = Lock()
        self._active_loggers_lock = Lock()
        self._update_resource(_get_process_dependent_resource())

    @property
    def resource(self):
        """The resource attached to every record from this provider.

        Returns:
            The current resource. It is replaced, not edited, when the process
            identity is merged in after a fork, so a reference taken earlier
            keeps the older contents.
        """
        return self._resource

    def _update_resource(self, resource: Resource) -> None:
        with self._active_loggers_lock:
            self._resource = self._resource.merge(resource)
            for logger in list(self._active_loggers):
                # pylint: disable-next=protected-access
                logger._set_resource(self._resource)

    def _get_logger_no_cache(
        self,
        name: str,
        version: str | None = None,
        schema_url: str | None = None,
        attributes: Attributes = None,
    ) -> Logger:
        scope = InstrumentationScope(name, version, schema_url, attributes)

        return Logger(
            self._resource,
            self._multi_log_record_processor,
            scope,
            logger_metrics=self._logger_metrics,
            _logger_config=self._apply_logger_configurator(scope),
            log_record_limits=self._log_record_limits,
        )

    def _get_logger_cached(
        self,
        name: str,
        version: str | None = None,
        schema_url: str | None = None,
    ) -> Logger:
        with self._logger_cache_lock:
            key = (name, version, schema_url)
            if key in self._logger_cache:
                return self._logger_cache[key]

            self._logger_cache[key] = self._get_logger_no_cache(name, version, schema_url)
            return self._logger_cache[key]

    def get_logger(
        self,
        name: str,
        version: str | None = None,
        schema_url: str | None = None,
        attributes: Attributes = None,
    ) -> APILogger:
        """Obtain a ``Logger`` for one instrumented library.

        Args:
            name: Name of the instrumented library. Convention is the module or
                package doing the logging.
            version: Version of the instrumented library, or ``None``.
            schema_url: URL of the schema the emitted records follow, or
                ``None``.
            attributes: Attributes describing the scope itself. Passing
                anything other than ``None``, including an empty mapping, skips
                the cache and returns a fresh logger on every call.

        Returns:
            A ``NoOpLogger`` when ``OTEL_SDK_DISABLED`` was true at the time
            this provider was built, in which case nothing emitted through it
            reaches a processor. Otherwise an SDK ``Logger``, the cached one
            when ``attributes`` is ``None`` and a new one when it is not.
            Either way the logger is tracked weakly, so later resource and
            configuration changes reach it.
        """
        if self._disabled:
            return NoOpLogger(
                name,
                version=version,
                schema_url=schema_url,
                attributes=attributes,
            )
        logger = (
            self._get_logger_cached(name, version, schema_url)
            if attributes is None
            else self._get_logger_no_cache(name, version, schema_url, attributes)
        )
        with self._active_loggers_lock:
            self._active_loggers.add(logger)
        return logger

    def add_log_record_processor(self, log_record_processor: LogRecordProcessor):
        """Registers a new :class:`LogRecordProcessor` for this `LoggerProvider` instance.

        The log processors are invoked in the same order they are registered.

        Args:
            log_record_processor: The processor to register. Registering the
                same one twice makes it receive each record twice.
        """
        self._multi_log_record_processor.add_log_record_processor(log_record_processor)

    def _set_logger_configurator(self, *, logger_configurator: _LoggerConfiguratorT):
        """Set a new LoggerConfigurator for this LoggerProvider.

        Setting a new LoggerConfigurator will result in the configurator being called
        for each outstanding Logger and for any newly created loggers thereafter.
        Therefore, it is important that the provided function returns quickly.
        """
        self._logger_configurator = logger_configurator
        with self._active_loggers_lock:
            for logger in list(self._active_loggers):
                # pylint: disable-next=protected-access
                logger._set_logger_config(self._apply_logger_configurator(logger.instrumentation_scope))

    def _apply_logger_configurator(self, instrumentation_scope: InstrumentationScope) -> _LoggerConfig:
        try:
            return self._logger_configurator(instrumentation_scope)
        # pylint: disable-next=broad-exception-caught
        except Exception:
            _logger.exception(
                "logger configurator failed for scope '%s', using default config",
                instrumentation_scope.name,
            )
            return _LoggerConfig.default()

    def shutdown(self) -> None:
        """Shuts down the log processors."""
        self._multi_log_record_processor.shutdown()
        if self._at_exit_handler is not None:
            atexit.unregister(self._at_exit_handler)
            self._at_exit_handler = None

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush the log processors.

        Args:
            timeout_millis: The maximum amount of time to wait for logs to be
                exported. The budget is shared: with a
                ``SynchronousMultiLogRecordProcessor`` each processor is given
                what the ones before it left, and once it is gone the remaining
                processors are not flushed at all. A
                ``ConcurrentMultiLogRecordProcessor`` gives the whole budget to
                every processor at once. Either way the value is a request,
                since ``BatchLogRecordProcessor`` ignores it and blocks until
                its queue is empty.

        Returns:
            True if all the log processors flushes the logs within timeout,
            False otherwise.

            ``False`` says a flush did not complete. It does not say which
            processor, nor whether the records it held were exported, dropped
            or are still queued. The three causes are a processor answering
            ``False``, a processor not finishing in time, and a processor that
            was already shut down, which is what a ``BatchLogRecordProcessor``
            reports after ``shutdown``. ``True`` only means every processor
            claimed to have handed its records to its exporter; an export that
            failed is logged and still counts as a successful flush.
        """
        return self._multi_log_record_processor.force_flush(timeout_millis)


_STD_TO_OTEL = {
    10: SeverityNumber.DEBUG,
    11: SeverityNumber.DEBUG2,
    12: SeverityNumber.DEBUG3,
    13: SeverityNumber.DEBUG4,
    14: SeverityNumber.DEBUG4,
    15: SeverityNumber.DEBUG4,
    16: SeverityNumber.DEBUG4,
    17: SeverityNumber.DEBUG4,
    18: SeverityNumber.DEBUG4,
    19: SeverityNumber.DEBUG4,
    20: SeverityNumber.INFO,
    21: SeverityNumber.INFO2,
    22: SeverityNumber.INFO3,
    23: SeverityNumber.INFO4,
    24: SeverityNumber.INFO4,
    25: SeverityNumber.INFO4,
    26: SeverityNumber.INFO4,
    27: SeverityNumber.INFO4,
    28: SeverityNumber.INFO4,
    29: SeverityNumber.INFO4,
    30: SeverityNumber.WARN,
    31: SeverityNumber.WARN2,
    32: SeverityNumber.WARN3,
    33: SeverityNumber.WARN4,
    34: SeverityNumber.WARN4,
    35: SeverityNumber.WARN4,
    36: SeverityNumber.WARN4,
    37: SeverityNumber.WARN4,
    38: SeverityNumber.WARN4,
    39: SeverityNumber.WARN4,
    40: SeverityNumber.ERROR,
    41: SeverityNumber.ERROR2,
    42: SeverityNumber.ERROR3,
    43: SeverityNumber.ERROR4,
    44: SeverityNumber.ERROR4,
    45: SeverityNumber.ERROR4,
    46: SeverityNumber.ERROR4,
    47: SeverityNumber.ERROR4,
    48: SeverityNumber.ERROR4,
    49: SeverityNumber.ERROR4,
    50: SeverityNumber.FATAL,
    51: SeverityNumber.FATAL2,
    52: SeverityNumber.FATAL3,
    53: SeverityNumber.FATAL4,
}


def std_to_otel(levelno: int) -> SeverityNumber:
    """
    Map python log levelno as defined in https://docs.python.org/3/library/logging.html#logging-levels
    to OTel log severity number as defined here: https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/logs/data-model.md#field-severitynumber
    """
    if levelno < 10:
        return SeverityNumber.UNSPECIFIED
    if levelno > 53:
        return SeverityNumber.FATAL4
    return _STD_TO_OTEL[levelno]
