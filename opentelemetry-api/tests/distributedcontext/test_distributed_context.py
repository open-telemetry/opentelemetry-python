# Copyright 2019, OpenTelemetry Authors
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

import unittest

from opentelemetry import distributedcontext


class TestEntryMetadata(unittest.TestCase):
    def test_entry_ttl_no_propagation(self):
        metadata = distributedcontext.EntryMetadata(
            distributedcontext.EntryMetadata.NO_PROPAGATION,
        )
        self.assertEqual(metadata.entry_ttl, 0)

    def test_entry_ttl_unlimited_propagation(self):
        metadata = distributedcontext.EntryMetadata(
            distributedcontext.EntryMetadata.UNLIMITED_PROPAGATION,
        )
        self.assertEqual(metadata.entry_ttl, -1)


class TestEntryKey(unittest.TestCase):
    def test_create_too_long(self):
        with self.assertRaises(ValueError):
            distributedcontext.EntryKey.create("a" * 256)

    def test_create_invalid_character(self):
        with self.assertRaises(ValueError):
            distributedcontext.EntryKey.create("\x00")

    def test_create_valid(self):
        key = distributedcontext.EntryKey.create("ok")
        self.assertEqual(key, "ok")

    def test_key_new(self):
        key = distributedcontext.EntryKey("ok")
        self.assertEqual(key, "ok")


class TestEntryValue(unittest.TestCase):
    def test_create_invalid_character(self):
        with self.assertRaises(ValueError):
            distributedcontext.EntryValue.create("\x00")

    def test_create_valid(self):
        key = distributedcontext.EntryValue.create("ok")
        self.assertEqual(key, "ok")

    def test_key_new(self):
        key = distributedcontext.EntryValue("ok")
        self.assertEqual(key, "ok")


class TestDistributedContext(unittest.TestCase):
    def setUp(self):
        entry = self.entry = distributedcontext.Entry(
            distributedcontext.EntryMetadata(
                distributedcontext.EntryMetadata.NO_PROPAGATION,
            ),
            distributedcontext.EntryKey("key"),
            distributedcontext.EntryValue("value"),
        )
        context = self.context = distributedcontext.DistributedContext()
        context[entry.key] = entry

    def test_get_entries(self):
        self.assertIn(self.entry, self.context.get_entries())

    def test_get_entry_value_present(self):
        value = self.context.get_entry_value(
            self.entry.key,
        )
        self.assertIs(value, self.entry)

    def test_get_entry_value_missing(self):
        key = distributedcontext.EntryKey("missing")
        value = self.context.get_entry_value(key)
        self.assertIsNone(value)


class TestDistributedContextManager(unittest.TestCase):
    def setUp(self):
        self.manager = distributedcontext.DistributedContextManager()

    def test_get_current_context(self):
        self.assertIsNone(self.manager.get_current_context())

    def test_use_context(self):
        expected = object()
        with self.manager.use_context(expected) as output:
            self.assertIs(output, expected)
