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

import unittest
from unittest import mock

from opentelemetry import metrics as metrics_api
from opentelemetry.sdk import metrics, resources
from opentelemetry.sdk.metrics import export
from opentelemetry.sdk.metrics.export.aggregate import (
    CounterAggregator,
    MinMaxSumCountAggregator
)
from opentelemetry.sdk.metrics.view import View


class TestMeterProvider(unittest.TestCase):
    def test_resource(self):
        resource = resources.Resource.create({})
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

    def test_collect_metrics(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        batcher_mock = mock.Mock()
        meter.batcher = batcher_mock
        counter = metrics.Counter(
            "name", "desc", "unit", float, meter
        )
        labels = {"key1": "value1"}
        meter.register_view(View(counter, CounterAggregator))
        counter.add(1.0, labels)
        meter.collect()
        self.assertTrue(batcher_mock.process.called)

    def test_collect_no_metrics(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        batcher_mock = mock.Mock()
        meter.batcher = batcher_mock
        meter.collect()
        self.assertFalse(batcher_mock.process.called)

    def test_collect_not_registered(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        batcher_mock = mock.Mock()
        meter.batcher = batcher_mock
        counter = metrics.Counter(
            "name", "desc", "unit", float, meter
        )
        labels = {"key1": "value1"}
        counter.add(1.0, labels)
        meter.collect()
        self.assertFalse(batcher_mock.process.called)

    def test_collect_disabled_metric(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        batcher_mock = mock.Mock()
        meter.batcher = batcher_mock
        counter = metrics.Counter(
            "name", "desc", "unit", float, meter, False
        )
        labels = {"key1": "value1"}
        meter.register_view(View(counter, CounterAggregator))
        counter.add(1.0, labels)
        meter.collect()
        self.assertFalse(batcher_mock.process.called)

    def test_collect_observers(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        batcher_mock = mock.Mock()
        meter.batcher = batcher_mock

        def callback(observer):
            self.assertIsInstance(observer, metrics_api.Observer)
            observer.observe(45, {})

        observer = metrics.Observer(
            callback, "name", "desc", "unit", int, (), True
        )

        meter.observers.add(observer)
        meter.collect()
        self.assertTrue(batcher_mock.process.called)

    def test_record_batch(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        labels = {"key1": "value1", "key2": "value2", "key3": "value3"}
        counter = metrics.Counter(
            "name", "desc", "unit", float, meter
        )
        measure = metrics.Measure(
            "name", "desc", "unit", float, meter
        )
        counter_v = View(counter, CounterAggregator)
        measure_v = View(measure, MinMaxSumCountAggregator)
        meter.register_view(counter_v)
        meter.register_view(measure_v)
        record_tuples = [(counter, 1.0), (measure, 3.0)]
        meter.record_batch(labels, record_tuples)
        labels_key = metrics.get_labels_as_key(labels)
        self.assertEqual(
            counter_v.view_datas.get(labels_key).aggregator.current,
            1.0
        )
        self.assertEqual(
            measure_v.view_datas.get(labels_key).aggregator.current,
            (3.0, 3.0, 3.0, 1)
        )

    def test_create_metric(self):
        resource = mock.Mock(spec=resources.Resource)
        meter_provider = metrics.MeterProvider(resource=resource)
        meter = meter_provider.get_meter(__name__)
        counter = meter.create_metric(
            "name", "desc", "unit", int, metrics.Counter
        )
        self.assertIsInstance(counter, metrics.Counter)
        self.assertEqual(counter.value_type, int)
        self.assertEqual(counter.name, "name")
        self.assertIs(counter.meter.resource, resource)
        self.assertEqual(counter.meter, meter)

    def test_create_measure(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        measure = meter.create_metric(
            "name", "desc", "unit", float, metrics.Measure
        )
        self.assertIsInstance(measure, metrics.Measure)
        self.assertEqual(measure.value_type, float)
        self.assertEqual(measure.name, "name")
        self.assertEqual(measure.meter, meter)

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

    def test_unregister_observer(self):
        meter = metrics.MeterProvider().get_meter(__name__)

        callback = mock.Mock()

        observer = meter.register_observer(
            callback, "name", "desc", "unit", int, (), True
        )

        meter.unregister_observer(observer)
        self.assertEqual(len(meter.observers), 0)

#     def test_direct_call_release_bound_instrument(self):
#         meter = metrics.MeterProvider().get_meter(__name__)
#         label_keys = ("key1",)
#         labels = {"key1": "value1"}

#         counter = metrics.Counter(
#             "name", "desc", "unit", float, meter, label_keys
#         )
#         meter.metrics.add(counter)
#         counter.add(4.0, labels)

#         measure = metrics.Measure(
#             "name", "desc", "unit", float, meter, label_keys
#         )
#         meter.metrics.add(measure)
#         measure.record(42.0, labels)

#         self.assertEqual(len(counter.bound_instruments), 1)
#         self.assertEqual(len(measure.bound_instruments), 1)

#         meter.collect()

#         self.assertEqual(len(counter.bound_instruments), 0)
#         self.assertEqual(len(measure.bound_instruments), 0)

#     def test_release_bound_instrument(self):
#         meter = metrics.MeterProvider().get_meter(__name__)
#         label_keys = ("key1",)
#         labels = {"key1": "value1"}

#         counter = metrics.Counter(
#             "name", "desc", "unit", float, meter, label_keys
#         )
#         meter.metrics.add(counter)
#         bound_counter = counter.bind(labels)
#         bound_counter.add(4.0)

#         measure = metrics.Measure(
#             "name", "desc", "unit", float, meter, label_keys
#         )
#         meter.metrics.add(measure)
#         bound_measure = measure.bind(labels)
#         bound_measure.record(42)

#         bound_counter.release()
#         bound_measure.release()

#         # be sure that bound instruments are only released after collection
#         self.assertEqual(len(counter.bound_instruments), 1)
#         self.assertEqual(len(measure.bound_instruments), 1)

#         meter.collect()

#         self.assertEqual(len(counter.bound_instruments), 0)
#         self.assertEqual(len(measure.bound_instruments), 0)


class TestMetric(unittest.TestCase):
    def test_bind(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        metric_types = [metrics.Counter, metrics.Measure]
        labels = {"key": "value"}
        key_labels = tuple(sorted(labels.items()))
        for _type in metric_types:
            metric = _type("name", "desc", "unit", int, meter, ("key",))
            bound_instrument = metric.bind(labels)
            self.assertEqual(
                metric.bound_instruments.get(key_labels), bound_instrument
            )


class TestCounter(unittest.TestCase):
    def test_add(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        metric = metrics.Counter("name", "desc", "unit", int, meter)
        labels = {"key": "value"}
        key_labels = tuple(sorted(labels.items()))
        counter_v = View(metric, CounterAggregator)
        meter.register_view(counter_v)
        bound_mock = metric.bind(labels)
        metric.add(3, labels)
        metric.add(2, labels)
        self.assertEqual(counter_v.view_datas[key_labels].aggregator.current, 5)


class TestMeasure(unittest.TestCase):
    def test_record(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        metric = metrics.Measure("name", "desc", "unit", int, meter)
        labels = {"key": "value"}
        key_labels = tuple(sorted(labels.items()))
        measure_v = View(metric, MinMaxSumCountAggregator)
        bound_measure = metric.bind(labels)
        meter.register_view(measure_v)
        values = (37, 42, 7)
        for val in values:
            metric.record(val, labels)
        self.assertEqual(
            measure_v.view_datas[key_labels].aggregator.current,
            (min(values), max(values), sum(values), len(values)),
        )


class TestObserver(unittest.TestCase):
    def test_observe(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        observer = metrics.Observer(
            None, "name", "desc", "unit", int, ("key",), True
        )
        labels = {"key": "value"}
        key_labels = tuple(sorted(labels.items()))
        values = (37, 42, 7, 21)
        for val in values:
            observer.observe(val, labels)
        self.assertEqual(
            observer.aggregators[key_labels].mmsc.current,
            (min(values), max(values), sum(values), len(values)),
        )

        self.assertEqual(observer.aggregators[key_labels].current, values[-1])

    def test_observe_disabled(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        observer = metrics.Observer(
            None, "name", "desc", "unit", int, ("key",), False
        )
        labels = {"key": "value"}
        observer.observe(37, labels)
        self.assertEqual(len(observer.aggregators), 0)

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_observe_incorrect_type(self, logger_mock):
        meter = metrics.MeterProvider().get_meter(__name__)
        observer = metrics.Observer(
            None, "name", "desc", "unit", int, ("key",), True
        )
        labels = {"key": "value"}
        observer.observe(37.0, labels)
        self.assertEqual(len(observer.aggregators), 0)
        self.assertTrue(logger_mock.warning.called)

    def test_run(self):
        meter = metrics.MeterProvider().get_meter(__name__)

        callback = mock.Mock()
        observer = metrics.Observer(
            callback, "name", "desc", "unit", int, (), True
        )

        self.assertTrue(observer.run())
        callback.assert_called_once_with(observer)

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_run_exception(self, logger_mock):
        meter = metrics.MeterProvider().get_meter(__name__)

        callback = mock.Mock()
        callback.side_effect = Exception("We have a problem!")

        observer = metrics.Observer(
            callback, "name", "desc", "unit", int, (), True
        )

        self.assertFalse(observer.run())
        self.assertTrue(logger_mock.warning.called)


class TestBoundCounter(unittest.TestCase):
    def test_add(self):
        meter_mock = mock.Mock()
        viewm_mock = mock.Mock()
        meter_mock.view_manager = viewm_mock
        metric_mock = mock.Mock()
        metric_mock.enabled = True
        metric_mock.value_type = int
        metric_mock.meter = meter_mock
        aggregator = export.aggregate.CounterAggregator()
        bound_metric = metrics.BoundCounter((), metric_mock)
        bound_metric.add(3)
        viewm_mock.update_view.assert_called_once_with(metric_mock, (), 3)

    def test_add_disabled(self):
        meter_mock = mock.Mock()
        viewm_mock = mock.Mock()
        meter_mock.view_manager = viewm_mock
        metric_mock = mock.Mock()
        metric_mock.enabled = False
        metric_mock.value_type = int
        metric_mock.meter = meter_mock
        aggregator = export.aggregate.CounterAggregator()
        bound_metric = metrics.BoundCounter((), metric_mock)
        bound_metric.add(3)
        viewm_mock.update_view.assert_not_called()

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_add_incorrect_type(self, logger_mock):
        meter_mock = mock.Mock()
        viewm_mock = mock.Mock()
        meter_mock.view_manager = viewm_mock
        metric_mock = mock.Mock()
        metric_mock.enabled = True
        metric_mock.value_type = float
        metric_mock.meter = meter_mock
        aggregator = export.aggregate.CounterAggregator()
        bound_metric = metrics.BoundCounter((), metric_mock)
        bound_metric.add(3)
        viewm_mock.update_view.assert_not_called()
        self.assertTrue(logger_mock.warning.called)


class TestBoundMeasure(unittest.TestCase):
    def test_record(self):
        meter_mock = mock.Mock()
        viewm_mock = mock.Mock()
        meter_mock.view_manager = viewm_mock
        metric_mock = mock.Mock()
        metric_mock.enabled = True
        metric_mock.value_type = int
        metric_mock.meter = meter_mock
        aggregator = export.aggregate.MinMaxSumCountAggregator()
        bound_metric = metrics.BoundMeasure((), metric_mock)
        bound_metric.record(3)
        viewm_mock.update_view.assert_called_once_with(metric_mock, (), 3)


    def test_record_disabled(self):
        meter_mock = mock.Mock()
        viewm_mock = mock.Mock()
        meter_mock.view_manager = viewm_mock
        metric_mock = mock.Mock()
        metric_mock.enabled = False
        metric_mock.value_type = int
        metric_mock.meter = meter_mock
        aggregator = export.aggregate.MinMaxSumCountAggregator()
        bound_metric = metrics.BoundMeasure((), metric_mock)
        bound_metric.record(3)
        viewm_mock.update_view.assert_not_called()

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_record_incorrect_type(self, logger_mock):
        meter_mock = mock.Mock()
        viewm_mock = mock.Mock()
        meter_mock.view_manager = viewm_mock
        metric_mock = mock.Mock()
        metric_mock.enabled = True
        metric_mock.value_type = float
        metric_mock.meter = meter_mock
        aggregator = export.aggregate.MinMaxSumCountAggregator()
        bound_metric = metrics.BoundMeasure((), metric_mock)
        bound_metric.record(3)
        viewm_mock.update_view.assert_not_called()
        self.assertTrue(logger_mock.warning.called)
