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

import collections
import unittest

from opentelemetry.attributes import (
    BoundedDict,
    _create_immutable_attributes,
    _filter_attributes,
    _is_valid_attribute_value,
)


class TestAttributes(unittest.TestCase):
    def test_is_valid_attribute_value(self):
        self.assertFalse(_is_valid_attribute_value([1, 2, 3.4, "ss", 4]))
        self.assertFalse(_is_valid_attribute_value([dict(), 1, 2, 3.4, 4]))
        self.assertFalse(_is_valid_attribute_value(["sw", "lf", 3.4, "ss"]))
        self.assertFalse(_is_valid_attribute_value([1, 2, 3.4, 5]))
        self.assertFalse(_is_valid_attribute_value(dict()))
        self.assertTrue(_is_valid_attribute_value(True))
        self.assertTrue(_is_valid_attribute_value("hi"))
        self.assertTrue(_is_valid_attribute_value(3.4))
        self.assertTrue(_is_valid_attribute_value(15))
        self.assertTrue(_is_valid_attribute_value([1, 2, 3, 5]))
        self.assertTrue(_is_valid_attribute_value([1.2, 2.3, 3.4, 4.5]))
        self.assertTrue(_is_valid_attribute_value([True, False]))
        self.assertTrue(_is_valid_attribute_value(["ss", "dw", "fw"]))
        self.assertTrue(_is_valid_attribute_value([]))
        # None in sequences are valid
        self.assertTrue(_is_valid_attribute_value(["A", None, None]))
        self.assertTrue(_is_valid_attribute_value(["A", None, None, "B"]))
        self.assertTrue(_is_valid_attribute_value([None, None]))
        self.assertFalse(_is_valid_attribute_value(["A", None, 1]))
        self.assertFalse(_is_valid_attribute_value([None, "A", None, 1]))

    def test_filter_attributes(self):
        attrs_with_invalid_keys = {
            "": "empty-key",
            None: "None-value",
            "attr-key": "attr-value",
        }
        _filter_attributes(attrs_with_invalid_keys)
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
        _filter_attributes(attrs_with_invalid_values)
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


class TestBoundedDict(unittest.TestCase):
    base = collections.OrderedDict(
        [
            ("name", "Firulais"),
            ("age", 7),
            ("weight", 13),
            ("vaccinated", True),
        ]
    )

    def test_negative_maxlen(self):
        with self.assertRaises(ValueError):
            BoundedDict(-1)

    def test_from_map(self):
        dic_len = len(self.base)
        base_copy = collections.OrderedDict(self.base)
        bdict = BoundedDict(dic_len, base_copy)

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
        bdict = BoundedDict(half_len, self.base)
        self.assertEqual(len(tuple(bdict)), half_len)
        self.assertEqual(bdict.dropped, dic_len - half_len)

    def test_bounded_dict(self):
        # create empty dict
        dic_len = len(self.base)
        bdict = BoundedDict(dic_len, immutable=False)
        self.assertEqual(len(bdict), 0)

        # fill dict
        for key in self.base:
            bdict[key] = self.base[key]

        self.assertEqual(len(bdict), dic_len)
        self.assertEqual(bdict.dropped, 0)

        for key in self.base:
            self.assertEqual(bdict[key], self.base[key])

        # test __iter__ in BoundedDict
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

        # test that elements in the dict are the new ones
        for key in self.base:
            self.assertEqual(bdict["new-" + key], self.base[key])

        # delete an element
        del bdict["new-name"]
        self.assertEqual(len(bdict), dic_len - 1)

        with self.assertRaises(KeyError):
            _ = bdict["new-name"]

    def test_no_limit_code(self):
        bdict = BoundedDict(maxlen=None, immutable=False)
        for num in range(100):
            bdict[num] = num

        for num in range(100):
            self.assertEqual(bdict[num], num)

    def test_immutable(self):
        bdict = BoundedDict()
        with self.assertRaises(TypeError):
            bdict["should-not-work"] = "dict immutable"
