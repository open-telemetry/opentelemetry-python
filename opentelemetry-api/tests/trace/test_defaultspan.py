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


class TestDefaultSpan(unittest.TestCase):
    def test_ctor(self):
        span = trace.DefaultSpan(
            1,
            1,
            is_remote=False,
            trace_flags=trace.DEFAULT_TRACE_OPTIONS,
            trace_state=trace.DEFAULT_TRACE_STATE,
        )
        self.assertEqual(1, span.trace_id)
        self.assertEqual(1, span.trace_id)
        self.assertEqual(False, span.is_remote)
        self.assertEqual(trace.DEFAULT_TRACE_OPTIONS, span.trace_flags)
        self.assertEqual(trace.DEFAULT_TRACE_STATE, span.trace_state)

    def test_invalid_span(self):
        # TODO: Test the actual expected values of an invalid Span.
        self.assertIsNotNone(trace.INVALID_SPAN)
        self.assertIsNotNone(trace.INVALID_SPAN.trace_id)
        self.assertIsNotNone(trace.INVALID_SPAN.span_id)
        self.assertIsNotNone(trace.INVALID_SPAN.is_remote)
        self.assertIsNotNone(trace.INVALID_SPAN.trace_flags)
        self.assertIsNotNone(trace.INVALID_SPAN.trace_state)
        self.assertFalse(trace.INVALID_SPAN.is_valid)
