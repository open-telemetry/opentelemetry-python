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

@staticmethod
def create_system_cpu_frequency(meter: Meter, callback: Sequence[Callable]) -> ObservableGauge:
    """Reports the current frequency of the CPU in Hz"""
    return meter.create_observable_gauge(
        name="system.cpu.frequency",
        callback=callback,
        description="Reports the current frequency of the CPU in Hz",
        unit="{Hz}",
    )


@staticmethod
def create_system_cpu_logical_count(meter: Meter) -> UpDownCounter:
    """Reports the number of logical (virtual) processor cores created by the operating system to manage multitasking"""
    return meter.create_up_down_counter(
        name="system.cpu.logical.count",
        description="Reports the number of logical (virtual) processor cores created by the operating system to manage multitasking",
        unit="{cpu}",
    )


@staticmethod
def create_system_cpu_physical_count(meter: Meter) -> UpDownCounter:
    """Reports the number of actual physical processor cores on the hardware"""
    return meter.create_up_down_counter(
        name="system.cpu.physical.count",
        description="Reports the number of actual physical processor cores on the hardware",
        unit="{cpu}",
    )


@staticmethod
def create_system_cpu_time(meter: Meter) -> Counter:
    """Seconds each logical CPU spent on each mode"""
    return meter.create_counter(
        name="system.cpu.time",
        description="Seconds each logical CPU spent on each mode",
        unit="s",
    )


@staticmethod
def create_system_cpu_utilization(meter: Meter, callback: Sequence[Callable]) -> ObservableGauge:
    """Difference in system.cpu.time since the last measurement, divided by the elapsed time and number of logical CPUs"""
    return meter.create_observable_gauge(
        name="system.cpu.utilization",
        callback=callback,
        description="Difference in system.cpu.time since the last measurement, divided by the elapsed time and number of logical CPUs",
        unit="1",
    )


@staticmethod
def create_system_disk_io(meter: Meter) -> Counter:
    """"""
    return meter.create_counter(
        name="system.disk.io",
        description="",
        unit="By",
    )


@staticmethod
def create_system_disk_io_time(meter: Meter) -> Counter:
    """Time disk spent activated"""
    return meter.create_counter(
        name="system.disk.io_time",
        description="Time disk spent activated",
        unit="s",
    )


@staticmethod
def create_system_disk_merged(meter: Meter) -> Counter:
    """"""
    return meter.create_counter(
        name="system.disk.merged",
        description="",
        unit="{operation}",
    )


@staticmethod
def create_system_disk_operation_time(meter: Meter) -> Counter:
    """Sum of the time each operation took to complete"""
    return meter.create_counter(
        name="system.disk.operation_time",
        description="Sum of the time each operation took to complete",
        unit="s",
    )


@staticmethod
def create_system_disk_operations(meter: Meter) -> Counter:
    """"""
    return meter.create_counter(
        name="system.disk.operations",
        description="",
        unit="{operation}",
    )


@staticmethod
def create_system_filesystem_usage(meter: Meter) -> UpDownCounter:
    """"""
    return meter.create_up_down_counter(
        name="system.filesystem.usage",
        description="",
        unit="By",
    )


@staticmethod
def create_system_filesystem_utilization(meter: Meter, callback: Sequence[Callable]) -> ObservableGauge:
    """"""
    return meter.create_observable_gauge(
        name="system.filesystem.utilization",
        callback=callback,
        description="",
        unit="1",
    )


@staticmethod
def create_system_linux_memory_available(meter: Meter) -> UpDownCounter:
    """An estimate of how much memory is available for starting new applications, without causing swapping"""
    return meter.create_up_down_counter(
        name="system.linux.memory.available",
        description="An estimate of how much memory is available for starting new applications, without causing swapping",
        unit="By",
    )


@staticmethod
def create_system_memory_limit(meter: Meter) -> UpDownCounter:
    """Total memory available in the system"""
    return meter.create_up_down_counter(
        name="system.memory.limit",
        description="Total memory available in the system.",
        unit="By",
    )


@staticmethod
def create_system_memory_usage(meter: Meter) -> UpDownCounter:
    """Reports memory in use by state"""
    return meter.create_up_down_counter(
        name="system.memory.usage",
        description="Reports memory in use by state.",
        unit="By",
    )


@staticmethod
def create_system_memory_utilization(meter: Meter, callback: Sequence[Callable]) -> ObservableGauge:
    """"""
    return meter.create_observable_gauge(
        name="system.memory.utilization",
        callback=callback,
        description="",
        unit="1",
    )


@staticmethod
def create_system_network_connections(meter: Meter) -> UpDownCounter:
    """"""
    return meter.create_up_down_counter(
        name="system.network.connections",
        description="",
        unit="{connection}",
    )


@staticmethod
def create_system_network_dropped(meter: Meter) -> Counter:
    """Count of packets that are dropped or discarded even though there was no error"""
    return meter.create_counter(
        name="system.network.dropped",
        description="Count of packets that are dropped or discarded even though there was no error",
        unit="{packet}",
    )


@staticmethod
def create_system_network_errors(meter: Meter) -> Counter:
    """Count of network errors detected"""
    return meter.create_counter(
        name="system.network.errors",
        description="Count of network errors detected",
        unit="{error}",
    )


@staticmethod
def create_system_network_io(meter: Meter) -> Counter:
    """"""
    return meter.create_counter(
        name="system.network.io",
        description="",
        unit="By",
    )


@staticmethod
def create_system_network_packets(meter: Meter) -> Counter:
    """"""
    return meter.create_counter(
        name="system.network.packets",
        description="",
        unit="{packet}",
    )


@staticmethod
def create_system_paging_faults(meter: Meter) -> Counter:
    """"""
    return meter.create_counter(
        name="system.paging.faults",
        description="",
        unit="{fault}",
    )


@staticmethod
def create_system_paging_operations(meter: Meter) -> Counter:
    """"""
    return meter.create_counter(
        name="system.paging.operations",
        description="",
        unit="{operation}",
    )


@staticmethod
def create_system_paging_usage(meter: Meter) -> UpDownCounter:
    """Unix swap or windows pagefile usage"""
    return meter.create_up_down_counter(
        name="system.paging.usage",
        description="Unix swap or windows pagefile usage",
        unit="By",
    )


@staticmethod
def create_system_paging_utilization(meter: Meter, callback: Sequence[Callable]) -> ObservableGauge:
    """"""
    return meter.create_observable_gauge(
        name="system.paging.utilization",
        callback=callback,
        description="",
        unit="1",
    )


@staticmethod
def create_system_processes_count(meter: Meter) -> UpDownCounter:
    """Total number of processes in each state"""
    return meter.create_up_down_counter(
        name="system.processes.count",
        description="Total number of processes in each state",
        unit="{process}",
    )


@staticmethod
def create_system_processes_created(meter: Meter) -> Counter:
    """Total number of processes created over uptime of the host"""
    return meter.create_counter(
        name="system.processes.created",
        description="Total number of processes created over uptime of the host",
        unit="{process}",
    )

