# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import io
import json
import logging
import unittest
from unittest.mock import Mock, patch

import opentelemetry.exporter.otlp.json.file._log_exporter as _log_exporter_mod
from opentelemetry._logs import LogRecord, SeverityNumber
from opentelemetry.exporter.otlp.json.common._log_encoder import encode_logs
from opentelemetry.exporter.otlp.json.file._internal import _format_line
from opentelemetry.exporter.otlp.json.file._log_exporter import (
    FileLogExporter,
)
from opentelemetry.sdk._logs import (
    LoggerProvider,
    LoggingHandler,
    ReadableLogRecord,
)
from opentelemetry.sdk._logs.export import (
    InMemoryLogRecordExporter,
    LogRecordExportResult,
    SimpleLogRecordProcessor,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope


def _make_log_record(
    body: str = "test log message",
    resource_attrs: dict | None = None,
) -> ReadableLogRecord:
    return ReadableLogRecord(
        LogRecord(
            body=body,
            severity_text="INFO",
            severity_number=SeverityNumber.INFO,
        ),
        resource=Resource(resource_attrs or {"service.name": "test"}),
        instrumentation_scope=InstrumentationScope("test-scope", "1.0"),
    )


class TestFileLogExporter(unittest.TestCase):
    def setUp(self):
        self._stream = io.StringIO()
        self._exporter = FileLogExporter(self._stream)

    def test_export_empty_sequence(self):
        result = self._exporter.export([])
        self.assertEqual(result, LogRecordExportResult.SUCCESS)
        self.assertEqual(self._stream.getvalue(), "")

    def test_export_single_log_returns_success(self):
        result = self._exporter.export([_make_log_record()])
        self.assertEqual(result, LogRecordExportResult.SUCCESS)

    def test_export_single_log_writes_one_json_line(self):
        self._exporter.export([_make_log_record()])
        lines = self._stream.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        json.loads(lines[0])  # must be valid JSON

    def test_export_log_body_in_output(self):
        self._exporter.export([_make_log_record("hello from test")])
        self.assertIn("hello from test", self._stream.getvalue())

    def test_export_multiple_logs_same_resource_writes_one_line(self):
        logs = [
            _make_log_record("first"),
            _make_log_record("second"),
        ]
        self._exporter.export(logs)
        lines = self._stream.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        data = json.loads(lines[0])
        total_logs = sum(len(sl["logRecords"]) for sl in data["scopeLogs"])
        self.assertEqual(total_logs, 2)

    def test_export_logs_different_resources_writes_multiple_lines(self):
        logs = [
            _make_log_record("from-a", resource_attrs={"host": "a"}),
            _make_log_record("from-b", resource_attrs={"host": "b"}),
        ]
        self._exporter.export(logs)
        lines = self._stream.getvalue().splitlines()
        self.assertEqual(len(lines), 2)

    def test_stream_flushed_after_export(self):
        mock_stream = Mock()
        exporter = FileLogExporter(mock_stream)
        exporter.export([_make_log_record()])
        mock_stream.flush.assert_called_once()

    def test_custom_formatter_called(self):
        formatter = Mock(return_value="formatted\n")
        exporter = FileLogExporter(self._stream, formatter=formatter)
        exporter.export([_make_log_record()])
        formatter.assert_called_once()
        self.assertIn("formatted\n", self._stream.getvalue())

    def test_export_after_shutdown_returns_failure(self):
        self._exporter.shutdown()
        result = self._exporter.export([_make_log_record()])
        self.assertEqual(result, LogRecordExportResult.FAILURE)

    def test_export_after_shutdown_logs_warning(self):
        self._exporter.shutdown()
        with patch.object(_log_exporter_mod._logger, "warning") as mock_warn:
            self._exporter.export([])
        mock_warn.assert_called_once()

    def test_export_after_shutdown_writes_nothing(self):
        self._exporter.shutdown()
        self._exporter.export([_make_log_record()])
        self.assertEqual(self._stream.getvalue(), "")

    def test_shutdown_idempotent_logs_warning(self):
        self._exporter.shutdown()
        with patch.object(_log_exporter_mod._logger, "warning") as mock_warn:
            self._exporter.shutdown()
        mock_warn.assert_called_once()

    def test_force_flush_returns_true(self):
        self.assertTrue(self._exporter.force_flush())

    def test_export_stream_error_returns_failure(self):
        mock_stream = Mock()
        mock_stream.writelines.side_effect = OSError("disk full")
        exporter = FileLogExporter(mock_stream)
        result = exporter.export([_make_log_record()])
        self.assertEqual(result, LogRecordExportResult.FAILURE)

    def test_export_stream_error_logs_exception(self):
        mock_stream = Mock()
        mock_stream.writelines.side_effect = OSError("disk full")
        exporter = FileLogExporter(mock_stream)
        with patch.object(_log_exporter_mod._logger, "exception") as mock_exc:
            exporter.export([_make_log_record()])
        mock_exc.assert_called_once()


class TestFileLogExporterIntegration(unittest.TestCase):
    def setUp(self):
        self._stream = io.StringIO()
        self._file_exporter = FileLogExporter(self._stream)
        self._in_memory = InMemoryLogRecordExporter()
        provider = LoggerProvider()
        provider.add_log_record_processor(
            SimpleLogRecordProcessor(self._file_exporter)
        )
        provider.add_log_record_processor(
            SimpleLogRecordProcessor(self._in_memory)
        )
        handler = LoggingHandler(logger_provider=provider)
        self._logger = logging.getLogger("test.file.log.exporter.integration")
        self._logger.addHandler(handler)
        self._logger.setLevel(logging.DEBUG)

    def tearDown(self):
        for h in self._logger.handlers[:]:
            self._logger.removeHandler(h)

    def _expected(self) -> str:
        return "".join(
            _format_line(rl.to_dict())
            for record in self._in_memory.get_finished_logs()
            for rl in encode_logs([record]).resource_logs
        )

    def test_single_log_matches_in_memory(self):
        self._logger.info("hello from integration")
        self.assertEqual(self._stream.getvalue(), self._expected())

    def test_multiple_logs_match_in_memory(self):
        self._logger.info("first message")
        self._logger.warning("second message")
        self.assertEqual(self._stream.getvalue(), self._expected())
