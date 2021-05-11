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

import unittest

from opentelemetry.attributes import (
    _clean_attribute_value,
    _clean_attributes,
    _create_immutable_attributes,
)


class TestAttributes(unittest.TestCase):
    def assertCleanAttr(self, value, valid):
        # pylint: disable=protected-access
        is_valid, cleaned = _clean_attribute_value(value, None)
        self.assertEqual(is_valid, valid)
        self.assertEqual(cleaned, value if valid else None)

    def test_validate_attribute_value(self):
        test_cases = [
            (
                [1, 2, 3.4, "ss", 4],
                False,
            ),
            (
                [dict(), 1, 2, 3.4, 4],
                False,
            ),
            (
                ["sw", "lf", 3.4, "ss"],
                False,
            ),
            (
                [1, 2, 3.4, 5],
                False,
            ),
            (
                dict(),
                False,
            ),
            (
                True,
                True,
            ),
            (
                "hi",
                True,
            ),
            (
                3.4,
                True,
            ),
            (
                15,
                True,
            ),
            (
                (1, 2, 3, 5),
                True,
            ),
            (
                (1.2, 2.3, 3.4, 4.5),
                True,
            ),
            (
                (True, False),
                True,
            ),
            (
                ("ss", "dw", "fw"),
                True,
            ),
            (
                [],
                True,
            ),
            # None in sequences are valid
            (
                ("A", None, None),
                True,
            ),
            (
                ("A", None, None, "B"),
                True,
            ),
            (
                (None, None),
                True,
            ),
            (
                ["A", None, 1],
                False,
            ),
            (
                [None, "A", None, 1],
                False,
            ),
        ]

        for value, want_valid in test_cases:
            # pylint: disable=protected-access
            got_valid, cleaned_value = _clean_attribute_value(value, None)
            self.assertEqual(got_valid, want_valid)
            self.assertIsNone(cleaned_value)

    def test_clean_attribute_value_truncate(self):
        test_cases = [
            ("a" * 50, None, None),
            ("a" * 50, "a" * 10, 10),
            ("abc", "a", 1),
            ("abc" * 50, "abcabcabca", 10),
            ("abc" * 50, "abc" * 50, 1000),
            ("abc" * 50, None, None),
            ([1, 2, 3, 5], (1, 2, 3, 5), 10),
            (
                [1.2, 2.3],
                (
                    1.2,
                    2.3,
                ),
                20,
            ),
            ([True, False], (True, False), 10),
            ([], None, 10),
            (True, None, 10),
            (
                3.4,
                None,
                True,
            ),
            (
                15,
                None,
                True,
            ),
        ]

        for value, expected, limit in test_cases:
            # pylint: disable=protected-access
            valid, cleaned = _clean_attribute_value(value, limit)
            self.assertTrue(valid)
            self.assertEqual(cleaned, expected)

    def test_clean_attributes(self):
        attrs_with_invalid_keys = {
            "": "empty-key",
            None: "None-value",
            "attr-key": "attr-value",
        }
        _clean_attributes(attrs_with_invalid_keys, None)
        self.assertTrue(len(attrs_with_invalid_keys), 1)
        self.assertEqual(attrs_with_invalid_keys, {"attr-key": "attr-value"})

        attrs_with_invalid_values = {
            "nonhomogeneous": [1, 2, 3.4, "ss", 4],
            "nonprimitive": dict(),
            "mixed": [1, 2.4, "st", dict()],
            "validkey1": "validvalue1",
            "intkey": 5,
            "floatkey": 3.14,
            "boolkey": True,
            "valid-byte-string": b"hello-otel",
        }
        _clean_attributes(attrs_with_invalid_values, None)
        self.assertEqual(len(attrs_with_invalid_values), 5)
        self.assertEqual(
            attrs_with_invalid_values,
            {
                "validkey1": "validvalue1",
                "intkey": 5,
                "floatkey": 3.14,
                "boolkey": True,
                "valid-byte-string": "hello-otel",
            },
        )

    def test_create_immutable_attributes(self):
        attrs = {"key": "value", "pi": 3.14}
        immutable = _create_immutable_attributes(attrs)
        # TypeError: 'mappingproxy' object does not support item assignment
        with self.assertRaises(TypeError):
            immutable["pi"] = 1.34
