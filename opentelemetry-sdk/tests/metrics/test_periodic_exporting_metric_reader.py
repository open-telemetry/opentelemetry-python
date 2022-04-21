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

import time
from unittest.mock import Mock

from flaky import flaky

from opentelemetry.sdk._metrics.export import (
    MetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk._metrics.point import Gauge, Metric, Sum
from opentelemetry.sdk.resources import Resource
from opentelemetry.test.concurrency_test import ConcurrencyTestBase
from opentelemetry.util._time import _time_ns


class FakeMetricsExporter(MetricExporter):
    def __init__(self, wait=0):
        self.wait = wait
        self.metrics = []
        self._shutdown = False

    def export(self, metrics):
        time.sleep(self.wait)
        self.metrics.extend(metrics)
        return True

    def shutdown(self):
        self._shutdown = True


metrics_list = [
    Metric(
        name="sum_name",
        attributes={},
        description="",
        instrumentation_scope=None,
        resource=Resource.create(),
        unit="",
        point=Sum(
            start_time_unix_nano=_time_ns(),
            time_unix_nano=_time_ns(),
            value=2,
            aggregation_temporality=1,
            is_monotonic=True,
        ),
    ),
    Metric(
        name="gauge_name",
        attributes={},
        description="",
        instrumentation_scope=None,
        resource=Resource.create(),
        unit="",
        point=Gauge(
            time_unix_nano=_time_ns(),
            value=2,
        ),
    ),
]


class TestPeriodicExportingMetricReader(ConcurrencyTestBase):
    def test_defaults(self):
        pmr = PeriodicExportingMetricReader(FakeMetricsExporter())
        self.assertEqual(pmr._export_interval_millis, 60000)
        self.assertEqual(pmr._export_timeout_millis, 30000)
        pmr.shutdown()

    def _create_periodic_reader(
        self, metrics, exporter, collect_wait=0, interval=60000
    ):

        pmr = PeriodicExportingMetricReader(exporter, interval)

        def _collect(reader, temp):
            time.sleep(collect_wait)
            pmr._receive_metrics(metrics)

        pmr._set_collect_callback(_collect)
        return pmr

    def test_ticker_called(self):
        collect_mock = Mock()
        pmr = PeriodicExportingMetricReader(Mock(), 1)
        pmr._set_collect_callback(collect_mock)
        time.sleep(0.1)
        self.assertTrue(collect_mock.assert_called_once)
        pmr.shutdown()

    @flaky(max_runs=3, min_passes=1)
    def test_ticker_collects_metrics(self):
        exporter = FakeMetricsExporter()

        pmr = self._create_periodic_reader(
            metrics_list, exporter, interval=100
        )
        time.sleep(0.15)
        self.assertEqual(exporter.metrics, metrics_list)
        pmr.shutdown()

    def test_shutdown(self):
        exporter = FakeMetricsExporter()

        pmr = self._create_periodic_reader([], exporter)
        pmr.shutdown()
        self.assertEqual(exporter.metrics, [])
        self.assertTrue(pmr._shutdown)
        self.assertTrue(exporter._shutdown)

    def test_shutdown_multiple_times(self):
        pmr = self._create_periodic_reader([], Mock())
        with self.assertLogs(level="WARNING") as w:
            self.run_with_many_threads(pmr.shutdown)
            self.assertTrue("Can't shutdown multiple times", w.output[0])
        pmr.shutdown()
