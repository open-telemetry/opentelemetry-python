# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=no-self-use,protected-access

from logging import WARNING

# from time import time_ns
from unittest import TestCase
from unittest.mock import Mock, patch

from opentelemetry.context import Context
from opentelemetry.metrics import Observation
from opentelemetry.metrics._internal.instrument import CallbackOptions
from opentelemetry.sdk.metrics import (
    Counter,
    Histogram,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.sdk.metrics import _Gauge as _SDKGauge
from opentelemetry.sdk.metrics._internal.instrument import (
    _Counter,
    _Gauge,
    _Histogram,
    _ObservableCounter,
    _ObservableGauge,
    _ObservableUpDownCounter,
    _UpDownCounter,
)
from opentelemetry.sdk.metrics._internal.measurement import Measurement


class TestCounter(TestCase):
    def testname(self):
        self.assertEqual(_Counter("name", Mock(), Mock()).name, "name")
        self.assertEqual(_Counter("Name", Mock(), Mock()).name, "name")

    def test_add(self):
        mc = Mock()
        counter = _Counter("name", Mock(), mc)
        counter.add(1.0)
        mc.consume_measurement.assert_called_once()

    def test_add_non_monotonic(self):
        mc = Mock()
        counter = _Counter("name", Mock(), mc)
        with self.assertLogs(level=WARNING):
            counter.add(-1.0)
        mc.consume_measurement.assert_not_called()

    def test_add_nan(self):
        mc = Mock()
        counter = _Counter("name", Mock(), mc)
        with self.assertLogs(level=WARNING):
            counter.add(float("nan"))
        mc.consume_measurement.assert_not_called()

    def test_add_inf(self):
        mc = Mock()
        counter = _Counter("name", Mock(), mc)
        with self.assertLogs(level=WARNING):
            counter.add(float("inf"))
        mc.consume_measurement.assert_not_called()

    def test_disallow_direct_counter_creation(self):
        with self.assertRaises(TypeError):
            # pylint: disable=abstract-class-instantiated
            Counter("name", Mock(), Mock())


class TestUpDownCounter(TestCase):
    def test_add(self):
        mc = Mock()
        counter = _UpDownCounter("name", Mock(), mc)
        counter.add(1.0)
        mc.consume_measurement.assert_called_once()

    def test_add_non_monotonic(self):
        mc = Mock()
        counter = _UpDownCounter("name", Mock(), mc)
        counter.add(-1.0)
        mc.consume_measurement.assert_called_once()

    def test_add_nan(self):
        mc = Mock()
        counter = _UpDownCounter("name", Mock(), mc)
        with self.assertLogs(level=WARNING):
            counter.add(float("nan"))
        mc.consume_measurement.assert_not_called()

    def test_add_inf(self):
        mc = Mock()
        counter = _UpDownCounter("name", Mock(), mc)
        with self.assertLogs(level=WARNING):
            counter.add(float("inf"))
        mc.consume_measurement.assert_not_called()

    def test_disallow_direct_up_down_counter_creation(self):
        with self.assertRaises(TypeError):
            # pylint: disable=abstract-class-instantiated
            UpDownCounter("name", Mock(), Mock())


TEST_ATTRIBUTES = {"foo": "bar"}
TEST_CONTEXT = Context()
TEST_TIMESTAMP = 1_000_000_000


def callable_callback_0(options: CallbackOptions):
    return [
        Observation(1, attributes=TEST_ATTRIBUTES, context=TEST_CONTEXT),
        Observation(2, attributes=TEST_ATTRIBUTES, context=TEST_CONTEXT),
        Observation(3, attributes=TEST_ATTRIBUTES, context=TEST_CONTEXT),
    ]


def callable_callback_1(options: CallbackOptions):
    return [
        Observation(4, attributes=TEST_ATTRIBUTES, context=TEST_CONTEXT),
        Observation(5, attributes=TEST_ATTRIBUTES, context=TEST_CONTEXT),
        Observation(6, attributes=TEST_ATTRIBUTES, context=TEST_CONTEXT),
    ]


def generator_callback_0():
    options = yield
    assert isinstance(options, CallbackOptions)
    options = yield [
        Observation(1, attributes=TEST_ATTRIBUTES, context=TEST_CONTEXT),
        Observation(2, attributes=TEST_ATTRIBUTES, context=TEST_CONTEXT),
        Observation(3, attributes=TEST_ATTRIBUTES, context=TEST_CONTEXT),
    ]
    assert isinstance(options, CallbackOptions)


def generator_callback_1():
    options = yield
    assert isinstance(options, CallbackOptions)
    options = yield [
        Observation(4, attributes=TEST_ATTRIBUTES, context=TEST_CONTEXT),
        Observation(5, attributes=TEST_ATTRIBUTES, context=TEST_CONTEXT),
        Observation(6, attributes=TEST_ATTRIBUTES, context=TEST_CONTEXT),
    ]
    assert isinstance(options, CallbackOptions)


@patch(
    "opentelemetry.sdk.metrics._internal.instrument.time_ns",
    Mock(return_value=TEST_TIMESTAMP),
)
class TestObservableGauge(TestCase):
    def testname(self):
        self.assertEqual(_ObservableGauge("name", Mock(), Mock()).name, "name")
        self.assertEqual(_ObservableGauge("Name", Mock(), Mock()).name, "name")

    def test_callable_callback_0(self):
        observable_gauge = _ObservableGauge(
            "name", Mock(), Mock(), [callable_callback_0]
        )

        assert list(observable_gauge.callback(CallbackOptions())) == (
            [
                Measurement(
                    1,
                    TEST_TIMESTAMP,
                    instrument=observable_gauge,
                    context=TEST_CONTEXT,
                    attributes=TEST_ATTRIBUTES,
                ),
                Measurement(
                    2,
                    TEST_TIMESTAMP,
                    instrument=observable_gauge,
                    context=TEST_CONTEXT,
                    attributes=TEST_ATTRIBUTES,
                ),
                Measurement(
                    3,
                    TEST_TIMESTAMP,
                    instrument=observable_gauge,
                    context=TEST_CONTEXT,
                    attributes=TEST_ATTRIBUTES,
                ),
            ]
        )

    def test_callable_multiple_callable_callback(self):
        observable_gauge = _ObservableGauge(
            "name", Mock(), Mock(), [callable_callback_0, callable_callback_1]
        )

        self.assertEqual(
            list(observable_gauge.callback(CallbackOptions())),
            [
                Measurement(
                    1,
                    TEST_TIMESTAMP,
                    instrument=observable_gauge,
                    context=TEST_CONTEXT,
                    attributes=TEST_ATTRIBUTES,
                ),
                Measurement(
                    2,
                    TEST_TIMESTAMP,
                    instrument=observable_gauge,
                    context=TEST_CONTEXT,
                    attributes=TEST_ATTRIBUTES,
                ),
                Measurement(
                    3,
                    TEST_TIMESTAMP,
                    instrument=observable_gauge,
                    context=TEST_CONTEXT,
                    attributes=TEST_ATTRIBUTES,
                ),
                Measurement(
                    4,
                    TEST_TIMESTAMP,
                    instrument=observable_gauge,
                    context=TEST_CONTEXT,
                    attributes=TEST_ATTRIBUTES,
                ),
                Measurement(
                    5,
                    TEST_TIMESTAMP,
                    instrument=observable_gauge,
                    context=TEST_CONTEXT,
                    attributes=TEST_ATTRIBUTES,
                ),
                Measurement(
                    6,
                    TEST_TIMESTAMP,
                    instrument=observable_gauge,
                    context=TEST_CONTEXT,
                    attributes=TEST_ATTRIBUTES,
                ),
            ],
        )

    def test_generator_callback_0(self):
        observable_gauge = _ObservableGauge(
            "name", Mock(), Mock(), [generator_callback_0()]
        )

        self.assertEqual(
            list(observable_gauge.callback(CallbackOptions())),
            [
                Measurement(
                    1,
                    TEST_TIMESTAMP,
                    instrument=observable_gauge,
                    context=TEST_CONTEXT,
                    attributes=TEST_ATTRIBUTES,
                ),
                Measurement(
                    2,
                    TEST_TIMESTAMP,
                    instrument=observable_gauge,
                    context=TEST_CONTEXT,
                    attributes=TEST_ATTRIBUTES,
                ),
                Measurement(
                    3,
                    TEST_TIMESTAMP,
                    instrument=observable_gauge,
                    context=TEST_CONTEXT,
                    attributes=TEST_ATTRIBUTES,
                ),
            ],
        )

    def test_generator_multiple_generator_callback(self):
        observable_gauge = _ObservableGauge(
            "name",
            Mock(),
            Mock(),
            callbacks=[generator_callback_0(), generator_callback_1()],
        )

        self.assertEqual(
            list(observable_gauge.callback(CallbackOptions())),
            [
                Measurement(
                    1,
                    TEST_TIMESTAMP,
                    instrument=observable_gauge,
                    context=TEST_CONTEXT,
                    attributes=TEST_ATTRIBUTES,
                ),
                Measurement(
                    2,
                    TEST_TIMESTAMP,
                    instrument=observable_gauge,
                    context=TEST_CONTEXT,
                    attributes=TEST_ATTRIBUTES,
                ),
                Measurement(
                    3,
                    TEST_TIMESTAMP,
                    instrument=observable_gauge,
                    context=TEST_CONTEXT,
                    attributes=TEST_ATTRIBUTES,
                ),
                Measurement(
                    4,
                    TEST_TIMESTAMP,
                    instrument=observable_gauge,
                    context=TEST_CONTEXT,
                    attributes=TEST_ATTRIBUTES,
                ),
                Measurement(
                    5,
                    TEST_TIMESTAMP,
                    instrument=observable_gauge,
                    context=TEST_CONTEXT,
                    attributes=TEST_ATTRIBUTES,
                ),
                Measurement(
                    6,
                    TEST_TIMESTAMP,
                    instrument=observable_gauge,
                    context=TEST_CONTEXT,
                    attributes=TEST_ATTRIBUTES,
                ),
            ],
        )

    def test_nan_callback_value_is_dropped(self):
        def nan_callback(options: CallbackOptions):
            return [
                Observation(float("nan"), attributes=TEST_ATTRIBUTES),
                Observation(1, attributes=TEST_ATTRIBUTES),
            ]

        observable_gauge = _ObservableGauge(
            "name", Mock(), Mock(), [nan_callback]
        )
        with self.assertLogs(level=WARNING):
            measurements = list(observable_gauge.callback(CallbackOptions()))
        self.assertEqual(len(measurements), 1)
        self.assertEqual(measurements[0].value, 1)

    def test_inf_callback_value_is_dropped(self):
        def inf_callback(options: CallbackOptions):
            return [
                Observation(float("inf"), attributes=TEST_ATTRIBUTES),
                Observation(1, attributes=TEST_ATTRIBUTES),
            ]

        observable_gauge = _ObservableGauge(
            "name", Mock(), Mock(), [inf_callback]
        )
        with self.assertLogs(level=WARNING):
            measurements = list(observable_gauge.callback(CallbackOptions()))
        self.assertEqual(len(measurements), 1)
        self.assertEqual(measurements[0].value, 1)

    def test_disallow_direct_observable_gauge_creation(self):
        with self.assertRaises(TypeError):
            # pylint: disable=abstract-class-instantiated
            ObservableGauge("name", Mock(), Mock())


@patch(
    "opentelemetry.sdk.metrics._internal.instrument.time_ns",
    Mock(return_value=TEST_TIMESTAMP),
)
class TestObservableCounter(TestCase):
    def test_callable_callback_0(self):
        observable_counter = _ObservableCounter(
            "name", Mock(), Mock(), [callable_callback_0]
        )

        self.assertEqual(
            list(observable_counter.callback(CallbackOptions())),
            [
                Measurement(
                    1,
                    TEST_TIMESTAMP,
                    instrument=observable_counter,
                    context=TEST_CONTEXT,
                    attributes=TEST_ATTRIBUTES,
                ),
                Measurement(
                    2,
                    TEST_TIMESTAMP,
                    instrument=observable_counter,
                    context=TEST_CONTEXT,
                    attributes=TEST_ATTRIBUTES,
                ),
                Measurement(
                    3,
                    TEST_TIMESTAMP,
                    instrument=observable_counter,
                    context=TEST_CONTEXT,
                    attributes=TEST_ATTRIBUTES,
                ),
            ],
        )

    def test_generator_callback_0(self):
        observable_counter = _ObservableCounter(
            "name", Mock(), Mock(), [generator_callback_0()]
        )

        self.assertEqual(
            list(observable_counter.callback(CallbackOptions())),
            [
                Measurement(
                    1,
                    TEST_TIMESTAMP,
                    instrument=observable_counter,
                    context=TEST_CONTEXT,
                    attributes=TEST_ATTRIBUTES,
                ),
                Measurement(
                    2,
                    TEST_TIMESTAMP,
                    instrument=observable_counter,
                    context=TEST_CONTEXT,
                    attributes=TEST_ATTRIBUTES,
                ),
                Measurement(
                    3,
                    TEST_TIMESTAMP,
                    instrument=observable_counter,
                    context=TEST_CONTEXT,
                    attributes=TEST_ATTRIBUTES,
                ),
            ],
        )

    def test_disallow_direct_observable_counter_creation(self):
        with self.assertRaises(TypeError):
            # pylint: disable=abstract-class-instantiated
            ObservableCounter("name", Mock(), Mock())


class TestGauge(TestCase):
    def testname(self):
        self.assertEqual(_Gauge("name", Mock(), Mock()).name, "name")
        self.assertEqual(_Gauge("Name", Mock(), Mock()).name, "name")

    def test_set(self):
        mc = Mock()
        gauge = _Gauge("name", Mock(), mc)
        gauge.set(1.0)
        mc.consume_measurement.assert_called_once()

    def test_set_nan(self):
        mc = Mock()
        gauge = _Gauge("name", Mock(), mc)
        with self.assertLogs(level=WARNING):
            gauge.set(float("nan"))
        mc.consume_measurement.assert_not_called()

    def test_set_inf(self):
        mc = Mock()
        gauge = _Gauge("name", Mock(), mc)
        with self.assertLogs(level=WARNING):
            gauge.set(float("inf"))
        mc.consume_measurement.assert_not_called()

    def test_disallow_direct_counter_creation(self):
        with self.assertRaises(TypeError):
            # pylint: disable=abstract-class-instantiated
            _SDKGauge("name", Mock(), Mock())


@patch(
    "opentelemetry.sdk.metrics._internal.instrument.time_ns",
    Mock(return_value=TEST_TIMESTAMP),
)
class TestObservableUpDownCounter(TestCase):
    def test_callable_callback_0(self):
        observable_up_down_counter = _ObservableUpDownCounter(
            "name", Mock(), Mock(), [callable_callback_0]
        )

        self.assertEqual(
            list(observable_up_down_counter.callback(CallbackOptions())),
            [
                Measurement(
                    1,
                    TEST_TIMESTAMP,
                    instrument=observable_up_down_counter,
                    context=TEST_CONTEXT,
                    attributes=TEST_ATTRIBUTES,
                ),
                Measurement(
                    2,
                    TEST_TIMESTAMP,
                    instrument=observable_up_down_counter,
                    context=TEST_CONTEXT,
                    attributes=TEST_ATTRIBUTES,
                ),
                Measurement(
                    3,
                    TEST_TIMESTAMP,
                    instrument=observable_up_down_counter,
                    context=TEST_CONTEXT,
                    attributes=TEST_ATTRIBUTES,
                ),
            ],
        )

    def test_generator_callback_0(self):
        observable_up_down_counter = _ObservableUpDownCounter(
            "name", Mock(), Mock(), [generator_callback_0()]
        )

        self.assertEqual(
            list(observable_up_down_counter.callback(CallbackOptions())),
            [
                Measurement(
                    1,
                    TEST_TIMESTAMP,
                    instrument=observable_up_down_counter,
                    context=TEST_CONTEXT,
                    attributes=TEST_ATTRIBUTES,
                ),
                Measurement(
                    2,
                    TEST_TIMESTAMP,
                    instrument=observable_up_down_counter,
                    context=TEST_CONTEXT,
                    attributes=TEST_ATTRIBUTES,
                ),
                Measurement(
                    3,
                    TEST_TIMESTAMP,
                    instrument=observable_up_down_counter,
                    context=TEST_CONTEXT,
                    attributes=TEST_ATTRIBUTES,
                ),
            ],
        )

    def test_disallow_direct_observable_up_down_counter_creation(self):
        with self.assertRaises(TypeError):
            # pylint: disable=abstract-class-instantiated
            ObservableUpDownCounter("name", Mock(), Mock())


class TestHistogram(TestCase):
    def test_record(self):
        mc = Mock()
        hist = _Histogram("name", Mock(), mc)
        hist.record(1.0)
        mc.consume_measurement.assert_called_once()

    def test_record_non_monotonic(self):
        mc = Mock()
        hist = _Histogram("name", Mock(), mc)
        with self.assertLogs(level=WARNING):
            hist.record(-1.0)
        mc.consume_measurement.assert_not_called()

    def test_record_nan(self):
        mc = Mock()
        hist = _Histogram("name", Mock(), mc)
        with self.assertLogs(level=WARNING):
            hist.record(float("nan"))
        mc.consume_measurement.assert_not_called()

    def test_record_inf(self):
        mc = Mock()
        hist = _Histogram("name", Mock(), mc)
        with self.assertLogs(level=WARNING):
            hist.record(float("inf"))
        mc.consume_measurement.assert_not_called()

    def test_disallow_direct_histogram_creation(self):
        with self.assertRaises(TypeError):
            # pylint: disable=abstract-class-instantiated
            Histogram("name", Mock(), Mock())


class TestBind(TestCase):
    _sync_instruments = [
        (_Counter, "add"),
        (_UpDownCounter, "add"),
        (_Histogram, "record"),
        (_Gauge, "set"),
    ]

    def test_bound_record_flows_through_consumer(self):
        cases = [
            ({"key": "value"}, None, {"key": "value"}),
            (None, None, {}),
            (
                {"key": "value", "keep": 1},
                {"key": "override", "new": 2},
                {"key": "override", "keep": 1, "new": 2},
            ),
        ]
        for cls, method in self._sync_instruments:
            for bound_attrs, call_attrs, expected in cases:
                with self.subTest(
                    instrument=cls.__name__, bound_attrs=bound_attrs
                ):
                    mc = Mock()
                    instrument = cls("name", Mock(), mc)
                    bound = instrument._bind(bound_attrs)
                    getattr(bound, method)(1.0, call_attrs)
                    mc.consume_measurement.assert_called_once()
                    measurement = mc.consume_measurement.call_args.args[0]
                    self.assertEqual(measurement.value, 1.0)
                    self.assertEqual(measurement.attributes, expected)

    def test_bound_record_invalid(self):
        mc = Mock()
        counter = _Counter("name", Mock(), mc)
        bound = counter._bind({"key": "value"})
        with self.assertLogs(level=WARNING):
            bound.add(-1.0)
        mc.consume_measurement.assert_not_called()
