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


from opentelemetry.distributedcontext import (
    Entry,
    EntryMetadata,
    EntryKey,
    EntryValue,
)

from opentelemetry.sdk import distributedcontext


class TestDistributedContext(unittest.TestCase):
    def setUp(self):
        entry = self.entry = Entry(
            EntryMetadata(EntryMetadata.NO_PROPAGATION),
            EntryKey("key"),
            EntryValue("value"),
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
        key = EntryKey("missing")
        value = self.context.get_entry_value(key)
        self.assertIsNone(value)


class TestDistributedContextManager(unittest.TestCase):
    def setUp(self):
        self.manager = distributedcontext.DistributedContextManager()

    def test_use_context(self):
        # Context is None initially
        self.assertIsNone(self.manager.get_current_context())

        # Start initial context
        dctx = distributedcontext.DistributedContext()
        with self.manager.use_context(dctx) as current:
            self.assertIs(current, dctx)
            self.assertIs(
                self.manager.get_current_context(),
                dctx,
            )

            # Context is overridden
            nested_dctx = distributedcontext.DistributedContext()
            with self.manager.use_context(nested_dctx) as current:
                self.assertIs(current, nested_dctx)
                self.assertIs(
                    self.manager.get_current_context(),
                    nested_dctx,
                )

            # Context is restored
            self.assertIs(
                self.manager.get_current_context(),
                dctx,
            )
