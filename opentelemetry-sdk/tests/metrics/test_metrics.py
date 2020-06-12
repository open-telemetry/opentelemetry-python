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


class TestMeterProvider(unittest.TestCase):
    def test_stateful(self):
        meter_provider = metrics.MeterProvider(stateful=False)
        meter = meter_provider.get_meter(__name__)
        self.assertIs(meter.batcher.stateful, False)

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

    def test_collect(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        batcher_mock = mock.Mock()
        meter.batcher = batcher_mock
        label_keys = ("key1",)
        counter = metrics.Counter(
            "name", "desc", "unit", float, meter, label_keys
        )
        labels = {"key1": "value1"}
        counter.add(1.0, labels)
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
        labels = {"key1": "value1"}
        counter.add(1.0, labels)
        meter.metrics.add(counter)
        meter.collect()
        self.assertFalse(batcher_mock.process.called)

    def test_collect_observers(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        batcher_mock = mock.Mock()
        meter.batcher = batcher_mock

        def callback(observer):
            self.assertIsInstance(observer, metrics_api.Observer)
            observer.observe(45, {})

        observer = metrics.ValueObserver(
            callback, "name", "desc", "unit", int, meter, (), True
        )

        meter.observers.add(observer)
        meter.collect()
        self.assertTrue(batcher_mock.process.called)

    def test_record_batch(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        label_keys = ("key1",)
        labels = {"key1": "value1"}
        counter = metrics.Counter(
            "name", "desc", "unit", float, meter, label_keys
        )
        record_tuples = [(counter, 1.0)]
        meter.record_batch(labels, record_tuples)
        self.assertEqual(counter.bind(labels).aggregator.current, 1.0)

    def test_record_batch_multiple(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        label_keys = ("key1", "key2", "key3")
        labels = {"key1": "value1", "key2": "value2", "key3": "value3"}
        counter = metrics.Counter(
            "name", "desc", "unit", float, meter, label_keys
        )
        valuerecorder = metrics.ValueRecorder(
            "name", "desc", "unit", float, meter, label_keys
        )
        record_tuples = [(counter, 1.0), (valuerecorder, 3.0)]
        meter.record_batch(labels, record_tuples)
        self.assertEqual(counter.bind(labels).aggregator.current, 1.0)
        self.assertEqual(
            valuerecorder.bind(labels).aggregator.current, (3.0, 3.0, 3.0, 1)
        )

    def test_record_batch_exists(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        label_keys = ("key1",)
        labels = {"key1": "value1"}
        counter = metrics.Counter(
            "name", "desc", "unit", float, meter, label_keys
        )
        counter.add(1.0, labels)
        bound_counter = counter.bind(labels)
        record_tuples = [(counter, 1.0)]
        meter.record_batch(labels, record_tuples)
        self.assertEqual(counter.bind(labels), bound_counter)
        self.assertEqual(bound_counter.aggregator.current, 2.0)

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

    def test_create_updowncounter(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        updowncounter = meter.create_metric(
            "name", "desc", "unit", float, metrics.UpDownCounter, ()
        )
        self.assertIsInstance(updowncounter, metrics.UpDownCounter)
        self.assertEqual(updowncounter.value_type, float)
        self.assertEqual(updowncounter.name, "name")

    def test_create_valuerecorder(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        valuerecorder = meter.create_metric(
            "name", "desc", "unit", float, metrics.ValueRecorder, ()
        )
        self.assertIsInstance(valuerecorder, metrics.ValueRecorder)
        self.assertEqual(valuerecorder.value_type, float)
        self.assertEqual(valuerecorder.name, "name")

    def test_register_observer(self):
        meter = metrics.MeterProvider().get_meter(__name__)

        callback = mock.Mock()

        observer = meter.register_observer(
            callback, "name", "desc", "unit", int, metrics.ValueObserver
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
            callback, "name", "desc", "unit", int, metrics.ValueObserver
        )

        meter.unregister_observer(observer)
        self.assertEqual(len(meter.observers), 0)

    def test_direct_call_release_bound_instrument(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        label_keys = ("key1",)
        labels = {"key1": "value1"}

        counter = metrics.Counter(
            "name", "desc", "unit", float, meter, label_keys
        )
        meter.metrics.add(counter)
        counter.add(4.0, labels)

        valuerecorder = metrics.ValueRecorder(
            "name", "desc", "unit", float, meter, label_keys
        )
        meter.metrics.add(valuerecorder)
        valuerecorder.record(42.0, labels)

        self.assertEqual(len(counter.bound_instruments), 1)
        self.assertEqual(len(valuerecorder.bound_instruments), 1)

        meter.collect()

        self.assertEqual(len(counter.bound_instruments), 0)
        self.assertEqual(len(valuerecorder.bound_instruments), 0)

    def test_release_bound_instrument(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        label_keys = ("key1",)
        labels = {"key1": "value1"}

        counter = metrics.Counter(
            "name", "desc", "unit", float, meter, label_keys
        )
        meter.metrics.add(counter)
        bound_counter = counter.bind(labels)
        bound_counter.add(4.0)

        valuerecorder = metrics.ValueRecorder(
            "name", "desc", "unit", float, meter, label_keys
        )
        meter.metrics.add(valuerecorder)
        bound_valuerecorder = valuerecorder.bind(labels)
        bound_valuerecorder.record(42)

        bound_counter.release()
        bound_valuerecorder.release()

        # be sure that bound instruments are only released after collection
        self.assertEqual(len(counter.bound_instruments), 1)
        self.assertEqual(len(valuerecorder.bound_instruments), 1)

        meter.collect()

        self.assertEqual(len(counter.bound_instruments), 0)
        self.assertEqual(len(valuerecorder.bound_instruments), 0)


class TestMetric(unittest.TestCase):
    def test_bind(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        metric_types = [metrics.Counter, metrics.ValueRecorder]
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
        metric = metrics.Counter("name", "desc", "unit", int, meter, ("key",))
        labels = {"key": "value"}
        bound_counter = metric.bind(labels)
        metric.add(3, labels)
        metric.add(2, labels)
        self.assertEqual(bound_counter.aggregator.current, 5)

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_add_non_decreasing_int_error(self, logger_mock):
        meter = metrics.MeterProvider().get_meter(__name__)
        metric = metrics.Counter("name", "desc", "unit", int, meter, ("key",))
        labels = {"key": "value"}
        bound_counter = metric.bind(labels)
        metric.add(3, labels)
        metric.add(0, labels)
        metric.add(-1, labels)
        self.assertEqual(bound_counter.aggregator.current, 3)
        self.assertEqual(logger_mock.warning.call_count, 1)

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_add_non_decreasing_float_error(self, logger_mock):
        meter = metrics.MeterProvider().get_meter(__name__)
        metric = metrics.Counter(
            "name", "desc", "unit", float, meter, ("key",)
        )
        labels = {"key": "value"}
        bound_counter = metric.bind(labels)
        metric.add(3.3, labels)
        metric.add(0.0, labels)
        metric.add(0.1, labels)
        metric.add(-0.1, labels)
        self.assertEqual(bound_counter.aggregator.current, 3.4)
        self.assertEqual(logger_mock.warning.call_count, 1)


class TestUpDownCounter(unittest.TestCase):
    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_add(self, logger_mock):
        meter = metrics.MeterProvider().get_meter(__name__)
        metric = metrics.UpDownCounter(
            "name", "desc", "unit", int, meter, ("key",)
        )
        labels = {"key": "value"}
        bound_counter = metric.bind(labels)
        metric.add(3, labels)
        metric.add(2, labels)
        self.assertEqual(bound_counter.aggregator.current, 5)

        metric.add(0, labels)
        metric.add(-3, labels)
        metric.add(-1, labels)
        self.assertEqual(bound_counter.aggregator.current, 1)
        self.assertEqual(logger_mock.warning.call_count, 0)


class TestValueRecorder(unittest.TestCase):
    def test_record(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        metric = metrics.ValueRecorder(
            "name", "desc", "unit", int, meter, ("key",)
        )
        labels = {"key": "value"}
        bound_valuerecorder = metric.bind(labels)
        values = (37, 42, 7)
        for val in values:
            metric.record(val, labels)
        self.assertEqual(
            bound_valuerecorder.aggregator.current,
            (min(values), max(values), sum(values), len(values)),
        )


class TestSumObserver(unittest.TestCase):
    def test_observe(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        observer = metrics.SumObserver(
            None, "name", "desc", "unit", int, meter, ("key",), True
        )
        labels = {"key": "value"}
        key_labels = tuple(sorted(labels.items()))
        values = (37, 42, 60, 100)
        for val in values:
            observer.observe(val, labels)

        self.assertEqual(observer.aggregators[key_labels].current, values[-1])

    def test_observe_disabled(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        observer = metrics.SumObserver(
            None, "name", "desc", "unit", int, meter, ("key",), False
        )
        labels = {"key": "value"}
        observer.observe(37, labels)
        self.assertEqual(len(observer.aggregators), 0)

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_observe_incorrect_type(self, logger_mock):
        meter = metrics.MeterProvider().get_meter(__name__)
        observer = metrics.SumObserver(
            None, "name", "desc", "unit", int, meter, ("key",), True
        )
        labels = {"key": "value"}
        observer.observe(37.0, labels)
        self.assertEqual(len(observer.aggregators), 0)
        self.assertTrue(logger_mock.warning.called)

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_observe_non_decreasing_error(self, logger_mock):
        meter = metrics.MeterProvider().get_meter(__name__)
        observer = metrics.SumObserver(
            None, "name", "desc", "unit", int, meter, ("key",), True
        )
        labels = {"key": "value"}
        observer.observe(37, labels)
        observer.observe(14, labels)
        self.assertEqual(len(observer.aggregators), 1)
        self.assertTrue(logger_mock.warning.called)

    def test_run(self):
        meter = metrics.MeterProvider().get_meter(__name__)

        callback = mock.Mock()
        observer = metrics.SumObserver(
            callback, "name", "desc", "unit", int, meter, (), True
        )

        self.assertTrue(observer.run())
        callback.assert_called_once_with(observer)

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_run_exception(self, logger_mock):
        meter = metrics.MeterProvider().get_meter(__name__)

        callback = mock.Mock()
        callback.side_effect = Exception("We have a problem!")

        observer = metrics.SumObserver(
            callback, "name", "desc", "unit", int, meter, (), True
        )

        self.assertFalse(observer.run())
        self.assertTrue(logger_mock.warning.called)


class TestUpDownSumObserver(unittest.TestCase):
    def test_observe(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        observer = metrics.UpDownSumObserver(
            None, "name", "desc", "unit", int, meter, ("key",), True
        )
        labels = {"key": "value"}
        key_labels = tuple(sorted(labels.items()))
        values = (37, 42, 14, 30)
        for val in values:
            observer.observe(val, labels)

        self.assertEqual(observer.aggregators[key_labels].current, values[-1])

    def test_observe_disabled(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        observer = metrics.UpDownSumObserver(
            None, "name", "desc", "unit", int, meter, ("key",), False
        )
        labels = {"key": "value"}
        observer.observe(37, labels)
        self.assertEqual(len(observer.aggregators), 0)

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_observe_incorrect_type(self, logger_mock):
        meter = metrics.MeterProvider().get_meter(__name__)
        observer = metrics.UpDownSumObserver(
            None, "name", "desc", "unit", int, meter, ("key",), True
        )
        labels = {"key": "value"}
        observer.observe(37.0, labels)
        self.assertEqual(len(observer.aggregators), 0)
        self.assertTrue(logger_mock.warning.called)

    def test_run(self):
        meter = metrics.MeterProvider().get_meter(__name__)

        callback = mock.Mock()
        observer = metrics.UpDownSumObserver(
            callback, "name", "desc", "unit", int, meter, (), True
        )

        self.assertTrue(observer.run())
        callback.assert_called_once_with(observer)

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_run_exception(self, logger_mock):
        meter = metrics.MeterProvider().get_meter(__name__)

        callback = mock.Mock()
        callback.side_effect = Exception("We have a problem!")

        observer = metrics.UpDownSumObserver(
            callback, "name", "desc", "unit", int, meter, (), True
        )

        self.assertFalse(observer.run())
        self.assertTrue(logger_mock.warning.called)


class TestValueObserver(unittest.TestCase):
    def test_observe(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        observer = metrics.ValueObserver(
            None, "name", "desc", "unit", int, meter, ("key",), True
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
        observer = metrics.ValueObserver(
            None, "name", "desc", "unit", int, meter, ("key",), False
        )
        labels = {"key": "value"}
        observer.observe(37, labels)
        self.assertEqual(len(observer.aggregators), 0)

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_observe_incorrect_type(self, logger_mock):
        meter = metrics.MeterProvider().get_meter(__name__)
        observer = metrics.ValueObserver(
            None, "name", "desc", "unit", int, meter, ("key",), True
        )
        labels = {"key": "value"}
        observer.observe(37.0, labels)
        self.assertEqual(len(observer.aggregators), 0)
        self.assertTrue(logger_mock.warning.called)

    def test_run(self):
        meter = metrics.MeterProvider().get_meter(__name__)

        callback = mock.Mock()
        observer = metrics.ValueObserver(
            callback, "name", "desc", "unit", int, meter, (), True
        )

        self.assertTrue(observer.run())
        callback.assert_called_once_with(observer)

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_run_exception(self, logger_mock):
        meter = metrics.MeterProvider().get_meter(__name__)

        callback = mock.Mock()
        callback.side_effect = Exception("We have a problem!")

        observer = metrics.ValueObserver(
            callback, "name", "desc", "unit", int, meter, (), True
        )

        self.assertFalse(observer.run())
        self.assertTrue(logger_mock.warning.called)


class TestBoundCounter(unittest.TestCase):
    def test_add(self):
        aggregator = export.aggregate.CounterAggregator()
        bound_metric = metrics.BoundCounter(int, True, aggregator)
        bound_metric.add(3)
        self.assertEqual(bound_metric.aggregator.current, 3)

    def test_add_disabled(self):
        aggregator = export.aggregate.CounterAggregator()
        bound_counter = metrics.BoundCounter(int, False, aggregator)
        bound_counter.add(3)
        self.assertEqual(bound_counter.aggregator.current, 0)

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_add_incorrect_type(self, logger_mock):
        aggregator = export.aggregate.CounterAggregator()
        bound_counter = metrics.BoundCounter(int, True, aggregator)
        bound_counter.add(3.0)
        self.assertEqual(bound_counter.aggregator.current, 0)
        self.assertTrue(logger_mock.warning.called)

    def test_update(self):
        aggregator = export.aggregate.CounterAggregator()
        bound_counter = metrics.BoundCounter(int, True, aggregator)
        bound_counter.update(4.0)
        self.assertEqual(bound_counter.aggregator.current, 4.0)


class TestBoundValueRecorder(unittest.TestCase):
    def test_record(self):
        aggregator = export.aggregate.MinMaxSumCountAggregator()
        bound_valuerecorder = metrics.BoundValueRecorder(int, True, aggregator)
        bound_valuerecorder.record(3)
        self.assertEqual(bound_valuerecorder.aggregator.current, (3, 3, 3, 1))

    def test_record_disabled(self):
        aggregator = export.aggregate.MinMaxSumCountAggregator()
        bound_valuerecorder = metrics.BoundValueRecorder(
            int, False, aggregator
        )
        bound_valuerecorder.record(3)
        self.assertEqual(
            bound_valuerecorder.aggregator.current, (None, None, None, 0)
        )

    @mock.patch("opentelemetry.sdk.metrics.logger")
    def test_record_incorrect_type(self, logger_mock):
        aggregator = export.aggregate.MinMaxSumCountAggregator()
        bound_valuerecorder = metrics.BoundValueRecorder(int, True, aggregator)
        bound_valuerecorder.record(3.0)
        self.assertEqual(
            bound_valuerecorder.aggregator.current, (None, None, None, 0)
        )
        self.assertTrue(logger_mock.warning.called)

    def test_update(self):
        aggregator = export.aggregate.MinMaxSumCountAggregator()
        bound_valuerecorder = metrics.BoundValueRecorder(int, True, aggregator)
        bound_valuerecorder.update(4.0)
        self.assertEqual(
            bound_valuerecorder.aggregator.current, (4.0, 4.0, 4.0, 1)
        )
