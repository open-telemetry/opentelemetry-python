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

from logging import WARNING
from unittest import TestCase
from unittest.mock import Mock

from opentelemetry.metrics import Meter, NoOpMeter

# FIXME Test that the meter methods can be called concurrently safely.


class ChildMeter(Meter):
    # pylint: disable=signature-differs
    def create_counter(self, name, unit="", description=""):
        super().create_counter(name, unit=unit, description=description)

    def create_up_down_counter(self, name, unit="", description=""):
        super().create_up_down_counter(
            name, unit=unit, description=description
        )

    def create_observable_counter(
        self, name, callbacks, unit="", description=""
    ):
        super().create_observable_counter(
            name, callbacks, unit=unit, description=description
        )

    def create_histogram(self, name, unit="", description=""):
        super().create_histogram(name, unit=unit, description=description)

    def create_gauge(self, name, unit="", description=""):
        super().create_gauge(name, unit=unit, description=description)

    def create_observable_gauge(
        self, name, callbacks, unit="", description=""
    ):
        super().create_observable_gauge(
            name, callbacks, unit=unit, description=description
        )

    def create_observable_up_down_counter(
        self, name, callbacks, unit="", description=""
    ):
        super().create_observable_up_down_counter(
            name, callbacks, unit=unit, description=description
        )


class TestMeter(TestCase):
    # pylint: disable=no-member
    def test_repeated_instrument_names(self):

        try:
            test_meter = NoOpMeter("name")

            test_meter.create_counter("counter")
            test_meter.create_up_down_counter("up_down_counter")
            test_meter.create_observable_counter("observable_counter", Mock())
            test_meter.create_histogram("histogram")
            test_meter.create_gauge("gauge")
            test_meter.create_observable_gauge("observable_gauge", Mock())
            test_meter.create_observable_up_down_counter(
                "observable_up_down_counter", Mock()
            )
        except Exception as error:  # pylint: disable=broad-exception-caught
            self.fail(f"Unexpected exception raised {error}")

        for instrument_name in [
            "counter",
            "up_down_counter",
            "histogram",
            "gauge",
        ]:
            with self.assertLogs(level=WARNING):
                getattr(test_meter, f"create_{instrument_name}")(
                    instrument_name
                )

        for instrument_name in [
            "observable_counter",
            "observable_gauge",
            "observable_up_down_counter",
        ]:
            with self.assertLogs(level=WARNING):
                getattr(test_meter, f"create_{instrument_name}")(
                    instrument_name, Mock()
                )

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

    def test_create_gauge(self):
        """
        Test that the meter provides a function to create a new Gauge
        """

        self.assertTrue(hasattr(Meter, "create_gauge"))

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
