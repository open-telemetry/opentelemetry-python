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
# type: ignore

from unittest import TestCase

from opentelemetry._metrics import Meter

# FIXME Test that the meter methods can be called concurrently safely.


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
