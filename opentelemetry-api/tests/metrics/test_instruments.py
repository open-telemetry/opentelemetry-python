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
from inspect import signature, Signature
from logging import ERROR

from opentelemetry.metrics.instrument import (
    Instrument,
)


class ChildInstrument(Instrument):
    def __init__(self, name, *args, unit="", description="", **kwargs):
        super().__init__(
            name, *args, unit=unit, description=description, **kwargs
        )


class TestInstrument(TestCase):

    def test_instrument_has_name(self):
        """
        Test that the instrument has name.
        """

        init_signature = signature(Instrument.__init__)
        self.assertIn("name", init_signature.parameters.keys())
        self.assertIs(
            init_signature.parameters["name"].default, Signature.empty
        )

        self.assertTrue(hasattr(Instrument, "name"))

    def test_instrument_has_unit(self):
        """
        Test that the instrument has unit.
        """

        init_signature = signature(Instrument.__init__)
        self.assertIn("unit", init_signature.parameters.keys())
        self.assertIs(
            init_signature.parameters["unit"].default, ""
        )

        self.assertTrue(hasattr(Instrument, "unit"))

    def test_instrument_has_description(self):
        """
        Test that the instrument has description.
        """

        init_signature = signature(Instrument.__init__)
        self.assertIn("description", init_signature.parameters.keys())
        self.assertIs(
            init_signature.parameters["description"].default, ""
        )

        self.assertTrue(hasattr(Instrument, "description"))

    def test_instrument_name_syntax(self):
        """
        Test that instrument names conform to the specified syntax.
        """

        with self.assertLogs(level=ERROR):
            ChildInstrument("")

        with self.assertLogs(level=ERROR):
            ChildInstrument(None)

        with self.assertLogs(level=ERROR):
            ChildInstrument("1a")

        with self.assertLogs(level=ERROR):
            ChildInstrument("_a")

        with self.assertLogs(level=ERROR):
            ChildInstrument("!a ")

        with self.assertLogs(level=ERROR):
            ChildInstrument("a ")

        with self.assertLogs(level=ERROR):
            ChildInstrument("a%")

        with self.assertLogs(level=ERROR):
            ChildInstrument("a" * 64)

        with self.assertRaises(AssertionError):
            with self.assertLogs(level=ERROR):
                ChildInstrument("abc_def_ghi")

    def test_instrument_unit_syntax(self):
        """
        Test that instrument names conform to the specified syntax.
        """

        with self.assertLogs(level=ERROR):
            ChildInstrument("name", unit="a" * 64)

        child_instrument = ChildInstrument("name", unit="a")
        self.assertEqual(child_instrument.unit, "a")

        child_instrument = ChildInstrument("name", unit="A")
        self.assertEqual(child_instrument.unit, "A")

        child_instrument = ChildInstrument("name")
        self.assertEqual(child_instrument.unit, "")

        child_instrument = ChildInstrument("name", unit=None)
        self.assertEqual(child_instrument.unit, "")
