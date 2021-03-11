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
from unittest.mock import patch

from opentelemetry import baggage
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.context import get_current


class TestBaggagePropagation(TestCase):
    def setUp(self):
        self.propagator = W3CBaggagePropagator()

    def _extract(self, header_value):
        """Test helper"""
        return baggage.get_all(
            self.propagator.extract({"baggage": header_value})
        )

    def _inject(self, values):
        """Test helper"""
        ctx = get_current()
        for k, v in values.items():
            ctx = baggage.set_baggage(k, v, context=ctx)
        output = {}
        self.propagator.inject(output, context=ctx)
        return output.get("baggage")

    def test_no_context_header(self):
        self.assertEqual(baggage.get_all(self.propagator.extract({})), {})

    def test_empty_context_header(self):
        self.assertEqual(self._extract(""), {})

    def test_valid_header(self):
        self.assertEqual(
            self._extract("key1=val1,key2=val2"),
            {"key1": "val1", "key2": "val2"},
        )

    def test_valid_header_with_space(self):
        self.assertEqual(
            self._extract("key1 =   val1,  key2 =val2   "),
            {"key1": "val1", "key2": "val2"},
        )

    def test_valid_header_with_properties(self):
        self.assertEqual(
            self._extract("key1=val1,key2=val2;prop=1"),
            {"key1": "val1", "key2": "val2;prop=1"},
        )

    def test_valid_header_with_url_escaped_comma(self):
        self.assertEqual(
            self._extract("key%2C1=val1,key2=val2%2Cval3"),
            {"key,1": "val1", "key2": "val2,val3"},
        )

    def test_valid_header_with_invalid_value(self):
        self.assertEqual(
            self._extract("key1=val1,key2=val2,a,val3"),
            {"key1": "val1", "key2": "val2"},
        )

    def test_valid_header_with_empty_value(self):
        self.assertEqual(
            self._extract("key1=,key2=val2"), {"key1": "", "key2": "val2"}
        )

    def test_invalid_header(self):
        self.assertEqual(self._extract("header1"), {})

    def test_header_too_long(self):
        self.assertEqual(
            self._extract(
                "key1={}".format(
                    "s" * (W3CBaggagePropagator._max_header_length + 1)
                )
            ),
            {},
        )

    def test_header_contains_too_many_entries(self):
        self.assertEqual(
            len(
                self._extract(
                    ",".join(
                        "key{}=val".format(k)
                        for k in range(W3CBaggagePropagator._max_pairs + 1)
                    )
                )
            ),
            W3CBaggagePropagator._max_pairs,
        )

    def test_header_contains_pair_too_long(self):
        self.assertEqual(
            self._extract(
                "key1=value1,key2={},key3=value3".format(
                    "s" * (W3CBaggagePropagator._max_pair_length + 1)
                )
            ),
            {"key1": "value1", "key3": "value3"},
        )

    def test_inject_no_baggage_entries(self):
        self.assertEqual(None, self._inject({}))

    def test_inject(self):
        output = self._inject({"key1": "val1", "key2": "val2"})
        self.assertIn("key1=val1", output)
        self.assertIn("key2=val2", output)

    def test_inject_escaped_values(self):
        output = self._inject({"key1": "val1,val2", "key2": "val3=4"})
        self.assertIn("key1=val1%2Cval2", output)
        self.assertIn("key2=val3%3D4", output)

    def test_inject_non_string_values(self):
        output = self._inject({"key1": True, "key2": 123, "key3": 123.567})
        self.assertIn("key1=True", output)
        self.assertIn("key2=123", output)
        self.assertIn("key3=123.567", output)

    @patch("opentelemetry.baggage.propagation.baggage")
    def test_fields(self, mock_baggage):

        mock_baggage.configure_mock(
            **{"get_all.return_value": {"a": "b", "c": "d"}}
        )

        carrier = {}

        self.propagator.inject(carrier)

        self.assertEqual(carrier.keys(), self.propagator.fields)
