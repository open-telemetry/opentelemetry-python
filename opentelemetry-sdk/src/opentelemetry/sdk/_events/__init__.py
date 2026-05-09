# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import logging
from time import time_ns

from typing_extensions import deprecated

from opentelemetry import trace
from opentelemetry._events import Event
from opentelemetry._events import EventLogger as APIEventLogger
from opentelemetry._events import EventLoggerProvider as APIEventLoggerProvider
from opentelemetry._logs import (
    LogRecord,
    NoOpLogger,
    SeverityNumber,
    get_logger_provider,
)
from opentelemetry.sdk._logs import Logger, LoggerProvider
from opentelemetry.util.types import _ExtendedAttributes

_logger = logging.getLogger(__name__)


@deprecated(
    "You should use `Logger` instead. "
    "Deprecated since version 1.39.0 and will be removed in a future release."
)
class EventLogger(APIEventLogger):
    def __init__(
        self,
        logger_provider: LoggerProvider,
        name: str,
        version: str | None = None,
        schema_url: str | None = None,
        attributes: _ExtendedAttributes | None = None,
    ):
        super().__init__(
            name=name,
            version=version,
            schema_url=schema_url,
            attributes=attributes,
        )
        self._logger: Logger = logger_provider.get_logger(
            name, version, schema_url, attributes
        )

    def emit(self, event: Event) -> None:
        if isinstance(self._logger, NoOpLogger):
            # Do nothing if SDK is disabled
            return

        # Build a context that carries the event's trace correlation.
        # If the Event was constructed with explicit trace_id/span_id,
        # wrap them in a NonRecordingSpan so LogRecord picks them up
        # from context instead of requiring the deprecated kwargs.
        context = event.context
        span_context = trace.get_current_span(context).get_span_context()
        if (
            event.trace_id != span_context.trace_id
            or event.span_id != span_context.span_id
            or event.trace_flags != span_context.trace_flags
        ):
            context = trace.set_span_in_context(
                trace.NonRecordingSpan(
                    trace.SpanContext(
                        trace_id=event.trace_id,
                        span_id=event.span_id,
                        is_remote=False,
                        trace_flags=event.trace_flags,
                    )
                ),
                context,
            )

        log_record = LogRecord(
            timestamp=event.timestamp or time_ns(),
            observed_timestamp=None,
            context=context,
            severity_text=None,
            severity_number=event.severity_number or SeverityNumber.INFO,
            body=event.body,
            attributes=event.attributes,
        )
        self._logger.emit(log_record)


@deprecated(
    "You should use `LoggerProvider` instead. "
    "Deprecated since version 1.39.0 and will be removed in a future release."
)
class EventLoggerProvider(APIEventLoggerProvider):
    def __init__(self, logger_provider: LoggerProvider | None = None):
        self._logger_provider = logger_provider or get_logger_provider()

    def get_event_logger(
        self,
        name: str,
        version: str | None = None,
        schema_url: str | None = None,
        attributes: _ExtendedAttributes | None = None,
    ) -> EventLogger:
        if not name:
            _logger.warning("EventLogger created with invalid name: %s", name)
        return EventLogger(
            self._logger_provider, name, version, schema_url, attributes
        )

    def shutdown(self):
        self._logger_provider.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        self._logger_provider.force_flush(timeout_millis)
