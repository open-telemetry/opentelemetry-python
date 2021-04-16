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

from opentelemetry import baggage, context


class TestBaggageManager(unittest.TestCase):
    def test_set_baggage(self):
        self.assertEqual({}, baggage.get_all())

        ctx = baggage.set_baggage("test", "value")
        self.assertEqual(baggage.get_baggage("test", context=ctx), "value")

        ctx = baggage.set_baggage("test", "value2", context=ctx)
        self.assertEqual(baggage.get_baggage("test", context=ctx), "value2")

    def test_baggages_current_context(self):
        token = context.attach(baggage.set_baggage("test", "value"))
        self.assertEqual(baggage.get_baggage("test"), "value")
        context.detach(token)
        self.assertEqual(baggage.get_baggage("test"), None)

    def test_set_multiple_baggage_entries(self):
        ctx = baggage.set_baggage("test", "value")
        ctx = baggage.set_baggage("test2", "value2", context=ctx)
        self.assertEqual(baggage.get_baggage("test", context=ctx), "value")
        self.assertEqual(baggage.get_baggage("test2", context=ctx), "value2")
        self.assertEqual(
            baggage.get_all(context=ctx),
            {"test": "value", "test2": "value2"},
        )

    def test_modifying_baggage(self):
        ctx = baggage.set_baggage("test", "value")
        self.assertEqual(baggage.get_baggage("test", context=ctx), "value")
        baggage_entries = baggage.get_all(context=ctx)
        with self.assertRaises(TypeError):
            baggage_entries["test"] = "mess-this-up"
        self.assertEqual(baggage.get_baggage("test", context=ctx), "value")

    def test_remove_baggage_entry(self):
        self.assertEqual({}, baggage.get_all())

        ctx = baggage.set_baggage("test", "value")
        ctx = baggage.set_baggage("test2", "value2", context=ctx)
        ctx = baggage.remove_baggage("test", context=ctx)
        self.assertEqual(baggage.get_baggage("test", context=ctx), None)
        self.assertEqual(baggage.get_baggage("test2", context=ctx), "value2")

    def test_clear_baggage(self):
        self.assertEqual({}, baggage.get_all())

        ctx = baggage.set_baggage("test", "value")
        self.assertEqual(baggage.get_baggage("test", context=ctx), "value")

        ctx = baggage.clear(context=ctx)
        self.assertEqual(baggage.get_all(context=ctx), {})
