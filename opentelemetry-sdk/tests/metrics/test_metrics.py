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
from unittest import mock

from opentelemetry import metrics as metrics_api
from opentelemetry.sdk import metrics


class TestMeter(unittest.TestCase):
    def test_extends_api(self):
        meter = metrics.Meter()
        self.assertIsInstance(meter, metrics_api.Meter)

    def test_record_batch(self):
        meter = metrics.Meter()
        label_keys = ["key1"]
        label_values = ("value1")
        float_counter = metrics.FloatCounter(
            "name",
            "desc",
            "unit",
            label_keys,
        )
        record_tuples = [(float_counter, 1.0)]
        meter.record_batch(label_values, record_tuples)
        self.assertEqual(float_counter.get_handle(label_values).data, 1.0)

    def test_record_batch_exists(self):
        meter = metrics.Meter()
        label_keys = ["key1"]
        label_values = ("value1")
        float_counter = metrics.FloatCounter(
            "name",
            "desc",
            "unit",
            label_keys
        )
        handle = float_counter.get_handle(label_values)
        handle.update(1.0)
        record_tuples = [(float_counter, 1.0)]
        meter.record_batch(label_values, record_tuples)
        self.assertEqual(float_counter.get_handle(label_values), handle)
        self.assertEqual(handle.data, 2.0)

    def test_create_counter(self):
        meter = metrics.Meter()
        counter = meter.create_counter(
            "name",
            "desc",
            "unit",
            int,
            []
        )
        self.assertTrue(isinstance(counter, metrics.IntCounter))
        self.assertEqual(counter.name, "name")

    def test_create_gauge(self):
        meter = metrics.Meter()
        gauge = meter.create_gauge(
            "name",
            "desc",
            "unit",
            float,
            []
        )
        self.assertTrue(isinstance(gauge, metrics.FloatGauge))
        self.assertEqual(gauge.name, "name")

    def test_create_measure(self):
        meter = metrics.Meter()
        measure = meter.create_measure(
            "name",
            "desc",
            "unit",
            float,
            []
        )
        self.assertTrue(isinstance(measure, metrics.FloatMeasure))
        self.assertEqual(measure.name, "name")


class TestMetric(unittest.TestCase):
    def test_get_handle(self):
        metric_types = [metrics.FloatCounter,
                        metrics.IntCounter,
                        metrics.FloatGauge,
                        metrics.IntGauge,
                        metrics.FloatMeasure,
                        metrics.IntMeasure]
        for _type in metric_types:
            metric = _type(
            "name",
            "desc",
            "unit",
            ["key"]
            )
            label_values = ("value")
            handle = metric.get_handle(label_values)
            self.assertEqual(metric.handles.get(label_values), handle)


class TestCounterHandle(unittest.TestCase):
    def test_update(self):
        handle = metrics.CounterHandle(
            float,
            False,
            False
        )
        handle.update(2.0)
        self.assertEqual(handle.data, 2.0)

    def test_add(self):
        handle = metrics.CounterHandle(
            int,
            False,
            False
        )
        handle._add(3)
        self.assertEqual(handle.data, 3)

    @mock.patch('opentelemetry.sdk.metrics.logger')
    def test_add_disabled(self, logger_mock):
        handle = metrics.CounterHandle(
            int,
            True,
            False
        )
        handle._add(3)
        self.assertEqual(handle.data, 0)
        logger_mock.warning.assert_called()

    @mock.patch('opentelemetry.sdk.metrics.logger')
    def test_add_monotonic(self, logger_mock):
        handle = metrics.CounterHandle(
            int,
            False,
            False
        )
        handle._add(-3)
        self.assertEqual(handle.data, 0)
        logger_mock.warning.assert_called()

    @mock.patch('opentelemetry.sdk.metrics.logger')
    def test_add_incorrect_type(self, logger_mock):
        handle = metrics.CounterHandle(
            int,
            False,
            False
        )
        handle._add(3.0)
        self.assertEqual(handle.data, 0)
        logger_mock.warning.assert_called()


class TestGaugeHandle(unittest.TestCase):
    def test_update(self):
        handle = metrics.GaugeHandle(
            float,
            False,
            False
        )
        handle.update(2.0)
        self.assertEqual(handle.data, 2.0)

    def test_set(self):
        handle = metrics.GaugeHandle(
            int,
            False,
            False
        )
        handle._set(3)
        self.assertEqual(handle.data, 3)

    @mock.patch('opentelemetry.sdk.metrics.logger')
    def test_set_disabled(self, logger_mock):
        handle = metrics.GaugeHandle(
            int,
            True,
            False
        )
        handle._set(3)
        self.assertEqual(handle.data, 0)
        logger_mock.warning.assert_called()

    @mock.patch('opentelemetry.sdk.metrics.logger')
    def test_set_monotonic(self, logger_mock):
        handle = metrics.GaugeHandle(
            int,
            False,
            True
        )
        handle._set(-3)
        self.assertEqual(handle.data, 0)
        logger_mock.warning.assert_called()

    @mock.patch('opentelemetry.sdk.metrics.logger')
    def test_set_incorrect_type(self, logger_mock):
        handle = metrics.GaugeHandle(
            int,
            False,
            False
        )
        handle._set(3.0)
        self.assertEqual(handle.data, 0)
        logger_mock.warning.assert_called()


class TestMeasureHandle(unittest.TestCase):
    def test_update(self):
        handle = metrics.MeasureHandle(
            float,
            False,
            False
        )
        handle.update(2.0)
        self.assertEqual(handle.data, 0)

    def test_record(self):
        handle = metrics.MeasureHandle(
            int,
            False,
            False
        )
        handle._record(3)
        self.assertEqual(handle.data, 0)

    @mock.patch('opentelemetry.sdk.metrics.logger')
    def test_record_disabled(self, logger_mock):
        handle = metrics.MeasureHandle(
            int,
            True,
            False
        )
        handle._record(3)
        self.assertEqual(handle.data, 0)
        logger_mock.warning.assert_called()

    @mock.patch('opentelemetry.sdk.metrics.logger')
    def test_record_monotonic(self, logger_mock):
        handle = metrics.MeasureHandle(
            int,
            False,
            True
        )
        handle._record(-3)
        self.assertEqual(handle.data, 0)
        logger_mock.warning.assert_called()

    @mock.patch('opentelemetry.sdk.metrics.logger')
    def test_record_incorrect_type(self, logger_mock):
        handle = metrics.MeasureHandle(
            int,
            False,
            False
        )
        handle._record(3.0)
        self.assertEqual(handle.data, 0)
        logger_mock.warning.assert_called()
