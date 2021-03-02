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


class TestNonRecordingSpan(unittest.TestCase):
    def test_ctor(self):
        context = trace.SpanContext(
            1,
            1,
            is_remote=False,
            trace_flags=trace.DEFAULT_TRACE_OPTIONS,
            trace_state=trace.DEFAULT_TRACE_STATE,
        )
        span = trace.NonRecordingSpan(context)
        self.assertEqual(context, span.get_span_context())

    def test_invalid_span(self):
        self.assertIsNotNone(trace.INVALID_SPAN)
        self.assertIsNotNone(trace.INVALID_SPAN.get_span_context())
        self.assertFalse(trace.INVALID_SPAN.get_span_context().is_valid)
