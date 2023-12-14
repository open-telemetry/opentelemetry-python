
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
    Number of classes currently loaded
    """
    @staticmethod
  
    def create_jvm_class_count(meter: Meter) -> UpDownCounter:
  
        return meter.create_up_down_counter(
            name="jvm.class.count",
            description="Number of classes currently loaded.",
            unit="{class}",
        )


    """
    Number of classes loaded since JVM start
    """
    @staticmethod
  
    def create_jvm_class_loaded(meter: Meter) -> Counter:
  
        return meter.create_counter(
            name="jvm.class.loaded",
            description="Number of classes loaded since JVM start.",
            unit="{class}",
        )


    """
    Number of classes unloaded since JVM start
    """
    @staticmethod
  
    def create_jvm_class_unloaded(meter: Meter) -> Counter:
  
        return meter.create_counter(
            name="jvm.class.unloaded",
            description="Number of classes unloaded since JVM start.",
            unit="{class}",
        )


    """
    Number of processors available to the Java virtual machine
    """
    @staticmethod
  
    def create_jvm_cpu_count(meter: Meter) -> UpDownCounter:
  
        return meter.create_up_down_counter(
            name="jvm.cpu.count",
            description="Number of processors available to the Java virtual machine.",
            unit="{cpu}",
        )


    """
    Recent CPU utilization for the process as reported by the JVM
    """
    @staticmethod
  
    def create_jvm_cpu_recent_utilization(meter: Meter, callback: Sequence[Callable]) -> ObservableGauge:
  
        return meter.create_observable_gauge(
            name="jvm.cpu.recent_utilization",
            callback=callback,
            description="Recent CPU utilization for the process as reported by the JVM.",
            unit="1",
        )


    """
    CPU time used by the process as reported by the JVM
    """
    @staticmethod
  
    def create_jvm_cpu_time(meter: Meter) -> Counter:
  
        return meter.create_counter(
            name="jvm.cpu.time",
            description="CPU time used by the process as reported by the JVM.",
            unit="s",
        )


    """
    Duration of JVM garbage collection actions
    """
    @staticmethod
  
    def create_jvm_gc_duration(meter: Meter) -> Histogram:
  
        return meter.create_histogram(
            name="jvm.gc.duration",
            description="Duration of JVM garbage collection actions.",
            unit="s",
        )


    """
    Measure of memory committed
    """
    @staticmethod
  
    def create_jvm_memory_committed(meter: Meter) -> UpDownCounter:
  
        return meter.create_up_down_counter(
            name="jvm.memory.committed",
            description="Measure of memory committed.",
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
    Measure of max obtainable memory
    """
    @staticmethod
  
    def create_jvm_memory_limit(meter: Meter) -> UpDownCounter:
  
        return meter.create_up_down_counter(
            name="jvm.memory.limit",
            description="Measure of max obtainable memory.",
            unit="By",
        )


    """
    Measure of memory used
    """
    @staticmethod
  
    def create_jvm_memory_usage(meter: Meter) -> UpDownCounter:
  
        return meter.create_up_down_counter(
            name="jvm.memory.usage",
            description="Measure of memory used.",
            unit="By",
        )


    """
    Measure of memory used, as measured after the most recent garbage collection event on this pool
    """
    @staticmethod
  
    def create_jvm_memory_usage_after_last_gc(meter: Meter) -> UpDownCounter:
  
        return meter.create_up_down_counter(
            name="jvm.memory.usage_after_last_gc",
            description="Measure of memory used, as measured after the most recent garbage collection event on this pool.",
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


    """
    Number of executing platform threads
    """
    @staticmethod
  
    def create_jvm_thread_count(meter: Meter) -> UpDownCounter:
  
        return meter.create_up_down_counter(
            name="jvm.thread.count",
            description="Number of executing platform threads.",
            unit="{thread}",
        )

