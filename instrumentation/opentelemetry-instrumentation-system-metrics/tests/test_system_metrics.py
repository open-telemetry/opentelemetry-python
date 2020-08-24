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
