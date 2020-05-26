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
process (CPU, memory, garbage collection) metrics.

Usage
-----

.. code:: python

    from opentelemetry.ext.system_metrics import SystemMetrics
    from opentelemetry.sdk.metrics.export import ConsoleMetricsExporter

    exporter = ConsoleMetricsExporter()
    SystemMetrics(exporter)

    # metrics are collected asynchronously
    input("...")

API
---
"""

import gc
import os
import typing

import psutil

from opentelemetry import metrics
from opentelemetry.sdk.metrics.export import MetricsExporter
from opentelemetry.sdk.metrics.export.controller import PushController


class SystemMetrics:
    def __init__(
        self,
        exporter: MetricsExporter,
        interval: int = 30,
        labels: typing.Optional[typing.Dict[str, str]] = None,
    ):
        self._labels = {} if labels is None else labels
        self.meter = metrics.get_meter(__name__)
        self.controller = PushController(
            meter=self.meter, exporter=exporter, interval=interval
        )
        self._proc = psutil.Process(os.getpid())
        self._system_memory_labels = {}
        self._system_cpu_labels = {}
        self._network_bytes_labels = {}
        self._runtime_memory_labels = {}
        self._runtime_gc_labels = {}
        # create the label set for each observer once
        for key, value in self._labels.items():
            self._system_memory_labels[key] = value
            self._system_cpu_labels[key] = value
            self._network_bytes_labels[key] = value
            self._runtime_memory_labels[key] = value
            self._runtime_gc_labels[key] = value

        self.meter.register_observer(
            callback=self._get_system_memory,
            name="system.mem",
            description="System memory",
            unit="bytes",
            value_type=int,
            label_keys=self._labels.keys(),
        )

        self.meter.register_observer(
            callback=self._get_system_cpu,
            name="system.cpu",
            description="System CPU",
            unit="seconds",
            value_type=float,
            label_keys=self._labels.keys(),
        )

        self.meter.register_observer(
            callback=self._get_network_bytes,
            name="system.net.bytes",
            description="System network bytes",
            unit="bytes",
            value_type=int,
            label_keys=self._labels.keys(),
        )

        self.meter.register_observer(
            callback=self._get_runtime_memory,
            name="runtime.python.mem",
            description="Runtime memory",
            unit="bytes",
            value_type=int,
            label_keys=self._labels.keys(),
        )

        self.meter.register_observer(
            callback=self._get_runtime_gc_count,
            name="runtime.python.gc.count",
            description="Runtime: gc objects",
            unit="objects",
            value_type=int,
            label_keys=self._labels.keys(),
        )

    def _get_system_memory(self, observer: metrics.Observer) -> None:
        """Observer callback for memory available

        Args:
            observer: the observer to update
        """
        system_memory = psutil.virtual_memory()
        _metrics = [
            "total",
            "available",
            "used",
            "free",
        ]
        for metric in _metrics:
            self._system_memory_labels["type"] = metric
            observer.observe(
                getattr(system_memory, metric), self._system_memory_labels
            )

    def _get_system_cpu(self, observer: metrics.Observer) -> None:
        """Observer callback for system cpu

        Args:
            observer: the observer to update
        """
        _metrics = [
            "user",
            "system",
            "idle",
        ]
        cpu_times = psutil.cpu_times()
        for metric in _metrics:
            self._system_cpu_labels["type"] = metric
            observer.observe(
                getattr(cpu_times, metric), self._system_cpu_labels
            )

    def _get_network_bytes(self, observer: metrics.Observer) -> None:
        """Observer callback for network bytes

        Args:
            observer: the observer to update
        """
        _metrics = [
            "bytes_recv",
            "bytes_sent",
        ]
        net_io = psutil.net_io_counters()
        for metric in _metrics:
            self._network_bytes_labels["type"] = metric
            observer.observe(
                getattr(net_io, metric), self._network_bytes_labels
            )

    def _get_runtime_memory(self, observer: metrics.Observer) -> None:
        """Observer callback for runtime memory

        Args:
            observer: the observer to update
        """
        _metrics = [
            "rss",
            "vms",
        ]
        proc_memory = self._proc.memory_info()
        for metric in _metrics:
            self._runtime_memory_labels["type"] = metric
            observer.observe(
                getattr(proc_memory, metric), self._runtime_memory_labels
            )

    def _get_runtime_gc_count(self, observer: metrics.Observer) -> None:
        """Observer callback for garbage collection

        Args:
            observer: the observer to update
        """
        gc_count = gc.get_count()
        for index, count in enumerate(gc_count):
            self._runtime_gc_labels["count"] = str(index)
            observer.observe(count, self._runtime_gc_labels)
