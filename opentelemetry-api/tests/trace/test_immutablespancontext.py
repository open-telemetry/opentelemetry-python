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
from opentelemetry.trace import TraceFlags, TraceState


class TestImmutableSpanContext(unittest.TestCase):
    def test_ctor(self):
        context = trace.SpanContext(
            1,
            1,
            is_remote=False,
            trace_flags=trace.DEFAULT_TRACE_OPTIONS,
            trace_state=trace.DEFAULT_TRACE_STATE,
        )

        self.assertEqual(context.trace_id, 1)
        self.assertEqual(context.span_id, 1)
        self.assertEqual(context.is_remote, False)
        self.assertEqual(context.trace_flags, trace.DEFAULT_TRACE_OPTIONS)
        self.assertEqual(context.trace_state, trace.DEFAULT_TRACE_STATE)

    def test_attempt_change_attributes(self):
        context = trace.SpanContext(
            1,
            2,
            is_remote=False,
            trace_flags=trace.DEFAULT_TRACE_OPTIONS,
            trace_state=trace.DEFAULT_TRACE_STATE,
        )

        # attempt to change the attribute values
        context.trace_id = 2  # type: ignore
        context.span_id = 3  # type: ignore
        context.is_remote = True  # type: ignore
        context.trace_flags = TraceFlags(3)  # type: ignore
        context.trace_state = TraceState([("test", "test")])  # type: ignore

        # check if attributes changed
        self.assertEqual(context.trace_id, 1)
        self.assertEqual(context.span_id, 2)
        self.assertEqual(context.is_remote, False)
        self.assertEqual(context.trace_flags, trace.DEFAULT_TRACE_OPTIONS)
        self.assertEqual(context.trace_state, trace.DEFAULT_TRACE_STATE)
