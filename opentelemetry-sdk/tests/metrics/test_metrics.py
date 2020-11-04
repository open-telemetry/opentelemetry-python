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
from opentelemetry.sdk.metrics.export.aggregate import (
    MinMaxSumCountAggregator,
    SumAggregator,
)
from opentelemetry.sdk.metrics.view import View


class TestMeterProvider(unittest.TestCase):
    def test_stateful(self):
        meter_provider = metrics.MeterProvider(stateful=False)
        meter = meter_provider.get_meter(__name__)
        self.assertIs(meter.processor.stateful, False)

    def test_resource(self):
        resource = resources.Resource.create({})
        meter_provider = metrics.MeterProvider(resource=resource)
        self.assertIs(meter_provider.resource, resource)

    def test_resource_empty(self):
        meter_provider = metrics.MeterProvider()
        # pylint: disable=protected-access
        self.assertEqual(meter_provider.resource, resources._DEFAULT_RESOURCE)

    def test_start_pipeline(self):
        exporter = mock.Mock()
        meter_provider = metrics.MeterProvider()
        meter = meter_provider.get_meter(__name__)
        # pylint: disable=protected-access
        meter_provider.start_pipeline(meter, exporter, 6)
        try:
            self.assertEqual(len(meter_provider._exporters), 1)
            self.assertEqual(len(meter_provider._controllers), 1)
        finally:
            meter_provider.shutdown()

    def test_shutdown(self):
        controller = mock.Mock()
        exporter = mock.Mock()
        meter_provider = metrics.MeterProvider()
        # pylint: disable=protected-access
        meter_provider._controllers = [controller]
        meter_provider._exporters = [exporter]
        meter_provider.shutdown()
        self.assertEqual(controller.shutdown.call_count, 1)
        self.assertEqual(exporter.shutdown.call_count, 1)
        self.assertIsNone(meter_provider._atexit_handler)


class TestMeter(unittest.TestCase):
    def test_extends_api(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        self.assertIsInstance(meter, metrics_api.Meter)

    def test_collect_metrics(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        processor_mock = mock.Mock()
        meter.processor = processor_mock
        counter = meter.create_counter("name", "desc", "unit", float,)
        labels = {"key1": "value1"}
        meter.register_view(View(counter, SumAggregator))
        counter.add(1.0, labels)
        meter.collect()
        self.assertTrue(processor_mock.process.called)

    def test_collect_no_metrics(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        processor_mock = mock.Mock()
        meter.processor = processor_mock
        meter.collect()
        self.assertFalse(processor_mock.process.called)

    def test_collect_not_registered(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        processor_mock = mock.Mock()
        meter.processor = processor_mock
        counter = metrics.Counter("name", "desc", "unit", float, meter)
        labels = {"key1": "value1"}
        counter.add(1.0, labels)
        meter.collect()
        self.assertFalse(processor_mock.process.called)

    def test_collect_disabled_metric(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        processor_mock = mock.Mock()
        meter.processor = processor_mock
        counter = metrics.Counter("name", "desc", "unit", float, meter, False)
        labels = {"key1": "value1"}
        meter.register_view(View(counter, SumAggregator))
        counter.add(1.0, labels)
        meter.collect()
        self.assertFalse(processor_mock.process.called)

    def test_collect_observers(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        processor_mock = mock.Mock()
        meter.processor = processor_mock

        def callback(observer):
            self.assertIsInstance(observer, metrics_api.Observer)
            observer.observe(45, {})

        observer = metrics.ValueObserver(
            callback, "name", "desc", "unit", int, (), True
        )

        meter.observers.add(observer)
        meter.collect()
        self.assertTrue(processor_mock.process.called)

    def test_record_batch(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        labels = {"key1": "value1", "key2": "value2", "key3": "value3"}
        counter = metrics.Counter("name", "desc", "unit", float, meter)
        valuerecorder = metrics.ValueRecorder(
            "name", "desc", "unit", float, meter
        )
        counter_v = View(counter, SumAggregator)
        measure_v = View(valuerecorder, MinMaxSumCountAggregator)
        meter.register_view(counter_v)
        meter.register_view(measure_v)
        record_tuples = [(counter, 1.0), (valuerecorder, 3.0)]
        meter.record_batch(labels, record_tuples)
        labels_key = metrics.get_dict_as_key(labels)
        self.assertEqual(
            counter.bound_instruments[labels_key]
            .view_datas.pop()
            .aggregator.current,
            1.0,
        )
        self.assertEqual(
            valuerecorder.bound_instruments[labels_key]
            .view_datas.pop()
            .aggregator.current,
            (3.0, 3.0, 3.0, 1),
        )

    def test_create_counter(self):
        resource = mock.Mock(spec=resources.Resource)
        meter_provider = metrics.MeterProvider(resource=resource)
        meter = meter_provider.get_meter(__name__)
        counter = meter.create_counter("name", "desc", "unit", int,)
        self.assertIsInstance(counter, metrics.Counter)
        self.assertEqual(counter.value_type, int)
        self.assertEqual(counter.name, "name")
        self.assertIs(meter_provider.resource, resource)
        self.assertEqual(counter.meter, meter)

    def test_create_updowncounter(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        updowncounter = meter.create_updowncounter(
            "name", "desc", "unit", float,
        )
        self.assertIsInstance(updowncounter, metrics.UpDownCounter)
        self.assertEqual(updowncounter.value_type, float)
        self.assertEqual(updowncounter.name, "name")

    def test_create_valuerecorder(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        valuerecorder = meter.create_valuerecorder(
            "name", "desc", "unit", float,
        )
        self.assertIsInstance(valuerecorder, metrics.ValueRecorder)
        self.assertEqual(valuerecorder.value_type, float)
        self.assertEqual(valuerecorder.name, "name")
        self.assertEqual(valuerecorder.meter, meter)

    def test_register_sumobserver(self):
        meter = metrics.MeterProvider().get_meter(__name__)

        callback = mock.Mock()

        observer = meter.register_sumobserver(
            callback, "name", "desc", "unit", int,
        )

        self.assertIsInstance(observer, metrics.SumObserver)
        self.assertEqual(len(meter.observers), 1)

        self.assertEqual(observer.callback, callback)
        self.assertEqual(observer.name, "name")
        self.assertEqual(observer.description, "desc")
        self.assertEqual(observer.unit, "unit")
        self.assertEqual(observer.value_type, int)
        self.assertEqual(observer.label_keys, ())
        self.assertTrue(observer.enabled)

    def test_register_updownsumobserver(self):
        meter = metrics.MeterProvider().get_meter(__name__)

        callback = mock.Mock()

        observer = meter.register_updownsumobserver(
            callback, "name", "desc", "unit", int,
        )

        self.assertIsInstance(observer, metrics.UpDownSumObserver)
        self.assertEqual(len(meter.observers), 1)

        self.assertEqual(observer.callback, callback)
        self.assertEqual(observer.name, "name")
        self.assertEqual(observer.description, "desc")
        self.assertEqual(observer.unit, "unit")
        self.assertEqual(observer.value_type, int)
        self.assertEqual(observer.label_keys, ())
        self.assertTrue(observer.enabled)

    def test_register_valueobserver(self):
        meter = metrics.MeterProvider().get_meter(__name__)

        callback = mock.Mock()

        observer = meter.register_valueobserver(
            callback, "name", "desc", "unit", int,
        )

        self.assertIsInstance(observer, metrics.ValueObserver)
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

        observer = meter.register_valueobserver(
            callback, "name", "desc", "unit", int, metrics.ValueObserver
        )

        meter.unregister_observer(observer)
        self.assertEqual(len(meter.observers), 0)


class TestMetric(unittest.TestCase):
    def test_bind(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        metric_types = [
            metrics.Counter,
            metrics.UpDownCounter,
            metrics.ValueRecorder,
        ]
        labels = {"key": "value"}
        key_labels = metrics.get_dict_as_key(labels)
        for _type in metric_types:
            metric = _type("name", "desc", "unit", int, meter)
            bound_instrument = metric.bind(labels)
            self.assertEqual(
                metric.bound_instruments.get(key_labels), bound_instrument
            )


class TestCounter(unittest.TestCase):
    def test_add(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        metric = metrics.Counter("name", "desc", "unit", int, meter)
        labels = {"key": "value"}
        counter_v = View(metric, SumAggregator)
        meter.register_view(counter_v)
        bound_mock = metric.bind(labels)
        metric.add(3, labels)
        metric.add(2, labels)
        self.assertEqual(bound_mock.view_datas.pop().aggregator.current, 5)

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_add_non_decreasing_int_error(self, logger_mock):
        meter = metrics.MeterProvider().get_meter(__name__)
        metric = metrics.Counter("name", "desc", "unit", int, meter)
        labels = {"key": "value"}
        counter_v = View(metric, SumAggregator)
        meter.register_view(counter_v)
        bound_counter = metric.bind(labels)
        metric.add(3, labels)
        metric.add(0, labels)
        metric.add(-1, labels)
        self.assertEqual(bound_counter.view_datas.pop().aggregator.current, 3)
        self.assertEqual(logger_mock.warning.call_count, 1)

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_add_non_decreasing_float_error(self, logger_mock):
        meter = metrics.MeterProvider().get_meter(__name__)
        metric = metrics.Counter("name", "desc", "unit", float, meter)
        labels = {"key": "value"}
        counter_v = View(metric, SumAggregator)
        meter.register_view(counter_v)
        bound_counter = metric.bind(labels)
        metric.add(3.3, labels)
        metric.add(0.0, labels)
        metric.add(0.1, labels)
        metric.add(-0.1, labels)
        self.assertEqual(
            bound_counter.view_datas.pop().aggregator.current, 3.4
        )
        self.assertEqual(logger_mock.warning.call_count, 1)


class TestUpDownCounter(unittest.TestCase):
    def test_add(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        metric = metrics.UpDownCounter("name", "desc", "unit", int, meter)
        labels = {"key": "value"}
        bound_counter = metric.bind(labels)
        counter_v = View(metric, SumAggregator)
        meter.register_view(counter_v)
        metric.add(3, labels)
        metric.add(2, labels)
        self.assertEqual(bound_counter.view_datas.pop().aggregator.current, 5)


class TestValueRecorder(unittest.TestCase):
    def test_record(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        metric = metrics.ValueRecorder("name", "desc", "unit", int, meter)
        labels = {"key": "value"}
        measure_v = View(metric, MinMaxSumCountAggregator)
        bound_valuerecorder = metric.bind(labels)
        meter.register_view(measure_v)
        values = (37, 42, 7)
        for val in values:
            metric.record(val, labels)
        self.assertEqual(
            bound_valuerecorder.view_datas.pop().aggregator.current,
            (min(values), max(values), sum(values), len(values)),
        )


class TestSumObserver(unittest.TestCase):
    def test_observe(self):
        observer = metrics.SumObserver(
            None, "name", "desc", "unit", int, ("key",), True
        )
        labels = {"key": "value"}
        key_labels = metrics.get_dict_as_key(labels)
        values = (37, 42, 60, 100)
        for val in values:
            observer.observe(val, labels)

        self.assertEqual(observer.aggregators[key_labels].current, values[-1])

    def test_observe_disabled(self):
        observer = metrics.SumObserver(
            None, "name", "desc", "unit", int, ("key",), False
        )
        labels = {"key": "value"}
        observer.observe(37, labels)
        self.assertEqual(len(observer.aggregators), 0)

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_observe_incorrect_type(self, logger_mock):
        observer = metrics.SumObserver(
            None, "name", "desc", "unit", int, ("key",), True
        )
        labels = {"key": "value"}
        observer.observe(37.0, labels)
        self.assertEqual(len(observer.aggregators), 0)
        self.assertTrue(logger_mock.warning.called)

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_observe_non_decreasing_error(self, logger_mock):
        observer = metrics.SumObserver(
            None, "name", "desc", "unit", int, ("key",), True
        )
        labels = {"key": "value"}
        observer.observe(37, labels)
        observer.observe(14, labels)
        self.assertEqual(len(observer.aggregators), 1)
        self.assertTrue(logger_mock.warning.called)

    def test_run(self):
        callback = mock.Mock()
        observer = metrics.SumObserver(
            callback, "name", "desc", "unit", int, (), True
        )

        self.assertTrue(observer.run())
        callback.assert_called_once_with(observer)

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_run_exception(self, logger_mock):
        callback = mock.Mock()
        callback.side_effect = Exception("We have a problem!")

        observer = metrics.SumObserver(
            callback, "name", "desc", "unit", int, (), True
        )

        self.assertFalse(observer.run())
        self.assertTrue(logger_mock.warning.called)


class TestUpDownSumObserver(unittest.TestCase):
    def test_observe(self):
        observer = metrics.UpDownSumObserver(
            None, "name", "desc", "unit", int, ("key",), True
        )
        labels = {"key": "value"}
        key_labels = metrics.get_dict_as_key(labels)
        values = (37, 42, 14, 30)
        for val in values:
            observer.observe(val, labels)

        self.assertEqual(observer.aggregators[key_labels].current, values[-1])

    def test_observe_disabled(self):
        observer = metrics.UpDownSumObserver(
            None, "name", "desc", "unit", int, ("key",), False
        )
        labels = {"key": "value"}
        observer.observe(37, labels)
        self.assertEqual(len(observer.aggregators), 0)

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_observe_incorrect_type(self, logger_mock):
        observer = metrics.UpDownSumObserver(
            None, "name", "desc", "unit", int, ("key",), True
        )
        labels = {"key": "value"}
        observer.observe(37.0, labels)
        self.assertEqual(len(observer.aggregators), 0)
        self.assertTrue(logger_mock.warning.called)

    def test_run(self):
        callback = mock.Mock()
        observer = metrics.UpDownSumObserver(
            callback, "name", "desc", "unit", int, (), True
        )

        self.assertTrue(observer.run())
        callback.assert_called_once_with(observer)

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_run_exception(self, logger_mock):
        callback = mock.Mock()
        callback.side_effect = Exception("We have a problem!")

        observer = metrics.UpDownSumObserver(
            callback, "name", "desc", "unit", int, (), True
        )

        self.assertFalse(observer.run())
        self.assertTrue(logger_mock.warning.called)


class TestValueObserver(unittest.TestCase):
    def test_observe(self):
        observer = metrics.ValueObserver(
            None, "name", "desc", "unit", int, ("key",), True
        )
        labels = {"key": "value"}
        key_labels = metrics.get_dict_as_key(labels)
        values = (37, 42, 7, 21)
        for val in values:
            observer.observe(val, labels)
        self.assertEqual(
            observer.aggregators[key_labels].mmsc.current,
            (min(values), max(values), sum(values), len(values)),
        )

        self.assertEqual(observer.aggregators[key_labels].current, values[-1])

    def test_observe_disabled(self):
        observer = metrics.ValueObserver(
            None, "name", "desc", "unit", int, ("key",), False
        )
        labels = {"key": "value"}
        observer.observe(37, labels)
        self.assertEqual(len(observer.aggregators), 0)

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_observe_incorrect_type(self, logger_mock):
        observer = metrics.ValueObserver(
            None, "name", "desc", "unit", int, ("key",), True
        )
        labels = {"key": "value"}
        observer.observe(37.0, labels)
        self.assertEqual(len(observer.aggregators), 0)
        self.assertTrue(logger_mock.warning.called)

    def test_run(self):
        callback = mock.Mock()
        observer = metrics.ValueObserver(
            callback, "name", "desc", "unit", int, (), True
        )

        self.assertTrue(observer.run())
        callback.assert_called_once_with(observer)

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_run_exception(self, logger_mock):
        callback = mock.Mock()
        callback.side_effect = Exception("We have a problem!")

        observer = metrics.ValueObserver(
            callback, "name", "desc", "unit", int, (), True
        )

        self.assertFalse(observer.run())
        self.assertTrue(logger_mock.warning.called)


# pylint: disable=no-self-use
class TestBoundCounter(unittest.TestCase):
    def test_add(self):
        meter_mock = mock.Mock()
        metric_mock = mock.Mock()
        metric_mock.enabled = True
        metric_mock.value_type = int
        metric_mock.meter = meter_mock
        bound_metric = metrics.BoundCounter((), metric_mock)
        view_datas_mock = mock.Mock()
        bound_metric.view_datas = [view_datas_mock]
        bound_metric.add(3)
        view_datas_mock.record.assert_called_once_with(3)

    def test_add_disabled(self):
        meter_mock = mock.Mock()
        metric_mock = mock.Mock()
        metric_mock.enabled = False
        metric_mock.value_type = int
        metric_mock.meter = meter_mock
        bound_metric = metrics.BoundCounter((), metric_mock)
        view_datas_mock = mock.Mock()
        bound_metric.view_datas = [view_datas_mock]
        bound_metric.add(3)
        view_datas_mock.record.update_view.assert_not_called()

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_add_incorrect_type(self, logger_mock):
        meter_mock = mock.Mock()
        viewm_mock = mock.Mock()
        meter_mock.view_manager = viewm_mock
        metric_mock = mock.Mock()
        metric_mock.enabled = True
        metric_mock.value_type = float
        metric_mock.meter = meter_mock
        bound_metric = metrics.BoundCounter((), metric_mock)
        view_datas_mock = mock.Mock()
        bound_metric.view_datas = [view_datas_mock]
        bound_metric.add(3)
        view_datas_mock.record.update_view.assert_not_called()
        self.assertTrue(logger_mock.warning.called)


class TestBoundValueRecorder(unittest.TestCase):
    def test_record(self):
        meter_mock = mock.Mock()
        metric_mock = mock.Mock()
        metric_mock.enabled = True
        metric_mock.value_type = int
        metric_mock.meter = meter_mock
        bound_valuerecorder = metrics.BoundValueRecorder((), metric_mock)
        view_datas_mock = mock.Mock()
        bound_valuerecorder.view_datas = [view_datas_mock]
        bound_valuerecorder.record(3)
        view_datas_mock.record.assert_called_once_with(3)

    def test_record_disabled(self):
        meter_mock = mock.Mock()
        metric_mock = mock.Mock()
        metric_mock.enabled = False
        metric_mock.value_type = int
        metric_mock.meter = meter_mock
        bound_valuerecorder = metrics.BoundValueRecorder((), metric_mock)
        view_datas_mock = mock.Mock()
        bound_valuerecorder.view_datas = [view_datas_mock]
        bound_valuerecorder.record(3)
        view_datas_mock.record.update_view.assert_not_called()

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_record_incorrect_type(self, logger_mock):
        meter_mock = mock.Mock()
        metric_mock = mock.Mock()
        metric_mock.enabled = True
        metric_mock.value_type = float
        metric_mock.meter = meter_mock
        bound_valuerecorder = metrics.BoundValueRecorder((), metric_mock)
        view_datas_mock = mock.Mock()
        bound_valuerecorder.view_datas = [view_datas_mock]
        bound_valuerecorder.record(3)
        view_datas_mock.record.update_view.assert_not_called()
        self.assertTrue(logger_mock.warning.called)
