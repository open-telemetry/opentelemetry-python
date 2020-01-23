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


def do_work():
    context.set_value("say-something", "bar")


class TestContext(unittest.TestCase):
    def test_context(self):
        self.assertIsNone(context.current().value("say-something"))
        empty_context = context.current()
        context.set_value("say-something", "foo")
        self.assertEqual(context.current().value("say-something"), "foo")
        second_context = context.current()

        do_work()
        self.assertEqual(context.current().value("say-something"), "bar")
        third_context = context.current()

        self.assertIsNone(empty_context.value("say-something"))
        self.assertEqual(second_context.value("say-something"), "foo")
        self.assertEqual(third_context.value("say-something"), "bar")

    def test_merge(self):
        context.set_value("name", "first")
        context.set_value("somebool", True)
        context.set_value("key", "value")
        context.set_value("otherkey", "othervalue")
        src_ctx = context.current()

        context.set_value("name", "second")
        context.set_value("somebool", False)
        context.set_value("anotherkey", "anothervalue")
        dst_ctx = context.current()

        context.set_current(
            context.merge_context_correlation(src_ctx, dst_ctx)
        )
        current = context.current()
        self.assertEqual(current.value("name"), "first")
        self.assertTrue(current.value("somebool"))
        self.assertEqual(current.value("key"), "value")
        self.assertEqual(current.value("otherkey"), "othervalue")
        self.assertEqual(current.value("anotherkey"), "anothervalue")

    def test_propagation(self):
        pass

    def test_restore_context_on_exit(self):
        context.set_current(context.new_context())
        context.set_value("a", "xxx")
        context.set_value("b", "yyy")

        self.assertEqual({"a": "xxx", "b": "yyy"}, context.current().snapshot)
        with context.use(a="foo"):
            self.assertEqual(
                {"a": "foo", "b": "yyy"}, context.current().snapshot
            )
            context.set_value("a", "i_want_to_mess_it_but_wont_work")
            context.set_value("b", "i_want_to_mess_it")
        self.assertEqual({"a": "xxx", "b": "yyy"}, context.current().snapshot)

    def test_set_value(self):
        first = context.set_value("a", "yyy")
        second = context.set_value("a", "zzz")
        third = context.set_value("a", "---", first)
        current_context = context.current()
        self.assertEqual("yyy", context.value("a", context=first))
        self.assertEqual("zzz", context.value("a", context=second))
        self.assertEqual("---", context.value("a", context=third))
        self.assertEqual("zzz", context.value("a", context=current_context))
