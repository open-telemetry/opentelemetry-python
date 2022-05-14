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

from unittest import TestCase
from unittest.mock import Mock

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
from opentelemetry.sdk.metrics._internal.measurement import Measurement


class TestCounter(TestCase):
    def testname(self):
        self.assertEqual(Counter("name", Mock(), Mock()).name, "name")
        self.assertEqual(Counter("Name", Mock(), Mock()).name, "name")

    def test_add(self):
        mc = Mock()
        counter = Counter("name", Mock(), mc)
        counter.add(1.0)
        mc.consume_measurement.assert_called_once()

    def test_add_non_monotonic(self):
        mc = Mock()
        counter = Counter("name", Mock(), mc)
        counter.add(-1.0)
        mc.consume_measurement.assert_not_called()


class TestUpDownCounter(TestCase):
    def test_add(self):
        mc = Mock()
        counter = UpDownCounter("name", Mock(), mc)
        counter.add(1.0)
        mc.consume_measurement.assert_called_once()

    def test_add_non_monotonic(self):
        mc = Mock()
        counter = UpDownCounter("name", Mock(), mc)
        counter.add(-1.0)
        mc.consume_measurement.assert_called_once()


TEST_ATTRIBUTES = {"foo": "bar"}


def callable_callback_0(options: CallbackOptions):
    return [
        Observation(1, attributes=TEST_ATTRIBUTES),
        Observation(2, attributes=TEST_ATTRIBUTES),
        Observation(3, attributes=TEST_ATTRIBUTES),
    ]


def callable_callback_1(options: CallbackOptions):
    return [
        Observation(4, attributes=TEST_ATTRIBUTES),
        Observation(5, attributes=TEST_ATTRIBUTES),
        Observation(6, attributes=TEST_ATTRIBUTES),
    ]


def generator_callback_0():
    options = yield
    assert isinstance(options, CallbackOptions)
    options = yield [
        Observation(1, attributes=TEST_ATTRIBUTES),
        Observation(2, attributes=TEST_ATTRIBUTES),
        Observation(3, attributes=TEST_ATTRIBUTES),
    ]
    assert isinstance(options, CallbackOptions)


def generator_callback_1():
    options = yield
    assert isinstance(options, CallbackOptions)
    options = yield [
        Observation(4, attributes=TEST_ATTRIBUTES),
        Observation(5, attributes=TEST_ATTRIBUTES),
        Observation(6, attributes=TEST_ATTRIBUTES),
    ]
    assert isinstance(options, CallbackOptions)


class TestObservableGauge(TestCase):
    def testname(self):
        self.assertEqual(ObservableGauge("name", Mock(), Mock()).name, "name")
        self.assertEqual(ObservableGauge("Name", Mock(), Mock()).name, "name")

    def test_callable_callback_0(self):
        observable_gauge = ObservableGauge(
            "name", Mock(), Mock(), [callable_callback_0]
        )

        self.assertEqual(
            list(observable_gauge.callback(CallbackOptions())),
            [
                Measurement(
                    1, instrument=observable_gauge, attributes=TEST_ATTRIBUTES
                ),
                Measurement(
                    2, instrument=observable_gauge, attributes=TEST_ATTRIBUTES
                ),
                Measurement(
                    3, instrument=observable_gauge, attributes=TEST_ATTRIBUTES
                ),
            ],
        )

    def test_callable_multiple_callable_callback(self):
        observable_gauge = ObservableGauge(
            "name", Mock(), Mock(), [callable_callback_0, callable_callback_1]
        )

        self.assertEqual(
            list(observable_gauge.callback(CallbackOptions())),
            [
                Measurement(
                    1, instrument=observable_gauge, attributes=TEST_ATTRIBUTES
                ),
                Measurement(
                    2, instrument=observable_gauge, attributes=TEST_ATTRIBUTES
                ),
                Measurement(
                    3, instrument=observable_gauge, attributes=TEST_ATTRIBUTES
                ),
                Measurement(
                    4, instrument=observable_gauge, attributes=TEST_ATTRIBUTES
                ),
                Measurement(
                    5, instrument=observable_gauge, attributes=TEST_ATTRIBUTES
                ),
                Measurement(
                    6, instrument=observable_gauge, attributes=TEST_ATTRIBUTES
                ),
            ],
        )

    def test_generator_callback_0(self):
        observable_gauge = ObservableGauge(
            "name", Mock(), Mock(), [generator_callback_0()]
        )

        self.assertEqual(
            list(observable_gauge.callback(CallbackOptions())),
            [
                Measurement(
                    1, instrument=observable_gauge, attributes=TEST_ATTRIBUTES
                ),
                Measurement(
                    2, instrument=observable_gauge, attributes=TEST_ATTRIBUTES
                ),
                Measurement(
                    3, instrument=observable_gauge, attributes=TEST_ATTRIBUTES
                ),
            ],
        )

    def test_generator_multiple_generator_callback(self):
        self.maxDiff = None
        observable_gauge = ObservableGauge(
            "name",
            Mock(),
            Mock(),
            callbacks=[generator_callback_0(), generator_callback_1()],
        )

        self.assertEqual(
            list(observable_gauge.callback(CallbackOptions())),
            [
                Measurement(
                    1, instrument=observable_gauge, attributes=TEST_ATTRIBUTES
                ),
                Measurement(
                    2, instrument=observable_gauge, attributes=TEST_ATTRIBUTES
                ),
                Measurement(
                    3, instrument=observable_gauge, attributes=TEST_ATTRIBUTES
                ),
                Measurement(
                    4, instrument=observable_gauge, attributes=TEST_ATTRIBUTES
                ),
                Measurement(
                    5, instrument=observable_gauge, attributes=TEST_ATTRIBUTES
                ),
                Measurement(
                    6, instrument=observable_gauge, attributes=TEST_ATTRIBUTES
                ),
            ],
        )


class TestObservableCounter(TestCase):
    def test_callable_callback_0(self):
        observable_counter = ObservableCounter(
            "name", Mock(), Mock(), [callable_callback_0]
        )

        self.assertEqual(
            list(observable_counter.callback(CallbackOptions())),
            [
                Measurement(
                    1,
                    instrument=observable_counter,
                    attributes=TEST_ATTRIBUTES,
                ),
                Measurement(
                    2,
                    instrument=observable_counter,
                    attributes=TEST_ATTRIBUTES,
                ),
                Measurement(
                    3,
                    instrument=observable_counter,
                    attributes=TEST_ATTRIBUTES,
                ),
            ],
        )

    def test_generator_callback_0(self):
        observable_counter = ObservableCounter(
            "name", Mock(), Mock(), [generator_callback_0()]
        )

        self.assertEqual(
            list(observable_counter.callback(CallbackOptions())),
            [
                Measurement(
                    1,
                    instrument=observable_counter,
                    attributes=TEST_ATTRIBUTES,
                ),
                Measurement(
                    2,
                    instrument=observable_counter,
                    attributes=TEST_ATTRIBUTES,
                ),
                Measurement(
                    3,
                    instrument=observable_counter,
                    attributes=TEST_ATTRIBUTES,
                ),
            ],
        )


class TestObservableUpDownCounter(TestCase):
    def test_callable_callback_0(self):
        observable_up_down_counter = ObservableUpDownCounter(
            "name", Mock(), Mock(), [callable_callback_0]
        )

        self.assertEqual(
            list(observable_up_down_counter.callback(CallbackOptions())),
            [
                Measurement(
                    1,
                    instrument=observable_up_down_counter,
                    attributes=TEST_ATTRIBUTES,
                ),
                Measurement(
                    2,
                    instrument=observable_up_down_counter,
                    attributes=TEST_ATTRIBUTES,
                ),
                Measurement(
                    3,
                    instrument=observable_up_down_counter,
                    attributes=TEST_ATTRIBUTES,
                ),
            ],
        )

    def test_generator_callback_0(self):
        observable_up_down_counter = ObservableUpDownCounter(
            "name", Mock(), Mock(), [generator_callback_0()]
        )

        self.assertEqual(
            list(observable_up_down_counter.callback(CallbackOptions())),
            [
                Measurement(
                    1,
                    instrument=observable_up_down_counter,
                    attributes=TEST_ATTRIBUTES,
                ),
                Measurement(
                    2,
                    instrument=observable_up_down_counter,
                    attributes=TEST_ATTRIBUTES,
                ),
                Measurement(
                    3,
                    instrument=observable_up_down_counter,
                    attributes=TEST_ATTRIBUTES,
                ),
            ],
        )


class TestHistogram(TestCase):
    def test_record(self):
        mc = Mock()
        hist = Histogram("name", Mock(), mc)
        hist.record(1.0)
        mc.consume_measurement.assert_called_once()

    def test_record_non_monotonic(self):
        mc = Mock()
        hist = Histogram("name", Mock(), mc)
        hist.record(-1.0)
        mc.consume_measurement.assert_not_called()
