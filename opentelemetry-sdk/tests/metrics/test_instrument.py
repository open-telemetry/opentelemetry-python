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

from opentelemetry.metrics.instrument import (
    Adding,
    Asynchronous,
    Counter,
    Grouping,
    Histogram,
    Instrument,
    Monotonic,
    NonMonotonic,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    Synchronous,
    UpDownCounter,
)
from opentelemetry.sdk.metrics.instrument import Counter as SDKCounter
from opentelemetry.sdk.metrics.instrument import Histogram as SDKHistogram
from opentelemetry.sdk.metrics.instrument import (
    ObservableCounter as SDKObservableCounter,
)
from opentelemetry.sdk.metrics.instrument import (
    ObservableGauge as SDKObservableGauge,
)
from opentelemetry.sdk.metrics.instrument import (
    ObservableUpDownCounter as SDKObservableUpDownCounter,
)
from opentelemetry.sdk.metrics.instrument import (
    UpDownCounter as SDKUpDownCounter,
)
from opentelemetry.sdk.metrics.meter import Meter as SDKMeter


class TestInstrument(TestCase):
    def test_create_counter(self):
        counter = SDKMeter().create_counter(
            "name", unit="unit", description="description"
        )
        self.assertEqual(counter.name, "name")
        self.assertEqual(counter.unit, "unit")
        self.assertEqual(counter.description, "description")
        self.assertIsInstance(counter, SDKCounter)
        self.assertIsInstance(counter, Counter)
        self.assertIsInstance(counter, Monotonic)
        self.assertIsInstance(counter, Adding)
        self.assertIsInstance(counter, Synchronous)
        self.assertIsInstance(counter, Instrument)

    def test_create_up_down_counter(self):
        up_down_counter = SDKMeter().create_up_down_counter(
            "name", unit="unit", description="description"
        )
        self.assertEqual(up_down_counter.name, "name")
        self.assertEqual(up_down_counter.unit, "unit")
        self.assertEqual(up_down_counter.description, "description")
        self.assertIsInstance(up_down_counter, SDKUpDownCounter)
        self.assertIsInstance(up_down_counter, UpDownCounter)
        self.assertIsInstance(up_down_counter, NonMonotonic)
        self.assertIsInstance(up_down_counter, Adding)
        self.assertIsInstance(up_down_counter, Synchronous)
        self.assertIsInstance(up_down_counter, Instrument)

    def test_create_observable_counter(self):
        callback = Mock()
        observable_counter = SDKMeter().create_observable_counter(
            "name", callback, unit="unit", description="description"
        )
        self.assertEqual(observable_counter.name, "name")
        self.assertIs(observable_counter._callback, callback)
        self.assertEqual(observable_counter.unit, "unit")
        self.assertEqual(observable_counter.description, "description")
        self.assertIsInstance(observable_counter, SDKObservableCounter)
        self.assertIsInstance(observable_counter, ObservableCounter)
        self.assertIsInstance(observable_counter, Monotonic)
        self.assertIsInstance(observable_counter, Adding)
        self.assertIsInstance(observable_counter, Asynchronous)
        self.assertIsInstance(observable_counter, Instrument)

    def test_create_observable_up_down_counter(self):
        callback = Mock()
        observable_up_down_counter = (
            SDKMeter().create_observable_up_down_counter(
                "name", callback, unit="unit", description="description"
            )
        )
        self.assertEqual(observable_up_down_counter.name, "name")
        self.assertIs(observable_up_down_counter._callback, callback)
        self.assertEqual(observable_up_down_counter.unit, "unit")
        self.assertEqual(observable_up_down_counter.description, "description")
        self.assertIsInstance(
            observable_up_down_counter, SDKObservableUpDownCounter
        )
        self.assertIsInstance(
            observable_up_down_counter, ObservableUpDownCounter
        )
        self.assertIsInstance(observable_up_down_counter, NonMonotonic)
        self.assertIsInstance(observable_up_down_counter, Adding)
        self.assertIsInstance(observable_up_down_counter, Asynchronous)
        self.assertIsInstance(observable_up_down_counter, Instrument)

    def test_create_histogram(self):
        histogram = SDKMeter().create_histogram(
            "name", unit="unit", description="description"
        )
        self.assertEqual(histogram.name, "name")
        self.assertEqual(histogram.unit, "unit")
        self.assertEqual(histogram.description, "description")
        self.assertIsInstance(histogram, SDKHistogram)
        self.assertIsInstance(histogram, Histogram)
        self.assertIsInstance(histogram, Grouping)
        self.assertIsInstance(histogram, Synchronous)
        self.assertIsInstance(histogram, Instrument)

    def test_create_observable_gauge(self):
        callback = Mock()
        observable_gauge = SDKMeter().create_observable_gauge(
            "name", callback, unit="unit", description="description"
        )
        self.assertEqual(observable_gauge.name, "name")
        self.assertIs(observable_gauge._callback, callback)
        self.assertEqual(observable_gauge.unit, "unit")
        self.assertEqual(observable_gauge.description, "description")
        self.assertIsInstance(observable_gauge, SDKObservableGauge)
        self.assertIsInstance(observable_gauge, ObservableGauge)
        self.assertIsInstance(observable_gauge, Grouping)
        self.assertIsInstance(observable_gauge, Asynchronous)
        self.assertIsInstance(observable_gauge, Instrument)
