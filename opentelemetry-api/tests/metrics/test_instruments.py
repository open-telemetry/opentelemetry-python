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

from inspect import Signature, isabstract, signature
from unittest import TestCase

from opentelemetry._metrics import Meter, NoOpMeter
from opentelemetry._metrics.instrument import (
    Counter,
    Histogram,
    Instrument,
    NoOpCounter,
    NoOpHistogram,
    NoOpUpDownCounter,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)

# FIXME Test that the instrument methods can be called concurrently safely.


class ChildInstrument(Instrument):
    def __init__(self, name, *args, unit="", description="", **kwargs):
        super().__init__(
            name, *args, unit=unit, description=description, **kwargs
        )


class TestCounter(TestCase):
    def test_create_counter(self):
        """
        Test that the Counter can be created with create_counter.
        """

        self.assertTrue(
            isinstance(NoOpMeter("name").create_counter("name"), Counter)
        )

    def test_api_counter_abstract(self):
        """
        Test that the API Counter is an abstract class.
        """

        self.assertTrue(isabstract(Counter))

    def test_create_counter_api(self):
        """
        Test that the API for creating a counter accepts the name of the instrument.
        Test that the API for creating a counter accepts the unit of the instrument.
        Test that the API for creating a counter accepts the description of the
        """

        create_counter_signature = signature(Meter.create_counter)
        self.assertIn("name", create_counter_signature.parameters.keys())
        self.assertIs(
            create_counter_signature.parameters["name"].default,
            Signature.empty,
        )

        create_counter_signature = signature(Meter.create_counter)
        self.assertIn("unit", create_counter_signature.parameters.keys())
        self.assertIs(create_counter_signature.parameters["unit"].default, "")

        create_counter_signature = signature(Meter.create_counter)
        self.assertIn(
            "description", create_counter_signature.parameters.keys()
        )
        self.assertIs(
            create_counter_signature.parameters["description"].default, ""
        )

    def test_counter_add_method(self):
        """
        Test that the counter has an add method.
        Test that the add method returns None.
        Test that the add method accepts optional attributes.
        Test that the add method accepts the increment amount.
        Test that the add method accepts only positive amounts.
        """

        self.assertTrue(hasattr(Counter, "add"))

        self.assertIsNone(NoOpCounter("name").add(1))

        add_signature = signature(Counter.add)
        self.assertIn("attributes", add_signature.parameters.keys())
        self.assertIs(add_signature.parameters["attributes"].default, None)

        self.assertIn("amount", add_signature.parameters.keys())
        self.assertIs(
            add_signature.parameters["amount"].default, Signature.empty
        )


class TestObservableCounter(TestCase):
    def test_create_observable_counter(self):
        """
        Test that the ObservableCounter can be created with create_observable_counter.
        """

        def callback():
            yield

        self.assertTrue(
            isinstance(
                NoOpMeter("name").create_observable_counter(
                    "name", callbacks=[callback()]
                ),
                ObservableCounter,
            )
        )

    def test_api_observable_counter_abstract(self):
        """
        Test that the API ObservableCounter is an abstract class.
        """

        self.assertTrue(isabstract(ObservableCounter))

    def test_create_observable_counter_api(self):
        """
        Test that the API for creating a observable_counter accepts the name of the instrument.
        Test that the API for creating a observable_counter accepts a sequence of callbacks.
        Test that the API for creating a observable_counter accepts the unit of the instrument.
        Test that the API for creating a observable_counter accepts the description of the instrument
        """

        create_observable_counter_signature = signature(
            Meter.create_observable_counter
        )
        self.assertIn(
            "name", create_observable_counter_signature.parameters.keys()
        )
        self.assertIs(
            create_observable_counter_signature.parameters["name"].default,
            Signature.empty,
        )
        create_observable_counter_signature = signature(
            Meter.create_observable_counter
        )
        self.assertIn(
            "callbacks", create_observable_counter_signature.parameters.keys()
        )
        self.assertIs(
            create_observable_counter_signature.parameters[
                "callbacks"
            ].default,
            None,
        )
        create_observable_counter_signature = signature(
            Meter.create_observable_counter
        )
        self.assertIn(
            "unit", create_observable_counter_signature.parameters.keys()
        )
        self.assertIs(
            create_observable_counter_signature.parameters["unit"].default, ""
        )

        create_observable_counter_signature = signature(
            Meter.create_observable_counter
        )
        self.assertIn(
            "description",
            create_observable_counter_signature.parameters.keys(),
        )
        self.assertIs(
            create_observable_counter_signature.parameters[
                "description"
            ].default,
            "",
        )

    def test_observable_counter_generator(self):
        """
        Test that the API for creating a asynchronous counter accepts a generator.
        Test that the generator function reports iterable of measurements.
        Test that there is a way to pass state to the generator.
        Test that the instrument accepts positive measurements.
        Test that the instrument does not accept negative measurements.
        """

        create_observable_counter_signature = signature(
            Meter.create_observable_counter
        )
        self.assertIn(
            "callbacks", create_observable_counter_signature.parameters.keys()
        )
        self.assertIs(
            create_observable_counter_signature.parameters["name"].default,
            Signature.empty,
        )


class TestHistogram(TestCase):
    def test_create_histogram(self):
        """
        Test that the Histogram can be created with create_histogram.
        """

        self.assertTrue(
            isinstance(NoOpMeter("name").create_histogram("name"), Histogram)
        )

    def test_api_histogram_abstract(self):
        """
        Test that the API Histogram is an abstract class.
        """

        self.assertTrue(isabstract(Histogram))

    def test_create_histogram_api(self):
        """
        Test that the API for creating a histogram accepts the name of the instrument.
        Test that the API for creating a histogram accepts the unit of the instrument.
        Test that the API for creating a histogram accepts the description of the
        """

        create_histogram_signature = signature(Meter.create_histogram)
        self.assertIn("name", create_histogram_signature.parameters.keys())
        self.assertIs(
            create_histogram_signature.parameters["name"].default,
            Signature.empty,
        )

        create_histogram_signature = signature(Meter.create_histogram)
        self.assertIn("unit", create_histogram_signature.parameters.keys())
        self.assertIs(
            create_histogram_signature.parameters["unit"].default, ""
        )

        create_histogram_signature = signature(Meter.create_histogram)
        self.assertIn(
            "description", create_histogram_signature.parameters.keys()
        )
        self.assertIs(
            create_histogram_signature.parameters["description"].default, ""
        )

    def test_histogram_record_method(self):
        """
        Test that the histogram has an record method.
        Test that the record method returns None.
        Test that the record method accepts optional attributes.
        Test that the record method accepts the increment amount.
        Test that the record method returns None.
        """

        self.assertTrue(hasattr(Histogram, "record"))

        self.assertIsNone(NoOpHistogram("name").record(1))

        record_signature = signature(Histogram.record)
        self.assertIn("attributes", record_signature.parameters.keys())
        self.assertIs(record_signature.parameters["attributes"].default, None)

        self.assertIn("amount", record_signature.parameters.keys())
        self.assertIs(
            record_signature.parameters["amount"].default, Signature.empty
        )

        self.assertIsNone(NoOpHistogram("name").record(1))


class TestObservableGauge(TestCase):
    def test_create_observable_gauge(self):
        """
        Test that the ObservableGauge can be created with create_observable_gauge.
        """

        def callback():
            yield

        self.assertTrue(
            isinstance(
                NoOpMeter("name").create_observable_gauge(
                    "name", [callback()]
                ),
                ObservableGauge,
            )
        )

    def test_api_observable_gauge_abstract(self):
        """
        Test that the API ObservableGauge is an abstract class.
        """

        self.assertTrue(isabstract(ObservableGauge))

    def test_create_observable_gauge_api(self):
        """
        Test that the API for creating a observable_gauge accepts the name of the instrument.
        Test that the API for creating a observable_gauge accepts a sequence of callbacks.
        Test that the API for creating a observable_gauge accepts the unit of the instrument.
        Test that the API for creating a observable_gauge accepts the description of the instrument
        """

        create_observable_gauge_signature = signature(
            Meter.create_observable_gauge
        )
        self.assertIn(
            "name", create_observable_gauge_signature.parameters.keys()
        )
        self.assertIs(
            create_observable_gauge_signature.parameters["name"].default,
            Signature.empty,
        )
        create_observable_gauge_signature = signature(
            Meter.create_observable_gauge
        )
        self.assertIn(
            "callbacks", create_observable_gauge_signature.parameters.keys()
        )
        self.assertIs(
            create_observable_gauge_signature.parameters["callbacks"].default,
            None,
        )
        create_observable_gauge_signature = signature(
            Meter.create_observable_gauge
        )
        self.assertIn(
            "unit", create_observable_gauge_signature.parameters.keys()
        )
        self.assertIs(
            create_observable_gauge_signature.parameters["unit"].default, ""
        )

        create_observable_gauge_signature = signature(
            Meter.create_observable_gauge
        )
        self.assertIn(
            "description", create_observable_gauge_signature.parameters.keys()
        )
        self.assertIs(
            create_observable_gauge_signature.parameters[
                "description"
            ].default,
            "",
        )

    def test_observable_gauge_callback(self):
        """
        Test that the API for creating a asynchronous gauge accepts a sequence of callbacks.
        Test that the callback function reports measurements.
        Test that there is a way to pass state to the callback.
        """

        create_observable_gauge_signature = signature(
            Meter.create_observable_gauge
        )
        self.assertIn(
            "callbacks", create_observable_gauge_signature.parameters.keys()
        )
        self.assertIs(
            create_observable_gauge_signature.parameters["name"].default,
            Signature.empty,
        )


class TestUpDownCounter(TestCase):
    def test_create_up_down_counter(self):
        """
        Test that the UpDownCounter can be created with create_up_down_counter.
        """

        self.assertTrue(
            isinstance(
                NoOpMeter("name").create_up_down_counter("name"),
                UpDownCounter,
            )
        )

    def test_api_up_down_counter_abstract(self):
        """
        Test that the API UpDownCounter is an abstract class.
        """

        self.assertTrue(isabstract(UpDownCounter))

    def test_create_up_down_counter_api(self):
        """
        Test that the API for creating a up_down_counter accepts the name of the instrument.
        Test that the API for creating a up_down_counter accepts the unit of the instrument.
        Test that the API for creating a up_down_counter accepts the description of the
        """

        create_up_down_counter_signature = signature(
            Meter.create_up_down_counter
        )
        self.assertIn(
            "name", create_up_down_counter_signature.parameters.keys()
        )
        self.assertIs(
            create_up_down_counter_signature.parameters["name"].default,
            Signature.empty,
        )

        create_up_down_counter_signature = signature(
            Meter.create_up_down_counter
        )
        self.assertIn(
            "unit", create_up_down_counter_signature.parameters.keys()
        )
        self.assertIs(
            create_up_down_counter_signature.parameters["unit"].default, ""
        )

        create_up_down_counter_signature = signature(
            Meter.create_up_down_counter
        )
        self.assertIn(
            "description", create_up_down_counter_signature.parameters.keys()
        )
        self.assertIs(
            create_up_down_counter_signature.parameters["description"].default,
            "",
        )

    def test_up_down_counter_add_method(self):
        """
        Test that the up_down_counter has an add method.
        Test that the add method returns None.
        Test that the add method accepts optional attributes.
        Test that the add method accepts the increment or decrement amount.
        Test that the add method accepts positive and negative amounts.
        """

        self.assertTrue(hasattr(UpDownCounter, "add"))

        self.assertIsNone(NoOpUpDownCounter("name").add(1))

        add_signature = signature(UpDownCounter.add)
        self.assertIn("attributes", add_signature.parameters.keys())
        self.assertIs(add_signature.parameters["attributes"].default, None)

        self.assertIn("amount", add_signature.parameters.keys())
        self.assertIs(
            add_signature.parameters["amount"].default, Signature.empty
        )


class TestObservableUpDownCounter(TestCase):
    def test_create_observable_up_down_counter(self):
        """
        Test that the ObservableUpDownCounter can be created with create_observable_up_down_counter.
        """

        def callback():
            yield

        self.assertTrue(
            isinstance(
                NoOpMeter("name").create_observable_up_down_counter(
                    "name", [callback()]
                ),
                ObservableUpDownCounter,
            )
        )

    def test_api_observable_up_down_counter_abstract(self):
        """
        Test that the API ObservableUpDownCounter is an abstract class.
        """

        self.assertTrue(isabstract(ObservableUpDownCounter))

    def test_create_observable_up_down_counter_api(self):
        """
        Test that the API for creating a observable_up_down_counter accepts the name of the instrument.
        Test that the API for creating a observable_up_down_counter accepts a sequence of callbacks.
        Test that the API for creating a observable_up_down_counter accepts the unit of the instrument.
        Test that the API for creating a observable_up_down_counter accepts the description of the instrument
        """

        create_observable_up_down_counter_signature = signature(
            Meter.create_observable_up_down_counter
        )
        self.assertIn(
            "name",
            create_observable_up_down_counter_signature.parameters.keys(),
        )
        self.assertIs(
            create_observable_up_down_counter_signature.parameters[
                "name"
            ].default,
            Signature.empty,
        )
        create_observable_up_down_counter_signature = signature(
            Meter.create_observable_up_down_counter
        )
        self.assertIn(
            "callbacks",
            create_observable_up_down_counter_signature.parameters.keys(),
        )
        self.assertIs(
            create_observable_up_down_counter_signature.parameters[
                "callbacks"
            ].default,
            None,
        )
        create_observable_up_down_counter_signature = signature(
            Meter.create_observable_up_down_counter
        )
        self.assertIn(
            "unit",
            create_observable_up_down_counter_signature.parameters.keys(),
        )
        self.assertIs(
            create_observable_up_down_counter_signature.parameters[
                "unit"
            ].default,
            "",
        )

        create_observable_up_down_counter_signature = signature(
            Meter.create_observable_up_down_counter
        )
        self.assertIn(
            "description",
            create_observable_up_down_counter_signature.parameters.keys(),
        )
        self.assertIs(
            create_observable_up_down_counter_signature.parameters[
                "description"
            ].default,
            "",
        )

    def test_observable_up_down_counter_callback(self):
        """
        Test that the API for creating a asynchronous up_down_counter accepts a sequence of callbacks.
        Test that the callback function reports measurements.
        Test that there is a way to pass state to the callback.
        Test that the instrument accepts positive and negative values.
        """

        create_observable_up_down_counter_signature = signature(
            Meter.create_observable_up_down_counter
        )
        self.assertIn(
            "callbacks",
            create_observable_up_down_counter_signature.parameters.keys(),
        )
        self.assertIs(
            create_observable_up_down_counter_signature.parameters[
                "name"
            ].default,
            Signature.empty,
        )
