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

import opentelemetry.sdk.trace as trace
import opentelemetry.sdk.trace.propagation.jaeger_propagator as jaeger
import opentelemetry.trace as trace_api
from opentelemetry import baggage
from opentelemetry.trace.propagation.textmap import DictGetter

FORMAT = jaeger.JaegerPropagator()


carrier_getter = DictGetter()


def get_context_new_carrier(old_carrier, carrier_baggage=None):

    ctx = FORMAT.extract(carrier_getter, old_carrier)
    if carrier_baggage:
        for key, value in carrier_baggage.items():
            ctx = baggage.set_baggage(key, value, ctx)
    parent_span_context = trace_api.get_current_span(ctx).get_span_context()

    parent = trace._Span("parent", parent_span_context)
    child = trace._Span(
        "child",
        trace_api.SpanContext(
            parent_span_context.trace_id,
            trace_api.RandomIdsGenerator().generate_span_id(),
            is_remote=False,
            trace_flags=parent_span_context.trace_flags,
            trace_state=parent_span_context.trace_state,
        ),
        parent=parent.get_span_context(),
    )

    new_carrier = {}
    ctx = trace_api.set_span_in_context(child, ctx)

    FORMAT.inject(dict.__setitem__, new_carrier, context=ctx)

    return ctx, new_carrier


class TestJaegerPropagator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ids_generator = trace_api.RandomIdsGenerator()
        cls.trace_id = ids_generator.generate_trace_id()
        cls.span_id = ids_generator.generate_span_id()
        cls.parent_span_id = ids_generator.generate_span_id()
        cls.serialized_uber_trace_id = "{:032x}:{:016x}:{:016x}:{:02x}".format(
            cls.trace_id, cls.span_id, cls.parent_span_id, 1
        )

    def test_extract_valid_span(self):
        old_carrier = {FORMAT.TRACE_ID_KEY: self.serialized_uber_trace_id}
        ctx = FORMAT.extract(carrier_getter, old_carrier)
        span_context = trace_api.get_current_span(ctx).get_span_context()
        self.assertEqual(span_context.trace_id, self.trace_id)
        self.assertEqual(span_context.span_id, self.span_id)

    def test_trace_id(self):
        old_carrier = {FORMAT.TRACE_ID_KEY: self.serialized_uber_trace_id}
        _, new_carrier = get_context_new_carrier(old_carrier)
        self.assertEqual(
            self.serialized_uber_trace_id.split(":")[0],
            new_carrier[FORMAT.TRACE_ID_KEY].split(":")[0],
        )

    def test_parent_span_id(self):
        old_carrier = {FORMAT.TRACE_ID_KEY: self.serialized_uber_trace_id}
        _, new_carrier = get_context_new_carrier(old_carrier)
        span_id = self.serialized_uber_trace_id.split(":")[1]
        parent_span_id = new_carrier[FORMAT.TRACE_ID_KEY].split(":")[2]
        self.assertEqual(span_id, parent_span_id)

    def test_sampled_flag(self):
        old_carrier = {FORMAT.TRACE_ID_KEY: self.serialized_uber_trace_id}
        _, new_carrier = get_context_new_carrier(old_carrier)
        sample_flag_value = (
            int(new_carrier[FORMAT.TRACE_ID_KEY].split(":")[3]) & 0x01
        )
        self.assertEqual(1, sample_flag_value)

    def test_baggage(self):
        old_carrier = {FORMAT.TRACE_ID_KEY: self.serialized_uber_trace_id}
        input_baggage = {"key1": "value1"}
        _, new_carrier = get_context_new_carrier(old_carrier, input_baggage)
        ctx = FORMAT.extract(carrier_getter, new_carrier)
        self.assertDictEqual(input_baggage, ctx["baggage"])

    def test_non_string_baggage(self):
        old_carrier = {FORMAT.TRACE_ID_KEY: self.serialized_uber_trace_id}
        input_baggage = {"key1": 1, "key2": True}
        formatted_baggage = {"key1": "1", "key2": "True"}
        _, new_carrier = get_context_new_carrier(old_carrier, input_baggage)
        ctx = FORMAT.extract(carrier_getter, new_carrier)
        self.assertDictEqual(formatted_baggage, ctx["baggage"])

    def test_extract_invalid_uber_trace_id(self):
        old_carrier = {
            "uber-trace-id": "000000000000000000000000deadbeef:00000000deadbef0:00",
            "uberctx-key1": "value1",
        }
        formatted_baggage = {"key1": "value1"}
        context = FORMAT.extract(carrier_getter, old_carrier)
        span_context = trace_api.get_current_span(context).get_span_context()
        self.assertEqual(span_context.span_id, trace_api.INVALID_SPAN_ID)
        self.assertDictEqual(formatted_baggage, context["baggage"])

    def test_extract_invalid_trace_id(self):
        old_carrier = {
            "uber-trace-id": "00000000000000000000000000000000:00000000deadbef0:00:00",
            "uberctx-key1": "value1",
        }
        formatted_baggage = {"key1": "value1"}
        context = FORMAT.extract(carrier_getter, old_carrier)
        span_context = trace_api.get_current_span(context).get_span_context()
        self.assertEqual(span_context.trace_id, trace_api.INVALID_TRACE_ID)
        self.assertDictEqual(formatted_baggage, context["baggage"])

    def test_extract_invalid_span_id(self):
        old_carrier = {
            "uber-trace-id": "000000000000000000000000deadbeef:0000000000000000:00:00",
            "uberctx-key1": "value1",
        }
        formatted_baggage = {"key1": "value1"}
        context = FORMAT.extract(carrier_getter, old_carrier)
        span_context = trace_api.get_current_span(context).get_span_context()
        self.assertEqual(span_context.span_id, trace_api.INVALID_SPAN_ID)
        self.assertDictEqual(formatted_baggage, context["baggage"])
