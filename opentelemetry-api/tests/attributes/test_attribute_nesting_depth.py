# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import unittest

from opentelemetry.attributes import BoundedAttributes, _clean_attribute_value


def _cyclic_list():
    value = [1, 2]
    value.append(value)
    return value


def _nested_list(depth):
    value = "value"
    for _ in range(depth):
        value = [value]
    return value


class TestAttributeNestingDepth(unittest.TestCase):
    def test_cyclic_sequence_is_replaced_with_none(self):
        with self.assertLogs("opentelemetry.attributes", level="WARNING"):
            self.assertIsNone(_clean_attribute_value(_cyclic_list(), None))

    def test_cyclic_mapping_is_replaced_with_none(self):
        value = {"value": 1}
        value["self"] = value
        with self.assertLogs("opentelemetry.attributes", level="WARNING"):
            self.assertIsNone(_clean_attribute_value(value, None))

    def test_twenty_nested_levels_are_preserved(self):
        cleaned = _clean_attribute_value(_nested_list(20), None)
        for _ in range(20):
            self.assertIsInstance(cleaned, tuple)
            cleaned = cleaned[0]
        self.assertEqual(cleaned, "value")

    def test_excessive_nesting_is_replaced_with_none(self):
        with self.assertLogs("opentelemetry.attributes", level="WARNING"):
            self.assertIsNone(_clean_attribute_value(_nested_list(21), None))

    def test_invalid_value_preserves_sibling_attributes(self):
        with self.assertLogs("opentelemetry.attributes", level="WARNING"):
            attributes = BoundedAttributes(attributes={"good": "kept", "cyclic": _cyclic_list()})
        self.assertEqual(attributes["good"], "kept")
        self.assertIsNone(attributes["cyclic"])

    def test_invalid_value_can_be_set_on_bounded_attributes(self):
        attributes = BoundedAttributes(immutable=False)
        with self.assertLogs("opentelemetry.attributes", level="WARNING"):
            attributes["cyclic"] = _cyclic_list()
        self.assertIn("cyclic", attributes)
        self.assertIsNone(attributes["cyclic"])
