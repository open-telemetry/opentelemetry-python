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
from contextlib import contextmanager
from unittest import mock

from opentelemetry import metrics


# pylint: disable=no-self-use
class TestMeter(unittest.TestCase):
    def setUp(self):
        self.meter = metrics.DefaultMeter()

    def test_record_batch(self):
        counter = metrics.Counter()
        label_set = metrics.LabelSet()
        self.meter.record_batch(label_set, ((counter, 1),))

    def test_create_metric(self):
        metric = self.meter.create_metric("", "", "", float, metrics.Counter)
        self.assertIsInstance(metric, metrics.DefaultMetric)

    def test_get_label_set(self):
        metric = self.meter.get_label_set({})
        self.assertIsInstance(metric, metrics.DefaultLabelSet)


class TestMetrics(unittest.TestCase):
    def test_default(self):
        default = metrics.DefaultMetric()
        default_ls = metrics.DefaultLabelSet()
        handle = default.get_handle(default_ls)
        self.assertIsInstance(handle, metrics.DefaultMetricHandle)

    def test_counter(self):
        counter = metrics.Counter()
        label_set = metrics.LabelSet()
        handle = counter.get_handle(label_set)
        self.assertIsInstance(handle, metrics.CounterHandle)

    def test_counter_add(self):
        counter = metrics.Counter()
        label_set = metrics.LabelSet()
        counter.add(1, label_set)

    def test_measure(self):
        measure = metrics.Measure()
        label_set = metrics.LabelSet()
        handle = measure.get_handle(label_set)
        self.assertIsInstance(handle, metrics.MeasureHandle)

    def test_measure_record(self):
        measure = metrics.Measure()
        label_set = metrics.LabelSet()
        measure.record(1, label_set)

    def test_default_handle(self):
        metrics.DefaultMetricHandle()

    def test_counter_handle(self):
        handle = metrics.CounterHandle()
        handle.add(1)

    def test_measure_handle(self):
        handle = metrics.MeasureHandle()
        handle.record(1)


@contextmanager
# type: ignore
def patch_metrics_globals(meter=None, meter_factory=None):
    """Mock metrics._METER and metrics._METER_FACTORY.

    This prevents previous changes to these values from affecting the code in
    this scope, and prevents changes in this scope from leaking out and
    affecting other tests.
    """
    with mock.patch("opentelemetry.metrics._METER", meter):
        with mock.patch("opentelemetry.metrics._METER_FACTORY", meter_factory):
            yield


class TestGlobals(unittest.TestCase):
    def test_meter_default_factory(self):
        """Check that the default meter is a DefaultMeter."""
        with patch_metrics_globals():
            meter = metrics.meter()
            self.assertIsInstance(meter, metrics.DefaultMeter)
            # Check that we don't create a new instance on each call
            self.assertIs(meter, metrics.meter())

    def test_meter_custom_factory(self):
        """Check that we use the provided factory for custom global meters."""
        mock_meter = mock.Mock(metrics.Meter)
        with patch_metrics_globals(meter_factory=lambda _: mock_meter):
            meter = metrics.meter()
            self.assertIs(meter, mock_meter)
