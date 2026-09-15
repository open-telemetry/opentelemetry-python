# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from unittest.mock import Mock

import opentelemetry.trace as trace_api
from opentelemetry import baggage
from opentelemetry.baggage import _BAGGAGE_KEY
from opentelemetry.context import Context
from opentelemetry.propagators import (  # pylint: disable=no-name-in-module
    jaeger,
)
from opentelemetry.propagators.textmap import DefaultGetter
from opentelemetry.sdk import trace
from opentelemetry.sdk.trace import id_generator
from opentelemetry.test import TestCase

FORMAT = jaeger.JaegerPropagator()


def get_context_new_carrier(old_carrier, carrier_baggage=None):
    ctx = FORMAT.extract(old_carrier)
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

    FORMAT.inject(new_carrier, context=ctx)

    return ctx, new_carrier


class TestJaegerPropagator(TestCase):
    # pylint: disable=too-many-public-methods

    @classmethod
    def setUpClass(cls):
        generator = id_generator.RandomIdGenerator()
        cls.trace_id = generator.generate_trace_id()
        cls.span_id = generator.generate_span_id()
        cls.parent_span_id = generator.generate_span_id()
        cls.serialized_uber_trace_id = jaeger._format_uber_trace_id(  # pylint: disable=protected-access
            cls.trace_id, cls.span_id, cls.parent_span_id, 11
        )

    def test_extract_valid_span(self):
        old_carrier = {FORMAT.TRACE_ID_KEY: self.serialized_uber_trace_id}
        ctx = FORMAT.extract(old_carrier)
        span_context = trace_api.get_current_span(ctx).get_span_context()
        self.assertEqual(span_context.trace_id, self.trace_id)
        self.assertEqual(span_context.span_id, self.span_id)

    def test_missing_carrier(self):
        old_carrier = {}
        ctx = FORMAT.extract(old_carrier)
        span_context = trace_api.get_current_span(ctx).get_span_context()
        self.assertEqual(span_context.trace_id, trace_api.INVALID_TRACE_ID)
        self.assertEqual(span_context.span_id, trace_api.INVALID_SPAN_ID)

    def test_trace_id(self):
        old_carrier = {FORMAT.TRACE_ID_KEY: self.serialized_uber_trace_id}
        _, new_carrier = get_context_new_carrier(old_carrier)
        self.assertEqual(
            self.serialized_uber_trace_id.split(":", maxsplit=1)[0],
            new_carrier[FORMAT.TRACE_ID_KEY].split(":")[0],
        )

    def test_parent_span_id(self):
        old_carrier = {FORMAT.TRACE_ID_KEY: self.serialized_uber_trace_id}
        _, new_carrier = get_context_new_carrier(old_carrier)
        span_id = self.serialized_uber_trace_id.split(":")[1]
        parent_span_id = new_carrier[FORMAT.TRACE_ID_KEY].split(":")[2]
        self.assertEqual(span_id, parent_span_id)

    def test_sampled_flag_set(self):
        old_carrier = {FORMAT.TRACE_ID_KEY: self.serialized_uber_trace_id}
        _, new_carrier = get_context_new_carrier(old_carrier)
        sample_flag_value = int(new_carrier[FORMAT.TRACE_ID_KEY].split(":")[3]) & 0x01
        self.assertEqual(1, sample_flag_value)

    def test_debug_flag_set(self):
        old_carrier = {FORMAT.TRACE_ID_KEY: self.serialized_uber_trace_id}
        _, new_carrier = get_context_new_carrier(old_carrier)
        debug_flag_value = int(new_carrier[FORMAT.TRACE_ID_KEY].split(":")[3]) & FORMAT.DEBUG_FLAG
        self.assertEqual(FORMAT.DEBUG_FLAG, debug_flag_value)

    def test_sample_debug_flags_unset(self):
        uber_trace_id = jaeger._format_uber_trace_id(  # pylint: disable=protected-access
            self.trace_id, self.span_id, self.parent_span_id, 0
        )
        old_carrier = {FORMAT.TRACE_ID_KEY: uber_trace_id}
        _, new_carrier = get_context_new_carrier(old_carrier)
        flags = int(new_carrier[FORMAT.TRACE_ID_KEY].split(":")[3])
        sample_flag_value = flags & 0x01
        debug_flag_value = flags & FORMAT.DEBUG_FLAG
        self.assertEqual(0, sample_flag_value)
        self.assertEqual(0, debug_flag_value)

    def test_baggage(self):
        old_carrier = {FORMAT.TRACE_ID_KEY: self.serialized_uber_trace_id}
        input_baggage = {"key1": "value1"}
        _, new_carrier = get_context_new_carrier(old_carrier, input_baggage)
        ctx = FORMAT.extract(new_carrier)
        self.assertDictEqual(input_baggage, ctx[_BAGGAGE_KEY])

    def test_non_string_baggage(self):
        old_carrier = {FORMAT.TRACE_ID_KEY: self.serialized_uber_trace_id}
        input_baggage = {"key1": 1, "key2": True}
        formatted_baggage = {"key1": "1", "key2": "True"}
        _, new_carrier = get_context_new_carrier(old_carrier, input_baggage)
        ctx = FORMAT.extract(new_carrier)
        self.assertDictEqual(formatted_baggage, ctx[_BAGGAGE_KEY])

    def test_extract_empty_baggage_value(self):
        old_carrier = {
            FORMAT.TRACE_ID_KEY: self.serialized_uber_trace_id,
            "uberctx-key1": [],
            "uberctx-key2": None,
            "uberctx-key3": "value3",
        }
        context = FORMAT.extract(old_carrier)
        self.assertDictEqual({"key3": "value3"}, context[_BAGGAGE_KEY])

    def test_extract_enforces_max_baggage_entries(self):
        old_carrier = {FORMAT.TRACE_ID_KEY: self.serialized_uber_trace_id}
        for index in range(200):
            old_carrier[f"uberctx-k{index}"] = f"v{index}"
        extracted = FORMAT.extract(old_carrier)[_BAGGAGE_KEY]
        self.assertEqual(FORMAT.MAX_BAGGAGE_ENTRIES, len(extracted))
        self.assertIn("k0", extracted)
        self.assertNotIn("k180", extracted)

    def test_extract_drops_oversized_baggage_entry(self):
        old_carrier = {
            FORMAT.TRACE_ID_KEY: self.serialized_uber_trace_id,
            "uberctx-ok": "value",
            "uberctx-big": "x" * 5000,
        }
        context = FORMAT.extract(old_carrier)
        self.assertDictEqual({"ok": "value"}, context[_BAGGAGE_KEY])

    def test_extract_measures_entry_limit_in_bytes(self):
        # 2100 multibyte characters is 4200 bytes: under the character limit,
        # over the byte limit, so the entry must be dropped.
        old_carrier = {
            FORMAT.TRACE_ID_KEY: self.serialized_uber_trace_id,
            "uberctx-ok": "value",
            "uberctx-u": "é" * 2100,
        }
        context = FORMAT.extract(old_carrier)
        self.assertDictEqual({"ok": "value"}, context[_BAGGAGE_KEY])

    def test_extract_enforces_max_baggage_total_bytes(self):
        old_carrier = {FORMAT.TRACE_ID_KEY: self.serialized_uber_trace_id}
        for index in range(100):
            old_carrier[f"uberctx-k{index}"] = "y" * 200
        extracted = FORMAT.extract(old_carrier)[_BAGGAGE_KEY]
        self.assertLess(len(extracted), 100)
        self.assertIn("k0", extracted)
        self.assertNotIn("k99", extracted)

    def test_extract_counts_the_key_value_separator_byte(self):
        old_carrier = {
            FORMAT.TRACE_ID_KEY: self.serialized_uber_trace_id,
            "uberctx-fits": "x" * (FORMAT.MAX_BAGGAGE_ENTRY_BYTES - len("fits") - 1),
            "uberctx-over": "x" * (FORMAT.MAX_BAGGAGE_ENTRY_BYTES - len("over")),
        }
        extracted = FORMAT.extract(old_carrier)[_BAGGAGE_KEY]
        self.assertIn("fits", extracted)
        self.assertNotIn("over", extracted)

    def test_extract_charges_a_separator_byte_between_accepted_entries(self):
        small_entry_bytes = len("small") + 1  # empty value
        filler_a_entry_bytes = FORMAT.MAX_BAGGAGE_ENTRY_BYTES
        filler_a_value_len = filler_a_entry_bytes - len("filler_a") - 1
        target_total_after_fillers = FORMAT.MAX_BAGGAGE_TOTAL_BYTES - small_entry_bytes
        filler_b_entry_bytes = target_total_after_fillers - filler_a_entry_bytes - 1
        filler_b_value_len = filler_b_entry_bytes - len("filler_b") - 1
        old_carrier = {
            FORMAT.TRACE_ID_KEY: self.serialized_uber_trace_id,
            "uberctx-filler_a": "x" * filler_a_value_len,
            "uberctx-filler_b": "x" * filler_b_value_len,
            "uberctx-small": "",
        }
        extracted = FORMAT.extract(old_carrier)[_BAGGAGE_KEY]
        self.assertIn("filler_a", extracted)
        self.assertIn("filler_b", extracted)
        self.assertNotIn("small", extracted)

    def test_extract_stops_inspecting_after_the_candidate_limit(self):
        old_carrier = {FORMAT.TRACE_ID_KEY: self.serialized_uber_trace_id}
        for index in range(1000):
            old_carrier[f"uberctx-k{index}"] = "x" * 5000

        class CountingGetter(DefaultGetter):
            def __init__(self):
                self.reads = 0

            def get(self, carrier, key):
                self.reads += 1
                return super().get(carrier, key)

        getter = CountingGetter()
        FORMAT.extract(old_carrier, getter=getter)
        self.assertLessEqual(getter.reads, FORMAT.MAX_BAGGAGE_ENTRIES + 1)

    def test_inject_enforces_max_baggage_entries(self):
        span = trace_api.NonRecordingSpan(trace_api.SpanContext(1, 1, True))
        ctx = trace_api.set_span_in_context(span)
        for index in range(200):
            ctx = baggage.set_baggage(f"k{index}", f"v{index}", ctx)

        carrier = {}
        FORMAT.inject(carrier, context=ctx)

        self.assertEqual(FORMAT.MAX_BAGGAGE_ENTRIES, sum(1 for key in carrier if key.startswith(FORMAT.BAGGAGE_PREFIX)))
        self.assertIn(FORMAT.BAGGAGE_PREFIX + "k0", carrier)
        self.assertNotIn(FORMAT.BAGGAGE_PREFIX + "k180", carrier)

    def test_inject_enforces_max_baggage_total_bytes(self):
        span = trace_api.NonRecordingSpan(trace_api.SpanContext(1, 1, True))
        ctx = trace_api.set_span_in_context(span)
        for index in range(100):
            ctx = baggage.set_baggage(f"k{index}", "y" * 200, ctx)

        carrier = {}
        FORMAT.inject(carrier, context=ctx)

        injected = [key for key in carrier if key.startswith(FORMAT.BAGGAGE_PREFIX)]
        self.assertLess(len(injected), 100)
        self.assertIn(FORMAT.BAGGAGE_PREFIX + "k0", carrier)
        self.assertNotIn(FORMAT.BAGGAGE_PREFIX + "k99", carrier)

    def test_extract_invalid_uber_trace_id(self):
        old_carrier = {
            "uber-trace-id": "000000000000000000000000deadbeef:00000000deadbef0:00",
            "uberctx-key1": "value1",
        }
        formatted_baggage = {"key1": "value1"}
        context = FORMAT.extract(old_carrier)
        span_context = trace_api.get_current_span(context).get_span_context()
        self.assertEqual(span_context.span_id, trace_api.INVALID_SPAN_ID)
        self.assertDictEqual(formatted_baggage, context[_BAGGAGE_KEY])

    def test_extract_invalid_trace_id(self):
        old_carrier = {
            "uber-trace-id": "00000000000000000000000000000000:00000000deadbef0:00:00",
            "uberctx-key1": "value1",
        }
        formatted_baggage = {"key1": "value1"}
        context = FORMAT.extract(old_carrier)
        span_context = trace_api.get_current_span(context).get_span_context()
        self.assertEqual(span_context.trace_id, trace_api.INVALID_TRACE_ID)
        self.assertDictEqual(formatted_baggage, context[_BAGGAGE_KEY])

    def test_extract_invalid_span_id(self):
        old_carrier = {
            "uber-trace-id": "000000000000000000000000deadbeef:0000000000000000:00:00",
            "uberctx-key1": "value1",
        }
        formatted_baggage = {"key1": "value1"}
        context = FORMAT.extract(old_carrier)
        span_context = trace_api.get_current_span(context).get_span_context()
        self.assertEqual(span_context.span_id, trace_api.INVALID_SPAN_ID)
        self.assertDictEqual(formatted_baggage, context[_BAGGAGE_KEY])

    def test_fields(self):
        tracer = trace.TracerProvider().get_tracer("sdk_tracer_provider")
        mock_setter = Mock()
        with tracer.start_as_current_span("parent"):
            with tracer.start_as_current_span("child"):
                FORMAT.inject({}, setter=mock_setter)
        inject_fields = set()
        for call in mock_setter.mock_calls:
            inject_fields.add(call[1][1])
        self.assertEqual(FORMAT.fields, inject_fields)

    def test_extract_no_trace_id_to_explicit_ctx(self):
        carrier = {}
        orig_ctx = Context({"k1": "v1"})

        ctx = FORMAT.extract(carrier, orig_ctx)
        self.assertDictEqual(orig_ctx, ctx)

    def test_extract_no_trace_id_to_implicit_ctx(self):
        carrier = {}

        ctx = FORMAT.extract(carrier)
        self.assertDictEqual(Context(), ctx)

    def test_extract_invalid_uber_trace_id_header_to_explicit_ctx(self):
        trace_id_headers = [
            "000000000000000000000000deadbeef:00000000deadbef0:00",
            "00000000000000000000000000000000:00000000deadbef0:00:00",
            "000000000000000000000000deadbeef:0000000000000000:00:00",
            "000000000000000000000000deadbeef:0000000000000000:00:xyz",
        ]
        for trace_id_header in trace_id_headers:
            with self.subTest(trace_id_header=trace_id_header):
                carrier = {"uber-trace-id": trace_id_header}
                orig_ctx = Context({"k1": "v1"})

                ctx = FORMAT.extract(carrier, orig_ctx)
                self.assertDictEqual(orig_ctx, ctx)

    def test_extract_invalid_uber_trace_id_header_to_implicit_ctx(self):
        trace_id_headers = [
            "000000000000000000000000deadbeef:00000000deadbef0:00",
            "00000000000000000000000000000000:00000000deadbef0:00:00",
            "000000000000000000000000deadbeef:0000000000000000:00:00",
            "000000000000000000000000deadbeef:0000000000000000:00:xyz",
        ]
        for trace_id_header in trace_id_headers:
            with self.subTest(trace_id_header=trace_id_header):
                carrier = {"uber-trace-id": trace_id_header}

                ctx = FORMAT.extract(carrier)
                self.assertDictEqual(Context(), ctx)

    def test_non_recording_span_does_not_crash(self):
        """Make sure propagator does not crash when working with NonRecordingSpan"""
        mock_setter = Mock()
        span = trace_api.NonRecordingSpan(trace_api.SpanContext(1, 1, True))
        with trace_api.use_span(span, end_on_exit=True):
            with self.assertNotRaises(Exception):
                FORMAT.inject({}, setter=mock_setter)
