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

from opentelemetry.metrics import (
    Counter,
    Histogram,
    Meter,
    UpDownCounter,
    ObservableGauge,
)
from typing import Callable, Sequence

class JvmMetrics:

    """
    Number of buffers in the pool
    """
    @staticmethod
    def create_jvm_buffer_count(meter: Meter) -> UpDownCounter:
        return meter.create_up_down_counter(
            name="jvm.buffer.count",
            description="Number of buffers in the pool.",
            unit="{buffer}",
        )


    """
    Measure of total memory capacity of buffers
    """
    @staticmethod
    def create_jvm_buffer_memory_limit(meter: Meter) -> UpDownCounter:
        return meter.create_up_down_counter(
            name="jvm.buffer.memory.limit",
            description="Measure of total memory capacity of buffers.",
            unit="By",
        )


    """
    Measure of memory used by buffers
    """
    @staticmethod
    def create_jvm_buffer_memory_usage(meter: Meter) -> UpDownCounter:
        return meter.create_up_down_counter(
            name="jvm.buffer.memory.usage",
            description="Measure of memory used by buffers.",
            unit="By",
        )


    """
    Measure of initial memory requested
    """
    @staticmethod
    def create_jvm_memory_init(meter: Meter) -> UpDownCounter:
        return meter.create_up_down_counter(
            name="jvm.memory.init",
            description="Measure of initial memory requested.",
            unit="By",
        )


    """
    Average CPU load of the whole system for the last minute as reported by the JVM
    """
    @staticmethod
    def create_jvm_system_cpu_load_1m(meter: Meter, callback: Sequence[Callable]) -> ObservableGauge:
        return meter.create_observable_gauge(
            name="jvm.system.cpu.load_1m",
            callback=callback,
            description="Average CPU load of the whole system for the last minute as reported by the JVM.",
            unit="{run_queue_item}",
        )


    """
    Recent CPU utilization for the whole system as reported by the JVM
    """
    @staticmethod
    def create_jvm_system_cpu_utilization(meter: Meter, callback: Sequence[Callable]) -> ObservableGauge:
        return meter.create_observable_gauge(
            name="jvm.system.cpu.utilization",
            callback=callback,
            description="Recent CPU utilization for the whole system as reported by the JVM.",
            unit="1",
        )
