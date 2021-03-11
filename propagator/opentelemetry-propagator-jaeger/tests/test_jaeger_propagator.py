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

from unittest import TestCase

import opentelemetry.sdk.trace as trace
import opentelemetry.sdk.trace.id_generator as id_generator
import opentelemetry.trace as trace_api
from opentelemetry import baggage
from opentelemetry.propagators.jaeger import (  # pylint: disable=no-name-in-module
    JaegerPropagator,
    _format_uber_trace_id,
)

format_ = JaegerPropagator()


def get_context_new_carrier(old_carrier, carrier_baggage=None):

    ctx = format_.extract(old_carrier)
    if carrier_baggage:
        for key, value in carrier_baggage.items():
            ctx = baggage.set_baggage(key, value, ctx)
    parent_span_context = trace_api.get_current_span(ctx).get_span_context()

    parent = trace._Span("parent", parent_span_context)
    child = trace._Span(
        "child",
        trace_api.SpanContext(
            parent_span_context.trace_id,
            id_generator.RandomIdGenerator().generate_span_id(),
            is_remote=False,
            trace_flags=parent_span_context.trace_flags,
            trace_state=parent_span_context.trace_state,
        ),
        parent=parent.get_span_context(),
    )

    new_carrier = {}
    ctx = trace_api.set_span_in_context(child, ctx)

    format_.inject(new_carrier, context=ctx)

    return ctx, new_carrier


class TestJaegerPropagator(TestCase):
    # pylint: disable=protected-access
    @classmethod
    def setUpClass(cls):
        generator = id_generator.RandomIdGenerator()
        cls.trace_id = generator.generate_trace_id()
        cls.span_id = generator.generate_span_id()
        cls.parent_span_id = generator.generate_span_id()
        cls.serialized_uber_trace_id = _format_uber_trace_id(
            cls.trace_id, cls.span_id, cls.parent_span_id, 11
        )

    def test_extract_valid_span(self):
        old_carrier = {format_._trace_id_key: self.serialized_uber_trace_id}
        ctx = format_.extract(old_carrier)
        span_context = trace_api.get_current_span(ctx).get_span_context()
        self.assertEqual(span_context.trace_id, self.trace_id)
        self.assertEqual(span_context.span_id, self.span_id)

    def test_missing_carrier(self):
        old_carrier = {}
        ctx = format_.extract(old_carrier)
        span_context = trace_api.get_current_span(ctx).get_span_context()
        self.assertEqual(span_context.trace_id, trace_api.INVALID_TRACE_ID)
        self.assertEqual(span_context.span_id, trace_api.INVALID_SPAN_ID)

    def test_trace_id(self):
        old_carrier = {format_._trace_id_key: self.serialized_uber_trace_id}
        _, new_carrier = get_context_new_carrier(old_carrier)
        self.assertEqual(
            self.serialized_uber_trace_id.split(":")[0],
            new_carrier[format_._trace_id_key].split(":")[0],
        )

    def test_parent_span_id(self):
        old_carrier = {format_._trace_id_key: self.serialized_uber_trace_id}
        _, new_carrier = get_context_new_carrier(old_carrier)
        span_id = self.serialized_uber_trace_id.split(":")[1]
        parent_span_id = new_carrier[format_._trace_id_key].split(":")[2]
        self.assertEqual(span_id, parent_span_id)

    def test_sampled_flag_set(self):
        old_carrier = {format_._trace_id_key: self.serialized_uber_trace_id}
        _, new_carrier = get_context_new_carrier(old_carrier)
        sample_flag_value = (
            int(new_carrier[format_._trace_id_key].split(":")[3]) & 0x01
        )
        self.assertEqual(1, sample_flag_value)

    def test_debug_flag_set(self):
        old_carrier = {format_._trace_id_key: self.serialized_uber_trace_id}
        _, new_carrier = get_context_new_carrier(old_carrier)
        debug_flag_value = (
            int(new_carrier[format_._trace_id_key].split(":")[3])
            & format_._debug_flag
        )
        self.assertEqual(format_._debug_flag, debug_flag_value)

    def test_sample_debug_flags_unset(self):
        uber_trace_id = _format_uber_trace_id(
            self.trace_id, self.span_id, self.parent_span_id, 0
        )
        old_carrier = {format_._trace_id_key: uber_trace_id}
        _, new_carrier = get_context_new_carrier(old_carrier)
        flags = int(new_carrier[format_._trace_id_key].split(":")[3])
        sample_flag_value = flags & 0x01
        debug_flag_value = flags & format_._debug_flag
        self.assertEqual(0, sample_flag_value)
        self.assertEqual(0, debug_flag_value)

    def test_baggage(self):
        old_carrier = {format_._trace_id_key: self.serialized_uber_trace_id}
        input_baggage = {"key1": "value1"}
        _, new_carrier = get_context_new_carrier(old_carrier, input_baggage)
        ctx = format_.extract(new_carrier)
        self.assertDictEqual(input_baggage, ctx["baggage"])

    def test_non_string_baggage(self):
        old_carrier = {format_._trace_id_key: self.serialized_uber_trace_id}
        input_baggage = {"key1": 1, "key2": True}
        formatted_baggage = {"key1": "1", "key2": "True"}
        _, new_carrier = get_context_new_carrier(old_carrier, input_baggage)
        ctx = format_.extract(new_carrier)
        self.assertDictEqual(formatted_baggage, ctx["baggage"])

    def test_extract_invalid_uber_trace_id(self):
        old_carrier = {
            "uber-trace-id": "000000000000000000000000deadbeef:00000000deadbef0:00",
            "uberctx-key1": "value1",
        }
        formatted_baggage = {"key1": "value1"}
        context = format_.extract(old_carrier)
        span_context = trace_api.get_current_span(context).get_span_context()
        self.assertEqual(span_context.span_id, trace_api.INVALID_SPAN_ID)
        self.assertDictEqual(formatted_baggage, context["baggage"])

    def test_extract_invalid_trace_id(self):
        old_carrier = {
            "uber-trace-id": "00000000000000000000000000000000:00000000deadbef0:00:00",
            "uberctx-key1": "value1",
        }
        formatted_baggage = {"key1": "value1"}
        context = format_.extract(old_carrier)
        span_context = trace_api.get_current_span(context).get_span_context()
        self.assertEqual(span_context.trace_id, trace_api.INVALID_TRACE_ID)
        self.assertDictEqual(formatted_baggage, context["baggage"])

    def test_extract_invalid_span_id(self):
        old_carrier = {
            "uber-trace-id": "000000000000000000000000deadbeef:0000000000000000:00:00",
            "uberctx-key1": "value1",
        }
        formatted_baggage = {"key1": "value1"}
        context = format_.extract(old_carrier)
        span_context = trace_api.get_current_span(context).get_span_context()
        self.assertEqual(span_context.span_id, trace_api.INVALID_SPAN_ID)
        self.assertDictEqual(formatted_baggage, context["baggage"])

    def test_fields(self):
        tracer = trace.TracerProvider().get_tracer("sdk_tracer_provider")

        carrier = {}

        with tracer.start_as_current_span("parent"):
            with tracer.start_as_current_span("child"):
                format_.inject(carrier)

        self.assertEqual(format_.fields, carrier.keys())
