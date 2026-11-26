# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import unittest
from collections.abc import Callable
from typing import cast
from unittest.mock import patch

from opentelemetry.logs import LogRecord
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
    @patch("opentelemetry.logs._internal.time_ns")
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

    def test_log_record_span_context_fields_from_current_span(self):
        with use_span(NonRecordingSpan(SPAN_CONTEXT)):
            log_record = LogRecord()
        self.assertEqual(log_record.trace_id, SPAN_CONTEXT.trace_id)
        self.assertEqual(log_record.span_id, SPAN_CONTEXT.span_id)
        self.assertEqual(log_record.trace_flags, SPAN_CONTEXT.trace_flags)

    def test_log_record_rejects_deprecated_span_context_fields(self):
        constructor = cast(Callable[..., LogRecord], LogRecord)
        for name in ("trace_id", "span_id", "trace_flags"):
            with self.subTest(parameter=name), self.assertRaisesRegex(TypeError, name):
                constructor(**{name: getattr(SPAN_CONTEXT, name)})
