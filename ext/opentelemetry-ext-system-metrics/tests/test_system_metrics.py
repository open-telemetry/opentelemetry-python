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
from opentelemetry.ext.system_metrics import SystemMetrics
from opentelemetry.sdk.metrics import Observer
from opentelemetry.test.test_base import TestBase


class TestSystemMetrics(TestBase):
    def test_system_metrics_constructor(self):
        # ensure the observers have been registered
        meter = metrics.get_meter(__name__)
        with mock.patch("opentelemetry.metrics.get_meter") as mock_get_meter:
            mock_get_meter.return_value = meter
            SystemMetrics(self.memory_metrics_exporter)
        self.assertEqual(len(meter.observers), 5)
        observer_names = [
            "system.mem",
            "system.cpu",
            "system.net.bytes",
            "runtime.python.mem",
            "runtime.python.gc.count",
        ]
        for observer in meter.observers:
            self.assertIn(observer.name, observer_names)
            observer_names.remove(observer.name)

    @mock.patch("psutil.cpu_times")
    def test_system_cpu(self, mock_cpu_times):
        CPUTimes = namedtuple("CPUTimes", ["user", "nice", "system", "idle"])
        mock_cpu_times.return_value = CPUTimes(
            user=332277.48, nice=0.0, system=309836.43, idle=6724698.94
        )

        meter = self.meter_provider.get_meter(__name__)
        with mock.patch("opentelemetry.metrics.get_meter") as mock_get_meter:
            mock_get_meter.return_value = meter
            system_metrics = SystemMetrics(self.memory_metrics_exporter)
            # pylint: disable=protected-access
            observer = Observer(
                None, "test-name", "test-desc", "test-unit", float, meter,
            )
            system_metrics._get_system_cpu(observer)
            self.assertEqual(
                observer.aggregators[(("type", "user"),)].current, 332277.48
            )
            self.assertEqual(
                observer.aggregators[(("type", "nice"),)].current, 0.0
            )
            self.assertEqual(
                observer.aggregators[(("type", "system"),)].current, 309836.43
            )
            self.assertEqual(
                observer.aggregators[(("type", "idle"),)].current, 6724698.94
            )

    @mock.patch("psutil.virtual_memory")
    def test_system_memory(self, mock_virtual_memory):
        VirtualMemory = namedtuple(
            "VirtualMemory",
            [
                "total",
                "available",
                "percent",
                "used",
                "free",
                "active",
                "inactive",
                "wired",
            ],
        )
        mock_virtual_memory.return_value = VirtualMemory(
            total=17179869184,
            available=5520928768,
            percent=67.9,
            used=10263990272,
            free=266964992,
            active=5282459648,
            inactive=5148700672,
            wired=4981530624,
        )

        meter = self.meter_provider.get_meter(__name__)
        with mock.patch("opentelemetry.metrics.get_meter") as mock_get_meter:
            mock_get_meter.return_value = meter
            system_metrics = SystemMetrics(self.memory_metrics_exporter)
            # pylint: disable=protected-access
            observer = Observer(
                None, "test-name", "test-desc", "test-unit", int, meter,
            )
            system_metrics._get_system_memory(observer)
            self.assertEqual(
                observer.aggregators[(("type", "total"),)].current, 17179869184
            )
            self.assertEqual(
                observer.aggregators[(("type", "available"),)].current,
                5520928768,
            )
            self.assertEqual(
                observer.aggregators[(("type", "used"),)].current, 10263990272
            )
            self.assertEqual(
                observer.aggregators[(("type", "free"),)].current, 266964992
            )
            self.assertEqual(
                observer.aggregators[(("type", "active"),)].current, 5282459648
            )
            self.assertEqual(
                observer.aggregators[(("type", "inactive"),)].current,
                5148700672,
            )
            self.assertEqual(
                observer.aggregators[(("type", "wired"),)].current, 4981530624
            )
            self.assertNotIn((("type", "percent"),), observer.aggregators)

    @mock.patch("psutil.net_io_counters")
    def test_network_bytes(self, mock_net_io_counters):
        NetworkIO = namedtuple(
            "NetworkIO",
            ["bytes_sent", "bytes_recv", "packets_recv", "packets_sent"],
        )
        mock_net_io_counters.return_value = NetworkIO(
            bytes_sent=23920188416,
            bytes_recv=46798894080,
            packets_sent=53127118,
            packets_recv=53205738,
        )

        meter = self.meter_provider.get_meter(__name__)
        with mock.patch("opentelemetry.metrics.get_meter") as mock_get_meter:
            mock_get_meter.return_value = meter
            system_metrics = SystemMetrics(self.memory_metrics_exporter)
            # pylint: disable=protected-access
            observer = Observer(
                None, "test-name", "test-desc", "test-unit", int, meter,
            )
            system_metrics._get_network_bytes(observer)
            self.assertEqual(
                observer.aggregators[(("type", "bytes_recv"),)].current,
                46798894080,
            )
            self.assertEqual(
                observer.aggregators[(("type", "bytes_sent"),)].current,
                23920188416,
            )

    def test_runtime_memory(self):
        meter = self.meter_provider.get_meter(__name__)
        with mock.patch("opentelemetry.metrics.get_meter") as mock_get_meter:
            mock_get_meter.return_value = meter
            system_metrics = SystemMetrics(self.memory_metrics_exporter)

            with mock.patch.object(
                system_metrics._proc,  # pylint: disable=protected-access
                "memory_info",
            ) as mock_runtime_memory:
                RuntimeMemory = namedtuple(
                    "RuntimeMemory", ["rss", "vms", "pfaults", "pageins"],
                )
                mock_runtime_memory.return_value = RuntimeMemory(
                    rss=9777152, vms=4385665024, pfaults=2631, pageins=49
                )
                observer = Observer(
                    None, "test-name", "test-desc", "test-unit", int, meter,
                )
                # pylint: disable=protected-access
                system_metrics._get_runtime_memory(observer)
                self.assertEqual(
                    observer.aggregators[(("type", "rss"),)].current, 9777152,
                )
                self.assertEqual(
                    observer.aggregators[(("type", "vms"),)].current,
                    4385665024,
                )
                self.assertEqual(
                    observer.aggregators[(("type", "pfaults"),)].current, 2631,
                )
                self.assertEqual(
                    observer.aggregators[(("type", "pageins"),)].current, 49,
                )

    @mock.patch("gc.get_count")
    def test_runtime_gc_count(self, mock_gc):
        mock_gc.return_value = [
            100,  # gen0
            50,  # gen1
            10,  # gen2
        ]
        meter = self.meter_provider.get_meter(__name__)
        with mock.patch("opentelemetry.metrics.get_meter") as mock_get_meter:
            mock_get_meter.return_value = meter
            system_metrics = SystemMetrics(self.memory_metrics_exporter)
            observer = Observer(
                None, "test-name", "test-desc", "test-unit", int, meter,
            )
            # pylint: disable=protected-access
            system_metrics._get_runtime_gc_count(observer)
            self.assertEqual(
                observer.aggregators[(("count", "0"),)].current, 100
            )
            self.assertEqual(
                observer.aggregators[(("count", "1"),)].current, 50
            )
            self.assertEqual(
                observer.aggregators[(("count", "2"),)].current, 10
            )
