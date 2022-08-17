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
import os
import threading
import traceback
from typing import Any, Callable, Optional, Tuple, Union, cast

from opentelemetry.sdk._logs.severity import SeverityNumber, std_to_otlp
from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_LOG_EMITTER_PROVIDER,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util import ns_to_iso_str
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.trace import (
    format_span_id,
    format_trace_id,
    get_current_span,
)
from opentelemetry.trace.span import TraceFlags
from opentelemetry.util._providers import _load_provider
from opentelemetry.util._time import _time_ns
from opentelemetry.util.types import Attributes

_logger = logging.getLogger(__name__)


class LogRecord:
    """A LogRecord instance represents an event being logged.

    LogRecord instances are created and emitted via `LogEmitter`
    every time something is logged. They contain all the information
    pertinent to the event being logged.
    """

    def __init__(
        self,
        timestamp: Optional[int] = None,
        trace_id: Optional[int] = None,
        span_id: Optional[int] = None,
        trace_flags: Optional[TraceFlags] = None,
        severity_text: Optional[str] = None,
        severity_number: Optional[SeverityNumber] = None,
        body: Optional[Any] = None,
        resource: Optional[Resource] = None,
        attributes: Optional[Attributes] = None,
    ):
        self.timestamp = timestamp
        self.trace_id = trace_id
        self.span_id = span_id
        self.trace_flags = trace_flags
        self.severity_text = severity_text
        self.severity_number = severity_number
        self.body = body
        self.resource = resource
        self.attributes = attributes

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LogRecord):
            return NotImplemented
        return self.__dict__ == other.__dict__

    def to_json(self) -> str:
        return json.dumps(
            {
                "body": self.body,
                "severity_number": repr(self.severity_number),
                "severity_text": self.severity_text,
                "attributes": self.attributes,
                "timestamp": ns_to_iso_str(self.timestamp),
                "trace_id": f"0x{format_trace_id(self.trace_id)}"
                if self.trace_id is not None
                else "",
                "span_id": f"0x{format_span_id(self.span_id)}"
                if self.span_id is not None
                else "",
                "trace_flags": self.trace_flags,
                "resource": repr(self.resource.attributes)
                if self.resource
                else "",
            },
            indent=4,
        )


class LogData:
    """Readable LogRecord data plus associated InstrumentationLibrary."""

    def __init__(
        self,
        log_record: LogRecord,
        instrumentation_scope: InstrumentationScope,
    ):
        self.log_record = log_record
        self.instrumentation_scope = instrumentation_scope


class LogProcessor(abc.ABC):
    """Interface to hook the log record emitting action.

    Log processors can be registered directly using
    :func:`LogEmitterProvider.add_log_processor` and they are invoked
    in the same order as they were registered.
    """

    @abc.abstractmethod
    def emit(self, log_data: LogData):
        """Emits the `LogData`"""

    @abc.abstractmethod
    def shutdown(self):
        """Called when a :class:`opentelemetry.sdk._logs.LogEmitter` is shutdown"""

    @abc.abstractmethod
    def force_flush(self, timeout_millis: int = 30000):
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
class SynchronousMultiLogProcessor(LogProcessor):
    """Implementation of class:`LogProcessor` that forwards all received
    events to a list of log processors sequentially.

    The underlying log processors are called in sequential order as they were
    added.
    """

    def __init__(self):
        # use a tuple to avoid race conditions when adding a new log and
        # iterating through it on "emit".
        self._log_processors = ()  # type: Tuple[LogProcessor, ...]
        self._lock = threading.Lock()

    def add_log_processor(self, log_processor: LogProcessor) -> None:
        """Adds a Logprocessor to the list of log processors handled by this instance"""
        with self._lock:
            self._log_processors += (log_processor,)

    def emit(self, log_data: LogData) -> None:
        for lp in self._log_processors:
            lp.emit(log_data)

    def shutdown(self) -> None:
        """Shutdown the log processors one by one"""
        for lp in self._log_processors:
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
        deadline_ns = _time_ns() + timeout_millis * 1000000
        for lp in self._log_processors:
            current_ts = _time_ns()
            if current_ts >= deadline_ns:
                return False

            if not lp.force_flush((deadline_ns - current_ts) // 1000000):
                return False

        return True


class ConcurrentMultiLogProcessor(LogProcessor):
    """Implementation of :class:`LogProcessor` that forwards all received
    events to a list of log processors in parallel.

    Calls to the underlying log processors are forwarded in parallel by
    submitting them to a thread pool executor and waiting until each log
    processor finished its work.

    Args:
        max_workers: The number of threads managed by the thread pool executor
            and thus defining how many log processors can work in parallel.
    """

    def __init__(self, max_workers: int = 2):
        # use a tuple to avoid race conditions when adding a new log and
        # iterating through it on "emit".
        self._log_processors = ()  # type: Tuple[LogProcessor, ...]
        self._lock = threading.Lock()
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers
        )

    def add_log_processor(self, log_processor: LogProcessor):
        with self._lock:
            self._log_processors += (log_processor,)

    def _submit_and_wait(
        self,
        func: Callable[[LogProcessor], Callable[..., None]],
        *args: Any,
        **kwargs: Any,
    ):
        futures = []
        for lp in self._log_processors:
            future = self._executor.submit(func(lp), *args, **kwargs)
            futures.append(future)
        for future in futures:
            future.result()

    def emit(self, log_data: LogData):
        self._submit_and_wait(lambda lp: lp.emit, log_data)

    def shutdown(self):
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
        for lp in self._log_processors:
            future = self._executor.submit(lp.force_flush, timeout_millis)
            futures.append(future)

        done_futures, not_done_futures = concurrent.futures.wait(
            futures, timeout_millis / 1e3
        )

        if not_done_futures:
            return False

        for future in done_futures:
            if not future.result():
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
    )
)


class LoggingHandler(logging.Handler):
    """A handler class which writes logging records, in OTLP format, to
    a network destination or file. Supports signals from the `logging` module.
    https://docs.python.org/3/library/logging.html
    """

    def __init__(
        self,
        level=logging.NOTSET,
        log_emitter=None,
    ) -> None:
        super().__init__(level=level)
        self._log_emitter = log_emitter or get_log_emitter(__name__)

    @staticmethod
    def _get_attributes(record: logging.LogRecord) -> Attributes:
        attributes = {
            k: v for k, v in vars(record).items() if k not in _RESERVED_ATTRS
        }
        if record.exc_info:
            exc_type = ""
            message = ""
            stack_trace = ""
            exctype, value, tb = record.exc_info
            if exctype is not None:
                exc_type = exctype.__name__
            if value is not None and value.args:
                message = value.args[0]
            if tb is not None:
                # https://github.com/open-telemetry/opentelemetry-specification/blob/9fa7c656b26647b27e485a6af7e38dc716eba98a/specification/trace/semantic_conventions/exceptions.md#stacktrace-representation
                stack_trace = "".join(
                    traceback.format_exception(*record.exc_info)
                )
            attributes[SpanAttributes.EXCEPTION_TYPE] = exc_type
            attributes[SpanAttributes.EXCEPTION_MESSAGE] = message
            attributes[SpanAttributes.EXCEPTION_STACKTRACE] = stack_trace
        return attributes

    def _translate(self, record: logging.LogRecord) -> LogRecord:
        timestamp = int(record.created * 1e9)
        span_context = get_current_span().get_span_context()
        attributes = self._get_attributes(record)
        severity_number = std_to_otlp(record.levelno)
        return LogRecord(
            timestamp=timestamp,
            trace_id=span_context.trace_id,
            span_id=span_context.span_id,
            trace_flags=span_context.trace_flags,
            severity_text=record.levelname,
            severity_number=severity_number,
            body=record.getMessage(),
            resource=self._log_emitter.resource,
            attributes=attributes,
        )

    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a record.

        The record is translated to OTLP format, and then sent across the pipeline.
        """
        self._log_emitter.emit(self._translate(record))

    def flush(self) -> None:
        """
        Flushes the logging output.
        """
        self._log_emitter.flush()


class LogEmitter:
    def __init__(
        self,
        resource: Resource,
        multi_log_processor: Union[
            SynchronousMultiLogProcessor, ConcurrentMultiLogProcessor
        ],
        instrumentation_scope: InstrumentationScope,
    ):
        self._resource = resource
        self._multi_log_processor = multi_log_processor
        self._instrumentation_scope = instrumentation_scope

    @property
    def resource(self):
        return self._resource

    def emit(self, record: LogRecord):
        """Emits the :class:`LogData` by associating :class:`LogRecord`
        and instrumentation info.
        """
        log_data = LogData(record, self._instrumentation_scope)
        self._multi_log_processor.emit(log_data)

    # TODO: Should this flush everything in pipeline?
    # Prior discussion https://github.com/open-telemetry/opentelemetry-python/pull/1916#discussion_r659945290
    def flush(self):
        """Ensure all logging output has been flushed."""
        self._multi_log_processor.force_flush()


class LogEmitterProvider:
    def __init__(
        self,
        resource: Resource = Resource.create(),
        shutdown_on_exit: bool = True,
        multi_log_processor: Union[
            SynchronousMultiLogProcessor, ConcurrentMultiLogProcessor
        ] = None,
    ):
        self._resource = resource
        self._multi_log_processor = (
            multi_log_processor or SynchronousMultiLogProcessor()
        )
        self._at_exit_handler = None
        if shutdown_on_exit:
            self._at_exit_handler = atexit.register(self.shutdown)

    @property
    def resource(self):
        return self._resource

    def get_log_emitter(
        self,
        instrumenting_module_name: str,
        instrumenting_module_version: str = "",
    ) -> LogEmitter:
        return LogEmitter(
            self._resource,
            self._multi_log_processor,
            InstrumentationScope(
                instrumenting_module_name, instrumenting_module_version
            ),
        )

    def add_log_processor(self, log_processor: LogProcessor):
        """Registers a new :class:`LogProcessor` for this `LogEmitterProvider` instance.

        The log processors are invoked in the same order they are registered.
        """
        self._multi_log_processor.add_log_processor(log_processor)

    def shutdown(self):
        """Shuts down the log processors."""
        self._multi_log_processor.shutdown()
        if self._at_exit_handler is not None:
            atexit.unregister(self._at_exit_handler)
            self._at_exit_handler = None

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush the log processors.

        Args:
            timeout_millis: The maximum amount of time to wait for logs to be
                exported.

        Returns:
            True if all the log processors flushes the logs within timeout,
            False otherwise.
        """
        return self._multi_log_processor.force_flush(timeout_millis)


_LOG_EMITTER_PROVIDER = None


def get_log_emitter_provider() -> LogEmitterProvider:
    """Gets the current global :class:`~.LogEmitterProvider` object."""
    global _LOG_EMITTER_PROVIDER  # pylint: disable=global-statement
    if _LOG_EMITTER_PROVIDER is None:
        if _OTEL_PYTHON_LOG_EMITTER_PROVIDER not in os.environ:
            _LOG_EMITTER_PROVIDER = LogEmitterProvider()
            return _LOG_EMITTER_PROVIDER

        _LOG_EMITTER_PROVIDER = cast(
            "LogEmitterProvider",
            _load_provider(
                _OTEL_PYTHON_LOG_EMITTER_PROVIDER, "log_emitter_provider"
            ),
        )

    return _LOG_EMITTER_PROVIDER


def set_log_emitter_provider(log_emitter_provider: LogEmitterProvider) -> None:
    """Sets the current global :class:`~.LogEmitterProvider` object.

    This can only be done once, a warning will be logged if any furter attempt
    is made.
    """
    global _LOG_EMITTER_PROVIDER  # pylint: disable=global-statement

    if _LOG_EMITTER_PROVIDER is not None:
        _logger.warning(
            "Overriding of current LogEmitterProvider is not allowed"
        )
        return

    _LOG_EMITTER_PROVIDER = log_emitter_provider


def get_log_emitter(
    instrumenting_module_name: str,
    instrumenting_library_version: str = "",
    log_emitter_provider: Optional[LogEmitterProvider] = None,
) -> LogEmitter:
    """Returns a `LogEmitter` for use within a python process.

    This function is a convenience wrapper for
    opentelemetry.sdk._logs.LogEmitterProvider.get_log_emitter.

    If log_emitter_provider param is omitted the current configured one is used.
    """
    if log_emitter_provider is None:
        log_emitter_provider = get_log_emitter_provider()
    return log_emitter_provider.get_log_emitter(
        instrumenting_module_name, instrumenting_library_version
    )
