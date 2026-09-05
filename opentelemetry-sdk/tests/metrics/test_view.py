# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=protected-access

from unittest import TestCase
from unittest.mock import Mock

from opentelemetry.sdk.metrics import Counter, MeterProvider
from opentelemetry.sdk.metrics.view import View


class TestView(TestCase):
    def test_required_instrument_criteria(self):
        with self.assertRaises(Exception):
            View()

    def test_instrument_type(self):
        self.assertTrue(View(instrument_type=Mock)._match(Mock()))

    def test_instrument_name(self):
        mock_instrument = Mock()
        mock_instrument.configure_mock(name="instrument_name")

        self.assertTrue(View(instrument_name="instrument_name")._match(mock_instrument))

    def test_instrument_name_case_insensitive(self):
        # The SDK stores instrument names lower-cased, so a view pattern that
        # reuses the instrument's original name must still match regardless of
        # case (and regardless of the host platform).
        mock_instrument = Mock()
        mock_instrument.configure_mock(name="instrument_name")

        self.assertTrue(View(instrument_name="Instrument_Name")._match(mock_instrument))
        self.assertTrue(View(instrument_name="INSTRUMENT_*")._match(mock_instrument))
        self.assertFalse(View(instrument_name="other_name")._match(mock_instrument))

    def test_instrument_unit(self):
        mock_instrument = Mock()
        mock_instrument.configure_mock(unit="instrument_unit")

        self.assertTrue(View(instrument_unit="instrument_unit")._match(mock_instrument))

    def test_instrument_unit_case_sensitive(self):
        # Units are case-sensitive and matching must not depend on the host
        # platform's filename case sensitivity.
        mock_instrument = Mock()
        mock_instrument.configure_mock(unit="By")

        self.assertTrue(View(instrument_unit="By")._match(mock_instrument))
        self.assertFalse(View(instrument_unit="by")._match(mock_instrument))

    def test_meter_name(self):
        self.assertTrue(View(meter_name="meter_name")._match(Mock(**{"instrumentation_scope.name": "meter_name"})))

    def test_meter_version(self):
        self.assertTrue(
            View(meter_version="meter_version")._match(Mock(**{"instrumentation_scope.version": "meter_version"}))
        )

    def test_meter_schema_url(self):
        self.assertTrue(
            View(meter_schema_url="meter_schema_url")._match(
                Mock(**{"instrumentation_scope.schema_url": "meter_schema_url"})
            )
        )
        self.assertFalse(
            View(meter_schema_url="meter_schema_url")._match(
                Mock(**{"instrumentation_scope.schema_url": "meter_schema_urlabc"})
            )
        )
        self.assertTrue(
            View(meter_schema_url="meter_schema_url")._match(
                Mock(**{"instrumentation_scope.schema_url": "meter_schema_url"})
            )
        )

    def test_additive_criteria(self):
        view = View(
            meter_name="meter_name",
            meter_version="meter_version",
            meter_schema_url="meter_schema_url",
        )

        self.assertTrue(
            view._match(
                Mock(
                    **{
                        "instrumentation_scope.name": "meter_name",
                        "instrumentation_scope.version": "meter_version",
                        "instrumentation_scope.schema_url": "meter_schema_url",
                    }
                )
            )
        )
        self.assertFalse(
            view._match(
                Mock(
                    **{
                        "instrumentation_scope.name": "meter_name",
                        "instrumentation_scope.version": "meter_version",
                        "instrumentation_scope.schema_url": "meter_schema_vrl",
                    }
                )
            )
        )

    def test_view_name(self):
        with self.assertRaises(Exception):
            View(name="name", instrument_name="instrument_name*")

    def test_view_name_wildcard(self):
        with self.assertRaisesRegex(
            Exception,
            r"View name declared with wildcard characters in instrument_name",
        ):
            View(name="name", instrument_name="instrument_name*")

        with self.assertRaisesRegex(
            Exception,
            r"View name declared with wildcard characters in instrument_name",
        ):
            View(name="name", instrument_name="*")

        with self.assertRaisesRegex(
            Exception,
            r"View name declared with wildcard characters in instrument_name",
        ):
            View(name="name", instrument_name="instrument?name")

    def test_view_name_without_instrument_name(self):
        with self.assertRaisesRegex(
            Exception,
            r"View custom_name specifies a name but no instrument_name, which may select multiple instruments",
        ):
            View(name="custom_name", instrument_type=Mock)

        with self.assertRaisesRegex(
            Exception,
            r"View custom_name specifies a name but no instrument_name, which may select multiple instruments",
        ):
            View(name="custom_name", meter_name="some_meter")

        with self.assertRaisesRegex(
            Exception,
            r"View custom_name specifies a name but no instrument_name, which may select multiple instruments",
        ):
            View(name="custom_name", instrument_unit="ms")

        with self.assertRaisesRegex(
            Exception,
            r"View custom_name specifies a name but no instrument_name, which may select multiple instruments",
        ):
            View(name="custom_name", meter_version="1.0.0")

        with self.assertRaisesRegex(
            Exception,
            r"View custom_name specifies a name but no instrument_name, which may select multiple instruments",
        ):
            View(name="custom_name", meter_schema_url="https://opentelemetry.io/schemas/1.4.0")

        with self.assertRaisesRegex(
            Exception,
            r"View name specifies a name but no instrument_name, which may select multiple instruments",
        ):
            View(name="name", instrument_type=Counter)

        with self.assertRaisesRegex(
            Exception,
            r"View custom_name specifies a name but no instrument_name, which may select multiple instruments",
        ):
            View(
                name="custom_name",
                instrument_type=Counter,
                meter_name="some_meter",
                instrument_unit="ms",
            )

        with self.assertRaisesRegex(
            Exception,
            r"View name specifies a name but no instrument_name, which may select multiple instruments",
        ):
            MeterProvider(views=[View(name="name", instrument_type=Counter)])

    def test_unnamed_view_without_instrument_name(self):
        view = View(instrument_type=Counter)
        self.assertIsNone(view._name)
        self.assertIs(view._instrument_type, Counter)
        self.assertIsNone(view._instrument_name)

        meter_provider = MeterProvider(views=[view])
        self.assertIsNotNone(meter_provider)

    def test_view_name_with_concrete_instrument_name(self):
        mock_instrument = Mock()
        mock_instrument.configure_mock(name="my_counter")

        view = View(name="custom_name", instrument_name="my_counter")
        self.assertEqual(view._name, "custom_name")
        self.assertEqual(view._instrument_name, "my_counter")
        self.assertTrue(view._match(mock_instrument))

        other_instrument = Mock()
        other_instrument.configure_mock(name="other_counter")
        self.assertFalse(view._match(other_instrument))

        view_with_type = View(
            name="custom_name",
            instrument_name="my_counter",
            instrument_type=Mock,
        )
        self.assertTrue(view_with_type._match(mock_instrument))

        view_with_counter = View(
            name="custom_name",
            instrument_name="my_counter",
            instrument_type=Counter,
        )
        self.assertEqual(view_with_counter._name, "custom_name")
        self.assertEqual(view_with_counter._instrument_name, "my_counter")
        self.assertIs(view_with_counter._instrument_type, Counter)
