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
from opentelemetry import correlationcontext as cctx


class TestCorrelationContextManager(unittest.TestCase):
    def test_set_correlation(self):
        self.assertEqual({}, cctx.get_correlations())

        ctx = cctx.set_correlation("test", "value")
        self.assertEqual(cctx.get_correlation("test", context=ctx), "value")

        ctx = cctx.set_correlation("test", "value2", context=ctx)
        self.assertEqual(cctx.get_correlation("test", context=ctx), "value2")

    def test_correlations_current_context(self):
        token = context.attach(cctx.set_correlation("test", "value"))
        self.assertEqual(cctx.get_correlation("test"), "value")
        context.detach(token)
        self.assertEqual(cctx.get_correlation("test"), None)

    def test_set_multiple_correlations(self):
        ctx = cctx.set_correlation("test", "value")
        ctx = cctx.set_correlation("test2", "value2", context=ctx)
        self.assertEqual(cctx.get_correlation("test", context=ctx), "value")
        self.assertEqual(cctx.get_correlation("test2", context=ctx), "value2")
        self.assertEqual(
            cctx.get_correlations(context=ctx),
            {"test": "value", "test2": "value2"},
        )

    def test_modifying_correlations(self):
        ctx = cctx.set_correlation("test", "value")
        self.assertEqual(cctx.get_correlation("test", context=ctx), "value")
        correlations = cctx.get_correlations(context=ctx)
        correlations["test"] = "mess-this-up"
        self.assertEqual(cctx.get_correlation("test", context=ctx), "value")

    def test_remove_correlations(self):
        self.assertEqual({}, cctx.get_correlations())

        ctx = cctx.set_correlation("test", "value")
        ctx = cctx.set_correlation("test2", "value2", context=ctx)
        ctx = cctx.remove_correlation("test", context=ctx)
        self.assertEqual(cctx.get_correlation("test", context=ctx), None)
        self.assertEqual(cctx.get_correlation("test2", context=ctx), "value2")

    def test_clear_correlations(self):
        self.assertEqual({}, cctx.get_correlations())

        ctx = cctx.set_correlation("test", "value")
        self.assertEqual(cctx.get_correlation("test", context=ctx), "value")

        ctx = cctx.clear_correlations(context=ctx)
        self.assertEqual(cctx.get_correlations(context=ctx), {})
