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

from opentelemetry import correlationcontext
from opentelemetry.context import ContextAPI


class TestCorrelationContextManager(unittest.TestCase):
    def setUp(self):
        self.context = ContextAPI()
        self.manager = correlationcontext.CorrelationContextManager()
        self.manager.set_correlation(
            self.context, "client-version", "initial.version"
        )

    def test_get_correlation(self):
        self.assertEqual(
            self.manager.get_correlation(self.context, "client-version"),
            "initial.version",
        )

    def test_set_correlation(self):
        context = self.manager.set_correlation(
            self.context, "client-version", "test.point.oh"
        )
        self.assertEqual(
            self.manager.get_correlation(context, "client-version"),
            "test.point.oh",
        )

    def test_remove_correlation(self):
        context = self.manager.set_correlation(
            self.context, "new-correlation", "value"
        )
        self.assertEqual(
            self.manager.get_correlation(context, "new-correlation"), "value"
        )
        context = self.manager.remove_correlation(context, "new-correlation")
        self.assertIsNone(
            self.manager.get_correlation(context, "new-correlation")
        )

    def test_clear_correlation(self):
        context = self.manager.set_correlation(
            self.context, "new-correlation", "value"
        )
        self.assertEqual(
            self.manager.get_correlation(context, "new-correlation"), "value"
        )
        context = self.manager.clear_correlations(context)
        self.assertIsNone(
            self.manager.get_correlation(context, "new-correlation")
        )
