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

import random
import time
from functools import partial
from unittest.mock import Mock

from opentelemetry.sdk._metrics.export import (
    MetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk._metrics.point import Gauge, Metric, Sum
from opentelemetry.sdk.resources import Resource
from opentelemetry.test.concurrency_test import ConcurrencyTestBase
from opentelemetry.util._time import _time_ns


class FakeProvider:
    def __init__(self, readers):
        self._metric_readers = readers

    def register_periodic_reader(self, periodic_reader):
        periodic_reader._register_meter_provider(self)


class FakeMetricsExporter(MetricExporter):
    def __init__(self, wait=0):
        self.wait = wait
        self.metrics = []

    def export(self, metrics):
        time.sleep(self.wait)
        self.metrics += metrics
        return random.choice([True, False])

    def shutdown(self):
        pass


metrics_list = [
    Metric(
        name="sum_name",
        attributes={},
        description="",
        instrumentation_info=None,
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
        instrumentation_info=None,
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
        r = PeriodicExportingMetricReader(FakeMetricsExporter())
        self.assertEqual(r._export_interval_millis, 60000)
        self.assertEqual(r._export_timeout_millis, 30000)

    def _create_periodic_reader(self, metrics, exporter, wait=0):
        mock = Mock()

        def _collect():
            time.sleep(wait)
            return metrics

        mock.collect = _collect
        provider = FakeProvider([mock])
        pmr = PeriodicExportingMetricReader(exporter)
        provider.register_periodic_reader(pmr)
        return pmr

    def test_force_flush(self):
        exporter = FakeMetricsExporter(wait=1)
        pmr = self._create_periodic_reader(metrics_list, exporter)
        ret = pmr.force_flush()
        self.assertTrue(ret)
        self.assertEqual(exporter.metrics, metrics_list)

    def test_force_flush_timeout(self):
        exporter = FakeMetricsExporter(wait=1)
        pmr = self._create_periodic_reader(metrics_list, exporter, 70)
        ret = pmr.force_flush(10)
        self.assertFalse(ret)

    def test_force_flush_mutiple_times(self):
        exporter = FakeMetricsExporter()
        pmr = self._create_periodic_reader(metrics_list, exporter, wait=5)

        self.run_with_many_threads(partial(pmr.force_flush, 8000))

        self.assertTrue(exporter.metrics, metrics_list)

    def test_shutdown(self):
        exporter = FakeMetricsExporter()

        pmr = self._create_periodic_reader([], exporter)
        pmr.shutdown()
        self.assertEqual(exporter.metrics, [])
        self.assertTrue(pmr._shutdown)

    def test_shutdown_multiple_times(self):
        pmr = self._create_periodic_reader([], Mock())
        with self.assertLogs(level="WARNING") as w:
            self.run_with_many_threads(pmr.shutdown)
            self.assertTrue("Can't shutdown multiple times", w.output[0])
