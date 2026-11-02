# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import unittest
from unittest.mock import patch

from opentelemetry._logs import LogRecord
from opentelemetry.trace import (
    NonRecordingSpan,
    SpanContext,
    TraceFlags,
    set_span_in_context,
    use_span,
)

OBSERVED_TIMESTAMP = "OBSERVED_TIMESTAMP"
SPAN_CONTEXT = SpanContext(
    trace_id=0x000000000000000000000000DEADBEEF,
    span_id=0x00000000DEADBEF0,
    is_remote=False,
    trace_flags=TraceFlags(TraceFlags.SAMPLED),
)


class TestLogRecord(unittest.TestCase):
    @patch("opentelemetry._logs._internal.time_ns")
    def test_log_record_observed_timestamp_default(self, time_ns_mock):  # type: ignore
        time_ns_mock.return_value = OBSERVED_TIMESTAMP
        self.assertEqual(LogRecord().observed_timestamp, OBSERVED_TIMESTAMP)

    def test_log_record_exception(self):
        exc = ValueError("boom")
        log_record = LogRecord(exception=exc)
        self.assertIs(log_record.exception, exc)

    def test_log_record_span_context_fields_from_context(self):
        log_record = LogRecord(context=set_span_in_context(NonRecordingSpan(SPAN_CONTEXT)))
        self.assertEqual(log_record.trace_id, SPAN_CONTEXT.trace_id)
        self.assertEqual(log_record.span_id, SPAN_CONTEXT.span_id)
        self.assertEqual(log_record.trace_flags, SPAN_CONTEXT.trace_flags)

    def test_log_record_explicit_span_context_fields(self):
        span_context = SpanContext(
            trace_id=SPAN_CONTEXT.trace_id,
            span_id=SPAN_CONTEXT.span_id,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.DEFAULT),
        )
        with use_span(NonRecordingSpan(span_context)):
            log_record = LogRecord(
                trace_id=1,
                span_id=2,
                trace_flags=TraceFlags(TraceFlags.SAMPLED),
            )
        self.assertEqual(log_record.trace_id, 1)
        self.assertEqual(log_record.span_id, 2)
        self.assertEqual(log_record.trace_flags, TraceFlags(TraceFlags.SAMPLED))
