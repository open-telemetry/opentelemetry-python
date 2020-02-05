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

from opentelemetry import context
from opentelemetry.sdk.context.contextvars_context import ContextVarsContext
from opentelemetry.sdk.context.threadlocal_context import ThreadLocalContext


def do_work() -> None:
    context.set_current(context.set_value("say-something", "bar"))


class TestThreadLocalContext(unittest.TestCase):
    def setUp(self):
        self.previous_context = context.get_current()
        context.set_current(ThreadLocalContext())

    def tearDown(self):
        context.set_current(self.previous_context)

    def test_context(self):
        self.assertIsNone(context.get_value("say-something"))
        empty_context = context.get_current()
        second_context = context.set_value("say-something", "foo")
        self.assertEqual(second_context.get_value("say-something"), "foo")

        do_work()
        self.assertEqual(context.get_value("say-something"), "bar")
        third_context = context.get_current()

        self.assertIsNone(empty_context.get_value("say-something"))
        self.assertEqual(second_context.get_value("say-something"), "foo")
        self.assertEqual(third_context.get_value("say-something"), "bar")

    def test_set_value(self):
        first = context.set_value("a", "yyy")
        second = context.set_value("a", "zzz")
        third = context.set_value("a", "---", first)
        self.assertEqual("yyy", context.get_value("a", context=first))
        self.assertEqual("zzz", context.get_value("a", context=second))
        self.assertEqual("---", context.get_value("a", context=third))
        self.assertEqual(None, context.get_value("a"))


class TestContextVarsContext(unittest.TestCase):
    def setUp(self):
        self.previous_context = context.get_current()
        context.set_current(ContextVarsContext())

    def tearDown(self):
        context.set_current(self.previous_context)

    def test_context(self):
        self.assertIsNone(context.get_value("say-something"))
        empty_context = context.get_current()
        second_context = context.set_value("say-something", "foo")
        self.assertEqual(second_context.get_value("say-something"), "foo")

        do_work()
        self.assertEqual(context.get_value("say-something"), "bar")
        third_context = context.get_current()

        self.assertIsNone(empty_context.get_value("say-something"))
        self.assertEqual(second_context.get_value("say-something"), "foo")
        self.assertEqual(third_context.get_value("say-something"), "bar")

    def test_set_value(self):
        first = context.set_value("a", "yyy")
        second = context.set_value("a", "zzz")
        third = context.set_value("a", "---", first)
        self.assertEqual("yyy", context.get_value("a", context=first))
        self.assertEqual("zzz", context.get_value("a", context=second))
        self.assertEqual("---", context.get_value("a", context=third))
        self.assertEqual(None, context.get_value("a"))
