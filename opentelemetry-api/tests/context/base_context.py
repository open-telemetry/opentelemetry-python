# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

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
                context.detach(token)

        def test_detach_out_of_order(self):
            t1 = context.attach(context.set_value("c", 1))
            self.assertEqual(context.get_current(), {"c": 1})
            t2 = context.attach(context.set_value("c", 2))
            self.assertEqual(context.get_current(), {"c": 2})
            context.detach(t1)
            self.assertEqual(context.get_current(), {})
            context.detach(t2)
            self.assertEqual(context.get_current(), {"c": 1})
