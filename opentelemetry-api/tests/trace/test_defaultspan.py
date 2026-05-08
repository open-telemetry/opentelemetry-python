# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

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
