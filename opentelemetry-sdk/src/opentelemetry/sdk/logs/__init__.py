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
import logging
import os
from typing import Any, Optional, cast

from opentelemetry.sdk.environment_variables import (
    OTEL_PYTHON_LOG_EMITTER_PROVIDER,
)
from opentelemetry.sdk.logs.severity import SeverityNumber
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationInfo
from opentelemetry.sdk.util.severity import std_to_otlp
from opentelemetry.trace import get_current_span
from opentelemetry.trace.span import TraceFlags
from opentelemetry.util._providers import _load_provider
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
        name: Optional[str] = None,
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
        self.name = name
        self.body = body
        self.resource = resource
        self.attributes = attributes

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LogRecord):
            return NotImplemented
        return self.__dict__ == other.__dict__


class LogData:
    """Readable LogRecord data plus associated InstrumentationLibrary."""

    def __init__(
        self,
        log_record: LogRecord,
        instrumentation_info: InstrumentationInfo,
    ):
        self.log_record = log_record
        self.instrumentation_info = instrumentation_info


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
        """Called when a :class:`opentelemetry.sdk.logs.LogEmitter` is shutdown"""

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


class OTLPHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET, log_emitter=None) -> None:
        super().__init__(level=level)
        self._log_emitter = log_emitter or get_log_emitter("")

    def _translate(self, record: logging.LogRecord) -> LogRecord:
        timestamp = int(record.created * 1e9)
        span_context = get_current_span().get_span_context()
        attributes: Attributes = {}  # TODO: attributes from record metadata
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
        self._log_emitter.emit(self._translate(record))

    def flush(self) -> None:
        self._log_emitter.flush()


class LogEmitter:
    # TODO: Add multi_log_processor
    def __init__(
        self,
        resource: Resource,
        instrumentation_info: InstrumentationInfo,
    ):
        self._resource = resource
        self._instrumentation_info = instrumentation_info

    @property
    def resource(self):
        return self._resource

    def emit(self, record: LogRecord):
        # TODO: multi_log_processor.emit
        pass

    def flush(self):
        # TODO: multi_log_processor.force_flush
        pass


class LogEmitterProvider:
    # TODO: Add multi_log_processor
    def __init__(
        self,
        resource: Resource = Resource.create(),
        shutdown_on_exit: bool = True,
    ):
        self._resource = resource
        self._at_exit_handler = None
        if shutdown_on_exit:
            self._at_exit_handler = atexit.register(self.shutdown)

    def get_log_emitter(
        self,
        instrumenting_module_name: str,
        instrumenting_module_verison: str = "",
    ) -> LogEmitter:
        return LogEmitter(
            self._resource,
            InstrumentationInfo(
                instrumenting_module_name, instrumenting_module_verison
            ),
        )

    def add_log_processor(self, log_processor: LogProcessor):
        """Registers a new :class:`LogProcessor` for this `LogEmitterProvider` instance.

        The log processors are invoked in the same order they are registered.
        """
        # TODO: multi_log_processor.add_log_processor.

    def shutdown(self):
        """Shuts down the log processors."""
        # TODO: multi_log_processor.shutdown
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
        # TODO: multi_log_processor.force_flush


_LOG_EMITTER_PROVIDER = None


def get_log_emitter_provider() -> LogEmitterProvider:
    """Gets the current global :class:`~.LogEmitterProvider` object."""
    global _LOG_EMITTER_PROVIDER  # pylint: disable=global-statement
    if _LOG_EMITTER_PROVIDER is None:
        if OTEL_PYTHON_LOG_EMITTER_PROVIDER not in os.environ:
            _LOG_EMITTER_PROVIDER = LogEmitterProvider()
            return _LOG_EMITTER_PROVIDER

        _LOG_EMITTER_PROVIDER = cast(
            "LogEmitterProvider",
            _load_provider(
                OTEL_PYTHON_LOG_EMITTER_PROVIDER, "log_emitter_provider"
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
    opentelemetry.sdk.logs.LogEmitterProvider.get_log_emitter.

    If log_emitter_provider param is omitted the current configured one is used.
    """
    if log_emitter_provider is None:
        log_emitter_provider = get_log_emitter_provider()
    return log_emitter_provider.get_log_emitter(
        instrumenting_module_name, instrumenting_library_version
    )
