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
from opentelemetry.sdk.metrics import export


class TestMeter(unittest.TestCase):
    def test_extends_api(self):
        meter = metrics.Meter()
        self.assertIsInstance(meter, metrics_api.Meter)

    def test_collect(self):
        meter = metrics.Meter()
        batcher_mock = mock.Mock()
        meter.batcher = batcher_mock
        label_keys = ("key1",)
        counter = metrics.Counter(
            "name", "desc", "unit", float, meter, label_keys
        )
        kvp = {"key1": "value1"}
        label_set = meter.get_label_set(kvp)
        counter.add(label_set, 1.0)
        meter.metrics.add(counter)
        meter.collect()
        self.assertTrue(batcher_mock.process.called)

    def test_collect_no_metrics(self):
        meter = metrics.Meter()
        batcher_mock = mock.Mock()
        meter.batcher = batcher_mock
        meter.collect()
        self.assertFalse(batcher_mock.process.called)

    def test_collect_disabled_metric(self):
        meter = metrics.Meter()
        batcher_mock = mock.Mock()
        meter.batcher = batcher_mock
        label_keys = ("key1",)
        counter = metrics.Counter(
            "name", "desc", "unit", float, meter, label_keys, False
        )
        kvp = {"key1": "value1"}
        label_set = meter.get_label_set(kvp)
        counter.add(label_set, 1.0)
        meter.metrics.add(counter)
        meter.collect()
        self.assertFalse(batcher_mock.process.called)

    def test_record_batch(self):
        meter = metrics.Meter()
        label_keys = ("key1",)
        counter = metrics.Counter(
            "name", "desc", "unit", float, meter, label_keys
        )
        kvp = {"key1": "value1"}
        label_set = meter.get_label_set(kvp)
        record_tuples = [(counter, 1.0)]
        meter.record_batch(label_set, record_tuples)
        self.assertEqual(counter.get_handle(label_set).aggregator.current, 1.0)

    def test_record_batch_multiple(self):
        meter = metrics.Meter()
        label_keys = ("key1", "key2", "key3")
        kvp = {"key1": "value1", "key2": "value2", "key3": "value3"}
        label_set = meter.get_label_set(kvp)
        counter = metrics.Counter(
            "name", "desc", "unit", float, meter, label_keys
        )
        gauge = metrics.Gauge("name", "desc", "unit", int, meter, label_keys)
        measure = metrics.Measure(
            "name", "desc", "unit", float, meter, label_keys
        )
        record_tuples = [(counter, 1.0), (gauge, 5), (measure, 3.0)]
        meter.record_batch(label_set, record_tuples)
        self.assertEqual(counter.get_handle(label_set).aggregator.current, 1.0)
        self.assertEqual(gauge.get_handle(label_set).aggregator.current, 5.0)
        # TODO: Fix when aggregator implemented for measure
        self.assertEqual(measure.get_handle(label_set).aggregator.current, 3.0)

    def test_record_batch_exists(self):
        meter = metrics.Meter()
        label_keys = ("key1",)
        kvp = {"key1": "value1"}
        label_set = meter.get_label_set(kvp)
        counter = metrics.Counter(
            "name", "desc", "unit", float, meter, label_keys
        )
        counter.add(1.0, label_set)
        handle = counter.get_handle(label_set)
        record_tuples = [(counter, 1.0)]
        meter.record_batch(label_set, record_tuples)
        self.assertEqual(counter.get_handle(label_set), handle)
        self.assertEqual(handle.aggregator.current, 2.0)

    def test_create_metric(self):
        meter = metrics.Meter()
        counter = meter.create_metric(
            "name", "desc", "unit", int, metrics.Counter, ()
        )
        self.assertTrue(isinstance(counter, metrics.Counter))
        self.assertEqual(counter.value_type, int)
        self.assertEqual(counter.name, "name")

    def test_create_gauge(self):
        meter = metrics.Meter()
        gauge = meter.create_metric(
            "name", "desc", "unit", float, metrics.Gauge, ()
        )
        self.assertTrue(isinstance(gauge, metrics.Gauge))
        self.assertEqual(gauge.value_type, float)
        self.assertEqual(gauge.name, "name")

    def test_create_measure(self):
        meter = metrics.Meter()
        measure = meter.create_metric(
            "name", "desc", "unit", float, metrics.Measure, ()
        )
        self.assertTrue(isinstance(measure, metrics.Measure))
        self.assertEqual(measure.value_type, float)
        self.assertEqual(measure.name, "name")

    def test_get_label_set(self):
        meter = metrics.Meter()
        kvp = {"environment": "staging", "a": "z"}
        label_set = meter.get_label_set(kvp)
        kvp2 = {"environment": "staging", "a": "z"}
        label_set2 = meter.get_label_set(kvp)
        labels = set([label_set, label_set2])
        self.assertEqual(len(labels), 1)

    def test_get_label_set_empty(self):
        meter = metrics.Meter()
        kvp = {}
        label_set = meter.get_label_set(kvp)
        self.assertEqual(label_set, metrics.EMPTY_LABEL_SET)


class TestMetric(unittest.TestCase):
    def test_get_handle(self):
        meter = metrics.Meter()
        metric_types = [metrics.Counter, metrics.Gauge, metrics.Measure]
        for _type in metric_types:
            metric = _type("name", "desc", "unit", int, meter, ("key",))
            kvp = {"key": "value"}
            label_set = meter.get_label_set(kvp)
            handle = metric.get_handle(label_set)
            self.assertEqual(metric.handles.get(label_set), handle)


class TestCounter(unittest.TestCase):
    def test_add(self):
        meter = metrics.Meter()
        metric = metrics.Counter("name", "desc", "unit", int, meter, ("key",))
        kvp = {"key": "value"}
        label_set = meter.get_label_set(kvp)
        handle = metric.get_handle(label_set)
        metric.add(3, label_set)
        metric.add(2, label_set)
        self.assertEqual(handle.aggregator.current, 5)


class TestGauge(unittest.TestCase):
    def test_set(self):
        meter = metrics.Meter()
        metric = metrics.Gauge("name", "desc", "unit", int, meter, ("key",))
        kvp = {"key": "value"}
        label_set = meter.get_label_set(kvp)
        handle = metric.get_handle(label_set)
        metric.set(3, label_set)
        self.assertEqual(handle.aggregator.current, 3)
        metric.set(2, label_set)
        # TODO: Fix once other aggregators implemented
        self.assertEqual(handle.aggregator.current, 5)


class TestMeasure(unittest.TestCase):
    def test_record(self):
        meter = metrics.Meter()
        metric = metrics.Measure("name", "desc", "unit", int, meter, ("key",))
        kvp = {"key": "value"}
        label_set = meter.get_label_set(kvp)
        handle = metric.get_handle(label_set)
        metric.record(3, label_set)
        # TODO: Fix once other aggregators implemented
        self.assertEqual(handle.aggregator.current, 3)


class TestCounterHandle(unittest.TestCase):
    def test_add(self):
        aggregator = export.aggregate.CounterAggregator()
        handle = metrics.CounterHandle(int, True, False, False, aggregator)
        handle.add(3)
        self.assertEqual(handle.aggregator.current, 3)

    def test_add_disabled(self):
        aggregator = export.aggregate.CounterAggregator()
        handle = metrics.CounterHandle(int, False, False, False, aggregator)
        handle.add(3)
        self.assertEqual(handle.aggregator.current, 0)

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_add_monotonic(self, logger_mock):
        aggregator = export.aggregate.CounterAggregator()
        handle = metrics.CounterHandle(int, True, True, False, aggregator)
        handle.add(-3)
        self.assertEqual(handle.aggregator.current, 0)
        self.assertTrue(logger_mock.warning.called)

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_add_incorrect_type(self, logger_mock):
        aggregator = export.aggregate.CounterAggregator()
        handle = metrics.CounterHandle(int, True, False, False, aggregator)
        handle.add(3.0)
        self.assertEqual(handle.aggregator.current, 0)
        self.assertTrue(logger_mock.warning.called)

    @mock.patch("opentelemetry.sdk.metrics.time_ns")
    def test_update(self, time_mock):
        aggregator = export.aggregate.CounterAggregator()
        handle = metrics.CounterHandle(int, True, False, False, aggregator)
        time_mock.return_value = 123
        handle.update(4.0)
        self.assertEqual(handle.last_update_timestamp, 123)
        self.assertEqual(handle.aggregator.current, 4.0)


# TODO: fix tests once aggregator implemented
class TestGaugeHandle(unittest.TestCase):
    def test_set(self):
        aggregator = export.aggregate.CounterAggregator()
        handle = metrics.GaugeHandle(int, True, False, False, aggregator)
        handle.set(3)
        self.assertEqual(handle.aggregator.current, 3)

    def test_set_disabled(self):
        aggregator = export.aggregate.CounterAggregator()
        handle = metrics.GaugeHandle(int, False, False, False, aggregator)
        handle.set(3)
        self.assertEqual(handle.aggregator.current, 0)

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_set_monotonic(self, logger_mock):
        aggregator = export.aggregate.CounterAggregator()
        handle = metrics.GaugeHandle(int, True, True, False, aggregator)
        handle.set(-3)
        self.assertEqual(handle.aggregator.current, 0)
        self.assertTrue(logger_mock.warning.called)

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_set_incorrect_type(self, logger_mock):
        aggregator = export.aggregate.CounterAggregator()
        handle = metrics.GaugeHandle(int, True, False, False, aggregator)
        handle.set(3.0)
        self.assertEqual(handle.aggregator.current, 0)
        self.assertTrue(logger_mock.warning.called)

    @mock.patch("opentelemetry.sdk.metrics.time_ns")
    def test_update(self, time_mock):
        aggregator = export.aggregate.CounterAggregator()
        handle = metrics.GaugeHandle(int, True, False, False, aggregator)
        time_mock.return_value = 123
        handle.update(4.0)
        self.assertEqual(handle.last_update_timestamp, 123)
        self.assertEqual(handle.aggregator.current, 4.0)


# TODO: fix tests once aggregator implemented
class TestMeasureHandle(unittest.TestCase):
    def test_record(self):
        aggregator = export.aggregate.CounterAggregator()
        handle = metrics.MeasureHandle(int, False, False, False, aggregator)
        handle.record(3)
        self.assertEqual(handle.aggregator.current, 0)

    def test_record_disabled(self):
        aggregator = export.aggregate.CounterAggregator()
        handle = metrics.MeasureHandle(int, False, False, False, aggregator)
        handle.record(3)
        self.assertEqual(handle.aggregator.current, 0)

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_record_monotonic(self, logger_mock):
        aggregator = export.aggregate.CounterAggregator()
        handle = metrics.MeasureHandle(int, True, False, True, aggregator)
        handle.record(-3)
        self.assertEqual(handle.aggregator.current, 0)
        self.assertTrue(logger_mock.warning.called)

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_record_incorrect_type(self, logger_mock):
        aggregator = export.aggregate.CounterAggregator()
        handle = metrics.MeasureHandle(int, True, False, False, aggregator)
        handle.record(3.0)
        self.assertEqual(handle.aggregator.current, 0)
        self.assertTrue(logger_mock.warning.called)

    @mock.patch("opentelemetry.sdk.metrics.time_ns")
    def test_update(self, time_mock):
        aggregator = export.aggregate.CounterAggregator()
        handle = metrics.MeasureHandle(int, True, False, False, aggregator)
        time_mock.return_value = 123
        handle.update(4.0)
        self.assertEqual(handle.last_update_timestamp, 123)
        self.assertEqual(handle.aggregator.current, 4.0)
