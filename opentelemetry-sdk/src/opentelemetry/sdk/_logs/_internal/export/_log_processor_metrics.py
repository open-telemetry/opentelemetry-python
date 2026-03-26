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

from opentelemetry.metrics import CallbackOptions, MeterProvider, Observation
from opentelemetry.semconv._incubating.attributes.otel_attributes import (
    OTEL_COMPONENT_NAME,
    OTEL_COMPONENT_TYPE,
)
from opentelemetry.semconv._incubating.metrics.otel_metrics import (
    OTEL_SDK_PROCESSOR_LOG_QUEUE_SIZE,
    create_otel_sdk_processor_log_processed,
    create_otel_sdk_processor_log_queue_capacity,
)
from opentelemetry.semconv.attributes.error_attributes import ERROR_TYPE

_component_counter = Counter()


class LogProcessorMetrics:
    def __init__(
        self,
        component_type: str,
        meter_provider: MeterProvider,
        *,
        capacity: int | None = None,
        get_queue_size: Callable[[], int] | None = None,
    ) -> None:
        meter = meter_provider.get_meter("opentelemetry-sdk")

        count = _component_counter[component_type]
        _component_counter[component_type] = count + 1

        self._standard_attrs = {
            OTEL_COMPONENT_TYPE: component_type,
            OTEL_COMPONENT_NAME: f"{component_type}/{count}",
        }

        self._dropped_attrs = {
            **self._standard_attrs,
            ERROR_TYPE: "queue_full",
        }

        self._processed_logs = create_otel_sdk_processor_log_processed(meter)

        if capacity is not None:
            self._queue_capacity = (
                create_otel_sdk_processor_log_queue_capacity(meter)
            )
            self._queue_capacity.add(capacity, self._standard_attrs)

        if get_queue_size is not None:

            def record_queue_size(
                _options: CallbackOptions,
            ) -> tuple[Observation]:
                return (Observation(get_queue_size(), self._standard_attrs),)

            meter.create_observable_up_down_counter(
                OTEL_SDK_PROCESSOR_LOG_QUEUE_SIZE,
                callbacks=(record_queue_size,),
                description="The number of logs in the queue of a given instance of an SDK log processor.",
                unit="{log}",
            )

    def drop_items(self, count: int) -> None:
        self._processed_logs.add(count, self._dropped_attrs)

    def finish_items(self, count: int, error: Exception | None) -> None:
        if not error:
            self._processed_logs.add(count, self._standard_attrs)
            return
        attrs = {
            **self._standard_attrs,
            ERROR_TYPE: type(error).__name__,
        }
        self._processed_logs.add(count, attrs)
