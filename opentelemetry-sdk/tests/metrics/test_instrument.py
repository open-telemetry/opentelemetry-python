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

# pylint: disable=no-self-use

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

    def test_disallow_direct_histogram_creation(self):
        with self.assertRaises(TypeError):
            # pylint: disable=abstract-class-instantiated
            Histogram("name", Mock(), Mock())
