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
import random
from collections import namedtuple
from functools import partial
from unittest.mock import Mock

from opentelemetry.sdk._metrics.export import PeriodicExportingMetricReader
from opentelemetry.test.concurrency_test import ConcurrencyTestBase


class FakeMeasurementConsumer:
    def __init__(self, metrics=None, wait=0):
        self.metrics = metrics
        self.wait = wait

    def collect(self):
        time.sleep(self.wait)
        return self.metrics


class FakeMetricsExporter:
    def __init__(self, wait=0):
        self.wait = wait
        self.metrics = []

    def export(self, metrics):
        time.sleep(self.wait)
        self.metrics += metrics
        return random.choice([True, False])

    def shutdown(self):
        pass


Metric = namedtuple("Metric", ["type", "value"])


class TestPeriodicExportingMetricReader(ConcurrencyTestBase):
    def test_defaults(self):
        r = PeriodicExportingMetricReader(FakeMetricsExporter())
        self.assertEqual(r._export_interval_millis, 60000)
        self.assertEqual(r._export_timeout_millis, 30000)

    def test_force_flush(self):
        consumer_metrics = [Metric("Sum", 2), Metric("Histogram", 3)]
        consumer = FakeMeasurementConsumer(consumer_metrics)
        exporter = FakeMetricsExporter(wait=1)
        pmr = PeriodicExportingMetricReader(exporter)
        pmr._set_measurement_consumer(consumer)
        ret = pmr.force_flush()
        self.assertTrue(ret)
        self.assertEqual(exporter.metrics, consumer_metrics)

    def test_force_flush_timeout(self):
        con = FakeMeasurementConsumer(wait=70)
        exporter = FakeMetricsExporter(wait=1)
        pmr = PeriodicExportingMetricReader(exporter)
        pmr._set_measurement_consumer(con)
        ret = pmr.force_flush(10)
        self.assertFalse(ret)

    def test_force_flush_mutiple_times(self):
        metrics = {Metric("Gauge", 5), Metric("Sum", 10)}
        exporter = FakeMetricsExporter()
        pmr = PeriodicExportingMetricReader(exporter)
        pmr._set_measurement_consumer(
            FakeMeasurementConsumer(metrics=metrics, wait=5)
        )

        self.run_with_many_threads(partial(pmr.force_flush, 8000))

        self.assertTrue(exporter.metrics, metrics)

    def test_shutdown(self):
        exporter = FakeMetricsExporter()
        pmr = PeriodicExportingMetricReader(exporter)
        pmr._set_measurement_consumer(FakeMeasurementConsumer(metrics=[]))
        pmr.shutdown()
        self.assertEqual(exporter.metrics, [])
        self.assertTrue(pmr._shutdown)

    def test_shutdown_multiple_times(self):
        pmr = PeriodicExportingMetricReader(Mock())
        pmr._set_measurement_consumer(Mock())
        with self.assertLogs(level="WARNING") as w:
            self.run_with_many_threads(pmr.shutdown)
            self.assertTrue("Can't shutdown multiple times", w.output[0])
