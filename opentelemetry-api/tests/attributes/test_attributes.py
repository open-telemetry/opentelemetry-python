# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# type: ignore

import copy
import logging
import threading
import unittest
import unittest.mock

from opentelemetry.attributes import (
    BoundedAttributes,
    _clean_attribute_value,
)


class _NoStrNoReprObject:
    def __init__(self):
        pass


class TestBoundedAttributes(unittest.TestCase):
    # pylint: disable=consider-using-dict-items
    base = {
        "name": "Firulais",
        "age": 7,
        "weight": 13,
        "vaccinated": True,
    }

    def test_clean_attribute_value_with_various_params(self):
        # A python object that isn't a primitive and has no string/repr method is converted to None.
        with self.assertLogs("opentelemetry", level="WARNING") as cm:
            self.assertEqual(
                _clean_attribute_value(_NoStrNoReprObject(), None),
                None,
            )
        self.assertEqual(len(cm.output), 1)
        self.assertIn("Expected one of bool, str, None, bytes, int, float", cm.output[0])

        valid_primitive_sequence = [1, 2.2, None, "cookie"]
        self.assertEqual(
            _clean_attribute_value(valid_primitive_sequence, None),
            tuple(valid_primitive_sequence),
        )
        for valid_primitive in valid_primitive_sequence:
            self.assertEqual(_clean_attribute_value(valid_primitive, None), valid_primitive)

        self.assertEqual(_clean_attribute_value(b"hello", 4), b"hello")

        with self.assertLogs("opentelemetry", level="WARNING") as cm:
            # String is truncated.
            self.assertEqual(_clean_attribute_value("a" * 1000, 5), "aaaaa")
        self.assertEqual(len(cm.output), 1)
        self.assertIn("String attribute value exceeds max length", cm.output[0])

        # Sequence of different types of values. List converted to tuple.
        self.assertEqual(
            _clean_attribute_value(["a", 2, _NoStrNoReprObject(), None, b"\xff"], None),
            ("a", 2, None, None, b"\xff"),
        )

        # non-str key in map... will be converted to string
        with self.assertLogs("opentelemetry", level="WARNING") as cm:
            self.assertEqual(_clean_attribute_value({2.2: 4.4}, None), {"2.2": 4.4})
        self.assertEqual(len(cm.output), 1)
        self.assertIn(
            "Invalid type",
            cm.output[0],
        )

        # Mapping of values..
        # Non string key without a string conversion method is dropped.
        self.assertEqual(
            _clean_attribute_value(
                {
                    "a": 1,
                    _NoStrNoReprObject(): 2,
                    "c": 3,
                    "d": [2, 3],
                    "bytes": b"\xff",
                },
                None,
            ),
            {"a": 1, "c": 3, "d": (2, 3), "bytes": b"\xff"},
        )

    def test_cyclic_attribute_values_are_replaced_with_none(self):
        cyclic_list = [1, 2]
        cyclic_list.append(cyclic_list)
        cyclic_mapping = {"value": 1}
        cyclic_mapping["self"] = cyclic_mapping

        with self.assertLogs("opentelemetry", level="WARNING") as cm:
            self.assertIsNone(_clean_attribute_value(cyclic_list, None))
            self.assertIsNone(_clean_attribute_value(cyclic_mapping, None))

        self.assertEqual(len(cm.output), 2)

    def test_excessively_nested_attribute_values_are_replaced_with_none(self):
        value = "value"
        for _ in range(5000):
            value = [value]

        with self.assertLogs("opentelemetry", level="WARNING"):
            self.assertIsNone(_clean_attribute_value(value, None))

    def test_attribute_values_at_supported_depth_are_preserved(self):
        value = "value"
        for _ in range(20):
            value = [value]

        cleaned = _clean_attribute_value(value, None)
        for _ in range(20):
            self.assertIsInstance(cleaned, tuple)
            cleaned = cleaned[0]
        self.assertEqual(cleaned, "value")

    def test_cyclic_attribute_keeps_sibling_attributes(self):
        cyclic = []
        cyclic.append(cyclic)

        with self.assertLogs("opentelemetry", level="WARNING"):
            attributes = BoundedAttributes(attributes={"good": "kept", "cyclic": cyclic})

        self.assertEqual(attributes["good"], "kept")
        self.assertIsNone(attributes["cyclic"])

    def test_cyclic_attribute_can_be_set_on_bounded_attributes(self):
        cyclic = {}
        cyclic["self"] = cyclic
        attributes = BoundedAttributes(immutable=False)

        with self.assertLogs("opentelemetry", level="WARNING"):
            attributes["cyclic"] = cyclic

        self.assertIn("cyclic", attributes)
        self.assertIsNone(attributes["cyclic"])

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

    def test_maxlen_reached(self):
        bdict = BoundedAttributes(1, {"first": "value"}, immutable=False)
        with self.assertLogs("opentelemetry", level="WARNING") as cm:
            bdict["second"] = "another"
        self.assertIn("Attributes dict is full. Dropping the oldest", cm.output[0])
        self.assertNotIn("first", bdict)
        self.assertEqual(bdict["second"], "another")
        self.assertEqual(bdict.dropped, 1)

    def test_maxlen_reached_logs_warning_once(self):
        bdict = BoundedAttributes(2, immutable=False)
        with self.assertLogs("opentelemetry", level="WARNING") as cm:
            for idx in range(5):
                bdict[f"key-{idx}"] = idx

        full_warnings = [warning for warning in cm.output if "Attributes dict is full" in warning]
        self.assertEqual(len(full_warnings), 1)
        self.assertEqual(len(bdict), 2)
        self.assertEqual(bdict.dropped, 3)

    def test_maxlen_reached_logs_warning_after_invalid_key_drop(self):
        bdict = BoundedAttributes(2, immutable=False)
        with self.assertLogs("opentelemetry", level="WARNING") as cm:
            bdict[1] = 2
            bdict["first"] = 1
            bdict["second"] = 2
            bdict["third"] = 3

        full_warnings = [warning for warning in cm.output if "Attributes dict is full" in warning]
        self.assertEqual(len(full_warnings), 1)
        self.assertEqual(bdict.dropped, 2)

    def test_negative_maxlen_not_allowed(self):
        with self.assertRaises(ValueError):
            BoundedAttributes(-1)

    def test_negative_max_value_len_not_allowed(self):
        with self.assertRaises(ValueError):
            BoundedAttributes(1, {"first": "value"}, immutable=False, max_value_len=-1)

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

    def test_no_deadlock_on_reentrant_logging(self):
        """Regression test for #3858.

        The deadlock scenario: a logging handler intercepts the warning
        emitted by _clean_attribute for an invalid value and calls __setitem__
        on the same BoundedAttributes instance from the same thread.
        With _clean_attribute called inside the lock this caused a deadlock.
        With _clean_attribute called before the lock is acquired, no deadlock
        occurs.
        """
        bdict = BoundedAttributes(immutable=False, max_value_len=20)

        class ReentrantHandler(logging.Handler):
            def emit(self, _record):
                # Simulates Sentry intercepting the OTel warning and writing
                # back into the same BoundedAttributes on the same thread.
                bdict["reentrant.key"] = "set_by_handler"

        otel_logger = logging.getLogger("opentelemetry.attributes")
        handler = ReentrantHandler()
        otel_logger.addHandler(handler)
        try:
            completed = threading.Event()

            def run():
                # A string value > 20 triggers a warning log in _clean_attribute, which fires the ReentrantHandler above.
                bdict["trigger.key"] = "a" * 21
                completed.set()

            thread = threading.Thread(target=run, daemon=True)
            thread.start()
            thread.join(timeout=2.0)

            self.assertTrue(
                completed.is_set(),
                "Deadlock detected: __setitem__ did not complete within 2s",
            )
            self.assertEqual(bdict.get("reentrant.key"), "set_by_handler")
        finally:
            otel_logger.removeHandler(handler)

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
        bdict = BoundedAttributes(maxlen=4, attributes=self.base, immutable=True)
        bdict_copy = copy.deepcopy(bdict)

        with self.assertRaises(TypeError):
            bdict_copy["invalid"] = "invalid"
