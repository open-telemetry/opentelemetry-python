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

# type: ignore

import unittest

from opentelemetry import baggage, trace
from opentelemetry.propagate import extract, inject
from opentelemetry.trace import get_current_span, set_span_in_context
from opentelemetry.trace.span import format_span_id, format_trace_id


class TestDefaultGlobalPropagator(unittest.TestCase):
    """Test ensures the default global composite propagator works as intended"""

    TRACE_ID = int("12345678901234567890123456789012", 16)  # type:int
    SPAN_ID = int("1234567890123456", 16)  # type:int

    def test_propagation(self):
        traceparent_value = (
            f"00-{format_trace_id(self.TRACE_ID)}-"
            f"{format_span_id(self.SPAN_ID)}-00"
        )
        tracestate_value = "foo=1,bar=2,baz=3"
        headers = {
            "baggage": ["key1=val1,key2=val2"],
            "traceparent": [traceparent_value],
            "tracestate": [tracestate_value],
        }
        ctx = extract(headers)
        baggage_entries = baggage.get_all(context=ctx)
        expected = {"key1": "val1", "key2": "val2"}
        self.assertEqual(baggage_entries, expected)
        span_context = get_current_span(context=ctx).get_span_context()

        self.assertEqual(span_context.trace_id, self.TRACE_ID)
        self.assertEqual(span_context.span_id, self.SPAN_ID)

        span = trace.NonRecordingSpan(span_context)
        ctx = baggage.set_baggage("key3", "val3")
        ctx = baggage.set_baggage("key4", "val4", context=ctx)
        ctx = set_span_in_context(span, context=ctx)
        output = {}
        inject(output, context=ctx)
        self.assertEqual(traceparent_value, output["traceparent"])
        self.assertIn("key3=val3", output["baggage"])
        self.assertIn("key4=val4", output["baggage"])
        self.assertIn("foo=1", output["tracestate"])
        self.assertIn("bar=2", output["tracestate"])
        self.assertIn("baz=3", output["tracestate"])
