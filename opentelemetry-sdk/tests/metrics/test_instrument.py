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

from opentelemetry._metrics.measurement import Measurement as APIMeasurement
from opentelemetry.sdk._metrics.instrument import (
    Counter,
    Histogram,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.sdk._metrics.measurement import Measurement


class TestCounter(TestCase):
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


def callable_callback():
    return [
        APIMeasurement(1, attributes=TEST_ATTRIBUTES),
        APIMeasurement(2, attributes=TEST_ATTRIBUTES),
        APIMeasurement(3, attributes=TEST_ATTRIBUTES),
    ]


def generator_callback():
    yield [
        APIMeasurement(1, attributes=TEST_ATTRIBUTES),
        APIMeasurement(2, attributes=TEST_ATTRIBUTES),
        APIMeasurement(3, attributes=TEST_ATTRIBUTES),
    ]


class TestObservableGauge(TestCase):
    def test_callable_callback(self):
        observable_gauge = ObservableGauge(
            "name", Mock(), Mock(), callable_callback
        )

        self.assertEqual(
            list(observable_gauge.callback()),
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

    def test_generator_callback(self):
        observable_gauge = ObservableGauge(
            "name", Mock(), Mock(), generator_callback()
        )

        self.assertEqual(
            list(observable_gauge.callback()),
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


class TestObservableCounter(TestCase):
    def test_callable_callback(self):
        observable_counter = ObservableCounter(
            "name", Mock(), Mock(), callable_callback
        )

        self.assertEqual(
            list(observable_counter.callback()),
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

    def test_generator_callback(self):
        observable_counter = ObservableCounter(
            "name", Mock(), Mock(), generator_callback()
        )

        self.assertEqual(
            list(observable_counter.callback()),
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
    def test_callable_callback(self):
        observable_up_down_counter = ObservableUpDownCounter(
            "name", Mock(), Mock(), callable_callback
        )

        self.assertEqual(
            list(observable_up_down_counter.callback()),
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

    def test_generator_callback(self):
        observable_up_down_counter = ObservableUpDownCounter(
            "name", Mock(), Mock(), generator_callback()
        )

        self.assertEqual(
            list(observable_up_down_counter.callback()),
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
