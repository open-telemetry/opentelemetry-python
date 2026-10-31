# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Self-observability metrics for the batch span and log record processors.

A processor reports how many items it finished, how many it dropped and why,
how large its queue is and what its capacity is. The metric names and the
attribute keys come from the incubating ``otel`` semantic conventions, so a
backend can chart the health of the SDK itself alongside the application.

Reporting is off by default. When it is off, ``create_processor_metrics``
returns a ``NoOpProcessorMetrics``, so each report costs one method call that
does nothing and no instrument is ever created.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from typing import Literal, Protocol

from opentelemetry.metrics import CallbackOptions, MeterProvider, Observation
from opentelemetry.semconv._incubating.attributes.otel_attributes import (
    OTEL_COMPONENT_NAME,
    OTEL_COMPONENT_TYPE,
    OtelComponentTypeValues,
)
from opentelemetry.semconv._incubating.metrics.otel_metrics import (
    OTEL_SDK_PROCESSOR_LOG_QUEUE_SIZE,
    OTEL_SDK_PROCESSOR_SPAN_QUEUE_SIZE,
    create_otel_sdk_processor_log_processed,
    create_otel_sdk_processor_log_queue_capacity,
    create_otel_sdk_processor_span_processed,
    create_otel_sdk_processor_span_queue_capacity,
)
from opentelemetry.semconv.attributes.error_attributes import ERROR_TYPE

_component_counter = Counter()


class ProcessorMetricsT(Protocol):
    """What a batch processor calls to report on itself.

    ``ProcessorMetrics`` and ``NoOpProcessorMetrics`` both satisfy this, so
    the processor never has to test whether reporting is on.
    """

    def register_queue_size(self, get_queue_size: Callable[[], int]) -> None:
        """Arrange for the queue size to be observed at each collection.

        Args:
            get_queue_size: A function returning the current number of queued
                items. It is called during metric collection, from whichever
                thread drives the metric reader, so it has to be cheap and
                safe to call concurrently with the processor.
        """

    def drop_items(self, count: int, error_type: str = "queue_full") -> None:
        """Report items the processor discarded without exporting them.

        Args:
            count: How many items were discarded.
            error_type: Why they were discarded, recorded as the
                ``error.type`` attribute. The values the processors use are
                ``"queue_full"``, ``"already_shutdown"`` and ``"recursion"``.
        """

    def finish_items(self, count: int) -> None:
        """Report items the processor handed to the exporter.

        The count is recorded when the batch is submitted, not when the
        export comes back, so an export that fails is still counted here.

        Args:
            count: How many items were submitted.
        """


class NoOpProcessorMetrics:
    """Discards every report, for a processor with reporting turned off."""

    def register_queue_size(self, get_queue_size: Callable[[], int]) -> None:
        """Ignore the queue size callback.

        Args:
            get_queue_size: The callback, which is never stored and never
                called.
        """

    def drop_items(self, count: int, error_type: str = "queue_full") -> None:
        """Ignore a report of discarded items.

        Args:
            count: How many items were discarded.
            error_type: Why they were discarded.
        """

    def finish_items(self, count: int) -> None:
        """Ignore a report of submitted items.

        Args:
            count: How many items were submitted.
        """


class ProcessorMetrics:
    """Records the self-observability metrics of one processor instance.

    Every instance is given its own ``otel.component.name``, built from the
    component type and a count of how many instances of that type have been
    created in this process, so two batch processors of the same kind can be
    told apart.

    Args:
        signal: Which telemetry the processor handles. It selects the span or
            the log variant of each instrument.
        component_type: The semantic convention value naming the kind of
            processor, recorded as the ``otel.component.type`` attribute.
        meter_provider: The provider the instruments are created from. Pass
            the one the SDK uses for its own telemetry, not necessarily the
            global one.
        capacity: The queue capacity to record once, in items. Pass ``None``
            to skip the capacity instrument altogether, which is what a
            processor without a bounded queue does.
    """

    def __init__(
        self,
        signal: Literal["traces", "logs"],
        component_type: OtelComponentTypeValues,
        meter_provider: MeterProvider,
        *,
        capacity: int | None = None,
    ) -> None:
        """Create the instruments and record the queue capacity.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders. ``capacity`` is keyword only.
        """
        self._signal = signal
        meter = meter_provider.get_meter("opentelemetry-sdk")
        self._meter = meter

        count = _component_counter[component_type.value]
        _component_counter[component_type.value] = count + 1

        self._standard_attrs = {
            OTEL_COMPONENT_TYPE: component_type.value,
            OTEL_COMPONENT_NAME: f"{component_type.value}/{count}",
        }

        self._dropped_attrs = {
            **self._standard_attrs,
            ERROR_TYPE: "queue_full",
        }

        self._already_shutdown_attrs = {
            **self._standard_attrs,
            ERROR_TYPE: "already_shutdown",
        }

        self._recursion_attrs = {
            **self._standard_attrs,
            ERROR_TYPE: "recursion",
        }

        if signal == "traces":
            create_processed = create_otel_sdk_processor_span_processed
            create_queue_capacity = create_otel_sdk_processor_span_queue_capacity
        else:
            create_processed = create_otel_sdk_processor_log_processed
            create_queue_capacity = create_otel_sdk_processor_log_queue_capacity

        self._processed = create_processed(meter)

        if capacity is not None:
            self._queue_capacity = create_queue_capacity(meter)
            self._queue_capacity.add(capacity, self._standard_attrs)

    def register_queue_size(self, get_queue_size: Callable[[], int]) -> None:
        """Create the observable up down counter for the queue size.

        The instrument is named ``otel.sdk.processor.span.queue.size`` for
        traces and ``otel.sdk.processor.log.queue.size`` for logs. Nothing is
        recorded here; the callback is invoked once per metric collection.

        Args:
            get_queue_size: A function returning the current number of queued
                items.
        """

        def record_queue_size(
            _options: CallbackOptions,
        ) -> tuple[Observation]:
            """Observe the queue size once, for one metric collection.

            Args:
                _options: The timeout and other collection options the metric
                    reader passes in. They are ignored, since reading the
                    queue size cannot block.

            Returns:
                A single observation of the current queue size, carrying the
                component type and component name attributes.
            """
            return (Observation(get_queue_size(), self._standard_attrs),)

        if self._signal == "traces":
            queue_size_name = OTEL_SDK_PROCESSOR_SPAN_QUEUE_SIZE
            queue_size_description = "The number of spans in the queue of a given instance of an SDK span processor."
            queue_size_unit = "{span}"
        else:
            queue_size_name = OTEL_SDK_PROCESSOR_LOG_QUEUE_SIZE
            queue_size_description = "The number of logs in the queue of a given instance of an SDK log processor."
            queue_size_unit = "{log}"

        self._meter.create_observable_up_down_counter(
            queue_size_name,
            callbacks=(record_queue_size,),
            description=queue_size_description,
            unit=queue_size_unit,
        )

    def drop_items(self, count: int, error_type: str = "queue_full") -> None:
        """Add to the processed counter with an ``error.type`` attribute.

        Dropped and finished items share one counter, told apart by whether
        ``error.type`` is present, so the drop rate is a ratio over the same
        instrument.

        Args:
            count: How many items were discarded.
            error_type: Why they were discarded. ``"already_shutdown"`` and
                ``"recursion"`` are recorded as themselves. Any other value,
                including the default, is recorded as ``"queue_full"``.
        """
        if error_type == "already_shutdown":
            self._processed.add(count, self._already_shutdown_attrs)
        elif error_type == "recursion":
            self._processed.add(count, self._recursion_attrs)
        else:
            self._processed.add(count, self._dropped_attrs)

    def finish_items(self, count: int) -> None:
        """Add to the processed counter with no ``error.type`` attribute.

        Args:
            count: How many items were handed to the exporter. They are
                counted at submission, so an export that then fails is still
                counted as finished.
        """
        self._processed.add(count, self._standard_attrs)


def create_processor_metrics(
    signal: Literal["traces", "logs"],
    component_type: OtelComponentTypeValues,
    meter_provider: MeterProvider,
    *,
    capacity: int | None = None,
    enabled: bool,
) -> ProcessorMetricsT:
    """Build the metrics object a processor should report through.

    Args:
        signal: Which telemetry the processor handles.
        component_type: The semantic convention value naming the kind of
            processor.
        meter_provider: The provider the instruments are created from. It is
            not touched when ``enabled`` is false.
        capacity: The queue capacity to record once, in items, or ``None`` to
            record no capacity.
        enabled: Whether to record anything at all. It is keyword only and
            has no default, so a caller has to state its choice.

    Returns:
        A ``ProcessorMetrics`` when ``enabled`` is true, which creates its
        instruments right away. A ``NoOpProcessorMetrics`` otherwise.
    """
    if not enabled:
        return NoOpProcessorMetrics()

    return ProcessorMetrics(
        signal,
        component_type,
        meter_provider,
        capacity=capacity,
    )
