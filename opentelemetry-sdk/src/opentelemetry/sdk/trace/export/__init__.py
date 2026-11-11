# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
"""Span processors and span exporters."""

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
    """Outcome of one call to ``SpanExporter.export``."""

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

        Args:
            span: The span that just started. Ignored.
            parent_context: Context the span was started in, or ``None`` for
                the current context. Ignored.
        """

    def _on_ending(self, span: Span) -> None:
        pass

    def on_end(self, span: ReadableSpan) -> None:
        """Export the span immediately, on the calling thread.

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
        """Stop accepting spans and shut the exporter down."""
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

        Returns:
            The exporter held by the underlying batch processor.
        """
        return self._batch_processor._exporter  # pylint: disable=protected-access

    def on_start(self, span: Span, parent_context: Context | None = None) -> None:
        """Ignore the start of a span.

        Args:
            span: The span that just started. Ignored.
            parent_context: Context the span was started in, or ``None`` for
                the current context. Ignored.
        """

    def _on_ending(self, span: Span) -> None:
        pass

    def on_end(self, span: ReadableSpan) -> None:
        """Put the span on the queue for the worker thread.

        Args:
            span: The span that just ended.
        """
        if not (span.context and span.context.trace_flags.sampled):
            return
        self._batch_processor.emit(span)

    def shutdown(self):
        """Stop accepting spans, drain the queue and shut the exporter down."""
        return self._batch_processor.shutdown()

    def force_flush(self, timeout_millis: int | None = None) -> bool:
        """Export everything queued, blocking until the queue is empty.

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
