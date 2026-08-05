# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0


import asyncio
from unittest import TestCase

from opentelemetry.context import get_current
from opentelemetry.trace import (
    INVALID_SPAN,
    NonRecordingSpan,
    NoOpTracer,
    Span,
    SpanContext,
    SpanKind,
    Tracer,
    _agnosticcontextmanager,
    get_current_span,
    set_span_in_context,
)
from opentelemetry.trace.propagation import tracecontext


class TestTracer(TestCase):
    def setUp(self):
        self.tracer = NoOpTracer()

    def test_start_span(self):
        with self.tracer.start_span("") as span:
            self.assertIsInstance(span, Span)

    def test_start_as_current_span_context_manager(self):
        with self.tracer.start_as_current_span("") as span:
            self.assertIsInstance(span, Span)

    def test_apply_egress_continuation_noop_tracer_preserves_context(self):
        propagator = tracecontext.TraceContextTextMapPropagator()
        span_context = SpanContext(
            trace_id=0x000000000000000000000000DEADBEEF,
            span_id=0x00000000DEADBEF0,
            is_remote=False,
        )
        context = set_span_in_context(NonRecordingSpan(span_context))

        with self.tracer.apply_egress_continuation(
            kind=SpanKind.CLIENT,
            context=context,
            attributes={"server.address": "api.example.com"},
        ) as injection_context:
            carrier: dict[str, str] = {}
            propagator.inject(carrier, context=injection_context)

        self.assertIn("traceparent", carrier)

    def test_apply_egress_continuation_noop_tracer_preserves_suppression(self):
        propagator = tracecontext.TraceContextTextMapPropagator()
        span_context = SpanContext(
            trace_id=0x000000000000000000000000DEADBEEF,
            span_id=0x00000000DEADBEF0,
            is_remote=False,
        )
        context = set_span_in_context(NonRecordingSpan(span_context))
        context = tracecontext.suppress_trace_context_injection(context)

        with self.tracer.apply_egress_continuation(
            kind=SpanKind.CLIENT,
            context=context,
            attributes={"server.address": "api.example.com"},
        ) as injection_context:
            carrier: dict[str, str] = {}
            propagator.inject(carrier, context=injection_context)

        self.assertNotIn("traceparent", carrier)

    def test_start_as_current_span_decorator(self):
        # using a list to track the mock call order
        calls = []

        class MockTracer(Tracer):
            def start_span(self, *args, **kwargs):
                return INVALID_SPAN

            @_agnosticcontextmanager  # pylint: disable=protected-access
            def start_as_current_span(self, *args, **kwargs):  # type: ignore
                calls.append(1)
                yield INVALID_SPAN
                calls.append(9)

            @_agnosticcontextmanager  # pylint: disable=protected-access
            def apply_egress_continuation(self, *args, **kwargs):  # type: ignore
                yield get_current()

        mock_tracer = MockTracer()

        # test 1 : sync function
        @mock_tracer.start_as_current_span("name")
        def function_sync(data: str) -> int:
            calls.append(5)
            return len(data)

        calls = []
        res = function_sync("123")
        self.assertEqual(res, 3)
        self.assertEqual(calls, [1, 5, 9])

        # test 2 : async function
        @mock_tracer.start_as_current_span("name")
        async def function_async(data: str) -> int:
            calls.append(5)
            return len(data)

        calls = []
        res = asyncio.run(function_async("123"))
        self.assertEqual(res, 3)
        self.assertEqual(calls, [1, 5, 9])

    def test_get_current_span(self):
        with self.tracer.start_as_current_span("test") as span:
            get_current_span().set_attribute("test", "test")
            self.assertFalse(span.is_recording())
            self.assertFalse(hasattr("span", "attributes"))
