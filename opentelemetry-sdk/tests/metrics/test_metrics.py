# Copyright 2020, OpenTelemetry Authors
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
from opentelemetry.sdk import metrics, resources
from opentelemetry.sdk.metrics import export


class TestMeterProvider(unittest.TestCase):
    def test_resource(self):
        resource = mock.Mock(spec=resources.Resource)
        meter_provider = metrics.MeterProvider(resource=resource)
        meter = meter_provider.get_meter(__name__)
        self.assertIs(meter.resource, resource)

    def test_resource_empty(self):
        meter_provider = metrics.MeterProvider()
        meter = meter_provider.get_meter(__name__)
        # pylint: disable=protected-access
        self.assertIs(meter.resource, resources._EMPTY_RESOURCE)


class TestMeter(unittest.TestCase):
    def test_extends_api(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        self.assertIsInstance(meter, metrics_api.Meter)

    def test_collect(self):
        meter = metrics.MeterProvider().get_meter(__name__)
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
        meter = metrics.MeterProvider().get_meter(__name__)
        batcher_mock = mock.Mock()
        meter.batcher = batcher_mock
        meter.collect()
        self.assertFalse(batcher_mock.process.called)

    def test_collect_disabled_metric(self):
        meter = metrics.MeterProvider().get_meter(__name__)
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

    def test_collect_observers(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        batcher_mock = mock.Mock()
        meter.batcher = batcher_mock

        def callback(observer):
            self.assertIsInstance(observer, metrics_api.Observer)
            observer.observe(45, meter.get_label_set(()))

        observer = metrics.Observer(
            callback, "name", "desc", "unit", int, meter, (), True
        )

        meter.observers.add(observer)
        meter.collect()
        self.assertTrue(batcher_mock.process.called)

    def test_record_batch(self):
        meter = metrics.MeterProvider().get_meter(__name__)
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
        meter = metrics.MeterProvider().get_meter(__name__)
        label_keys = ("key1", "key2", "key3")
        kvp = {"key1": "value1", "key2": "value2", "key3": "value3"}
        label_set = meter.get_label_set(kvp)
        counter = metrics.Counter(
            "name", "desc", "unit", float, meter, label_keys
        )
        measure = metrics.Measure(
            "name", "desc", "unit", float, meter, label_keys
        )
        record_tuples = [(counter, 1.0), (measure, 3.0)]
        meter.record_batch(label_set, record_tuples)
        self.assertEqual(counter.get_handle(label_set).aggregator.current, 1.0)
        self.assertEqual(
            measure.get_handle(label_set).aggregator.current,
            (3.0, 3.0, 3.0, 1),
        )

    def test_record_batch_exists(self):
        meter = metrics.MeterProvider().get_meter(__name__)
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
        resource = mock.Mock(spec=resources.Resource)
        meter_provider = metrics.MeterProvider(resource=resource)
        meter = meter_provider.get_meter(__name__)
        counter = meter.create_metric(
            "name", "desc", "unit", int, metrics.Counter, ()
        )
        self.assertIsInstance(counter, metrics.Counter)
        self.assertEqual(counter.value_type, int)
        self.assertEqual(counter.name, "name")
        self.assertIs(counter.meter.resource, resource)

    def test_create_measure(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        measure = meter.create_metric(
            "name", "desc", "unit", float, metrics.Measure, ()
        )
        self.assertIsInstance(measure, metrics.Measure)
        self.assertEqual(measure.value_type, float)
        self.assertEqual(measure.name, "name")

    def test_register_observer(self):
        meter = metrics.MeterProvider().get_meter(__name__)

        callback = mock.Mock()

        observer = meter.register_observer(
            callback, "name", "desc", "unit", int, (), True
        )

        self.assertIsInstance(observer, metrics_api.Observer)
        self.assertEqual(len(meter.observers), 1)

        self.assertEqual(observer.callback, callback)
        self.assertEqual(observer.name, "name")
        self.assertEqual(observer.description, "desc")
        self.assertEqual(observer.unit, "unit")
        self.assertEqual(observer.value_type, int)
        self.assertEqual(observer.label_keys, ())
        self.assertTrue(observer.enabled)

    def test_get_label_set(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        kvp = {"environment": "staging", "a": "z"}
        label_set = meter.get_label_set(kvp)
        label_set2 = meter.get_label_set(kvp)
        labels = set([label_set, label_set2])
        self.assertEqual(len(labels), 1)

    def test_get_label_set_empty(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        kvp = {}
        label_set = meter.get_label_set(kvp)
        self.assertEqual(label_set, metrics.EMPTY_LABEL_SET)


class TestMetric(unittest.TestCase):
    def test_get_handle(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        metric_types = [metrics.Counter, metrics.Measure]
        for _type in metric_types:
            metric = _type("name", "desc", "unit", int, meter, ("key",))
            kvp = {"key": "value"}
            label_set = meter.get_label_set(kvp)
            handle = metric.get_handle(label_set)
            self.assertEqual(metric.handles.get(label_set), handle)


class TestCounter(unittest.TestCase):
    def test_add(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        metric = metrics.Counter("name", "desc", "unit", int, meter, ("key",))
        kvp = {"key": "value"}
        label_set = meter.get_label_set(kvp)
        handle = metric.get_handle(label_set)
        metric.add(3, label_set)
        metric.add(2, label_set)
        self.assertEqual(handle.aggregator.current, 5)


class TestMeasure(unittest.TestCase):
    def test_record(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        metric = metrics.Measure("name", "desc", "unit", int, meter, ("key",))
        kvp = {"key": "value"}
        label_set = meter.get_label_set(kvp)
        handle = metric.get_handle(label_set)
        values = (37, 42, 7)
        for val in values:
            metric.record(val, label_set)
        self.assertEqual(
            handle.aggregator.current,
            (min(values), max(values), sum(values), len(values)),
        )


class TestObserver(unittest.TestCase):
    def test_observe(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        observer = metrics.Observer(
            None, "name", "desc", "unit", int, meter, ("key",), True
        )
        kvp = {"key": "value"}
        label_set = meter.get_label_set(kvp)
        values = (37, 42, 7, 21)
        for val in values:
            observer.observe(val, label_set)
        self.assertEqual(
            observer.aggregators[label_set].mmsc.current,
            (min(values), max(values), sum(values), len(values)),
        )

        self.assertEqual(observer.aggregators[label_set].current, values[-1])

    def test_observe_disabled(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        observer = metrics.Observer(
            None, "name", "desc", "unit", int, meter, ("key",), False
        )
        kvp = {"key": "value"}
        label_set = meter.get_label_set(kvp)
        observer.observe(37, label_set)
        self.assertEqual(len(observer.aggregators), 0)

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_observe_incorrect_type(self, logger_mock):
        meter = metrics.MeterProvider().get_meter(__name__)
        observer = metrics.Observer(
            None, "name", "desc", "unit", int, meter, ("key",), True
        )
        kvp = {"key": "value"}
        label_set = meter.get_label_set(kvp)
        observer.observe(37.0, label_set)
        self.assertEqual(len(observer.aggregators), 0)
        self.assertTrue(logger_mock.warning.called)

    def test_run(self):
        meter = metrics.MeterProvider().get_meter(__name__)

        callback = mock.Mock()
        observer = metrics.Observer(
            callback, "name", "desc", "unit", int, meter, (), True
        )

        self.assertTrue(observer.run())
        callback.assert_called_once_with(observer)

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_run_exception(self, logger_mock):
        meter = metrics.MeterProvider().get_meter(__name__)

        callback = mock.Mock()
        callback.side_effect = Exception("We have a problem!")

        observer = metrics.Observer(
            callback, "name", "desc", "unit", int, meter, (), True
        )

        self.assertFalse(observer.run())
        self.assertTrue(logger_mock.warning.called)


class TestCounterHandle(unittest.TestCase):
    def test_add(self):
        aggregator = export.aggregate.CounterAggregator()
        handle = metrics.CounterHandle(int, True, aggregator)
        handle.add(3)
        self.assertEqual(handle.aggregator.current, 3)

    def test_add_disabled(self):
        aggregator = export.aggregate.CounterAggregator()
        handle = metrics.CounterHandle(int, False, aggregator)
        handle.add(3)
        self.assertEqual(handle.aggregator.current, 0)

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_add_incorrect_type(self, logger_mock):
        aggregator = export.aggregate.CounterAggregator()
        handle = metrics.CounterHandle(int, True, aggregator)
        handle.add(3.0)
        self.assertEqual(handle.aggregator.current, 0)
        self.assertTrue(logger_mock.warning.called)

    @mock.patch("opentelemetry.sdk.metrics.time_ns")
    def test_update(self, time_mock):
        aggregator = export.aggregate.CounterAggregator()
        handle = metrics.CounterHandle(int, True, aggregator)
        time_mock.return_value = 123
        handle.update(4.0)
        self.assertEqual(handle.last_update_timestamp, 123)
        self.assertEqual(handle.aggregator.current, 4.0)


class TestMeasureHandle(unittest.TestCase):
    def test_record(self):
        aggregator = export.aggregate.MinMaxSumCountAggregator()
        handle = metrics.MeasureHandle(int, True, aggregator)
        handle.record(3)
        self.assertEqual(handle.aggregator.current, (3, 3, 3, 1))

    def test_record_disabled(self):
        aggregator = export.aggregate.MinMaxSumCountAggregator()
        handle = metrics.MeasureHandle(int, False, aggregator)
        handle.record(3)
        self.assertEqual(handle.aggregator.current, (None, None, None, 0))

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_record_incorrect_type(self, logger_mock):
        aggregator = export.aggregate.MinMaxSumCountAggregator()
        handle = metrics.MeasureHandle(int, True, aggregator)
        handle.record(3.0)
        self.assertEqual(handle.aggregator.current, (None, None, None, 0))
        self.assertTrue(logger_mock.warning.called)

    @mock.patch("opentelemetry.sdk.metrics.time_ns")
    def test_update(self, time_mock):
        aggregator = export.aggregate.MinMaxSumCountAggregator()
        handle = metrics.MeasureHandle(int, True, aggregator)
        time_mock.return_value = 123
        handle.update(4.0)
        self.assertEqual(handle.last_update_timestamp, 123)
        self.assertEqual(handle.aggregator.current, (4.0, 4.0, 4.0, 1))
