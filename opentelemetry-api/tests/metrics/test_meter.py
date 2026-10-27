# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
# type: ignore

from logging import WARNING
from unittest import TestCase
from unittest.mock import Mock

from opentelemetry.metrics import Meter, NoOpMeter

# FIXME Test that the meter methods can be called concurrently safely.


class ChildMeter(Meter):
    # pylint: disable=signature-differs
    def create_counter(self, name, unit="", description="", *, _opt_in_advisory=None):
        super().create_counter(
            name,
            unit=unit,
            description=description,
            _opt_in_advisory=_opt_in_advisory,
        )

    def create_up_down_counter(self, name, unit="", description="", *, _opt_in_advisory=None):
        super().create_up_down_counter(
            name,
            unit=unit,
            description=description,
            _opt_in_advisory=_opt_in_advisory,
        )

    def create_observable_counter(
        self,
        name,
        callbacks,
        unit="",
        description="",
        *,
        _opt_in_advisory=None,
    ):
        super().create_observable_counter(
            name,
            callbacks,
            unit=unit,
            description=description,
            _opt_in_advisory=_opt_in_advisory,
        )

    def create_histogram(
        self,
        name,
        unit="",
        description="",
        *,
        explicit_bucket_boundaries_advisory=None,
        _opt_in_advisory=None,
    ):
        super().create_histogram(
            name,
            unit=unit,
            description=description,
            explicit_bucket_boundaries_advisory=explicit_bucket_boundaries_advisory,
            _opt_in_advisory=_opt_in_advisory,
        )

    def create_gauge(self, name, unit="", description="", *, _opt_in_advisory=None):
        super().create_gauge(
            name,
            unit=unit,
            description=description,
            _opt_in_advisory=_opt_in_advisory,
        )

    def create_observable_gauge(
        self,
        name,
        callbacks,
        unit="",
        description="",
        *,
        _opt_in_advisory=None,
    ):
        super().create_observable_gauge(
            name,
            callbacks,
            unit=unit,
            description=description,
            _opt_in_advisory=_opt_in_advisory,
        )

    def create_observable_up_down_counter(
        self,
        name,
        callbacks,
        unit="",
        description="",
        *,
        _opt_in_advisory=None,
    ):
        super().create_observable_up_down_counter(
            name,
            callbacks,
            unit=unit,
            description=description,
            _opt_in_advisory=_opt_in_advisory,
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

            test_meter.create_counter("counter", _opt_in_advisory=True)
            test_meter.create_up_down_counter("up_down_counter", _opt_in_advisory=True)
            test_meter.create_observable_counter(
                "observable_counter",
                Mock(),
                _opt_in_advisory=True,
            )
            test_meter.create_histogram("histogram", explicit_bucket_boundaries_advisory=[1.0])
            test_meter.create_histogram("histogram_opt_in", _opt_in_advisory=True)
            test_meter.create_gauge("gauge", _opt_in_advisory=True)
            test_meter.create_observable_gauge(
                "observable_gauge",
                Mock(),
                _opt_in_advisory=True,
            )
            test_meter.create_observable_up_down_counter(
                "observable_up_down_counter",
                Mock(),
                _opt_in_advisory=True,
            )
        except Exception as error:  # pylint: disable=broad-exception-caught
            self.fail(f"Unexpected exception raised {error}")

        for method_name, instrument_name in [
            ("create_counter", "counter"),
            ("create_up_down_counter", "up_down_counter"),
            ("create_histogram", "histogram"),
            ("create_histogram", "histogram_opt_in"),
            ("create_gauge", "gauge"),
        ]:
            with self.assertLogs(level=WARNING):
                getattr(test_meter, method_name)(
                    instrument_name,
                )

        for instrument_name in [
            "observable_counter",
            "observable_gauge",
            "observable_up_down_counter",
        ]:
            with self.assertLogs(level=WARNING):
                getattr(test_meter, f"create_{instrument_name}")(
                    instrument_name,
                    Mock(),
                )

    def test_opt_in_advisory_validation(self):
        test_meter = NoOpMeter("name")
        for idx, invalid_value in enumerate(("true", 123, [True])):
            with self.subTest(invalid_value=invalid_value):
                with self.assertLogs(level=WARNING) as log:
                    test_meter.create_counter(
                        f"counter_{idx}",
                        _opt_in_advisory=invalid_value,
                    )
                self.assertIn(
                    "_opt_in_advisory must be a bool",
                    log.output[0],
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
        self.assertTrue(Meter.create_observable_up_down_counter.__isabstractmethod__)
