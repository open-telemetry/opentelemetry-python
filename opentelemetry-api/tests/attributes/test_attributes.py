# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# type: ignore

import copy
import unittest
import unittest.mock

from opentelemetry.attributes import (
    BoundedAttributes,
    _clean_attribute_value,
)


class _NoStrObject:
    def __init__(self):
        pass

    def __str__(self):
        raise Exception("I am a string that fails to be created!")


class TestBoundedAttributes(unittest.TestCase):
    # pylint: disable=consider-using-dict-items
    base = {
        "name": "Firulais",
        "age": 7,
        "weight": 13,
        "vaccinated": True,
    }

    def test_clean_attribute_value_with_various_params(self):
        # A python type that isn't a primitive and has no string method
        # is converted to None.
        with self.assertLogs("opentelemetry", level="WARNING") as cm:
            self.assertEqual(
                _clean_attribute_value(_NoStrObject(), None),
                None,
            )
        self.assertEqual(len(cm.output), 1)
        self.assertIn(
            "Expected one of bool, str, None, bytes, int, float", cm.output[0]
        )

        valid_primitive_sequence = [1, 2.2, None, "cookie"]
        self.assertEqual(
            _clean_attribute_value(valid_primitive_sequence, None),
            tuple(valid_primitive_sequence),
        )
        for valid_primitive in valid_primitive_sequence:
            self.assertEqual(
                _clean_attribute_value(valid_primitive, None), valid_primitive
            )

        # Strings too long
        with self.assertLogs("opentelemetry", level="WARNING") as cm:
            # valid utf-8 bytes are converted to strings and truncated according to max_string_value_length.
            self.assertEqual(_clean_attribute_value(b"hello", 4), "hell")
            self.assertEqual(_clean_attribute_value("a" * 1000, 5), "aaaaa")
        self.assertEqual(len(cm.output), 1)
        self.assertIn(
            "String attribute value exceeds max length", cm.output[0]
        )

        # Sequence of different types of values. Non utf-8 bytes kept as bytes.
        # List converted to tuple.
        self.assertEqual(
            _clean_attribute_value(
                ["a", 2, _NoStrObject(), None, b"\xff"], None
            ),
            ("a", 2, None, None, b"\xff"),
        )

        # non-str key in map... will be converted to string
        with self.assertLogs("opentelemetry", level="WARNING") as cm:
            self.assertEqual(
                _clean_attribute_value({2.2: 4.4}, None), {"2.2": 4.4}
            )
        self.assertEqual(len(cm.output), 1)
        self.assertIn(
            "invalid key `2.2` inside an attribute value mapping.",
            cm.output[0],
        )

        # Mapping of values..
        self.assertEqual(
            _clean_attribute_value(
                {
                    "a": 1,
                    _NoStrObject(): 2,
                    "c": 3,
                    "d": [2, 3],
                    "bytes": b"\xff",
                },
                None,
            ),
            {"a": 1, "c": 3, "d": (2, 3), "bytes": b"\xff"},
        )

    def test_same_key_value_overwritten(self):
        bdict = BoundedAttributes(1, {"name": "Firulais"}, immutable=False)
        self.assertEqual(bdict["name"], "Firulais")
        self.assertEqual(bdict.dropped, 0)
        bdict["name"] = "Bruno"
        self.assertEqual(bdict["name"], "Bruno")
        self.assertEqual(bdict.dropped, 0)

    def test_invalid_key_not_used(self):
        bdict = BoundedAttributes(50, {}, immutable=False)
        with self.assertLogs("opentelemetry", level="WARNING") as cm:
            bdict[1] = 2
        self.assertEqual(len(cm.output), 1)
        self.assertIn("invalid key", cm.output[0])
        self.assertNotIn(1, bdict)
        self.assertEqual(bdict.dropped, 1)

    def test_maxvalue_reached_and_duplicate_logs_filter_works(self):
        bdict = BoundedAttributes(1, {"first": "value"}, immutable=False)
        with self.assertLogs("opentelemetry", level="WARNING") as cm:
            bdict["second"] = "another"
            # Same log should be filtered out..
            bdict["third"] = "another"
        self.assertEqual(len(cm.output), 1)
        self.assertIn(
            "Attributes dict is full. Dropping the oldest", cm.output[0]
        )
        self.assertNotIn("first", bdict)
        self.assertEqual(bdict["third"], "another")
        self.assertEqual(bdict.dropped, 2)

    def test_negative_maxlen_not_allowed(self):
        with self.assertRaises(ValueError):
            BoundedAttributes(-1)

    def test_base_copy_isolated_and_len_works(self):
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

    def test_basic_insertion_update_iteration_and_deletion(self):
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

        # try to append more elements, old elements should be dropped
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

    def test_wsgi_request_conversion_to_string(self):
        """Test that WSGI request objects are converted to strings when _clean_attribute_value is called."""

        class DummyWSGIRequest:
            def __str__(self):
                return "<DummyWSGIRequest method=GET path=/example/>"

        self.assertEqual(
            "<DummyWSGIRequest method=GET path=/example/>",
            _clean_attribute_value(DummyWSGIRequest(), None),
        )

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
