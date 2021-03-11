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

from opentelemetry import trace


class TestTracer(unittest.TestCase):
    def setUp(self):
        # pylint: disable=protected-access
        self.tracer = trace._DefaultTracer()

    def test_start_span(self):
        with self.tracer.start_span("") as span:
            self.assertIsInstance(span, trace.Span)

    def test_start_as_current_span(self):
        with self.tracer.start_as_current_span("") as span:
            self.assertIsInstance(span, trace.Span)

    def test_get_current_span(self):
        with self.tracer.start_as_current_span("test") as span:
            trace.get_current_span().set_attribute("test", "test")
            self.assertEqual(span, trace.INVALID_SPAN)
            self.assertFalse(hasattr("span", "attributes"))
