# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
# type: ignore

from dataclasses import FrozenInstanceError, dataclass
from logging import WARNING
from unittest import TestCase
from unittest.mock import Mock

from opentelemetry.metrics import InstrumentOptions, Meter, NoOpMeter

# FIXME Test that the meter methods can be called concurrently safely.


class ChildMeter(Meter):
    # pylint: disable=signature-differs
    def create_counter(self, name, unit="", description=""):
        super().create_counter(name, unit=unit, description=description)

    def create_up_down_counter(self, name, unit="", description=""):
        super().create_up_down_counter(name, unit=unit, description=description)

    def create_observable_counter(self, name, callbacks, unit="", description=""):
        super().create_observable_counter(
            name,
            callbacks,
            unit=unit,
            description=description,
        )

    def create_histogram(
        self,
        name,
        unit="",
        description="",
        *,
        explicit_bucket_boundaries_advisory=None,
    ):
        super().create_histogram(
            name,
            unit=unit,
            description=description,
            explicit_bucket_boundaries_advisory=explicit_bucket_boundaries_advisory,
        )

    def create_gauge(self, name, unit="", description=""):
        super().create_gauge(name, unit=unit, description=description)

    def create_observable_gauge(self, name, callbacks, unit="", description=""):
        super().create_observable_gauge(
            name,
            callbacks,
            unit=unit,
            description=description,
        )

    def create_observable_up_down_counter(self, name, callbacks, unit="", description=""):
        super().create_observable_up_down_counter(
            name,
            callbacks,
            unit=unit,
            description=description,
        )


class LegacyMeter(Meter):
    """A third party meter implemented without any knowledge of options."""

    # pylint: disable=signature-differs
    def create_counter(self, name, unit="", description=""):
        return ("counter", name, unit, description)

    def create_up_down_counter(self, name, unit="", description=""):
        return ("up_down_counter", name, unit, description)

    def create_observable_counter(self, name, callbacks=None, unit="", description=""):
        return ("observable_counter", name, callbacks, unit, description)

    def create_histogram(
        self,
        name,
        unit="",
        description="",
        *,
        explicit_bucket_boundaries_advisory=None,
    ):
        return ("histogram", name, unit, description, explicit_bucket_boundaries_advisory)

    def create_gauge(self, name, unit="", description=""):
        return ("gauge", name, unit, description)

    def create_observable_gauge(self, name, callbacks=None, unit="", description=""):
        return ("observable_gauge", name, callbacks, unit, description)

    def create_observable_up_down_counter(self, name, callbacks=None, unit="", description=""):
        return ("observable_up_down_counter", name, callbacks, unit, description)


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
            test_meter.create_observable_up_down_counter("observable_up_down_counter", Mock())
        except Exception as error:  # pylint: disable=broad-exception-caught
            self.fail(f"Unexpected exception raised {error}")

        for instrument_name in [
            "counter",
            "up_down_counter",
            "histogram",
            "gauge",
        ]:
            with self.assertNoLogs("opentelemetry.metrics._internal", level="WARNING"):
                getattr(test_meter, f"create_{instrument_name}")(instrument_name)

        for instrument_name in [
            "observable_counter",
            "observable_gauge",
            "observable_up_down_counter",
        ]:
            with self.assertNoLogs("opentelemetry.metrics._internal", level="WARNING"):
                getattr(test_meter, f"create_{instrument_name}")(instrument_name, Mock())

    def test_repeated_instrument_names_with_different_advisory(self):
        try:
            test_meter = NoOpMeter("name")

            test_meter.create_histogram("histogram", explicit_bucket_boundaries_advisory=[1.0])
        except Exception as error:  # pylint: disable=broad-exception-caught
            self.fail(f"Unexpected exception raised {error}")

        for instrument_name in [
            "histogram",
        ]:
            with self.assertLogs(level=WARNING):
                getattr(test_meter, f"create_{instrument_name}")(
                    instrument_name,
                )

    def test_repeated_instrument_names_with_different_attributes_advisory(
        self,
    ):
        test_meter = NoOpMeter("name")

        for instrument_name in [
            "counter",
            "up_down_counter",
            "histogram",
            "gauge",
            "observable_counter",
            "observable_up_down_counter",
            "observable_gauge",
        ]:
            with self.subTest(instrument_name=instrument_name):
                create_instrument = getattr(test_meter, f"create_{instrument_name}_with_options")
                create_instrument(instrument_name, options=InstrumentOptions(_attributes_advisory=["a", "b"]))

                with self.assertNoLogs(level=WARNING):
                    create_instrument(instrument_name, options=InstrumentOptions(_attributes_advisory=["b", "a"]))

                with self.assertLogs(level=WARNING):
                    create_instrument(instrument_name, options=InstrumentOptions(_attributes_advisory=["c"]))

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
        self.assertTrue(Meter.create_observable_up_down_counter.__isabstractmethod__)

    def test_with_options_defaults_delegate_to_legacy_methods(self):
        """Meters that only implement the create_* methods ignore options"""
        meter = LegacyMeter("name")
        options = InstrumentOptions(_attributes_advisory=["a"])
        callbacks = [Mock()]

        for instrument_name in ["counter", "up_down_counter", "gauge"]:
            with self.subTest(instrument_name=instrument_name):
                self.assertEqual(
                    getattr(meter, f"create_{instrument_name}_with_options")("foo", "s", "bar", options=options),
                    (instrument_name, "foo", "s", "bar"),
                )

        for instrument_name in [
            "observable_counter",
            "observable_gauge",
            "observable_up_down_counter",
        ]:
            with self.subTest(instrument_name=instrument_name):
                self.assertEqual(
                    getattr(meter, f"create_{instrument_name}_with_options")(
                        "foo", callbacks, "s", "bar", options=options
                    ),
                    (instrument_name, "foo", callbacks, "s", "bar"),
                )

        self.assertEqual(
            meter.create_histogram_with_options(
                "foo",
                "s",
                "bar",
                explicit_bucket_boundaries_advisory=[1.0],
                options=options,
            ),
            ("histogram", "foo", "s", "bar", [1.0]),
        )

    def test_instrument_options_frozen_and_slotted(self):
        options = InstrumentOptions(_attributes_advisory=["a"])

        with self.assertRaises(FrozenInstanceError):
            options._attributes_advisory = ["b"]  # pylint: disable=protected-access
        self.assertFalse(hasattr(options, "__dict__"))

    def test_instrument_options_accepts_specialized_subclass(self):
        @dataclass(frozen=True, slots=True, kw_only=True)
        class CounterOptions(InstrumentOptions):
            monotonic_hint: bool = False

        options = CounterOptions(_attributes_advisory=["a"], monotonic_hint=True)

        self.assertIsInstance(options, InstrumentOptions)
        self.assertEqual(
            LegacyMeter("name").create_counter_with_options("foo", options=options),
            ("counter", "foo", "", ""),
        )
        NoOpMeter("name").create_counter_with_options("foo", options=options)
