# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import io
import json
import logging
import unittest
from unittest.mock import Mock

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

_LOGGER_NAME = "opentelemetry.exporter.otlp.json.file._log_exporter"


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

    def test_export_single_log(self):
        result = self._exporter.export([_make_log_record("hello from test")])
        self.assertEqual(result, LogRecordExportResult.SUCCESS)
        lines = self._stream.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        json.loads(lines[0])
        self.assertIn("hello from test", self._stream.getvalue())

    def test_export_multiple_logs_same_resource(self):
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

    def test_export_logs_different_resources(self):
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

    def test_custom_formatter(self):
        formatter = Mock(return_value="formatted\n")
        exporter = FileLogExporter(self._stream, formatter=formatter)
        exporter.export([_make_log_record()])
        formatter.assert_called_once()
        self.assertIn("formatted\n", self._stream.getvalue())

    def test_export_after_shutdown(self):
        self._exporter.shutdown()
        with self.assertLogs(_LOGGER_NAME, level="WARNING"):
            result = self._exporter.export([_make_log_record()])
        self.assertEqual(result, LogRecordExportResult.FAILURE)
        self.assertEqual(self._stream.getvalue(), "")

    def test_shutdown_idempotent(self):
        self._exporter.shutdown()
        with self.assertLogs(_LOGGER_NAME, level="WARNING"):
            self._exporter.shutdown()

    def test_force_flush_returns_true(self):
        self.assertTrue(self._exporter.force_flush())

    def test_export_stream_error(self):
        mock_stream = Mock()
        mock_stream.writelines.side_effect = OSError("disk full")
        exporter = FileLogExporter(mock_stream)
        with self.assertLogs(_LOGGER_NAME, level="ERROR"):
            result = exporter.export([_make_log_record()])
        self.assertEqual(result, LogRecordExportResult.FAILURE)


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
