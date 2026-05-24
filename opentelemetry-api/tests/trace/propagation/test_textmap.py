# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# type: ignore

import unittest

from opentelemetry.propagators.textmap import DefaultGetter


class TestDefaultGetter(unittest.TestCase):
    def test_get_none(self):
        getter = DefaultGetter()
        carrier = {}
        val = getter.get(carrier, "test")
        self.assertIsNone(val)

    def test_get_str(self):
        getter = DefaultGetter()
        carrier = {"test": "val"}
        val = getter.get(carrier, "test")
        self.assertEqual(val, ["val"])

    def test_get_iter(self):
        getter = DefaultGetter()
        carrier = {"test": ["val"]}
        val = getter.get(carrier, "test")
        self.assertEqual(val, ["val"])

    def test_keys(self):
        getter = DefaultGetter()
        keys = getter.keys({"test": "val"})
        self.assertEqual(keys, ["test"])
