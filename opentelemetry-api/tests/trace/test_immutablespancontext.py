# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

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
