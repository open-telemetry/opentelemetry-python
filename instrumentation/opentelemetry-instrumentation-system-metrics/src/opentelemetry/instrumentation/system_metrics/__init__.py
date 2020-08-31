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
"""
Instrument to report system (CPU, memory, network) and
process (CPU, memory, garbage collection) metrics. By default, the
following metrics are configured:

"system_cpu_times": ["user", "system", "idle"],
"system_memory": ["total", "available", "used", "free"],
"network_bytes": ["bytes_recv", "bytes_sent"],
"runtime_memory": ["rss", "vms"],
"runtime_cpu": ["user", "system"],


Usage
-----

.. code:: python

    from opentelemetry import metrics
    from opentelemetry.instrumentation.system_metrics import SystemMetrics
    from opentelemetry.sdk.metrics import MeterProvider,
    from opentelemetry.sdk.metrics.export import ConsoleMetricsExporter

    metrics.set_meter_provider(MeterProvider())
    exporter = ConsoleMetricsExporter()
    SystemMetrics(exporter)

    # metrics are collected asynchronously
    input("...")

    # to configure custom metrics
    configuration = {
        "system_memory": ["total", "available", "used", "free", "active", "inactive", "wired"],
        "system_cpu": ["user", "nice", "system", "idle"],
        "network_bytes": ["bytes_recv", "bytes_sent"],
        "runtime_memory": ["rss", "vms"],
        "runtime_cpu": ["user", "system"],
    }
    SystemMetrics(exporter, config=configuration)

API
---
"""

import gc
import os
import typing

import psutil

from opentelemetry import metrics
from opentelemetry.sdk.metrics import SumObserver, ValueObserver
from opentelemetry.sdk.metrics.export import MetricsExporter
from opentelemetry.sdk.metrics.export.controller import PushController


class SystemMetrics:
    # pylint: disable=too-many-statements
    def __init__(
        self,
        exporter: MetricsExporter,
        interval: int = 30,
        labels: typing.Optional[typing.Dict[str, str]] = None,
        config: typing.Optional[typing.Dict[str, typing.List[str]]] = None,
    ):
        self._labels = {} if labels is None else labels
        self.meter = metrics.get_meter(__name__)
        self.controller = PushController(
            meter=self.meter, exporter=exporter, interval=interval
        )
        if config is None:
            self._config = {
                "system_cpu_time": ["idle", "user", "system", "irq"],
                "system_cpu_utilization": ["idle", "user", "system", "irq"],
                "system_memory_usage": ["used", "free", "cached"],
                "system_memory_utilization": ["used", "free", "cached"],
                "system_swap_usage": ["used", "free"],
                "system_swap_utilization": ["used", "free"],
                # system_swap_page_faults: [],
                # system_swap_page_operations: [],
                "system_disk_io": ["read", "write"],
                "system_disk_operations": ["read", "write"],
                "system_disk_time": ["read", "write"],
                "system_disk_merged": ["read", "write"],
                # "system_filesystem_usage": [],
                # "system_filesystem_utilization": [],
                "system_network_dropped_packets": ["transmit", "receive"],
                "system_network_packets": ["transmit", "receive"],
                "system_network_errors": ["transmit", "receive"],
                "system_network_io": ["trasmit", "receive"],
                "system_network_connections": ["family", "type"],
                "runtime_CPython_memory": ["rss", "vms"],
                "runtime_CPython_cpu_time": ["user", "system"],
            }
        else:
            self._config = config

        self._proc = psutil.Process(os.getpid())

        self._system_cpu_time_labels = {}
        self._system_cpu_utilization_labels = {}

        self._system_memory_usage_labels = {}
        self._system_memory_utilization_labels = {}

        self._system_swap_usage_labels = {}
        self._system_swap_utilization_labels = {}
        # self._system_swap_page_faults = {}
        # self._system_swap_page_operations = {}

        self._system_disk_io_labels = {}
        self._system_disk_operations_labels = {}
        self._system_disk_time_labels = {}
        self._system_disk_merged_labels = {}

        # self._system_filesystem_usage_labels = {}
        # self._system_filesystem_utilization_labels = {}

        self._system_network_dropped_packets_labels = {}
        self._system_network_packets_labels = {}
        self._system_network_errors_labels = {}
        self._system_network_io_labels = {}
        self._system_network_connections_labels = {}

        self._runtime_cpython_memory_labels = {}
        self._runtime_cpython_cpu_time_labels = {}
        self._runtime_cpython_gc_count_labels = {}

        # create the label set for each observer once
        for key, value in self._labels.items():
            self._system_cpu_time_labels[key] = value
            self._system_cpu_utilization_labels[key] = value

            self._system_memory_usage_labels[key] = value
            self._system_memory_utilization_labels[key] = value

            self._system_swap_usage_labels[key] = value
            self._system_swap_utilization_labels[key] = value
            # self._system_swap_page_faults[key] = value
            # self._system_swap_page_operations [key] = value

            self._system_disk_io_labels[key] = value
            self._system_disk_operations_labels[key] = value
            self._system_disk_time_labels[key] = value
            self._system_disk_merged_labels[key] = value

            # self._system_filesystem_usage_labels[key] = value
            # self._system_filesystem_utilization_labels[key] = value

            self._system_network_dropped_packets_labels[key] = value
            self._system_network_packets_labels[key] = value
            self._system_network_errors_labels[key] = value
            self._system_network_io_labels[key] = value
            self._system_network_connections_labels[key] = value

        self.meter.register_observer(
            callback=self._get_system_cpu_time,
            name="system.cpu.time",
            description="System CPU time",
            unit="seconds",
            value_type=float,
            observer_type=SumObserver,
        )

        self.meter.register_observer(
            callback=self._get_system_cpu_utilization,
            name="system.cpu.utilization",
            description="System CPU utilization",
            unit="1",
            value_type=float,
            observer_type=ValueObserver,
        )

        self.meter.register_observer(
            callback=self._get_system_memory_usage,
            name="system.memory.usage",
            description="System memory usage",
            unit="bytes",
            value_type=int,
            observer_type=ValueObserver,
        )

        self.meter.register_observer(
            callback=self._get_system_memory_utilization,
            name="system.memory.utilization",
            description="System memory utilization",
            unit="1",
            value_type=float,
            observer_type=ValueObserver,
        )

        self.meter.register_observer(
            callback=self._get_system_swap_usage,
            name="system.swap.usage",
            description="System swap usage",
            unit="pages",
            value_type=int,
            observer_type=ValueObserver,
        )

        self.meter.register_observer(
            callback=self._get_system_swap_utilization,
            name="system.swap.utilization",
            description="System swap utilization",
            unit="1",
            value_type=float,
            observer_type=ValueObserver,
        )

        # self.meter.register_observer(
        #     callback=self._get_system_swap_page_faults,
        #     name="system.swap.page_faults",
        #     description="System swap page faults",
        #     unit="faults",
        #     value_type=int,
        #     observer_type=SumObserver,
        # )

        # self.meter.register_observer(
        #     callback=self._get_system_swap_page_operations,
        #     name="system.swap.page_operations",
        #     description="System swap page operations",
        #     unit="operations",
        #     value_type=int,
        #     observer_type=SumObserver,
        # )

        self.meter.register_observer(
            callback=self._get_system_disk_io,
            name="system.disk.io",
            description="System disk IO",
            unit="bytes",
            value_type=int,
            observer_type=SumObserver,
        )

        self.meter.register_observer(
            callback=self._get_system_disk_operations,
            name="system.disk.operations",
            description="System disk operations",
            unit="operations",
            value_type=int,
            observer_type=SumObserver,
        )

        self.meter.register_observer(
            callback=self._get_system_disk_time,
            name="system.disk.time",
            description="System disk time",
            unit="seconds",
            value_type=float,
            observer_type=SumObserver,
        )

        self.meter.register_observer(
            callback=self._get_system_disk_merged,
            name="system.disk.merged",
            description="System disk merged",
            unit="1",
            value_type=int,
            observer_type=SumObserver,
        )

        # self.meter.register_observer(
        #     callback=self._get_system_filesystem_usage,
        #     name="system.filesystem.usage",
        #     description="System filesystem usage",
        #     unit="bytes",
        #     value_type=int,
        #     observer_type=ValueObserver,
        # )

        # self.meter.register_observer(
        #     callback=self._get_system_filesystem_utilization,
        #     name="system.filesystem.utilization",
        #     description="System filesystem utilization",
        #     unit="1",
        #     value_type=float,
        #     observer_type=ValueObserver,
        # )

        self.meter.register_observer(
            callback=self._get_system_network_dropped_packets,
            name="system.network.dropped_packets",
            description="System network dropped_packets",
            unit="packets",
            value_type=int,
            observer_type=SumObserver,
        )

        self.meter.register_observer(
            callback=self._get_system_network_packets,
            name="system.network.packets",
            description="System network packets",
            unit="packets",
            value_type=int,
            observer_type=SumObserver,
        )

        self.meter.register_observer(
            callback=self._get_system_network_errors,
            name="system.network.errors",
            description="System network errors",
            unit="errors",
            value_type=int,
            observer_type=SumObserver,
        )

        self.meter.register_observer(
            callback=self._get_system_network_io,
            name="system.network.io",
            description="System network io",
            unit="bytes",
            value_type=int,
            observer_type=SumObserver,
        )

        self.meter.register_observer(
            callback=self._get_system_network_connections,
            name="system.network.connections",
            description="System network connections",
            unit="connections",
            value_type=int,
            observer_type=ValueObserver,
        )

        self.meter.register_observer(
            callback=self._get_runtime_cpython_memory,
            name="runtime.CPython.memory",
            description="Runtime CPython memory",
            unit="bytes",
            value_type=int,
            observer_type=ValueObserver,
        )

        self.meter.register_observer(
            callback=self._get_runtime_cpython_cpu_time,
            name="runtime.CPython.cpu_time",
            description="Runtime CPython CPU time",
            unit="seconds",
            value_type=float,
            observer_type=SumObserver,
        )

        self.meter.register_observer(
            callback=self._get_runtime_cpython_memory,
            name="runtime.CPython.gc_count",
            description="Runtime CPython GC count",
            unit="bytes",
            value_type=int,
            observer_type=SumObserver,
        )

    def _get_system_cpu_time(self, observer: metrics.ValueObserver) -> None:
        """Observer callback for system CPU time

        Args:
            observer: the observer to update
        """
        for cpu, times in enumerate(psutil.cpu_times(percpu=True)):
            for metric in self._config["system_cpu_time"]:
                self._system_cpu_time_labels["state"] = metric
                self._system_cpu_time_labels["cpu"] = cpu + 1
                observer.observe(
                    getattr(times, metric), self._system_cpu_time_labels
                )

    def _get_system_cpu_utilization(
        self, observer: metrics.ValueObserver
    ) -> None:
        """Observer callback for system CPU utilization

        Args:
            observer: the observer to update
        """

        for cpu, times_percent in enumerate(
            psutil.cpu_times_percent(percpu=True)
        ):
            for metric in self._config["system_cpu_utilization"]:
                self._system_cpu_utilization_labels["state"] = metric
                self._system_cpu_utilization_labels["cpu"] = cpu + 1
                observer.observe(
                    getattr(times_percent, metric) / 100,
                    self._system_cpu_utilization_labels,
                )

    def _get_system_memory_usage(
        self, observer: metrics.ValueObserver
    ) -> None:
        """Observer callback for memory usage

        Args:
            observer: the observer to update
        """
        virtual_memory = psutil.virtual_memory()
        for metric in self._config["system_memory_usage"]:
            self._system_memory_usage_labels["state"] = metric
            observer.observe(
                getattr(virtual_memory, metric),
                self._system_memory_usage_labels,
            )

    def _get_system_memory_utilization(
        self, observer: metrics.ValueObserver
    ) -> None:
        """Observer callback for memory utilization

        Args:
            observer: the observer to update
        """
        system_memory = psutil.virtual_memory()

        for metric in self._config["system_memory_utilization"]:
            self._system_memory_utilization_labels["state"] = metric
            observer.observe(
                getattr(system_memory, metric) / system_memory.total,
                self._system_memory_utilization_labels,
            )

    def _get_system_swap_usage(self, observer: metrics.ValueObserver) -> None:
        """Observer callback for swap usage

        Args:
            observer: the observer to update
        """
        system_swap = psutil.swap_memory()

        for metric in self._config["system_swap_usage"]:
            self._system_swap_usage_labels["state"] = metric
            observer.observe(
                getattr(system_swap, metric), self._system_swap_usage_labels
            )

    def _get_system_swap_utilization(
        self, observer: metrics.ValueObserver
    ) -> None:
        """Observer callback for swap utilization

        Args:
            observer: the observer to update
        """
        system_swap = psutil.swap_memory()

        for metric in self._config["system_swap_utilization"]:
            self._system_swap_utilization_labels["state"] = metric
            observer.observe(
                getattr(system_swap, metric) / system_swap.total,
                self._system_swap_utilization_labels,
            )

    # TODO Add _get_system_swap_page_faults
    # TODO Add _get_system_swap_page_operations

    def _get_system_disk_io(self, observer: metrics.SumObserver) -> None:
        """Observer callback for disk IO

        Args:
            observer: the observer to update
        """
        for device, counters in psutil.disk_io_counters(perdisk=True).items():
            for metric in self._config["system_disk_io"]:
                self._system_disk_io_labels["device"] = device
                self._system_disk_io_labels["direction"] = metric
                observer.observe(
                    getattr(counters, "{}_bytes".format(metric)),
                    self._system_disk_io_labels,
                )

    def _get_system_disk_operations(
        self, observer: metrics.SumObserver
    ) -> None:
        """Observer callback for disk operations

        Args:
            observer: the observer to update
        """
        for device, counters in psutil.disk_io_counters(perdisk=True).items():
            for metric in self._config["system_disk_operations"]:
                self._system_disk_operations_labels["device"] = device
                self._system_disk_operations_labels["direction"] = metric
                observer.observe(
                    getattr(counters, "{}_count".format(metric)),
                    self._system_disk_operations_labels,
                )

    def _get_system_disk_time(self, observer: metrics.SumObserver) -> None:
        """Observer callback for disk time

        Args:
            observer: the observer to update
        """
        for device, counters in psutil.disk_io_counters(perdisk=True).items():
            for metric in self._config["system_disk_time"]:
                self._system_disk_time_labels["device"] = device
                self._system_disk_time_labels["direction"] = metric
                observer.observe(
                    getattr(counters, "{}_time".format(metric)) / 1000,
                    self._system_disk_time_labels,
                )

    def _get_system_disk_merged(self, observer: metrics.SumObserver) -> None:
        """Observer callback for disk merged operations

        Args:
            observer: the observer to update
        """

        # FIXME The units in the spec is 1, it seems like it should be
        # operations or the value type should be Double

        for device, counters in psutil.disk_io_counters(perdisk=True).items():
            for metric in self._config["system_disk_time"]:
                self._system_disk_merged_labels["device"] = device
                self._system_disk_merged_labels["direction"] = metric
                observer.observe(
                    getattr(counters, "{}_merged_count".format(metric)),
                    self._system_disk_merged_labels,
                )

    # TODO Add _get_system_filesystem_usage
    # TODO Add _get_system_filesystem_utilization
    # TODO Filesystem information can be obtained with os.statvfs in Unix-like
    # OSs, how to do the same in Windows?

    def _get_system_network_dropped_packets(
        self, observer: metrics.SumObserver
    ) -> None:
        """Observer callback for network dropped packets

        Args:
            observer: the observer to update
        """

        for device, counters in psutil.net_io_counters(pernic=True).items():
            for metric in self._config["system_network_dropped_packets"]:
                in_out = {"receive": "in", "transmit": "out"}[metric]
                self._system_network_dropped_packets_labels["device"] = device
                self._system_network_dropped_packets_labels[
                    "direction"
                ] = metric
                observer.observe(
                    getattr(counters, "drop{}".format(in_out)),
                    self._system_network_dropped_packets_labels,
                )

    def _get_system_network_packets(
        self, observer: metrics.SumObserver
    ) -> None:
        """Observer callback for network packets

        Args:
            observer: the observer to update
        """

        for device, counters in psutil.net_io_counters(pernic=True).items():
            for metric in self._config["system_network_dropped_packets"]:
                recv_sent = {"receive": "recv", "transmit": "sent"}[metric]
                self._system_network_packets_labels["device"] = device
                self._system_network_packets_labels["direction"] = metric
                observer.observe(
                    getattr(counters, "packets_{}".format(recv_sent)),
                    self._system_network_packets_labels,
                )

    def _get_system_network_errors(
        self, observer: metrics.SumObserver
    ) -> None:
        """Observer callback for network errors

        Args:
            observer: the observer to update
        """
        for device, counters in psutil.net_io_counters(pernic=True).items():
            for metric in self._config["system_network_errors"]:
                in_out = {"receive": "in", "transmit": "out"}[metric]
                self._system_network_errors_labels["device"] = device
                self._system_network_errors_labels["direction"] = metric
                observer.observe(
                    getattr(counters, "err{}".format(in_out)),
                    self._system_network_errors_labels,
                )

    def _get_system_network_io(self, observer: metrics.SumObserver) -> None:
        """Observer callback for network IO

        Args:
            observer: the observer to update
        """

        for device, counters in psutil.net_io_counters(pernic=True).items():
            for metric in self._config["system_network_dropped_packets"]:
                recv_sent = {"receive": "recv", "transmit": "sent"}[metric]
                self._system_network_io_labels["device"] = device
                self._system_network_io_labels["direction"] = metric
                observer.observe(
                    getattr(counters, "bytes_{}".format(recv_sent)),
                    self._system_network_io_labels,
                )

    def _get_system_network_connections(
        self, observer: metrics.ValueObserver
    ) -> None:
        """Observer callback for network connections

        Args:
            observer: the observer to update
        """
        # TODO How to find the device identifier for a particular
        # connection?
        for net_connection in psutil.net_connections():
            for metric in self._config["system_network_connections"]:
                self._system_network_connections_labels["protocol"] = {
                    1: "tcp",
                    2: "udp",
                }[net_connection.type.value]
                self._system_network_connections_labels[
                    "state"
                ] = net_connection.status
                observer.observe(
                    getattr(net_connection, metric),
                    self._system_network_connections_labels,
                )

    def _get_runtime_cpython_memory(
        self, observer: metrics.ValueObserver
    ) -> None:
        """Observer callback for runtime CPyhton memory

        Args:
            observer: the observer to update
        """
        proc_memory = self._proc.memory_info()
        for metric in self._config["runtime_CPython_memory"]:
            self._runtime_cpython_memory_labels["type"] = metric
            observer.observe(
                getattr(proc_memory, metric),
                self._runtime_cpython_memory_labels,
            )

    def _get_runtime_cpython_cpu_time(
        self, observer: metrics.SumObserver
    ) -> None:
        """Observer callback for runtime CPython CPU time

        Args:
            observer: the observer to update
        """
        proc_cpu = self._proc.cpu_times()
        for metric in self._config["runtime_CPython_cpu_time"]:
            self._runtime_cpython_cpu_time_labels["type"] = metric
            observer.observe(
                getattr(proc_cpu, metric),
                self._runtime_cpython_cpu_time_labels,
            )

    def _get_runtime_cpython_gc_count(
        self, observer: metrics.SumObserver
    ) -> None:
        """Observer callback for CPython garbage collection

        Args:
            observer: the observer to update
        """
        for index, count in enumerate(gc.get_count()):
            self._runtime_cpython_gc_count_labels["count"] = str(index)
            observer.observe(count, self._runtime_cpython_gc_count_labels)
