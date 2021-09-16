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

from logging import WARNING
from unittest import TestCase
from unittest.mock import Mock

from opentelemetry.metrics import Meter


class ChildMeter(Meter):
    def create_counter(self, name, unit="", description=""):
        super().create_counter(name, unit=unit, description=description)

    def create_up_down_counter(self, name, unit="", description=""):
        super().create_up_down_counter(
            name, unit=unit, description=description
        )

    def create_observable_counter(
        self, name, callback, unit="", description=""
    ):
        super().create_observable_counter(
            name, callback, unit=unit, description=description
        )

    def create_histogram(self, name, unit="", description=""):
        super().create_histogram(name, unit=unit, description=description)

    def create_observable_gauge(self, name, callback, unit="", description=""):
        super().create_observable_gauge(
            name, callback, unit=unit, description=description
        )

    def create_observable_up_down_counter(
        self, name, callback, unit="", description=""
    ):
        super().create_observable_up_down_counter(
            name, callback, unit=unit, description=description
        )


class TestMeter(TestCase):
    def test_create_counter(self):
        """
        Test that the meter provides a function to create a new Counter
        """

        self.assertTrue(hasattr(Meter, "create_counter"))
        self.assertTrue(Meter.create_counter.__isabstractmethod__)

    def test_create_up_down_counter(self):
        """
        Test that the meter provides a function to create a new UpDownCounter
        """

        self.assertTrue(hasattr(Meter, "create_up_down_counter"))
        self.assertTrue(Meter.create_up_down_counter.__isabstractmethod__)

    def test_create_observable_counter(self):
        """
        Test that the meter provides a function to create a new ObservableCounter
        """

        self.assertTrue(hasattr(Meter, "create_observable_counter"))
        self.assertTrue(Meter.create_observable_counter.__isabstractmethod__)

    def test_create_histogram(self):
        """
        Test that the meter provides a function to create a new Histogram
        """

        self.assertTrue(hasattr(Meter, "create_histogram"))
        self.assertTrue(Meter.create_histogram.__isabstractmethod__)

    def test_create_observable_gauge(self):
        """
        Test that the meter provides a function to create a new ObservableGauge
        """

        self.assertTrue(hasattr(Meter, "create_observable_gauge"))
        self.assertTrue(Meter.create_observable_gauge.__isabstractmethod__)

    def test_create_observable_up_down_counter(self):
        """
        Test that the meter provides a function to create a new
        ObservableUpDownCounter
        """

        self.assertTrue(hasattr(Meter, "create_observable_up_down_counter"))
        self.assertTrue(
            Meter.create_observable_up_down_counter.__isabstractmethod__
        )

    def test_no_repeated_instrument_names(self):
        """
        Test that the meter returns an error when multiple instruments are
        registered under the same Meter using the same name.
        """

        meter = ChildMeter("name")

        meter.create_counter("name")

        with self.assertLogs(level=WARNING):
            meter.create_counter("name")

        with self.assertLogs(level=WARNING):
            meter.create_up_down_counter("name")

        with self.assertLogs(level=WARNING):
            meter.create_observable_counter("name", Mock())

        with self.assertLogs(level=WARNING):
            meter.create_histogram("name")

        with self.assertLogs(level=WARNING):
            meter.create_observable_gauge("name", Mock())

        with self.assertLogs(level=WARNING):
            meter.create_observable_up_down_counter("name", Mock())

    def test_same_name_instrument_different_meter(self):
        """
        Test that is possible to register two instruments with the same name
        under different meters.
        """

        meter_0 = ChildMeter("meter_0")
        meter_1 = ChildMeter("meter_1")

        meter_0.create_counter("counter")
        meter_0.create_up_down_counter("up_down_counter")
        meter_0.create_observable_counter("observable_counter", Mock())
        meter_0.create_histogram("histogram")
        meter_0.create_observable_gauge("observable_gauge", Mock())
        meter_0.create_observable_up_down_counter(
            "observable_up_down_counter", Mock()
        )

        with self.assertRaises(AssertionError):
            with self.assertLogs(level=WARNING):
                meter_1.create_counter("counter")

        with self.assertRaises(AssertionError):
            with self.assertLogs(level=WARNING):
                meter_1.create_up_down_counter("up_down_counter")

        with self.assertRaises(AssertionError):
            with self.assertLogs(level=WARNING):
                meter_1.create_observable_counter("observable_counter", Mock())

        with self.assertRaises(AssertionError):
            with self.assertLogs(level=WARNING):
                meter_1.create_histogram("histogram")

        with self.assertRaises(AssertionError):
            with self.assertLogs(level=WARNING):
                meter_1.create_observable_gauge("observable_gauge", Mock())

        with self.assertRaises(AssertionError):
            with self.assertLogs(level=WARNING):
                meter_1.create_observable_up_down_counter(
                    "observable_up_down_counter", Mock()
                )
