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
from logging import ERROR

from opentelemetry import context


def do_work() -> None:
    context.attach(context.set_value("say", "bar"))


class ContextTestCases:
    class BaseTest(unittest.TestCase):
        def setUp(self) -> None:
            self.previous_context = context.get_current()

        def tearDown(self) -> None:
            context.attach(self.previous_context)

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

        def test_attach(self):
            context.attach(context.set_value("a", "yyy"))

            token = context.attach(context.set_value("a", "zzz"))
            self.assertEqual("zzz", context.get_value("a"))

            context.detach(token)
            self.assertEqual("yyy", context.get_value("a"))

            with self.assertLogs(level=ERROR):
                context.detach("some garbage")

        def test_detach_out_of_order(self):
            t1 = context.attach(context.set_value("c", 1))
            self.assertEqual(context.get_current(), {"c": 1})
            t2 = context.attach(context.set_value("c", 2))
            self.assertEqual(context.get_current(), {"c": 2})
            context.detach(t1)
            self.assertEqual(context.get_current(), {})
            context.detach(t2)
            self.assertEqual(context.get_current(), {"c": 1})
