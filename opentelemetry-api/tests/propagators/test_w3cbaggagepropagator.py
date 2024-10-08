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
#
# type: ignore

from logging import WARNING
from unittest import TestCase
from unittest.mock import Mock, patch

from opentelemetry.baggage import get_all, set_baggage
from opentelemetry.baggage.propagation import (
    W3CBaggagePropagator,
    _format_baggage,
)
from opentelemetry.context import get_current


class TestW3CBaggagePropagator(TestCase):
    # pylint: disable=protected-access
    # pylint: disable=too-many-public-methods
    def setUp(self):
        self.propagator = W3CBaggagePropagator()

    def _extract(self, header_value):
        """Test helper"""
        header = {"baggage": [header_value]}
        return get_all(self.propagator.extract(header))

    def _inject(self, values):
        """Test helper"""
        ctx = get_current()
        for k, v in values.items():  # pylint: disable=invalid-name
            ctx = set_baggage(k, v, context=ctx)
        output = {}
        self.propagator.inject(output, context=ctx)
        return output.get("baggage")

    def test_no_context_header(self):
        baggage_entries = get_all(self.propagator.extract({}))
        self.assertEqual(baggage_entries, {})

    def test_empty_context_header(self):
        header = ""
        self.assertEqual(self._extract(header), {})

    def test_valid_header(self):
        header = "key1=val1,key2=val2"
        expected = {"key1": "val1", "key2": "val2"}
        self.assertEqual(self._extract(header), expected)

    def test_invalid_header_with_space(self):
        header = "key1 =   val1,  key2 =val2   "
        self.assertEqual(self._extract(header), {})

    def test_valid_header_with_properties(self):
        header = "key1=val1,key2=val2;prop=1;prop2;prop3=2"
        expected = {"key1": "val1", "key2": "val2;prop=1;prop2;prop3=2"}
        self.assertEqual(self._extract(header), expected)

    def test_valid_header_with_url_escaped_values(self):
        header = "key1=val1,key2=val2%3Aval3,key3=val4%40%23%24val5"
        expected = {
            "key1": "val1",
            "key2": "val2:val3",
            "key3": "val4@#$val5",
        }
        self.assertEqual(self._extract(header), expected)

    def test_header_with_invalid_value(self):
        header = "key1=val1,key2=val2,a,val3"
        with self.assertLogs(level=WARNING) as warning:
            self._extract(header)
            self.assertIn(
                "Baggage list-member `a` doesn't match the format",
                warning.output[0],
            )

    def test_valid_header_with_empty_value(self):
        header = "key1=,key2=val2"
        expected = {"key1": "", "key2": "val2"}
        self.assertEqual(self._extract(header), expected)

    def test_invalid_header(self):
        self.assertEqual(self._extract("header1"), {})
        self.assertEqual(self._extract(" = "), {})

    def test_header_too_long(self):
        long_value = "s" * (W3CBaggagePropagator._MAX_HEADER_LENGTH + 1)
        header = f"key1={long_value}"
        expected = {}
        self.assertEqual(self._extract(header), expected)

    def test_header_contains_too_many_entries(self):
        header = ",".join(
            [f"key{k}=val" for k in range(W3CBaggagePropagator._MAX_PAIRS + 1)]
        )
        self.assertEqual(
            len(self._extract(header)), W3CBaggagePropagator._MAX_PAIRS
        )

    def test_header_contains_pair_too_long(self):
        long_value = "s" * (W3CBaggagePropagator._MAX_PAIR_LENGTH + 1)
        header = f"key1=value1,key2={long_value},key3=value3"
        expected = {"key1": "value1", "key3": "value3"}
        with self.assertLogs(level=WARNING) as warning:
            self.assertEqual(self._extract(header), expected)
            self.assertIn(
                "exceeded the maximum number of bytes per list-member",
                warning.output[0],
            )

    def test_extract_unquote_plus(self):
        self.assertEqual(
            self._extract("keykey=value%5Evalue"), {"keykey": "value^value"}
        )
        self.assertEqual(
            self._extract("key%23key=value%23value"),
            {"key#key": "value#value"},
        )

    def test_header_max_entries_skip_invalid_entry(self):

        with self.assertLogs(level=WARNING) as warning:
            self.assertEqual(
                self._extract(
                    ",".join(
                        [
                            (
                                f"key{index}=value{index}"
                                if index != 2
                                else (
                                    f"key{index}="
                                    f"value{'s' * (W3CBaggagePropagator._MAX_PAIR_LENGTH + 1)}"
                                )
                            )
                            for index in range(
                                W3CBaggagePropagator._MAX_PAIRS + 1
                            )
                        ]
                    )
                ),
                {
                    f"key{index}": f"value{index}"
                    for index in range(W3CBaggagePropagator._MAX_PAIRS + 1)
                    if index != 2
                },
            )
            self.assertIn(
                "exceeded the maximum number of list-members",
                warning.output[0],
            )

        with self.assertLogs(level=WARNING) as warning:
            self.assertEqual(
                self._extract(
                    ",".join(
                        [
                            (
                                f"key{index}=value{index}"
                                if index != 2
                                else f"key{index}xvalue{index}"
                            )
                            for index in range(
                                W3CBaggagePropagator._MAX_PAIRS + 1
                            )
                        ]
                    )
                ),
                {
                    f"key{index}": f"value{index}"
                    for index in range(W3CBaggagePropagator._MAX_PAIRS + 1)
                    if index != 2
                },
            )
            self.assertIn(
                "exceeded the maximum number of list-members",
                warning.output[0],
            )

    def test_inject_no_baggage_entries(self):
        values = {}
        output = self._inject(values)
        self.assertEqual(None, output)

    def test_inject_space_entries(self):
        self.assertEqual("key=val+ue", self._inject({"key": "val ue"}))

    def test_inject(self):
        values = {
            "key1": "val1",
            "key2": "val2",
        }
        output = self._inject(values)
        self.assertIn("key1=val1", output)
        self.assertIn("key2=val2", output)

    def test_inject_escaped_values(self):
        values = {
            "key1": "val1,val2",
            "key2": "val3=4",
        }
        output = self._inject(values)
        self.assertIn("key2=val3%3D4", output)

    def test_inject_non_string_values(self):
        values = {
            "key1": True,
            "key2": 123,
            "key3": 123.567,
        }
        output = self._inject(values)
        self.assertIn("key1=True", output)
        self.assertIn("key2=123", output)
        self.assertIn("key3=123.567", output)

    @patch("opentelemetry.baggage.propagation.get_all")
    @patch("opentelemetry.baggage.propagation._format_baggage")
    def test_fields(self, mock_format_baggage, mock_baggage):

        mock_setter = Mock()

        self.propagator.inject({}, setter=mock_setter)

        inject_fields = set()

        for mock_call in mock_setter.mock_calls:
            inject_fields.add(mock_call[1][1])

        self.assertEqual(inject_fields, self.propagator.fields)

    def test__format_baggage(self):
        self.assertEqual(
            _format_baggage({"key key": "value value"}), "key+key=value+value"
        )
        self.assertEqual(
            _format_baggage({"key/key": "value/value"}),
            "key%2Fkey=value%2Fvalue",
        )

    @patch("opentelemetry.baggage._BAGGAGE_KEY", new="abc")
    def test_inject_extract(self):

        carrier = {}

        context = set_baggage(
            "transaction", "string with spaces", context=get_current()
        )

        self.propagator.inject(carrier, context)

        context = self.propagator.extract(carrier)

        self.assertEqual(
            carrier, {"baggage": "transaction=string+with+spaces"}
        )

        self.assertEqual(
            context, {"abc": {"transaction": "string with spaces"}}
        )
