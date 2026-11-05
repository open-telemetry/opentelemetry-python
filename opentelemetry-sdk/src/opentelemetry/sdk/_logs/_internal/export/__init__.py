# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
"""Sending log records out of the SDK.

Holds the ``LogRecordExporter`` interface that an exporter implements, the
console exporter the SDK ships, and the two processors that stand between
``Logger`` and an exporter: ``SimpleLogRecordProcessor``, which exports each
record on the emitting thread, and ``BatchLogRecordProcessor``, which queues
records and exports them from a background thread.

The module-level logger used for reporting export failures carries a
``DuplicateFilter``, which suppresses a message identical to the one it just
let through until the clock reaches the next twenty-second boundary. An export
that keeps failing the same way is therefore reported every twenty seconds
rather than once per batch.
"""

from __future__ import annotations

import abc
import copy
import enum
import logging
import sys
from collections.abc import Callable, Sequence
from os import environ, linesep
from typing import IO

from typing_extensions import deprecated

from opentelemetry.context import (
    _ON_EMIT_RECURSION_COUNT_KEY,
    _SUPPRESS_INSTRUMENTATION_KEY,
    Context,
    attach,
    detach,
    get_value,
    set_value,
)
from opentelemetry.metrics import MeterProvider, get_meter_provider
from opentelemetry.sdk._logs import (
    LogRecordProcessor,
    ReadableLogRecord,
    ReadWriteLogRecord,
)
from opentelemetry.sdk._shared_internal import (
    BatchProcessor,
    DuplicateFilter,
)
from opentelemetry.sdk._shared_internal._processor_metrics import (
    create_processor_metrics,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_BLRP_EXPORT_TIMEOUT,
    OTEL_BLRP_MAX_EXPORT_BATCH_SIZE,
    OTEL_BLRP_MAX_QUEUE_SIZE,
    OTEL_BLRP_SCHEDULE_DELAY,
    OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED,
)
from opentelemetry.sdk.environment_variables._internal import (
    parse_boolean_environment_variable,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv._incubating.attributes.otel_attributes import (
    OtelComponentTypeValues,
)

_DEFAULT_SCHEDULE_DELAY_MILLIS = 1000
_DEFAULT_MAX_EXPORT_BATCH_SIZE = 512
_DEFAULT_EXPORT_TIMEOUT_MILLIS = 30000
_DEFAULT_MAX_QUEUE_SIZE = 2048
_ENV_VAR_INT_VALUE_ERROR_MESSAGE = "Unable to parse value for %s as integer. Defaulting to %s."
_logger = logging.getLogger(__name__)
_logger.addFilter(DuplicateFilter())

_propagate_false_logger = logging.getLogger(__name__ + ".propagate.false")
_propagate_false_logger.propagate = False


class LogRecordExportResult(enum.Enum):
    """Outcome an exporter reports for one batch.

    ``FAILURE`` covers everything that went wrong, with no distinction between
    a failure worth retrying and a permanent one. Neither processor in this
    module retries or reports the value further, so an exporter that wants a
    retry has to do it inside ``export``.
    """

    SUCCESS = 0
    FAILURE = 1


@deprecated("Use LogRecordExportResult. Since logs are not stable yet this WILL be removed in future releases.")
class LogExportResult(enum.Enum):
    """Deprecated alias of ``LogRecordExportResult``.

    It is a separate enum rather than a subclass, so its members do not compare
    equal to the members of ``LogRecordExportResult``. Code that checks an
    exporter's return value against this enum will not match a modern exporter.
    """

    SUCCESS = 0
    FAILURE = 1


class LogRecordExporter(abc.ABC):
    """Interface for exporting logs.

    Interface to be implemented by services that want to export logs received
    in their own format.

    To export data this MUST be registered to the :class:`opentelemetry.sdk._logs.Logger`
    using a log processor.

    Important
    ---------
    The ``export()`` method may raise exceptions (e.g., network errors,
    timeouts, serialization errors). It is the responsibility of the
    ``LogRecordProcessor`` calling this exporter to handle these exceptions
    appropriately to prevent application crashes. See ``LogRecordProcessor``
    for guidance on implementing proper error handling.
    """

    @abc.abstractmethod
    def export(self, batch: Sequence[ReadableLogRecord]) -> LogRecordExportResult:
        """Exports a batch of logs.

        Args:
            batch: The list of ``ReadableLogRecord`` objects to be exported.

        Returns:
            The result of the export.

        Raises:
            Exception: This method may raise exceptions on network errors,
                timeouts, or other failures. Callers (i.e., log processors)
                should handle these exceptions to comply with OpenTelemetry
                error handling principles.
        """

    @abc.abstractmethod
    def shutdown(self):
        """Shuts down the exporter.

        Called when the SDK is shut down.
        """

    @abc.abstractmethod
    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Hint to ensure that the export of any ``ReadableLogRecord`` objects
        the exporter has received prior to the call to ``force_flush`` SHOULD be
        completed as soon as possible, preferably before returning from this method.

        Args:
            timeout_millis: The maximum amount of time to wait for the flush to
                complete, in milliseconds.

        Returns:
            ``True`` if the flush completed successfully within the timeout,
            ``False`` otherwise.
        """


@deprecated("Use LogRecordExporter. Since logs are not stable yet this WILL be removed in future releases.")
class LogExporter(LogRecordExporter):
    """Deprecated alias of ``LogRecordExporter``.

    A subclass, so an exporter written against this name is still accepted
    everywhere a ``LogRecordExporter`` is expected.
    """


class ConsoleLogRecordExporter(LogRecordExporter):
    """Implementation of :class:`LogRecordExporter` that prints log records to the
    console.

    This class can be used for diagnostic purposes. It prints the exported
    log records to the console STDOUT.

    Both attributes are plain instance attributes with no validation, so
    reassigning ``out`` or ``formatter`` after construction takes effect on the
    next export.

    Args:
        out: The stream to write to. The default is bound when this module is
            imported rather than when an exporter is built, so replacing
            ``sys.stdout`` at any point after that import does not redirect an
            exporter that was built with the default. Pass the stream
            explicitly to write anywhere else.
        formatter: Turns one record into the text written for it. The default
            emits the indented JSON of ``ReadableLogRecord.to_json`` followed
            by the platform line separator. A formatter that returns text
            without a trailing separator runs its records together.
    """

    def __init__(
        self,
        out: IO = sys.stdout,
        formatter: Callable[[ReadableLogRecord], str] = lambda record: record.to_json() + linesep,
    ):
        """Build the exporter.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        self.out = out
        self.formatter = formatter

    def export(self, batch: Sequence[ReadableLogRecord]):
        """Write each record to the stream and flush it.

        Args:
            batch: The records to write, in the order they are to appear.

        Returns:
            ``LogRecordExportResult.SUCCESS``, always. A write that fails
            raises instead, and the calling processor is the one that has to
            catch it.
        """
        for log_record in batch:
            self.out.write(self.formatter(log_record))
        self.out.flush()
        return LogRecordExportResult.SUCCESS

    def shutdown(self):
        """Do nothing.

        The stream is not closed, since the exporter does not own it, and
        writes after this still reach it.
        """

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Do nothing, since ``export`` already flushed the stream.

        Args:
            timeout_millis: Ignored. Accepted so that the signature matches
                ``LogRecordExporter``.

        Returns:
            ``True``, always.
        """
        return True


@deprecated("Use ConsoleLogRecordExporter. Since logs are not stable yet this WILL be removed in future releases.")
class ConsoleLogExporter(ConsoleLogRecordExporter):
    """Deprecated alias of ``ConsoleLogRecordExporter``.

    Same constructor, same behaviour.
    """


class SimpleLogRecordProcessor(LogRecordProcessor):
    """Implementation of LogRecordProcessor that exports logs synchronously.

    This processor passes received logs directly to the configured
    ``LogRecordExporter`` as soon as they are emitted.

    This class serves as a reference implementation for custom log processors,
    demonstrating proper error handling. Note how the ``on_emit`` method wraps
    the exporter call in a try/except block to prevent exceptions from
    propagating to the application.

    Exporting happens on whatever thread called ``Logger.emit``, so the cost of
    the export, including any network round trip, is paid by the application
    code that logged. Each record is exported on its own, in a batch of one.
    ``BatchLogRecordProcessor`` is the alternative for anything other than
    tests and short-lived programs.

    Args:
        exporter: Where records are sent. ``shutdown`` is forwarded to it.
        meter_provider: Provider for the processor's own self-observability
            counters, which record how many records were submitted to the
            exporter and how many were dropped. ``None`` uses the globally
            configured meter provider. Nothing is recorded at all unless
            ``OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED`` is set to true.
    """

    def __init__(
        self,
        exporter: LogRecordExporter,
        *,
        meter_provider: MeterProvider | None = None,
    ):
        """Build the processor.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        self._exporter = exporter
        self._shutdown = False
        self._metrics = create_processor_metrics(
            "logs",
            OtelComponentTypeValues.SIMPLE_LOG_PROCESSOR,
            meter_provider or get_meter_provider(),
            enabled=parse_boolean_environment_variable(OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED),
        )

    def on_emit(self, log_record: ReadWriteLogRecord):
        """Export one record immediately, on the calling thread.

        The record is narrowed to a ``ReadableLogRecord`` and handed to the
        exporter as a one-element batch. Instrumentation is suppressed for the
        duration, so telemetry the exporter itself produces is not re-emitted.

        A record is dropped, and the drop counted, in two cases. The first is
        reaching a recursion depth above three, which happens when exporting a
        record causes another record to be emitted; the warning about it is
        written to a logger with propagation switched off, so it does not feed
        the loop it is reporting. The second is the processor having been shut
        down.

        An exception from the exporter is caught and logged rather than
        allowed to reach the code that called ``Logger.emit``.

        Args:
            log_record: The record to export. Its ``resource`` is used as is,
                and an unset one is replaced with ``Resource.create({})``
                rather than treated as an error. That replacement is not
                empty: the default detectors run, so it carries the
                ``telemetry.sdk.*``, ``service.name`` and
                ``service.instance.id`` attributes.
        """
        # Prevent entering a recursive loop.
        cnt = get_value(_ON_EMIT_RECURSION_COUNT_KEY) or 0
        # Recursive depth of 3 is sort of arbitrary. It's possible that an Exporter.export call
        # emits a log which returns us to this function, but when we call Exporter.export again the log
        # is no longer emitted and we exit this recursive loop naturally, a depth of >3 allows 3
        # recursive log calls but exits after because it's likely endless.
        if cnt > 3:  # pyright: ignore[reportOperatorIssue]
            _propagate_false_logger.warning(
                "SimpleLogRecordProcessor.on_emit has entered a recursive loop. Dropping log and exiting the loop."
            )
            self._metrics.drop_items(1, "recursion")
            return
        token = attach(
            set_value(
                _SUPPRESS_INSTRUMENTATION_KEY,
                True,
                set_value(_ON_EMIT_RECURSION_COUNT_KEY, cnt + 1),  # pyright: ignore[reportOperatorIssue]
            )
        )
        try:
            if self._shutdown:
                _logger.warning("Processor is already shutdown, ignoring call")
                self._metrics.drop_items(1, "already_shutdown")
                return
            # Convert ReadWriteLogRecord to ReadableLogRecord before exporting
            # Note: resource should not be None at this point as it's set during Logger.emit()
            resource = log_record.resource if log_record.resource is not None else Resource.create({})
            readable_log_record = ReadableLogRecord(
                log_record=log_record.log_record,
                resource=resource,
                instrumentation_scope=log_record.instrumentation_scope,
                limits=log_record.limits,
            )
            # Record on submission to the exporter.
            self._metrics.finish_items(1)
            self._exporter.export((readable_log_record,))
        except Exception:  # pylint: disable=broad-exception-caught
            _logger.exception("Exception while exporting logs.")
        finally:
            detach(token)

    def shutdown(self):
        """Stop accepting records and shut the exporter down.

        Nothing is buffered, so there is nothing to flush first. Later calls to
        ``on_emit`` log a warning and count a drop.

        The call is not guarded against repetition: calling it twice calls
        ``shutdown`` on the exporter twice, which matters for an exporter whose
        own ``shutdown`` is not idempotent.
        """
        self._shutdown = True
        self._exporter.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:  # pylint: disable=no-self-use
        """Do nothing, since every record was exported as it was emitted.

        Args:
            timeout_millis: Ignored. Accepted so that the signature matches
                ``LogRecordProcessor``.

        Returns:
            ``True``, always, including after ``shutdown``.
        """
        return True


class BatchLogRecordProcessor(LogRecordProcessor):
    """This is an implementation of LogRecordProcessor which creates batches of
    received logs and sends them to the configured LogRecordExporter.

    `BatchLogRecordProcessor` is configurable with the following environment
    variables which correspond to constructor parameters:

    - :envvar:`OTEL_BLRP_SCHEDULE_DELAY`
    - :envvar:`OTEL_BLRP_MAX_QUEUE_SIZE`
    - :envvar:`OTEL_BLRP_MAX_EXPORT_BATCH_SIZE`
    - :envvar:`OTEL_BLRP_EXPORT_TIMEOUT`

    All the logic for emitting logs, shutting down etc. resides in the BatchProcessor class.

    A background daemon thread drains the queue. It wakes on the schedule
    delay, and early whenever the queue reaches ``max_export_batch_size`` or
    the schedule delay is zero. Records are exported oldest first.

    When the queue is already at ``max_queue_size``, the new record is still
    added and the oldest queued record is discarded to make room; the drop is
    counted and a warning logged. After a fork, the child clears whatever the
    queue held at the moment of the fork and starts a fresh worker thread, so
    records queued in the parent and not yet exported are lost in the child.
    The parent is unaffected.

    Args:
        exporter: Where batches are sent. The worker thread calls its
            ``export``, and an exception from it is caught and logged.
        schedule_delay_millis: How long the worker waits between drains, in
            milliseconds. ``None`` reads ``OTEL_BLRP_SCHEDULE_DELAY``,
            falling back to 1000. Zero means export on every emit, which
            removes the batching.
        max_export_batch_size: Largest number of records handed to ``export``
            in one call. ``None`` reads
            ``OTEL_BLRP_MAX_EXPORT_BATCH_SIZE``, falling back to 512.
        export_timeout_millis: Not used. No way currently exists to pass a
            timeout to ``export``, so the value is validated and then ignored.
            ``None`` reads ``OTEL_BLRP_EXPORT_TIMEOUT``, falling back to
            30000.
        max_queue_size: How many records may wait to be exported. ``None``
            reads ``OTEL_BLRP_MAX_QUEUE_SIZE``, falling back to 2048.
        meter_provider: Provider for the processor's own self-observability
            instruments, which report the queue length and its capacity and
            count submitted and dropped records. ``None`` uses the globally
            configured meter provider. Nothing is recorded at all unless
            ``OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED`` is set to true.

    Raises:
        ValueError: If ``max_queue_size`` or ``max_export_batch_size`` is not
            positive, if ``schedule_delay_millis`` is negative, if
            ``export_timeout_millis`` is not positive, or if
            ``max_export_batch_size`` exceeds ``max_queue_size``. A value that
            came from an environment variable and did not parse as an integer
            does not raise: the default is used and the failure is logged.
    """

    def __init__(
        self,
        exporter: LogRecordExporter,
        schedule_delay_millis: float | None = None,
        max_export_batch_size: int | None = None,
        export_timeout_millis: float | None = None,
        max_queue_size: int | None = None,
        *,
        meter_provider: MeterProvider | None = None,
    ):
        """Build the processor and start its worker thread.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.

        Raises:
            ValueError: On an invalid combination of sizes and delays. The
                class docstring lists each case.
        """
        if max_queue_size is None:
            max_queue_size = BatchLogRecordProcessor._default_max_queue_size()

        if schedule_delay_millis is None:
            schedule_delay_millis = BatchLogRecordProcessor._default_schedule_delay_millis()

        if max_export_batch_size is None:
            max_export_batch_size = BatchLogRecordProcessor._default_max_export_batch_size()
        # Not used. No way currently to pass timeout to export.
        if export_timeout_millis is None:
            export_timeout_millis = BatchLogRecordProcessor._default_export_timeout_millis()

        BatchLogRecordProcessor._validate_arguments(
            max_queue_size,
            schedule_delay_millis,
            max_export_batch_size,
            export_timeout_millis,
        )
        # Initializes BatchProcessor
        self._batch_processor = BatchProcessor(
            exporter,
            schedule_delay_millis,
            max_export_batch_size,
            export_timeout_millis,
            max_queue_size,
            "Log",
            create_processor_metrics(
                "logs",
                OtelComponentTypeValues.BATCHING_LOG_PROCESSOR,
                meter_provider or get_meter_provider(),
                capacity=max_queue_size,
                enabled=parse_boolean_environment_variable(OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED),
            ),
        )

    def on_emit(self, log_record: ReadWriteLogRecord) -> None:
        """Put one record on the queue, to be exported by the worker thread.

        The API log record is shallow-copied and the copy's context replaced
        with an empty one, so that a queued record does not keep a whole
        ``Context`` alive while it waits. The record the caller passed keeps
        its context, which is what the other processors registered on the same
        provider still see. The trace id, span id and trace flags were already
        resolved onto the record, so dropping the context does not lose the
        correlation.

        The record is discarded, and the drop counted, when the processor has
        already been shut down. When the queue is full the oldest queued record
        is discarded instead and this one is kept.

        Args:
            log_record: The record to queue. Its ``resource`` is used as is,
                and an unset one is replaced with ``Resource.create({})``
                rather than treated as an error. That replacement is not
                empty: the default detectors run, so it carries the
                ``telemetry.sdk.*``, ``service.name`` and
                ``service.instance.id`` attributes.
        """
        # Convert ReadWriteLogRecord to ReadableLogRecord before passing to BatchProcessor
        # Note: resource should not be None at this point as it's set during Logger.emit()
        resource = log_record.resource if log_record.resource is not None else Resource.create({})
        # Shallow copy the API log record to break the reference to the potentially large context
        # while keeping the original context intact for other processors.
        api_log_record = copy.copy(log_record.log_record)
        api_log_record.context = Context()

        readable_log_record = ReadableLogRecord(
            log_record=api_log_record,
            resource=resource,
            instrumentation_scope=log_record.instrumentation_scope,
            limits=log_record.limits,
        )
        return self._batch_processor.emit(readable_log_record)

    def shutdown(self):
        """Drain the queue, stop the worker thread and shut the exporter down.

        The worker is woken, given up to thirty seconds to finish, and then
        prevented from starting another export even if records remain queued.
        The exporter's ``shutdown`` is then called with whatever is left of
        those thirty seconds, when its signature accepts a timeout. Later calls
        to ``on_emit`` are ignored and counted as drops.

        The call is idempotent: a second call returns at once, exports nothing
        and does not touch the exporter again.
        """
        return self._batch_processor.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Export everything queued, blocking until the queue is empty.

        Args:
            timeout_millis: Ignored. The flush runs to completion however long
                it takes, so a slow exporter blocks the caller past this value.

        Returns:
            ``False`` when the processor has already been shut down, in which
            case nothing is exported. ``True`` otherwise, once the queue has
            been drained. ``True`` does not mean the exporter accepted the
            records: a failing export is logged and still reports success here.
        """
        return self._batch_processor.force_flush(timeout_millis)

    @staticmethod
    def _default_max_queue_size():
        """Read the queue capacity from the environment.

        Returns:
            The integer value of ``OTEL_BLRP_MAX_QUEUE_SIZE``, or 2048 when
            that variable is unset or does not parse as an integer. A value
            that does not parse is reported through the module logger and then
            ignored.
        """
        try:
            return int(environ.get(OTEL_BLRP_MAX_QUEUE_SIZE, _DEFAULT_MAX_QUEUE_SIZE))
        except ValueError:
            _logger.exception(
                _ENV_VAR_INT_VALUE_ERROR_MESSAGE,
                OTEL_BLRP_MAX_QUEUE_SIZE,
                _DEFAULT_MAX_QUEUE_SIZE,
            )
            return _DEFAULT_MAX_QUEUE_SIZE

    @staticmethod
    def _default_schedule_delay_millis():
        """Read the delay between drains from the environment.

        Returns:
            The integer value of ``OTEL_BLRP_SCHEDULE_DELAY`` in milliseconds,
            or 1000 when that variable is unset or does not parse as an
            integer. A value that does not parse is reported through the module
            logger and then ignored.
        """
        try:
            return int(environ.get(OTEL_BLRP_SCHEDULE_DELAY, _DEFAULT_SCHEDULE_DELAY_MILLIS))
        except ValueError:
            _logger.exception(
                _ENV_VAR_INT_VALUE_ERROR_MESSAGE,
                OTEL_BLRP_SCHEDULE_DELAY,
                _DEFAULT_SCHEDULE_DELAY_MILLIS,
            )
            return _DEFAULT_SCHEDULE_DELAY_MILLIS

    @staticmethod
    def _default_max_export_batch_size():
        """Read the largest batch size from the environment.

        Returns:
            The integer value of ``OTEL_BLRP_MAX_EXPORT_BATCH_SIZE``, or 512
            when that variable is unset or does not parse as an integer. A
            value that does not parse is reported through the module logger and
            then ignored.
        """
        try:
            return int(
                environ.get(
                    OTEL_BLRP_MAX_EXPORT_BATCH_SIZE,
                    _DEFAULT_MAX_EXPORT_BATCH_SIZE,
                )
            )
        except ValueError:
            _logger.exception(
                _ENV_VAR_INT_VALUE_ERROR_MESSAGE,
                OTEL_BLRP_MAX_EXPORT_BATCH_SIZE,
                _DEFAULT_MAX_EXPORT_BATCH_SIZE,
            )
            return _DEFAULT_MAX_EXPORT_BATCH_SIZE

    @staticmethod
    def _default_export_timeout_millis():
        """Read the export timeout from the environment.

        The value is validated and stored but never applied, since the exporter
        interface has no way to receive a per-export timeout.

        Returns:
            The integer value of ``OTEL_BLRP_EXPORT_TIMEOUT`` in milliseconds,
            or 30000 when that variable is unset or does not parse as an
            integer. A value that does not parse is reported through the module
            logger and then ignored.
        """
        try:
            return int(environ.get(OTEL_BLRP_EXPORT_TIMEOUT, _DEFAULT_EXPORT_TIMEOUT_MILLIS))
        except ValueError:
            _logger.exception(
                _ENV_VAR_INT_VALUE_ERROR_MESSAGE,
                OTEL_BLRP_EXPORT_TIMEOUT,
                _DEFAULT_EXPORT_TIMEOUT_MILLIS,
            )
            return _DEFAULT_EXPORT_TIMEOUT_MILLIS

    @staticmethod
    def _validate_arguments(
        max_queue_size,
        schedule_delay_millis,
        max_export_batch_size,
        export_timeout_millis=None,
    ):
        """Reject a combination of sizes and delays the processor cannot use.

        Called once from the constructor, after the environment variables and
        the defaults have been resolved, so it sees the values that will
        actually be used rather than what the caller passed.

        Args:
            max_queue_size: Queue capacity in records.
            schedule_delay_millis: Delay between drains in milliseconds. Zero
                is allowed and turns batching off.
            max_export_batch_size: Largest batch handed to the exporter.
            export_timeout_millis: Export timeout in milliseconds, or ``None``
                to skip the check on it. The constructor always passes a
                number, so the ``None`` case only arises when this is called
                directly.

        Raises:
            ValueError: If ``max_queue_size`` is not positive, if
                ``schedule_delay_millis`` is negative, if
                ``max_export_batch_size`` is not positive or exceeds
                ``max_queue_size``, or if ``export_timeout_millis`` is given
                and is not positive.
        """
        if max_queue_size <= 0:
            raise ValueError("max_queue_size must be a positive integer.")

        if schedule_delay_millis < 0:
            raise ValueError("schedule_delay_millis must be non-negative.")

        if max_export_batch_size <= 0:
            raise ValueError("max_export_batch_size must be a positive integer.")

        if max_export_batch_size > max_queue_size:
            raise ValueError("max_export_batch_size must be less than or equal to max_queue_size.")

        if export_timeout_millis is not None and export_timeout_millis <= 0:
            raise ValueError("export_timeout_millis must be positive.")
