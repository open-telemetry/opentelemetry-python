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

from collections import namedtuple
from unittest import mock

from opentelemetry import metrics
from opentelemetry.instrumentation.system_metrics import SystemMetrics
from opentelemetry.test.test_base import TestBase


class TestSystemMetrics(TestBase):
    def setUp(self):
        super().setUp()
        self.memory_metrics_exporter.clear()

    def test_system_metrics_constructor(self):
        # ensure the observers have been registered
        meter = metrics.get_meter(__name__)
        with mock.patch("opentelemetry.metrics.get_meter") as mock_get_meter:
            mock_get_meter.return_value = meter
            SystemMetrics(self.memory_metrics_exporter)

        self.assertEqual(len(meter.observers), 18)

        observer_names = [
            "system.cpu.time",
            "system.cpu.utilization",
            "system.memory.usage",
            "system.memory.utilization",
            "system.swap.usage",
            "system.swap.utilization",
            "system.disk.io",
            "system.disk.operations",
            "system.disk.time",
            "system.disk.merged",
            "system.network.dropped_packets",
            "system.network.packets",
            "system.network.errors",
            "system.network.io",
            "system.network.connections",
            "runtime.cpython.memory",
            "runtime.cpython.cpu_time",
            "runtime.cpython.gc_count",
        ]

        for observer in meter.observers:
            self.assertIn(observer.name, observer_names)
            observer_names.remove(observer.name)

    def _assert_metrics(self, observer_name, system_metrics, expected):
        system_metrics.controller.tick()
        assertions = 0
        for (
            metric
        ) in (
            self.memory_metrics_exporter._exported_metrics  # pylint: disable=protected-access
        ):
            if (
                metric.labels in expected
                and metric.instrument.name == observer_name
            ):
                self.assertEqual(
                    metric.aggregator.checkpoint, expected[metric.labels],
                )
                assertions += 1
        self.assertEqual(len(expected), assertions)

    def _test_metrics(self, observer_name, expected):
        meter = self.meter_provider.get_meter(__name__)

        with mock.patch("opentelemetry.metrics.get_meter") as mock_get_meter:
            mock_get_meter.return_value = meter
            system_metrics = SystemMetrics(self.memory_metrics_exporter)
            self._assert_metrics(observer_name, system_metrics, expected)

    @mock.patch("psutil.cpu_times")
    def test_system_cpu_time(self, mock_cpu_times):
        CPUTimes = namedtuple("CPUTimes", ["idle", "user", "system", "irq"])
        mock_cpu_times.return_value = [
            CPUTimes(idle=1.2, user=3.4, system=5.6, irq=7.8),
            CPUTimes(idle=1.2, user=3.4, system=5.6, irq=7.8),
        ]

        expected = {
            (("cpu", 1), ("state", "idle"),): 1.2,
            (("cpu", 1), ("state", "user"),): 3.4,
            (("cpu", 1), ("state", "system"),): 5.6,
            (("cpu", 1), ("state", "irq"),): 7.8,
            (("cpu", 2), ("state", "idle"),): 1.2,
            (("cpu", 2), ("state", "user"),): 3.4,
            (("cpu", 2), ("state", "system"),): 5.6,
            (("cpu", 2), ("state", "irq"),): 7.8,
        }
        self._test_metrics("system.cpu.time", expected)

    @mock.patch("psutil.cpu_times_percent")
    def test_system_cpu_utilization(self, mock_cpu_times_percent):
        CPUTimesPercent = namedtuple(
            "CPUTimesPercent", ["idle", "user", "system", "irq"]
        )
        mock_cpu_times_percent.return_value = [
            CPUTimesPercent(idle=1.2, user=3.4, system=5.6, irq=7.8),
            CPUTimesPercent(idle=1.2, user=3.4, system=5.6, irq=7.8),
        ]

        expected = {
            (("cpu", 1), ("state", "idle"),): 1.2 / 100,
            (("cpu", 1), ("state", "user"),): 3.4 / 100,
            (("cpu", 1), ("state", "system"),): 5.6 / 100,
            (("cpu", 1), ("state", "irq"),): 7.8 / 100,
            (("cpu", 2), ("state", "idle"),): 1.2 / 100,
            (("cpu", 2), ("state", "user"),): 3.4 / 100,
            (("cpu", 2), ("state", "system"),): 5.6 / 100,
            (("cpu", 2), ("state", "irq"),): 7.8 / 100,
        }
        self._test_metrics("system.cpu.utilization", expected)

    @mock.patch("psutil.virtual_memory")
    def test_system_memory_usage(self, mock_virtual_memory):
        VirtualMemory = namedtuple(
            "VirtualMemory", ["used", "free", "cached", "total"]
        )
        mock_virtual_memory.return_value = VirtualMemory(
            used=1, free=2, cached=3, total=4
        )

        expected = {
            (("state", "used"),): 1,
            (("state", "free"),): 2,
            (("state", "cached"),): 3,
        }
        self._test_metrics("system.memory.usage", expected)

    @mock.patch("psutil.virtual_memory")
    def test_system_memory_utilization(self, mock_virtual_memory):
        VirtualMemory = namedtuple(
            "VirtualMemory", ["used", "free", "cached", "total"]
        )
        mock_virtual_memory.return_value = VirtualMemory(
            used=1, free=2, cached=3, total=4
        )

        expected = {
            (("state", "used"),): 1 / 4,
            (("state", "free"),): 2 / 4,
            (("state", "cached"),): 3 / 4,
        }
        self._test_metrics("system.memory.utilization", expected)

    @mock.patch("psutil.swap_memory")
    def test_system_swap_usage(self, mock_swap_memory):
        SwapMemory = namedtuple(
            "SwapMemory", ["used", "free", "total"]
        )
        mock_swap_memory.return_value = SwapMemory(
            used=1, free=2, total=3
        )

        expected = {
            (("state", "used"),): 1,
            (("state", "free"),): 2,
        }
        self._test_metrics("system.swap.usage", expected)

    @mock.patch("psutil.swap_memory")
    def test_system_swap_utilization(self, mock_swap_memory):
        SwapMemory = namedtuple(
            "SwapMemory", ["used", "free", "total"]
        )
        mock_swap_memory.return_value = SwapMemory(
            used=1, free=2, total=3
        )

        expected = {
            (("state", "used"),): 1 / 3,
            (("state", "free"),): 2 / 3,
        }
        self._test_metrics("system.swap.utilization", expected)

    @mock.patch("psutil.disk_io_counters")
    def test_system_disk_io(self, mock_disk_io_counters):
        DiskIO = namedtuple(
            "DiskIO", [
                "read_count",
                "write_count",
                "read_bytes",
                "write_bytes",
                "read_time",
                "write_time",
                "read_merged_count",
                "write_merged_count",
            ]
        )
        mock_disk_io_counters.return_value = {
            "sda": DiskIO(
                read_count=1,
                write_count=2,
                read_bytes=3,
                write_bytes=4,
                read_time=5,
                write_time=6,
                read_merged_count=7,
                write_merged_count=8,
            ),
            "sdb": DiskIO(
                read_count=9,
                write_count=10,
                read_bytes=11,
                write_bytes=12,
                read_time=13,
                write_time=14,
                read_merged_count=15,
                write_merged_count=16,
            ),
        }

        expected = {
            (("device", "sda"), ("direction", "read"),): 3,
            (("device", "sda"), ("direction", "write"),): 4,
            (("device", "sdb"), ("direction", "read"),): 11,
            (("device", "sdb"), ("direction", "write"),): 12,
        }
        self._test_metrics("system.disk.io", expected)

    @mock.patch("psutil.disk_io_counters")
    def test_system_disk_operations(self, mock_disk_io_counters):
        DiskIO = namedtuple(
            "DiskIO", [
                "read_count",
                "write_count",
                "read_bytes",
                "write_bytes",
                "read_time",
                "write_time",
                "read_merged_count",
                "write_merged_count",
            ]
        )
        mock_disk_io_counters.return_value = {
            "sda": DiskIO(
                read_count=1,
                write_count=2,
                read_bytes=3,
                write_bytes=4,
                read_time=5,
                write_time=6,
                read_merged_count=7,
                write_merged_count=8,
            ),
            "sdb": DiskIO(
                read_count=9,
                write_count=10,
                read_bytes=11,
                write_bytes=12,
                read_time=13,
                write_time=14,
                read_merged_count=15,
                write_merged_count=16,
            ),
        }

        expected = {
            (("device", "sda"), ("direction", "read"),): 1,
            (("device", "sda"), ("direction", "write"),): 2,
            (("device", "sdb"), ("direction", "read"),): 9,
            (("device", "sdb"), ("direction", "write"),): 10,
        }
        self._test_metrics("system.disk.operations", expected)

    @mock.patch("psutil.disk_io_counters")
    def test_system_disk_time(self, mock_disk_io_counters):
        DiskIO = namedtuple(
            "DiskIO", [
                "read_count",
                "write_count",
                "read_bytes",
                "write_bytes",
                "read_time",
                "write_time",
                "read_merged_count",
                "write_merged_count",
            ]
        )
        mock_disk_io_counters.return_value = {
            "sda": DiskIO(
                read_count=1,
                write_count=2,
                read_bytes=3,
                write_bytes=4,
                read_time=5,
                write_time=6,
                read_merged_count=7,
                write_merged_count=8,
            ),
            "sdb": DiskIO(
                read_count=9,
                write_count=10,
                read_bytes=11,
                write_bytes=12,
                read_time=13,
                write_time=14,
                read_merged_count=15,
                write_merged_count=16,
            ),
        }

        expected = {
            (("device", "sda"), ("direction", "read"),): 5 / 1000,
            (("device", "sda"), ("direction", "write"),): 6 / 1000,
            (("device", "sdb"), ("direction", "read"),): 13 / 1000,
            (("device", "sdb"), ("direction", "write"),): 14 / 1000,
        }
        self._test_metrics("system.disk.time", expected)
