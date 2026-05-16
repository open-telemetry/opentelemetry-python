# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import io
import json
import unittest
from unittest.mock import Mock

from opentelemetry.exporter.otlp.json.common.trace_encoder import encode_spans
from opentelemetry.exporter.otlp.json.file._internal import _format_line
from opentelemetry.exporter.otlp.json.file.trace_exporter import (
    FileSpanExporter,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    SimpleSpanProcessor,
    SpanExportResult,
)
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

_LOGGER_NAME = "opentelemetry.exporter.otlp.json.file.trace_exporter"


class TestFileSpanExporter(unittest.TestCase):
    def setUp(self):
        self._stream = io.StringIO()
        self._exporter = FileSpanExporter(self._stream)

        self._in_memory = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(self._in_memory))
        self._tracer = provider.get_tracer(__name__)

    def _finished_spans(self):
        return list(self._in_memory.get_finished_spans())

    def _make_span(self, name: str = "test-span"):
        with self._tracer.start_as_current_span(name):
            pass
        return self._finished_spans()

    def test_export_empty_sequence(self):
        result = self._exporter.export([])
        self.assertEqual(result, SpanExportResult.SUCCESS)
        self.assertEqual(self._stream.getvalue(), "")

    def test_export_single_span_returns_success(self):
        result = self._exporter.export(self._make_span())
        self.assertEqual(result, SpanExportResult.SUCCESS)

    def test_export_single_span_writes_one_json_line(self):
        self._exporter.export(self._make_span())
        lines = self._stream.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        json.loads(lines[0])  # must be valid JSON

    def test_export_span_name_in_output(self):
        self._exporter.export(self._make_span("my-span"))
        self.assertIn("my-span", self._stream.getvalue())

    def test_export_multiple_spans_same_resource_writes_one_line(self):
        with self._tracer.start_as_current_span("first"):
            pass
        with self._tracer.start_as_current_span("second"):
            pass
        self._exporter.export(self._finished_spans())
        lines = self._stream.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        data = json.loads(lines[0])
        total_spans = sum(len(ss["spans"]) for ss in data["scopeSpans"])
        self.assertEqual(total_spans, 2)

    def test_stream_flushed_after_export(self):
        mock_stream = Mock()
        exporter = FileSpanExporter(mock_stream)
        exporter.export(self._make_span())
        mock_stream.flush.assert_called_once()

    def test_custom_formatter_called(self):
        formatter = Mock(return_value="formatted\n")
        exporter = FileSpanExporter(self._stream, formatter=formatter)
        exporter.export(self._make_span())
        formatter.assert_called_once()
        self.assertIn("formatted\n", self._stream.getvalue())

    def test_export_after_shutdown_returns_failure(self):
        self._exporter.shutdown()
        result = self._exporter.export(self._make_span())
        self.assertEqual(result, SpanExportResult.FAILURE)

    def test_export_after_shutdown_logs_warning(self):
        self._exporter.shutdown()
        with self.assertLogs(_LOGGER_NAME, level="WARNING"):
            self._exporter.export([])

    def test_export_after_shutdown_writes_nothing(self):
        self._exporter.shutdown()
        self._exporter.export(self._make_span())
        self.assertEqual(self._stream.getvalue(), "")

    def test_shutdown_idempotent_logs_warning(self):
        self._exporter.shutdown()
        with self.assertLogs(_LOGGER_NAME, level="WARNING"):
            self._exporter.shutdown()

    def test_force_flush_returns_true(self):
        self.assertTrue(self._exporter.force_flush())

    def test_force_flush_returns_true_after_export(self):
        self._exporter.export(self._make_span())
        self.assertTrue(self._exporter.force_flush())

    def test_export_stream_error_returns_failure(self):
        mock_stream = Mock()
        mock_stream.writelines.side_effect = OSError("disk full")
        exporter = FileSpanExporter(mock_stream)
        result = exporter.export(self._make_span())
        self.assertEqual(result, SpanExportResult.FAILURE)

    def test_export_stream_error_logs_exception(self):
        mock_stream = Mock()
        mock_stream.writelines.side_effect = OSError("disk full")
        exporter = FileSpanExporter(mock_stream)
        with self.assertLogs(_LOGGER_NAME, level="ERROR"):
            exporter.export(self._make_span())


class TestFileSpanExporterIntegration(unittest.TestCase):
    def setUp(self):
        self._stream = io.StringIO()
        self._file_exporter = FileSpanExporter(self._stream)
        self._in_memory = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(self._file_exporter))
        provider.add_span_processor(SimpleSpanProcessor(self._in_memory))
        self._tracer = provider.get_tracer(__name__)

    def _expected(self) -> str:
        return "".join(
            _format_line(rs.to_dict())
            for span in self._in_memory.get_finished_spans()
            for rs in encode_spans([span]).resource_spans
        )

    def test_single_span_matches_in_memory(self):
        with self._tracer.start_as_current_span("span-a"):
            pass
        self.assertEqual(self._stream.getvalue(), self._expected())

    def test_multiple_spans_match_in_memory(self):
        with self._tracer.start_as_current_span("span-a"):
            pass
        with self._tracer.start_as_current_span("span-b"):
            pass
        self.assertEqual(self._stream.getvalue(), self._expected())
