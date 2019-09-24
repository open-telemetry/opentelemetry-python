# Copyright 2019, OpenTelemetry Authors
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

import unittest

from opentelemetry import metrics


# pylint: disable=no-self-use
class TestMeter(unittest.TestCase):
    def setUp(self):
        self.meter = metrics.Meter()

    def test_record_batch(self):
        self.meter.record_batch((), ())

    def test_create_metric(self):
        self.meter.create_metric("", "", "", float, metrics.Counter)


class TestMetrics(unittest.TestCase):
    def test_counter(self):
        counter = metrics.Counter()
        counter.get_handle(("test"))

    def test_gauge(self):
        gauge = metrics.Gauge()
        gauge.get_handle(("test"))

    def test_measure(self):
        measure = metrics.Measure()
        measure.get_handle(("test"))

    def test_remove_handle(self):
        counter = metrics.Counter()
        counter.remove_handle(("test"))

    def test_clear(self):
        counter = metrics.Counter()
        counter.clear()

    def test_counter_handle(self):
        handle = metrics.CounterHandle()
        handle.add(1)

    def test_gauge_handle(self):
        handle = metrics.GaugeHandle()
        handle.set(1)

    def test_measure_handle(self):
        handle = metrics.MeasureHandle()
        handle.record(1)
