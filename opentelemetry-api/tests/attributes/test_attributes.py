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

import copy
import unittest
import unittest.mock
from typing import MutableSequence

from opentelemetry.attributes import (
    BoundedAttributes,
    _clean_attribute,
    _clean_extended_attribute,
    _clean_extended_attribute_value,
)


class TestAttributes(unittest.TestCase):
    # pylint: disable=invalid-name
    def assertValid(self, value, key="k"):
        expected = value
        if isinstance(value, MutableSequence):
            expected = tuple(value)
        self.assertEqual(_clean_attribute(key, value, None), expected)

    def assertInvalid(self, value, key="k"):
        self.assertIsNone(_clean_attribute(key, value, None))

    def test_attribute_key_validation(self):
        # only non-empty strings are valid keys
        self.assertInvalid(1, "")
        self.assertInvalid(1, 1)
        self.assertInvalid(1, {})
        self.assertInvalid(1, [])
        self.assertInvalid(1, b"1")
        self.assertValid(1, "k")
        self.assertValid(1, "1")

    def test_clean_attribute(self):
        self.assertInvalid([1, 2, 3.4, "ss", 4])
        self.assertInvalid([{}, 1, 2, 3.4, 4])
        self.assertInvalid(["sw", "lf", 3.4, "ss"])
        self.assertInvalid([1, 2, 3.4, 5])
        self.assertInvalid({})
        self.assertInvalid([1, True])
        self.assertValid(True)
        self.assertValid("hi")
        self.assertValid(3.4)
        self.assertValid(15)
        self.assertValid([1, 2, 3, 5])
        self.assertValid([1.2, 2.3, 3.4, 4.5])
        self.assertValid([True, False])
        self.assertValid(["ss", "dw", "fw"])
        self.assertValid([])
        # None in sequences are valid
        self.assertValid(["A", None, None])
        self.assertValid(["A", None, None, "B"])
        self.assertValid([None, None])
        self.assertInvalid(["A", None, 1])
        self.assertInvalid([None, "A", None, 1])

        # test keys
        self.assertValid("value", "key")
        self.assertInvalid("value", "")
        self.assertInvalid("value", None)

    def test_sequence_attr_decode(self):
        seq = [
            None,
            b"Content-Disposition",
            b"Content-Type",
            b"\x81",
            b"Keep-Alive",
        ]
        expected = [
            None,
            "Content-Disposition",
            "Content-Type",
            None,
            "Keep-Alive",
        ]
        self.assertEqual(
            _clean_attribute("headers", seq, None), tuple(expected)
        )


class TestExtendedAttributes(unittest.TestCase):
    # pylint: disable=invalid-name
    def assertValid(self, value, key="k"):
        expected = value
        if isinstance(value, MutableSequence):
            expected = tuple(value)
        self.assertEqual(_clean_extended_attribute(key, value, None), expected)

    def assertInvalid(self, value, key="k"):
        self.assertIsNone(_clean_extended_attribute(key, value, None))

    def test_attribute_key_validation(self):
        # only non-empty strings are valid keys
        self.assertInvalid(1, "")
        self.assertInvalid(1, 1)
        self.assertInvalid(1, {})
        self.assertInvalid(1, [])
        self.assertInvalid(1, b"1")
        self.assertValid(1, "k")
        self.assertValid(1, "1")

    def test_clean_extended_attribute(self):
        self.assertInvalid([1, 2, 3.4, "ss", 4])
        self.assertInvalid([{}, 1, 2, 3.4, 4])
        self.assertInvalid(["sw", "lf", 3.4, "ss"])
        self.assertInvalid([1, 2, 3.4, 5])
        self.assertInvalid([1, True])
        self.assertValid(None)
        self.assertValid(True)
        self.assertValid("hi")
        self.assertValid(3.4)
        self.assertValid(15)
        self.assertValid([1, 2, 3, 5])
        self.assertValid([1.2, 2.3, 3.4, 4.5])
        self.assertValid([True, False])
        self.assertValid(["ss", "dw", "fw"])
        self.assertValid([])
        # None in sequences are valid
        self.assertValid(["A", None, None])
        self.assertValid(["A", None, None, "B"])
        self.assertValid([None, None])
        self.assertInvalid(["A", None, 1])
        self.assertInvalid([None, "A", None, 1])
        # mappings
        self.assertValid({})
        self.assertValid({"k": "v"})
        # mappings in sequences
        self.assertValid([{"k": "v"}])

        # test keys
        self.assertValid("value", "key")
        self.assertInvalid("value", "")
        self.assertInvalid("value", None)

    def test_sequence_attr_decode(self):
        seq = [
            None,
            b"Content-Disposition",
            b"Content-Type",
            b"\x81",
            b"Keep-Alive",
        ]
        self.assertEqual(
            _clean_extended_attribute("headers", seq, None), tuple(seq)
        )

    def test_mapping(self):
        mapping = {
            "": "invalid",
            b"bytes": "invalid",
            "none": {"": "invalid"},
            "valid_primitive": "str",
            "valid_sequence": ["str"],
            "invalid_sequence": ["str", 1],
            "valid_mapping": {"str": 1},
            "invalid_mapping": {"": 1},
        }
        expected = {
            "none": {},
            "valid_primitive": "str",
            "valid_sequence": ("str",),
            "invalid_sequence": None,
            "valid_mapping": {"str": 1},
            "invalid_mapping": {},
        }
        self.assertEqual(
            _clean_extended_attribute("headers", mapping, None), expected
        )


class TestBoundedAttributes(unittest.TestCase):
    base = {
        "name": "Firulais",
        "age": 7,
        "weight": 13,
        "vaccinated": True,
    }

    def test_invalid_anyvalue_type_raises_typeerror(self):
        class BadStr:
            def __str__(self):
                raise Exception("boom")

        with self.assertRaises(TypeError):
            _clean_extended_attribute_value(BadStr(), None)

    def test_deepcopy(self):
        bdict = BoundedAttributes(4, self.base, immutable=False)
        bdict.dropped = 10
        bdict_copy = copy.deepcopy(bdict)

        for key in bdict_copy:
            self.assertEqual(bdict_copy[key], bdict[key])

        self.assertEqual(bdict_copy.dropped, bdict.dropped)
        self.assertEqual(bdict_copy.maxlen, bdict.maxlen)
        self.assertEqual(bdict_copy.max_value_len, bdict.max_value_len)

        bdict_copy["name"] = "Bob"
        self.assertNotEqual(bdict_copy["name"], bdict["name"])

        bdict["age"] = 99
        self.assertNotEqual(bdict["age"], bdict_copy["age"])

    def test_deepcopy_preserves_immutability(self):
        bdict = BoundedAttributes(
            maxlen=4, attributes=self.base, immutable=True
        )
        bdict_copy = copy.deepcopy(bdict)

        with self.assertRaises(TypeError):
            bdict_copy["invalid"] = "invalid"
