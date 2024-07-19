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
from typing import MutableSequence

from opentelemetry.attributes import BoundedAttributes, _clean_attribute


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


class TestBoundedAttributes(unittest.TestCase):
    # pylint: disable=consider-using-dict-items
    base = {
        "name": "Firulais",
        "age": 7,
        "weight": 13,
        "vaccinated": True,
    }

    def test_negative_maxlen(self):
        with self.assertRaises(ValueError):
            BoundedAttributes(-1)

    def test_from_map(self):
        dic_len = len(self.base)
        base_copy = self.base.copy()
        bdict = BoundedAttributes(dic_len, base_copy)

        self.assertEqual(len(bdict), dic_len)

        # modify base_copy and test that bdict is not changed
        base_copy["name"] = "Bruno"
        base_copy["age"] = 3

        for key in self.base:
            self.assertEqual(bdict[key], self.base[key])

        # test that iter yields the correct number of elements
        self.assertEqual(len(tuple(bdict)), dic_len)

        # map too big
        half_len = dic_len // 2
        bdict = BoundedAttributes(half_len, self.base)
        self.assertEqual(len(tuple(bdict)), half_len)
        self.assertEqual(bdict.dropped, dic_len - half_len)

    def test_bounded_dict(self):
        # create empty dict
        dic_len = len(self.base)
        bdict = BoundedAttributes(dic_len, immutable=False)
        self.assertEqual(len(bdict), 0)

        # fill dict
        for key in self.base:
            bdict[key] = self.base[key]

        self.assertEqual(len(bdict), dic_len)
        self.assertEqual(bdict.dropped, 0)

        for key in self.base:
            self.assertEqual(bdict[key], self.base[key])

        # test __iter__ in BoundedAttributes
        for key in bdict:
            self.assertEqual(bdict[key], self.base[key])

        # updating an existing element should not drop
        bdict["name"] = "Bruno"
        self.assertEqual(bdict.dropped, 0)

        # try to append more elements
        for key in self.base:
            bdict["new-" + key] = self.base[key]

        self.assertEqual(len(bdict), dic_len)
        self.assertEqual(bdict.dropped, dic_len)
        # Invalid values shouldn't be considered for `dropped`
        bdict["invalid-seq"] = [None, 1, "2"]
        self.assertEqual(bdict.dropped, dic_len)

        # test that elements in the dict are the new ones
        for key in self.base:
            self.assertEqual(bdict["new-" + key], self.base[key])

        # delete an element
        del bdict["new-name"]
        self.assertEqual(len(bdict), dic_len - 1)

        with self.assertRaises(KeyError):
            _ = bdict["new-name"]

    def test_no_limit_code(self):
        bdict = BoundedAttributes(maxlen=None, immutable=False)
        for num in range(100):
            bdict[str(num)] = num

        for num in range(100):
            self.assertEqual(bdict[str(num)], num)

    def test_immutable(self):
        bdict = BoundedAttributes()
        with self.assertRaises(TypeError):
            bdict["should-not-work"] = "dict immutable"

    def test_locking(self):
        """Supporting test case for a commit titled: Fix class BoundedAttributes to have RLock rather than Lock. See #3858.
        The change was introduced because __iter__ of the class BoundedAttributes holds lock, and we observed some deadlock symptoms
        in the codebase. This test case is to verify that the fix works as expected.
        """
        bdict = BoundedAttributes(immutable=False)

        with bdict._lock:  # pylint: disable=protected-access
            for num in range(100):
                bdict[str(num)] = num

        for num in range(100):
            self.assertEqual(bdict[str(num)], num)
