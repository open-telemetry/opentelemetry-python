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

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from typing import Literal

from opentelemetry.metrics import CallbackOptions, MeterProvider, Observation
from opentelemetry.sdk.environment_variables import (
    OTEL_PYTHON_SDK_METRICS_ENABLED,
)
from opentelemetry.sdk.environment_variables._internal import (
    parse_boolean_environment_variable,
)
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


class ProcessorMetrics:
    def __init__(
        self,
        signal: Literal["traces", "logs"],
        component_type: OtelComponentTypeValues,
        meter_provider: MeterProvider,
        *,
        capacity: int | None = None,
    ) -> None:
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

        if signal == "traces":
            create_processed = create_otel_sdk_processor_span_processed
            create_queue_capacity = (
                create_otel_sdk_processor_span_queue_capacity
            )
        else:
            create_processed = create_otel_sdk_processor_log_processed
            create_queue_capacity = (
                create_otel_sdk_processor_log_queue_capacity
            )

        self._processed = create_processed(meter)
        self._enabled = parse_boolean_environment_variable(
            OTEL_PYTHON_SDK_METRICS_ENABLED
        )

        if capacity is not None:
            self._queue_capacity = create_queue_capacity(meter)
            if self._enabled:
                self._queue_capacity.add(capacity, self._standard_attrs)

    def register_queue_size(self, get_queue_size: Callable[[], int]) -> None:
        if not self._enabled:
            return

        def record_queue_size(
            _options: CallbackOptions,
        ) -> tuple[Observation]:
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

    def drop_items(self, count: int) -> None:
        if not self._enabled:
            return
        self._processed.add(count, self._dropped_attrs)

    def finish_items(self, count: int, error: Exception | None) -> None:
        if not self._enabled:
            return
        if not error:
            self._processed.add(count, self._standard_attrs)
            return
        attrs = {
            **self._standard_attrs,
            ERROR_TYPE: type(error).__name__,
        }
        self._processed.add(count, attrs)
