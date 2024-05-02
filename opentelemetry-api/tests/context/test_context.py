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
from unittest.mock import patch

from opentelemetry import context
from opentelemetry.context.context import Context
from opentelemetry.context.contextvars_context import ContextVarsRuntimeContext
from opentelemetry.environment_variables import OTEL_PYTHON_CONTEXT


def _do_work() -> str:
    key = context.create_key("say")
    context.attach(context.set_value(key, "bar"))
    return key


class TestContext(unittest.TestCase):
    def setUp(self):
        context.attach(Context())

    def test_context_key(self):
        key1 = context.create_key("say")
        key2 = context.create_key("say")
        self.assertNotEqual(key1, key2)
        first = context.set_value(key1, "foo")
        second = context.set_value(key2, "bar")
        self.assertEqual(context.get_value(key1, context=first), "foo")
        self.assertEqual(context.get_value(key2, context=second), "bar")

    def test_context(self):
        key1 = context.create_key("say")
        self.assertIsNone(context.get_value(key1))
        empty = context.get_current()
        second = context.set_value(key1, "foo")
        self.assertEqual(context.get_value(key1, context=second), "foo")

        key2 = _do_work()
        self.assertEqual(context.get_value(key2), "bar")
        third = context.get_current()

        self.assertIsNone(context.get_value(key1, context=empty))
        self.assertEqual(context.get_value(key1, context=second), "foo")
        self.assertEqual(context.get_value(key2, context=third), "bar")

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


class TestInitContext(unittest.TestCase):
    def test_load_runtime_context_default(self):
        ctx = context._load_runtime_context()  # pylint: disable=W0212
        self.assertIsInstance(ctx, ContextVarsRuntimeContext)

    @patch.dict("os.environ", {OTEL_PYTHON_CONTEXT: "contextvars_context"})
    def test_load_runtime_context(self):  # type: ignore[misc]
        ctx = context._load_runtime_context()  # pylint: disable=W0212
        self.assertIsInstance(ctx, ContextVarsRuntimeContext)

    @patch.dict("os.environ", {OTEL_PYTHON_CONTEXT: "foo"})
    def test_load_runtime_context_fallback(self):  # type: ignore[misc]
        ctx = context._load_runtime_context()  # pylint: disable=W0212
        self.assertIsInstance(ctx, ContextVarsRuntimeContext)
