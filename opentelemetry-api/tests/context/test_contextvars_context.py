# Copyright 2020, OpenTelemetry Authors
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
from unittest.mock import patch

from opentelemetry import context

try:
    import contextvars  # pylint: disable=unused-import
    from opentelemetry.context.contextvars_context import (
        ContextVarsRuntimeContext,
    )
except ImportError:
    raise unittest.SkipTest("contextvars not available")


def do_work() -> None:
    context.attach(context.set_value("say", "bar"))


class TestContextVarsContext(unittest.TestCase):
    def setUp(self):
        self.previous_context = context.get_current()

    def tearDown(self):
        context.attach(self.previous_context)

    @patch(
        "opentelemetry.context._RUNTIME_CONTEXT",  # type: ignore
        ContextVarsRuntimeContext(),
    )
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

    @patch(
        "opentelemetry.context._RUNTIME_CONTEXT",  # type: ignore
        ContextVarsRuntimeContext(),
    )
    def test_set_value(self):
        first = context.set_value("a", "yyy")
        second = context.set_value("a", "zzz")
        third = context.set_value("a", "---", first)
        self.assertEqual("yyy", context.get_value("a", context=first))
        self.assertEqual("zzz", context.get_value("a", context=second))
        self.assertEqual("---", context.get_value("a", context=third))
        self.assertEqual(None, context.get_value("a"))

    @patch(
        "opentelemetry.context._RUNTIME_CONTEXT",  # type: ignore
        ContextVarsRuntimeContext(),
    )
    def test_set_current(self):
        context.attach(context.set_value("a", "yyy"))

        token = context.attach(context.set_value("a", "zzz"))
        self.assertEqual("zzz", context.get_value("a"))

        context.detach(token)
        self.assertEqual("yyy", context.get_value("a"))

        with self.assertLogs(level=ERROR):
            context.detach("some garbage")
