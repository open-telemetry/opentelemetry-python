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

from opentelemetry import correlationcontext
from opentelemetry.correlationcontext import CorrelationContext
from opentelemetry.correlationcontext.propagation.context import (
    from_context,
    with_correlation_context,
)


class TestEntryMetadata(unittest.TestCase):
    def test_entry_ttl_no_propagation(self):
        metadata = correlationcontext.EntryMetadata(
            correlationcontext.EntryMetadata.NO_PROPAGATION
        )
        self.assertEqual(metadata.entry_ttl, 0)

    def test_entry_ttl_unlimited_propagation(self):
        metadata = correlationcontext.EntryMetadata(
            correlationcontext.EntryMetadata.UNLIMITED_PROPAGATION
        )
        self.assertEqual(metadata.entry_ttl, -1)


class TestEntryKey(unittest.TestCase):
    def test_create_empty(self):
        with self.assertRaises(ValueError):
            correlationcontext.EntryKey.create("")

    def test_create_too_long(self):
        with self.assertRaises(ValueError):
            correlationcontext.EntryKey.create("a" * 256)

    def test_create_invalid_character(self):
        with self.assertRaises(ValueError):
            correlationcontext.EntryKey.create("\x00")

    def test_create_valid(self):
        key = correlationcontext.EntryKey.create("ok")
        self.assertEqual(key, "ok")

    def test_key_new(self):
        key = correlationcontext.EntryKey("ok")
        self.assertEqual(key, "ok")


class TestEntryValue(unittest.TestCase):
    def test_create_invalid_character(self):
        with self.assertRaises(ValueError):
            correlationcontext.EntryValue.create("\x00")

    def test_create_valid(self):
        key = correlationcontext.EntryValue.create("ok")
        self.assertEqual(key, "ok")

    def test_key_new(self):
        key = correlationcontext.EntryValue("ok")
        self.assertEqual(key, "ok")


# TODO:replace these
# class TestCorrelationContext(unittest.TestCase):
#     def setUp(self):
#         self.entry = correlationcontext.Entry(
#             correlationcontext.EntryMetadata(
#                 correlationcontext.EntryMetadata.NO_PROPAGATION
#             ),
#             correlationcontext.EntryKey("key"),
#             correlationcontext.EntryValue("value"),
#         )
#         self.context = with_correlation_context(
#             CorrelationContext(entries=[self.entry])
#         )

#     def test_get_entries(self):
#         self.assertIn(
#             self.entry, from_context(self.context).get_entries(),
#         )

#     def test_get_entry_value_present(self):
#         value = correlationcontext.CorrelationContext.get_entry_value(
#             self.context, self.entry.key
#         )
#         self.assertIs(value, self.entry.value)

#     def test_get_entry_value_missing(self):
#         key = correlationcontext.EntryKey("missing")
#         value = correlationcontext.CorrelationContext.get_entry_value(
#             self.context, key
#         )
#         self.assertIsNone(value)


# TODO:replace these
# class TestCorrelationContextManager(unittest.TestCase):
#     def setUp(self):
#         self.manager = correlationcontext.CorrelationContextManager()

#     def test_current_context(self):
#         self.assertIsNone(self.manager.current_context())

#     def test_use_context(self):
#         expected = correlationcontext.CorrelationContext(
#             (
#                 correlationcontext.Entry(
#                     correlationcontext.EntryMetadata(0),
#                     correlationcontext.EntryKey("0"),
#                     correlationcontext.EntryValue(""),
#                 ),
#             )
#         )
#         with self.manager.use_context(expected) as output:
#             self.assertIs(output, expected)
