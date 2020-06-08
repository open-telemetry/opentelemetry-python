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

import typing
import unittest

from opentelemetry import correlationcontext, trace
from opentelemetry.propagators import extract, inject
from opentelemetry.trace import get_current_span, set_span_in_context


def get_as_list(
    dict_object: typing.Dict[str, typing.List[str]], key: str
) -> typing.List[str]:
    value = dict_object.get(key)
    return value if value is not None else []


class TestDefaultGlobalPropagator(unittest.TestCase):
    """Test ensures the default global composite propagator works as intended
    """

    TRACE_ID = int("12345678901234567890123456789012", 16)  # type:int
    SPAN_ID = int("1234567890123456", 16)  # type:int

    def test_propagation(self):
        traceparent_value = "00-{trace_id}-{span_id}-00".format(
            trace_id=format(self.TRACE_ID, "032x"),
            span_id=format(self.SPAN_ID, "016x"),
        )
        tracestate_value = "foo=1,bar=2,baz=3"
        headers = {
            "otcorrelationcontext": ["key1=val1,key2=val2"],
            "traceparent": [traceparent_value],
            "tracestate": [tracestate_value],
        }
        ctx = extract(get_as_list, headers)
        correlations = correlationcontext.get_correlations(context=ctx)
        expected = {"key1": "val1", "key2": "val2"}
        self.assertEqual(correlations, expected)
        span_context = get_current_span(context=ctx).get_context()

        self.assertEqual(span_context.trace_id, self.TRACE_ID)
        self.assertEqual(span_context.span_id, self.SPAN_ID)

        span = trace.DefaultSpan(span_context)
        ctx = correlationcontext.set_correlation("key3", "val3")
        ctx = correlationcontext.set_correlation("key4", "val4", context=ctx)
        ctx = set_span_in_context(span, context=ctx)
        output = {}
        inject(dict.__setitem__, output, context=ctx)
        self.assertEqual(traceparent_value, output["traceparent"])
        self.assertIn("key3=val3", output["otcorrelationcontext"])
        self.assertIn("key4=val4", output["otcorrelationcontext"])
        self.assertIn("foo=1", output["tracestate"])
        self.assertIn("bar=2", output["tracestate"])
        self.assertIn("baz=3", output["tracestate"])
