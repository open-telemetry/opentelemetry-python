from unittest import TestCase

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.sdk.metrics._internal.exemplar import (
    AlwaysOffExemplarFilter,
    AlwaysOnExemplarFilter,
    TraceBasedExemplarFilter,
)
from opentelemetry.trace import TraceFlags
from opentelemetry.trace.span import SpanContext


class TestAlwaysOnExemplarFilter(TestCase):
    def test_should_sample(self):
        filter = AlwaysOnExemplarFilter()
        self.assertTrue(filter.should_sample(10, 0, {}, Context()))


class TestAlwaysOffExemplarFilter(TestCase):
    def test_should_sample(self):
        filter = AlwaysOffExemplarFilter()
        self.assertFalse(filter.should_sample(10, 0, {}, Context()))


class TestTraceBasedExemplarFilter(TestCase):
    TRACE_ID = int("d4cda95b652f4a1592b449d5929fda1b", 16)
    SPAN_ID = int("6e0c63257de34c92", 16)

    def test_should_not_sample_without_trace(self):
        filter = TraceBasedExemplarFilter()
        span_context = SpanContext(
            trace_id=self.TRACE_ID,
            span_id=self.SPAN_ID,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.DEFAULT),
            trace_state={},
        )
        span = trace.NonRecordingSpan(span_context)
        ctx = trace.set_span_in_context(span)
        self.assertFalse(filter.should_sample(10, 0, {}, ctx))

    def test_should_not_sample_with_invalid_span(self):
        filter = TraceBasedExemplarFilter()
        self.assertFalse(filter.should_sample(10, 0, {}, Context()))

    def test_should_sample_when_trace_is_sampled(self):
        filter = TraceBasedExemplarFilter()
        span_context = SpanContext(
            trace_id=self.TRACE_ID,
            span_id=self.SPAN_ID,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
            trace_state={},
        )
        span = trace.NonRecordingSpan(span_context)
        ctx = trace.set_span_in_context(span)
        self.assertTrue(filter.should_sample(10, 0, {}, ctx))
