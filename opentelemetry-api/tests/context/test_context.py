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

import unittest

from opentelemetry import context
from opentelemetry.context.context import Context


def do_work() -> None:
    context.attach(context.set_value("say", "bar"))


class TestContext(unittest.TestCase):
    def setUp(self):
        context.attach(Context())

    def test_context(self):
        self.assertIsNone(context.get_value("say"))
        empty = context.get_current()
        second = context.set_value("say", "foo")
        self.assertEqual(context.get_value("say", context=second), "foo")

        do_work()
        self.assertEqual(context.get_value("say"), "bar")
        third = context.get_current()

        self.assertIsNone(context.get_value("say", context=empty))
        self.assertEqual(context.get_value("say", context=second), "foo")
        self.assertEqual(context.get_value("say", context=third), "bar")

    def test_set_value(self):
        first = context.set_value("a", "yyy")
        second = context.set_value("a", "zzz")
        third = context.set_value("a", "---", first)
        self.assertEqual("yyy", context.get_value("a", context=first))
        self.assertEqual("zzz", context.get_value("a", context=second))
        self.assertEqual("---", context.get_value("a", context=third))
        self.assertEqual(None, context.get_value("a"))

    def test_context_is_immutable(self):
        with self.assertRaises(ValueError):
            # ensure a context
            context.get_current()["test"] = "cant-change-immutable"

    def test_set_current(self):
        context.attach(context.set_value("a", "yyy"))

        token = context.attach(context.set_value("a", "zzz"))
        self.assertEqual("zzz", context.get_value("a"))

        context.detach(token)
        self.assertEqual("yyy", context.get_value("a"))
