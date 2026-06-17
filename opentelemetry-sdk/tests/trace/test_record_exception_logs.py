# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Tests for OTEL_SEMCONV_EXCEPTION_SIGNAL_OPT_IN handling in record_exception."""

import os
import unittest
from unittest import mock

from opentelemetry._logs import SeverityNumber
from opentelemetry.sdk.trace import (
    _OTEL_SEMCONV_EXCEPTION_SIGNAL_OPT_IN as OTEL_SEMCONV_EXCEPTION_SIGNAL_OPT_IN,
)
from opentelemetry.sdk.trace import (
    TracerProvider,
)
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)


class _CapturingLogger:
    """A minimal Logger that records emitted LogRecords."""

    def __init__(self):
        self.records = []

    def emit(self, record):
        self.records.append(record)


class TestRecordExceptionSignalOptIn(unittest.TestCase):
    def setUp(self):
        self.span_exporter = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(self.span_exporter))
        self.tracer = provider.get_tracer("test-scope", "1.0")
        self.logger = _CapturingLogger()
        patcher = mock.patch(
            "opentelemetry.sdk.trace._logs.get_logger",
            return_value=self.logger,
        )
        self.mock_get_logger = patcher.start()
        self.addCleanup(patcher.stop)

    def _raise_in_span(self):
        with self.assertRaises(ValueError):
            with self.tracer.start_as_current_span("op"):
                raise ValueError("boom")

    def _exception_events(self):
        finished_span = self.span_exporter.get_finished_spans()[0]
        return [e for e in finished_span.events if e.name == "exception"]

    def test_unset_records_span_event_only(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self._raise_in_span()
        self.assertEqual(len(self._exception_events()), 1)
        self.assertEqual(self.logger.records, [])

    def test_unrecognized_value_records_span_event_only(self):
        with mock.patch.dict(
            os.environ, {OTEL_SEMCONV_EXCEPTION_SIGNAL_OPT_IN: "bogus"}
        ):
            self._raise_in_span()
        self.assertEqual(len(self._exception_events()), 1)
        self.assertEqual(self.logger.records, [])

    def test_logs_records_log_only(self):
        with mock.patch.dict(
            os.environ, {OTEL_SEMCONV_EXCEPTION_SIGNAL_OPT_IN: "logs"}
        ):
            self._raise_in_span()
        self.assertEqual(self._exception_events(), [])
        self.assertEqual(len(self.logger.records), 1)
        record = self.logger.records[0]
        self.assertEqual(record.event_name, "exception")
        self.assertEqual(record.severity_number, SeverityNumber.ERROR)
        self.assertEqual(record.attributes["exception.type"], "ValueError")
        self.assertEqual(record.attributes["exception.message"], "boom")
        self.assertIn(
            "ValueError: boom", record.attributes["exception.stacktrace"]
        )
        # The deprecated exception.escaped attribute is not set on logs.
        self.assertNotIn("exception.escaped", record.attributes)

    def test_logs_dup_records_both(self):
        with mock.patch.dict(
            os.environ, {OTEL_SEMCONV_EXCEPTION_SIGNAL_OPT_IN: "logs/dup"}
        ):
            self._raise_in_span()
        self.assertEqual(len(self._exception_events()), 1)
        self.assertEqual(len(self.logger.records), 1)

    def test_log_is_correlated_with_span(self):
        with mock.patch.dict(
            os.environ, {OTEL_SEMCONV_EXCEPTION_SIGNAL_OPT_IN: "logs"}
        ):
            self._raise_in_span()
        finished_span = self.span_exporter.get_finished_spans()[0]
        record = self.logger.records[0]
        self.assertEqual(record.trace_id, finished_span.context.trace_id)
        self.assertEqual(record.span_id, finished_span.context.span_id)

    def test_logs_uses_instrumentation_scope_for_logger(self):
        with mock.patch.dict(
            os.environ, {OTEL_SEMCONV_EXCEPTION_SIGNAL_OPT_IN: "logs"}
        ):
            self._raise_in_span()
        # The logger is obtained using the span's instrumentation scope.
        args, _ = self.mock_get_logger.call_args
        self.assertEqual(args[0], "test-scope")

    def test_directly_recorded_exception_is_logged(self):
        with mock.patch.dict(
            os.environ, {OTEL_SEMCONV_EXCEPTION_SIGNAL_OPT_IN: "logs"}
        ):
            with self.tracer.start_as_current_span("op") as span:
                try:
                    raise ValueError("handled")
                except ValueError as err:
                    span.record_exception(err)
        record = self.logger.records[0]
        self.assertEqual(record.event_name, "exception")
        self.assertEqual(record.severity_number, SeverityNumber.ERROR)
        self.assertEqual(record.attributes["exception.type"], "ValueError")

    def test_extra_attributes_forwarded_to_log(self):
        with mock.patch.dict(
            os.environ, {OTEL_SEMCONV_EXCEPTION_SIGNAL_OPT_IN: "logs"}
        ):
            with self.tracer.start_as_current_span("op") as span:
                span.record_exception(
                    ValueError("boom"), attributes={"custom.key": "v"}
                )
        record = self.logger.records[0]
        self.assertEqual(record.attributes["custom.key"], "v")
