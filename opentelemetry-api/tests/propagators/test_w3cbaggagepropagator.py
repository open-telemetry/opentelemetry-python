# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
#
# type: ignore

from logging import WARNING
from unittest import TestCase
from unittest.mock import Mock, patch

from opentelemetry.baggage import get_all, set_baggage
from opentelemetry.baggage.propagation import (
    W3CBaggagePropagator,
    _encode_baggage_pairs,
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

    def test_valid_header_with_whitespace(self):
        for header, expected in (
            (
                "key1 =   val1,  key2 =val2   ",
                {"key1": "val1", "key2": "val2"},
            ),
            ("some_name = some_value", {"some_name": "some_value"}),
            ("key1\t=\tval1", {"key1": "val1"}),
            ("key1=val1 , ,\tkey2=val2", {"key1": "val1", "key2": "val2"}),
            (" \tkey1=val1,,key2=val2\t ", {"key1": "val1", "key2": "val2"}),
            ("key1 = val1;prop=1", {"key1": "val1"}),
            (
                "key1 = val1 ; prop1 = 1 ; prop2 ;prop3= 2",
                {"key1": "val1"},
            ),
            (
                "key1=val1, key2 = val2;prop = 1;prop2",
                {"key1": "val1", "key2": "val2"},
            ),
        ):
            with self.subTest(header=header):
                self.assertEqual(self._extract(header), expected)

    def test_invalid_header_with_inner_whitespace(self):
        for header in (
            "key 1=val1",
            "key1=val 1",
            "key1=val1;pr op=1",
            " = ",
        ):
            with self.subTest(header=header):
                self.assertEqual(self._extract(header), {})

    def test_valid_header_with_properties(self):
        header = "key1=val1,key2=val2;prop=1;prop2;prop3=2"
        expected = {"key1": "val1", "key2": "val2"}
        self.assertEqual(self._extract(header), expected)

    def test_properties_not_propagated_as_value(self):
        context = self.propagator.extract({"baggage": ["key1=val%201;prop=1"]})
        carrier = {}
        self.propagator.inject(carrier, context)
        self.assertEqual(carrier, {"baggage": "key1=val%201"})

    def test_extract_multiple_headers(self):
        for headers, expected in (
            (["key1=val1", "key2=val2"], {"key1": "val1", "key2": "val2"}),
            (["key1=val1,key2=val2", "key3=val3"], {"key1": "val1", "key2": "val2", "key3": "val3"}),
            (["", "key1=val1"], {"key1": "val1"}),
            (["key1=val1", "key1=val2"], {"key1": "val2"}),
        ):
            with self.subTest(headers=headers):
                self.assertEqual(get_all(self.propagator.extract({"baggage": headers})), expected)

    def test_extract_multiple_headers_combined_limits(self):
        half = W3CBaggagePropagator._MAX_PAIRS // 2 + 1
        headers = [
            ",".join(f"a{k}=val" for k in range(half)),
            ",".join(f"b{k}=val" for k in range(half)),
        ]
        with self.assertLogs(level=WARNING) as warning:
            result = get_all(self.propagator.extract({"baggage": headers}))
            self.assertIn("exceeded the maximum number of list-members", warning.output[0])
        self.assertEqual(len(result), W3CBaggagePropagator._MAX_PAIRS)

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
        # Three 3000 byte list-members: only the first two fit into the baggage string limit
        value = "s" * 2995
        header = f"key1={value},key2={value},key3={value}"
        expected = {"key1": value, "key2": value}
        with self.assertLogs(level=WARNING) as warning:
            self.assertEqual(self._extract(header), expected)
            self.assertIn(
                "exceeded the maximum number of bytes per baggage-string",
                warning.output[0],
            )

    def test_extract_non_ascii_header(self):
        """Extract should skip non-ASCII entries but keep valid ones."""
        header = "key1=val1,key2=test\u00e9"
        with self.assertLogs(level=WARNING) as warning:
            result = self._extract(header)
            self.assertEqual(result, {"key1": "val1"})
            self.assertIn(
                "contains non-ASCII characters",
                warning.output[0],
            )

    def test_extract_non_ascii_header_exceeds_byte_limit(self):
        """A non-ASCII entry over the byte limit when encoded should be rejected."""
        # Each \u00e9 encodes to 2 bytes in UTF-8, so we need fewer chars to exceed the byte limit
        non_ascii_value = "\u00e9" * (W3CBaggagePropagator._MAX_HEADER_LENGTH)
        header = f"key1={non_ascii_value}"
        with self.assertLogs(level=WARNING) as warning:
            result = self._extract(header)
            self.assertEqual(result, {})
            self.assertIn(
                "contains non-ASCII characters",
                warning.output[0],
            )

    def test_header_contains_too_many_entries(self):
        header = ",".join([f"key{k}=val" for k in range(W3CBaggagePropagator._MAX_PAIRS + 1)])
        with self.assertLogs(level=WARNING):
            self.assertEqual(len(self._extract(header)), W3CBaggagePropagator._MAX_PAIRS)

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

    def test_extract_percent_decoding(self):
        for header, expected in (
            ("keykey=value%5Evalue", {"keykey": "value^value"}),
            ("key%23key=value%23value", {"key%23key": "value#value"}),
            ("key=a+b", {"key": "a+b"}),
            ("key=a%20b", {"key": "a b"}),
            ("key=a%2Bb", {"key": "a+b"}),
            ("key=%20val%20", {"key": " val "}),
            ("key = %09val%09 ", {"key": "\tval\t"}),
            ("key=%E2%82%AC", {"key": "\u20ac"}),
            ("key=%FF", {"key": "\ufffd"}),
        ):
            with self.subTest(header=header):
                self.assertEqual(self._extract(header), expected)

    def test_header_max_entries_skip_invalid_entry(self):
        # 181 entries where index 2 is too long: skipping it leaves exactly 180 valid entries
        with self.assertLogs(level=WARNING) as warning:
            self.assertEqual(
                self._extract(
                    ",".join(
                        [
                            (
                                f"key{index}=value{index}"
                                if index != 2
                                else (f"key{index}=value{'s' * (W3CBaggagePropagator._MAX_PAIR_LENGTH + 1)}")
                            )
                            for index in range(W3CBaggagePropagator._MAX_PAIRS + 1)
                        ]
                    )
                ),
                {f"key{index}": f"value{index}" for index in range(W3CBaggagePropagator._MAX_PAIRS + 1) if index != 2},
            )
            self.assertTrue(
                any("exceeded the maximum number of bytes per list-member" in msg for msg in warning.output)
            )

        # 181 entries where index 2 is malformed (no '='): _apply_baggage_limits
        # accepts the first 180 entries (indices 0-179), then the malformed entry
        # at index 2 is skipped during parsing
        with self.assertLogs(level=WARNING) as warning:
            self.assertEqual(
                self._extract(
                    ",".join(
                        [
                            (f"key{index}=value{index}" if index != 2 else f"key{index}xvalue{index}")
                            for index in range(W3CBaggagePropagator._MAX_PAIRS + 1)
                        ]
                    )
                ),
                {f"key{index}": f"value{index}" for index in range(W3CBaggagePropagator._MAX_PAIRS) if index != 2},
            )
            self.assertTrue(any("exceeded the maximum number of list-members" in msg for msg in warning.output))
            self.assertTrue(any("doesn't match the format" in msg for msg in warning.output))

    def test_inject_no_baggage_entries(self):
        values = {}
        output = self._inject(values)
        self.assertEqual(None, output)

    def test_inject_space_entries(self):
        self.assertEqual("key=val%20ue", self._inject({"key": "val ue"}))

    def test_inject_plus_sign(self):
        self.assertEqual("key=a%2Bb", self._inject({"key": "a+b"}))

    def test_inject_invalid_key(self):
        for key in ("key key", "key/key", "key,key", ""):
            with self.subTest(key=key):
                with self.assertLogs(level=WARNING) as warning:
                    self.assertEqual("valid=val", self._inject({key: "val", "valid": "val"}))
                    self.assertIn("is not a valid token", warning.output[0])

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
    def test_fields(self, mock_baggage):
        mock_baggage.return_value = {"key": "value"}
        mock_setter = Mock()

        self.propagator.inject({}, setter=mock_setter)

        inject_fields = set()

        for mock_call in mock_setter.mock_calls:
            inject_fields.add(mock_call[1][1])

        self.assertEqual(inject_fields, self.propagator.fields)

    def test_encode_baggage_pairs(self):
        self.assertEqual(
            list(_encode_baggage_pairs({"key": "value value", "key/key": "value", "k": "a/b;c,d=e%f\u20ac"})),
            ["key=value%20value", "k=a%2Fb%3Bc%2Cd%3De%25f%E2%82%AC"],
        )

    def test_inject_too_many_entries(self):
        """Inject should drop entries exceeding _MAX_PAIRS."""
        values = {f"key{i}": f"val{i}" for i in range(self.propagator._MAX_PAIRS + 10)}
        ctx = get_current()
        for key, val in values.items():
            ctx = set_baggage(key, val, context=ctx)
        output = {}
        with self.assertLogs(level=WARNING) as warning:
            self.propagator.inject(output, context=ctx)
            self.assertIn(
                "exceeded the maximum number of list-members",
                warning.output[0],
            )
        baggage_str = output.get("baggage", "")
        pairs = baggage_str.split(",")
        self.assertEqual(len(pairs), self.propagator._MAX_PAIRS)
        self.assertNotIn(
            f"key{self.propagator._MAX_PAIRS}=",
            baggage_str,
        )

    def test_inject_entry_too_long(self):
        """Inject should skip individual entries that exceed _MAX_PAIR_LENGTH."""
        long_value = "x" * self.propagator._MAX_PAIR_LENGTH
        values = {"key1": "val1", "big": long_value, "key3": "val3"}
        ctx = get_current()
        for key, val in values.items():
            ctx = set_baggage(key, val, context=ctx)
        output = {}
        with self.assertLogs(level=WARNING) as warning:
            self.propagator.inject(output, context=ctx)
            self.assertIn(
                "exceeded the maximum number of bytes per list-member",
                warning.output[0],
            )
        baggage_str = output.get("baggage", "")
        self.assertIn("key1=val1", baggage_str)
        self.assertIn("key3=val3", baggage_str)
        self.assertNotIn("big=", baggage_str)

    def test_inject_total_header_too_long(self):
        """Inject should stop adding entries when total header would exceed _MAX_HEADER_LENGTH."""
        # Create entries that individually fit but collectively exceed the max header length
        # Each entry "kNNN=<value>" with value ~200 chars; 50 of these > 8192
        value = "v" * 200
        values = {f"k{i:03d}": value for i in range(50)}
        ctx = get_current()
        for key, val in values.items():
            ctx = set_baggage(key, val, context=ctx)
        output = {}
        with self.assertLogs(level=WARNING) as warning:
            self.propagator.inject(output, context=ctx)
            self.assertIn(
                "exceeded the maximum number of bytes per baggage-string",
                warning.output[0],
            )
        baggage_str = output.get("baggage", "")
        self.assertLessEqual(len(baggage_str), self.propagator._MAX_HEADER_LENGTH)

    def test_inject_empty_after_all_dropped(self):
        """If all entries are too long, nothing should be injected."""
        long_value = "x" * self.propagator._MAX_PAIR_LENGTH
        values = {"big1": long_value, "big2": long_value}
        ctx = get_current()
        for key, val in values.items():
            ctx = set_baggage(key, val, context=ctx)
        output = {}
        self.propagator.inject(output, context=ctx)
        self.assertNotIn("baggage", output)

    @patch("opentelemetry.baggage._BAGGAGE_KEY", new="abc")
    def test_inject_extract(self):
        carrier = {}

        context = set_baggage("transaction", "string with spaces", context=get_current())

        self.propagator.inject(carrier, context)

        context = self.propagator.extract(carrier)

        self.assertEqual(carrier, {"baggage": "transaction=string%20with%20spaces"})

        self.assertEqual(context, {"abc": {"transaction": "string with spaces"}})
