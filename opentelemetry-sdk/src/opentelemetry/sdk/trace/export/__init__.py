# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
"""Span processors and span exporters.

A ``SpanExporter`` turns ended spans into whatever shape a backend accepts and
sends them. A ``SpanProcessor`` decides when an exporter is called. Two
processors are provided here.

``SimpleSpanProcessor`` exports each sampled span on the thread that ended it,
one span per export call. Nothing is buffered, so no span is lost on a crash,
and the ending thread pays the cost of the export.

``BatchSpanProcessor`` puts sampled spans on a bounded queue and lets a
background thread export them in batches. The queue holds 2048 spans, the
thread wakes every 5000 milliseconds, and at most 512 spans go out per export
call. Each of those is overridable through a constructor argument or through
``OTEL_BSP_MAX_QUEUE_SIZE``, ``OTEL_BSP_SCHEDULE_DELAY`` and
``OTEL_BSP_MAX_EXPORT_BATCH_SIZE``. An emit onto a queue that is already full
drops the oldest span in it and logs a warning.

``ConsoleSpanExporter`` writes spans to a stream as JSON, and is useful while
developing. ``InMemorySpanExporter``, in the sibling module
``opentelemetry.sdk.trace.export.in_memory_span_exporter``, keeps them in a
deque for tests.
"""

from __future__ import annotations

import collections.abc
import logging
import sys
import typing
from enum import Enum
from os import environ, linesep

from opentelemetry.context import (
    _SUPPRESS_INSTRUMENTATION_KEY,
    Context,
    attach,
    detach,
    set_value,
)
from opentelemetry.metrics import MeterProvider, get_meter_provider
from opentelemetry.sdk._shared_internal import (
    BatchProcessor,
)
from opentelemetry.sdk._shared_internal._processor_metrics import (
    create_processor_metrics,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_BSP_EXPORT_TIMEOUT,
    OTEL_BSP_MAX_EXPORT_BATCH_SIZE,
    OTEL_BSP_MAX_QUEUE_SIZE,
    OTEL_BSP_SCHEDULE_DELAY,
    OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED,
)
from opentelemetry.sdk.environment_variables._internal import (
    parse_boolean_environment_variable,
)
from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor
from opentelemetry.semconv._incubating.attributes.otel_attributes import (
    OtelComponentTypeValues,
)

_DEFAULT_SCHEDULE_DELAY_MILLIS = 5000
_DEFAULT_MAX_EXPORT_BATCH_SIZE = 512
_DEFAULT_EXPORT_TIMEOUT_MILLIS = 30000
_DEFAULT_MAX_QUEUE_SIZE = 2048
_ENV_VAR_INT_VALUE_ERROR_MESSAGE = "Unable to parse value for %s as integer. Defaulting to %s."

logger = logging.getLogger(__name__)


class SpanExportResult(Enum):
    """Outcome of one call to ``SpanExporter.export``.

    ``SUCCESS`` means the batch was handed over. ``FAILURE`` means it was not,
    and since neither processor in this module retries, the spans in that
    batch are gone.
    """

    SUCCESS = 0
    FAILURE = 1


class SpanExporter:
    """Interface for exporting spans.

    Interface to be implemented by services that want to export spans recorded
    in their own format.

    To export data this MUST be registered to the :class`opentelemetry.sdk.trace.Tracer` using a
    `SimpleSpanProcessor` or a `BatchSpanProcessor`.
    """

    def export(self, spans: collections.abc.Sequence[ReadableSpan]) -> SpanExportResult:  # pyright: ignore[reportReturnType]
        """Exports a batch of telemetry data.

        Args:
            spans: The list of `opentelemetry.trace.Span` objects to be exported

        Returns:
            The result of the export
        """

    def shutdown(self) -> None:
        """Shuts down the exporter.

        Called when the SDK is shut down.
        """

    def force_flush(self, timeout_millis: int = 30000) -> bool:  # pyright: ignore[reportReturnType]
        """Hint to ensure that the export of any spans the exporter has received
        prior to the call to ForceFlush SHOULD be completed as soon as possible, preferably
        before returning from this method.

        The base implementation does nothing and returns ``None``. An exporter
        that holds spans of its own should override it.

        Args:
            timeout_millis: Upper bound on the flush, in milliseconds.

        Returns:
            ``True`` when everything held was flushed within the timeout,
            ``False`` otherwise.
        """


class SimpleSpanProcessor(SpanProcessor):
    """Simple SpanProcessor implementation.

    SimpleSpanProcessor is an implementation of `SpanProcessor` that
    passes ended spans directly to the configured `SpanExporter`.

    The export happens on the thread that ended the span and blocks it until
    the exporter returns, one span per export call. Spans whose sampled flag
    is not set are discarded without reaching the exporter.

    Args:
        span_exporter: Exporter each sampled span is handed to.
        meter_provider: Provider used for the self-observability metrics of
            this processor. ``None`` means the globally configured provider.
            Whether those metrics are recorded at all is decided by
            ``OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED``.
    """

    def __init__(
        self,
        span_exporter: SpanExporter,
        *,
        meter_provider: MeterProvider | None = None,
    ):
        """Build the processor.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        self.span_exporter = span_exporter
        self._shutdown = False
        self._metrics = create_processor_metrics(
            "traces",
            OtelComponentTypeValues.SIMPLE_SPAN_PROCESSOR,
            meter_provider or get_meter_provider(),
            enabled=parse_boolean_environment_variable(OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED),
        )

    def on_start(self, span: Span, parent_context: Context | None = None) -> None:
        """Ignore the start of a span.

        This processor acts only when a span ends, so nothing happens here.

        Args:
            span: The span that just started. Ignored.
            parent_context: Context the span was started in, or ``None`` for
                the current context. Ignored.
        """

    def _on_ending(self, span: Span) -> None:
        """Ignore the moment just before a span ends.

        This hook exists so a processor can still mutate a span while it is
        writable. This processor does not, so nothing happens here.

        Args:
            span: The span about to end. Ignored.
        """

    def on_end(self, span: ReadableSpan) -> None:
        """Export the span immediately, on the calling thread.

        A span whose sampled flag is not set returns without reaching the
        exporter. After ``shutdown``, the span is counted as dropped with
        error type ``already_shutdown`` and a warning is logged. An exception
        raised by the exporter is caught and logged, so it never reaches the
        code that ended the span.

        Instrumentation is suppressed for the duration of the export, which
        keeps an exporter that is itself instrumented from producing spans
        about its own export.

        Args:
            span: The span that just ended.
        """
        if not (span.context and span.context.trace_flags.sampled):
            return
        if self._shutdown:
            logger.warning("Processor is already shutdown, ignoring call")
            self._metrics.drop_items(1, "already_shutdown")
            return
        token = attach(set_value(_SUPPRESS_INSTRUMENTATION_KEY, True))
        # Record on submission to the exporter.
        self._metrics.finish_items(1)
        try:
            self.span_exporter.export((span,))
        # pylint: disable=broad-exception-caught
        except Exception:
            logger.exception("Exception while exporting Span.")
        finally:
            detach(token)

    def shutdown(self) -> None:
        """Stop accepting spans and shut the exporter down.

        Nothing is queued here, so there is nothing left to flush. Every span
        that ends afterwards is dropped with a warning.
        """
        self._shutdown = True
        self.span_exporter.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Do nothing, since every span was already exported as it ended.

        Args:
            timeout_millis: Ignored. Accepted so that this processor matches
                the ``SpanProcessor`` interface.

        Returns:
            ``True`` always, including after ``shutdown``.
        """
        # pylint: disable=unused-argument
        return True


class BatchSpanProcessor(SpanProcessor):
    """Batch span processor implementation.

    `BatchSpanProcessor` is an implementation of `SpanProcessor` that
    batches ended spans and pushes them to the configured `SpanExporter`.

    `BatchSpanProcessor` is configurable with the following environment
    variables which correspond to constructor parameters:

    - :envvar:`OTEL_BSP_SCHEDULE_DELAY`
    - :envvar:`OTEL_BSP_MAX_QUEUE_SIZE`
    - :envvar:`OTEL_BSP_MAX_EXPORT_BATCH_SIZE`
    - :envvar:`OTEL_BSP_EXPORT_TIMEOUT`

    All the logic for emitting spans, shutting down etc. resides in the `BatchProcessor` class.

    Ended spans whose sampled flag is set are put on a bounded queue, and a
    daemon thread drains it. The thread exports as soon as the queue holds at
    least ``max_export_batch_size`` spans, and otherwise once every
    ``schedule_delay_millis``. A ``schedule_delay_millis`` of zero turns that
    into an export on every emit.

    When the queue is full, the span that has waited longest is discarded to
    make room for the new one, a warning is logged, and the discarded span is
    counted with error type ``queue_full``.

    Args:
        span_exporter: Exporter each batch is handed to.
        max_queue_size: Number of spans the queue holds. ``None`` reads
            ``OTEL_BSP_MAX_QUEUE_SIZE``, falling back to 2048 when that
            variable is unset or does not parse as an integer. Must be
            positive.
        schedule_delay_millis: Time the worker thread waits between exports,
            in milliseconds. ``None`` reads ``OTEL_BSP_SCHEDULE_DELAY``,
            falling back to 5000. Must not be negative.
        max_export_batch_size: Largest number of spans passed to the exporter
            in one call. ``None`` reads ``OTEL_BSP_MAX_EXPORT_BATCH_SIZE``,
            falling back to 512. Must be positive and no larger than
            ``max_queue_size``.
        export_timeout_millis: Budget for one export call, in milliseconds.
            ``None`` reads ``OTEL_BSP_EXPORT_TIMEOUT``, falling back to 30000.
            It is validated and stored, and the export path has no way to
            apply it, so it currently bounds nothing.
        meter_provider: Provider used for the self-observability metrics of
            this processor. ``None`` means the globally configured provider.
            Whether those metrics are recorded at all is decided by
            ``OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED``.
    """

    def __init__(
        self,
        span_exporter: SpanExporter,
        max_queue_size: int | None = None,
        schedule_delay_millis: float | None = None,
        max_export_batch_size: int | None = None,
        export_timeout_millis: float | None = None,
        *,
        meter_provider: MeterProvider | None = None,
    ):
        """Build the processor and start its worker thread.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.

        Raises:
            ValueError: If ``max_queue_size`` or ``max_export_batch_size`` is
                not positive, if ``schedule_delay_millis`` is negative, if
                ``max_export_batch_size`` exceeds ``max_queue_size``, or if
                ``export_timeout_millis`` is not positive.
        """
        if max_queue_size is None:
            max_queue_size = BatchSpanProcessor._default_max_queue_size()

        if schedule_delay_millis is None:
            schedule_delay_millis = BatchSpanProcessor._default_schedule_delay_millis()

        if max_export_batch_size is None:
            max_export_batch_size = BatchSpanProcessor._default_max_export_batch_size()

        # Not used. No way currently to pass timeout to export.
        if export_timeout_millis is None:
            export_timeout_millis = BatchSpanProcessor._default_export_timeout_millis()

        BatchSpanProcessor._validate_arguments(
            max_queue_size,
            schedule_delay_millis,
            max_export_batch_size,
            export_timeout_millis,
        )

        self._batch_processor = BatchProcessor(
            span_exporter,
            schedule_delay_millis,
            max_export_batch_size,
            export_timeout_millis,
            max_queue_size,
            "Span",
            create_processor_metrics(
                "traces",
                OtelComponentTypeValues.BATCHING_SPAN_PROCESSOR,
                meter_provider or get_meter_provider(),
                capacity=max_queue_size,
                enabled=parse_boolean_environment_variable(OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED),
            ),
        )

    # Added for backward compatibility. Not recommended to directly access/use underlying exporter.
    @property
    def span_exporter(self):
        """The exporter passed to the constructor.

        Kept for callers written against an earlier version that stored the
        exporter as an attribute. Reaching through it to call ``export`` or
        ``shutdown`` directly bypasses the queue and the worker thread.

        Returns:
            The exporter held by the underlying batch processor.
        """
        return self._batch_processor._exporter  # pylint: disable=protected-access

    def on_start(self, span: Span, parent_context: Context | None = None) -> None:
        """Ignore the start of a span.

        This processor acts only when a span ends, so nothing happens here.

        Args:
            span: The span that just started. Ignored.
            parent_context: Context the span was started in, or ``None`` for
                the current context. Ignored.
        """

    def _on_ending(self, span: Span) -> None:
        """Ignore the moment just before a span ends.

        This hook exists so a processor can still mutate a span while it is
        writable. This processor does not, so nothing happens here.

        Args:
            span: The span about to end. Ignored.
        """

    def on_end(self, span: ReadableSpan) -> None:
        """Put the span on the queue for the worker thread.

        A span whose sampled flag is not set returns without being queued.
        After ``shutdown``, the span is discarded and counted with error type
        ``already_shutdown``. On a full queue, the oldest queued span is
        discarded instead. The call does not wait for an export.

        Args:
            span: The span that just ended.
        """
        if not (span.context and span.context.trace_flags.sampled):
            return
        self._batch_processor.emit(span)

    def shutdown(self):
        """Stop accepting spans, drain the queue and shut the exporter down.

        The worker thread is woken and exports what is still queued, then is
        joined with a 30 second budget. Whatever remains queued when that
        budget runs out is never exported. The exporter is shut down last,
        with the part of the budget the join left over when it accepts a
        ``timeout_millis`` argument. A second call returns at once.
        """
        return self._batch_processor.shutdown()

    def force_flush(self, timeout_millis: int | None = None) -> bool:
        """Export everything queued, blocking until the queue is empty.

        The export runs on the calling thread, in batches of at most
        ``max_export_batch_size``, and shares a lock with the worker thread.

        Args:
            timeout_millis: Accepted and currently ignored, so the call
                blocks for as long as draining the queue takes. ``None``
                requests no particular bound.

        Returns:
            ``False`` if the processor has been shut down, in which case
            nothing was exported, ``True`` otherwise.
        """
        return self._batch_processor.force_flush(timeout_millis)

    @staticmethod
    def _default_max_queue_size():
        """Read the queue capacity from the environment.

        Returns:
            ``OTEL_BSP_MAX_QUEUE_SIZE`` as an integer, or 2048 when the
            variable is unset or does not parse, in which case the parse
            failure is logged with its traceback.
        """
        try:
            return int(environ.get(OTEL_BSP_MAX_QUEUE_SIZE, _DEFAULT_MAX_QUEUE_SIZE))
        except ValueError:
            logger.exception(
                _ENV_VAR_INT_VALUE_ERROR_MESSAGE,
                OTEL_BSP_MAX_QUEUE_SIZE,
                _DEFAULT_MAX_QUEUE_SIZE,
            )
            return _DEFAULT_MAX_QUEUE_SIZE

    @staticmethod
    def _default_schedule_delay_millis():
        """Read the delay between scheduled exports from the environment.

        Returns:
            ``OTEL_BSP_SCHEDULE_DELAY`` as an integer number of milliseconds,
            or 5000 when the variable is unset or does not parse, in which
            case the parse failure is logged with its traceback.
        """
        try:
            return int(environ.get(OTEL_BSP_SCHEDULE_DELAY, _DEFAULT_SCHEDULE_DELAY_MILLIS))
        except ValueError:
            logger.exception(
                _ENV_VAR_INT_VALUE_ERROR_MESSAGE,
                OTEL_BSP_SCHEDULE_DELAY,
                _DEFAULT_SCHEDULE_DELAY_MILLIS,
            )
            return _DEFAULT_SCHEDULE_DELAY_MILLIS

    @staticmethod
    def _default_max_export_batch_size():
        """Read the largest export batch size from the environment.

        Returns:
            ``OTEL_BSP_MAX_EXPORT_BATCH_SIZE`` as an integer, or 512 when the
            variable is unset or does not parse, in which case the parse
            failure is logged with its traceback.
        """
        try:
            return int(
                environ.get(
                    OTEL_BSP_MAX_EXPORT_BATCH_SIZE,
                    _DEFAULT_MAX_EXPORT_BATCH_SIZE,
                )
            )
        except ValueError:
            logger.exception(
                _ENV_VAR_INT_VALUE_ERROR_MESSAGE,
                OTEL_BSP_MAX_EXPORT_BATCH_SIZE,
                _DEFAULT_MAX_EXPORT_BATCH_SIZE,
            )
            return _DEFAULT_MAX_EXPORT_BATCH_SIZE

    @staticmethod
    def _default_export_timeout_millis():
        """Read the export timeout from the environment.

        Returns:
            ``OTEL_BSP_EXPORT_TIMEOUT`` as an integer number of milliseconds,
            or 30000 when the variable is unset or does not parse, in which
            case the parse failure is logged with its traceback.
        """
        try:
            return int(environ.get(OTEL_BSP_EXPORT_TIMEOUT, _DEFAULT_EXPORT_TIMEOUT_MILLIS))
        except ValueError:
            logger.exception(
                _ENV_VAR_INT_VALUE_ERROR_MESSAGE,
                OTEL_BSP_EXPORT_TIMEOUT,
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
        """Reject a combination of settings the batch processor cannot honour.

        Returns ``None`` when every value is acceptable.

        Args:
            max_queue_size: Number of spans the queue would hold.
            schedule_delay_millis: Delay between scheduled exports, in
                milliseconds. Zero is allowed and means export on every emit.
            max_export_batch_size: Largest number of spans per export call.
            export_timeout_millis: Budget for one export call, in
                milliseconds. ``None`` skips the check on it.

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


class ConsoleSpanExporter(SpanExporter):
    """Implementation of :class:`SpanExporter` that prints spans to the
    console.

    This class can be used for diagnostic purposes. It prints the exported
    spans to the console STDOUT.

    Args:
        service_name: Stored on the instance and read by nothing else here.
            The service name that reaches a backend comes from the resource
            of the tracer provider, so setting this does not change the
            printed output.
        out: Stream the formatted spans are written to. The default is bound
            when this module is imported rather than when an exporter is
            built, so replacing ``sys.stdout`` at any point after that import
            does not redirect an exporter that was built with the default.
            Pass the stream explicitly to write anywhere else.
        formatter: Turns one span into the text written for it. The default
            emits the indented JSON of ``ReadableSpan.to_json``, which spans
            several lines, followed by the platform line separator. Pass a
            formatter calling ``to_json(indent=None)`` to get one span per
            line. A formatter that returns text without a trailing separator
            runs the spans together.
    """

    def __init__(
        self,
        service_name: str | None = None,
        out: typing.IO = sys.stdout,
        formatter: collections.abc.Callable[[ReadableSpan], str] = lambda span: span.to_json() + linesep,
    ):
        """Build the exporter.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        self.out = out
        self.formatter = formatter
        self.service_name = service_name

    def export(self, spans: collections.abc.Sequence[ReadableSpan]) -> SpanExportResult:
        """Write each span through the formatter and flush the stream.

        Args:
            spans: The spans to write, in the order given.

        Returns:
            ``SpanExportResult.SUCCESS`` always. A stream that raises on
            write propagates the exception instead of reporting failure.
        """
        for span in spans:
            self.out.write(self.formatter(span))
        self.out.flush()
        return SpanExportResult.SUCCESS

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Do nothing, since ``export`` already flushed the stream.

        Args:
            timeout_millis: Ignored. Accepted so that this exporter matches
                the ``SpanExporter`` interface.

        Returns:
            ``True`` always.
        """
        return True
