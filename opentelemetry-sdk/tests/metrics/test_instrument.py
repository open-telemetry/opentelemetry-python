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

from opentelemetry.sdk._metrics.instrument import (
    Counter,
    Histogram,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)


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


class TestObservableGauge(TestCase):
    def test_callable_callback(self):
        def callback():
            return [1, 2, 3]

        observable_gauge = ObservableGauge("name", Mock(), Mock(), callback)

        self.assertEqual(observable_gauge.callback(), [1, 2, 3])

    def test_generator_callback(self):
        def callback():
            yield [1, 2, 3]

        observable_gauge = ObservableGauge("name", Mock(), Mock(), callback())

        self.assertEqual(observable_gauge.callback(), [1, 2, 3])


class TestObservableCounter(TestCase):
    def test_callable_callback(self):
        def callback():
            return [1, 2, 3]

        observable_counter = ObservableCounter(
            "name", Mock(), Mock(), callback
        )

        self.assertEqual(observable_counter.callback(), [1, 2, 3])

    def test_generator_callback(self):
        def callback():
            yield [1, 2, 3]

        observable_counter = ObservableCounter(
            "name", Mock(), Mock(), callback()
        )

        self.assertEqual(observable_counter.callback(), [1, 2, 3])


class TestObservableUpDownCounter(TestCase):
    def test_callable_callback(self):
        def callback():
            return [1, 2, 3]

        observable_up_down_counter = ObservableUpDownCounter(
            "name", Mock(), Mock(), callback
        )

        self.assertEqual(observable_up_down_counter.callback(), [1, 2, 3])

    def test_generator_callback(self):
        def callback():
            yield [1, 2, 3]

        observable_up_down_counter = ObservableUpDownCounter(
            "name", Mock(), Mock(), callback()
        )

        self.assertEqual(observable_up_down_counter.callback(), [1, 2, 3])


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
