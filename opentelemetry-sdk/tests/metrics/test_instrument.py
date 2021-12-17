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
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
)


class TestObservableGauge(TestCase):
    def test_callable_callback(self):
        def callback():
            return [1, 2, 3]

        observable_gauge = ObservableGauge(Mock(), "name", Mock(), callback)

        mock = Mock()
        observable_gauge._measurement_consumer = mock

        observable_gauge.callback()

        mock.consume.assert_called_with(3)

    def test_generator_callback(self):
        def callback():
            yield [1, 2, 3]

        observable_gauge = ObservableGauge(Mock(), "name", Mock(), callback())

        mock = Mock()
        observable_gauge._measurement_consumer = mock

        observable_gauge.callback()

        mock.consume.assert_called_with(3)


class TestObservableCounter(TestCase):
    def test_callable_callback(self):
        def callback():
            return [1, 2, 3]

        observable_counter = ObservableCounter(
            Mock(), "name", Mock(), callback
        )

        mock = Mock()
        observable_counter._measurement_consumer = mock

        observable_counter.callback()

        mock.consume.assert_called_with(3)

    def test_generator_callback(self):
        def callback():
            yield [1, 2, 3]

        observable_counter = ObservableCounter(
            Mock(), "name", Mock(), callback()
        )

        mock = Mock()
        observable_counter._measurement_consumer = mock

        observable_counter.callback()

        mock.consume.assert_called_with(3)


class TestObservableUpDownCounter(TestCase):
    def test_callable_callback(self):
        def callback():
            return [1, 2, 3]

        observable_up_down_counter = ObservableUpDownCounter(
            Mock(), "name", Mock(), callback
        )

        mock = Mock()
        observable_up_down_counter._measurement_consumer = mock

        observable_up_down_counter.callback()

        mock.consume.assert_called_with(3)

    def test_generator_callback(self):
        def callback():
            yield [1, 2, 3]

        observable_up_down_counter = ObservableUpDownCounter(
            Mock(), "name", Mock(), callback()
        )

        mock = Mock()
        observable_up_down_counter._measurement_consumer = mock

        observable_up_down_counter.callback()

        mock.consume.assert_called_with(3)
