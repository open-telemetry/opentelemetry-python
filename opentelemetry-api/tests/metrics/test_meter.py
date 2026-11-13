# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
# type: ignore

from logging import WARNING
from unittest import TestCase
from unittest.mock import Mock

from opentelemetry.metrics import Instrument, Meter, NoOpMeter
from opentelemetry.metrics._internal import _ProxyMeter

# FIXME Test that the meter methods can be called concurrently safely.


class ChildMeter(Meter):
    # pylint: disable=signature-differs,arguments-differ
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
    """A third party meter implemented without any knowledge of _attributes_advisory."""

    # pylint: disable=signature-differs,arguments-differ
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
                create_instrument = getattr(test_meter, f"create_{instrument_name}")
                create_instrument(instrument_name, _attributes_advisory=["a", "b"])

                with self.assertNoLogs(level=WARNING):
                    create_instrument(instrument_name, _attributes_advisory=["b", "a"])

                with self.assertLogs(level=WARNING):
                    create_instrument(instrument_name, _attributes_advisory=["c"])

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

    def test_legacy_meter_ignores_attributes_advisory(self):
        """Meters implemented without _attributes_advisory ignore it"""
        # pylint: disable=unexpected-keyword-arg
        meter = LegacyMeter("name")
        callbacks = [Mock()]

        for instrument_name in ["counter", "up_down_counter", "gauge"]:
            with self.subTest(instrument_name=instrument_name):
                self.assertEqual(
                    getattr(meter, f"create_{instrument_name}")("foo", "s", "bar", _attributes_advisory=["a"]),
                    (instrument_name, "foo", "s", "bar"),
                )

        for instrument_name in [
            "observable_counter",
            "observable_gauge",
            "observable_up_down_counter",
        ]:
            with self.subTest(instrument_name=instrument_name):
                self.assertEqual(
                    getattr(meter, f"create_{instrument_name}")(
                        "foo", callbacks, "s", "bar", _attributes_advisory=["a"]
                    ),
                    (instrument_name, "foo", callbacks, "s", "bar"),
                )

        self.assertEqual(
            meter.create_histogram(
                "foo",
                "s",
                "bar",
                explicit_bucket_boundaries_advisory=[1.0],
                _attributes_advisory=["a"],
            ),
            ("histogram", "foo", "s", "bar", [1.0]),
        )

    def test_create_methods_ignore_unknown_kwargs(self):
        """The API meters accept and ignore keyword arguments they don't know"""
        # pylint: disable=unexpected-keyword-arg
        for meter in (NoOpMeter("name"), _ProxyMeter("name")):
            for instrument_name in ["counter", "up_down_counter", "histogram", "gauge"]:
                with self.subTest(meter=type(meter).__name__, instrument_name=instrument_name):
                    instrument = getattr(meter, f"create_{instrument_name}")(instrument_name, unknown=1)
                    self.assertIsInstance(instrument, Instrument)

            for instrument_name in [
                "observable_counter",
                "observable_gauge",
                "observable_up_down_counter",
            ]:
                with self.subTest(meter=type(meter).__name__, instrument_name=instrument_name):
                    instrument = getattr(meter, f"create_{instrument_name}")(
                        instrument_name, callbacks=[Mock()], unknown=1
                    )
                    self.assertIsInstance(instrument, Instrument)
