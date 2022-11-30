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

from unittest import TestCase

from opentelemetry.baggage import (
    _is_valid_value,
    clear,
    get_all,
    get_baggage,
    remove_baggage,
    set_baggage,
)
from opentelemetry.context import attach, detach


class TestBaggageManager(TestCase):
    def test_set_baggage(self):
        self.assertEqual({}, get_all())

        ctx = set_baggage("test", "value")
        self.assertEqual(get_baggage("test", context=ctx), "value")

        ctx = set_baggage("test", "value2", context=ctx)
        self.assertEqual(get_baggage("test", context=ctx), "value2")

    def test_baggages_current_context(self):
        token = attach(set_baggage("test", "value"))
        self.assertEqual(get_baggage("test"), "value")
        detach(token)
        self.assertEqual(get_baggage("test"), None)

    def test_set_multiple_baggage_entries(self):
        ctx = set_baggage("test", "value")
        ctx = set_baggage("test2", "value2", context=ctx)
        self.assertEqual(get_baggage("test", context=ctx), "value")
        self.assertEqual(get_baggage("test2", context=ctx), "value2")
        self.assertEqual(
            get_all(context=ctx),
            {"test": "value", "test2": "value2"},
        )

    def test_modifying_baggage(self):
        ctx = set_baggage("test", "value")
        self.assertEqual(get_baggage("test", context=ctx), "value")
        baggage_entries = get_all(context=ctx)
        with self.assertRaises(TypeError):
            baggage_entries["test"] = "mess-this-up"
        self.assertEqual(get_baggage("test", context=ctx), "value")

    def test_remove_baggage_entry(self):
        self.assertEqual({}, get_all())

        ctx = set_baggage("test", "value")
        ctx = set_baggage("test2", "value2", context=ctx)
        ctx = remove_baggage("test", context=ctx)
        self.assertEqual(get_baggage("test", context=ctx), None)
        self.assertEqual(get_baggage("test2", context=ctx), "value2")

    def test_clear_baggage(self):
        self.assertEqual({}, get_all())

        ctx = set_baggage("test", "value")
        self.assertEqual(get_baggage("test", context=ctx), "value")

        ctx = clear(context=ctx)
        self.assertEqual(get_all(context=ctx), {})

    def test__is_valid_value(self):
        self.assertTrue(_is_valid_value("GET%20%2Fapi%2F%2Freport"))
