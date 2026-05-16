# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import io
import os
import sys
import tempfile
import unittest
from unittest.mock import Mock

from opentelemetry._logs import LogRecord, SeverityNumber
from opentelemetry.exporter.otlp.json.common._log_encoder import encode_logs
from opentelemetry.exporter.otlp.json.file._internal import _format_line
from opentelemetry.exporter.otlp.json.file._log_exporter import (
    FileLogExporter,
)
from opentelemetry.proto_json.logs.v1.logs import ResourceLogs
from opentelemetry.sdk._logs import (
    LoggerProvider,
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
        self._exporter = FileLogExporter(stream=self._stream)

    def test_export_empty_sequence(self):
        result = self._exporter.export([])
        self.assertEqual(result, LogRecordExportResult.SUCCESS)
        self.assertEqual(self._stream.getvalue(), "")

    def test_export_single_log(self):
        result = self._exporter.export([_make_log_record("hello from test")])
        self.assertEqual(result, LogRecordExportResult.SUCCESS)
        lines = self._stream.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        rl = ResourceLogs.from_json(lines[0])
        self.assertEqual(
            rl.scope_logs[0].log_records[0].body.string_value,  # type: ignore
            "hello from test",
        )

    def test_export_multiple_logs_same_resource(self):
        logs = [
            _make_log_record("first"),
            _make_log_record("second"),
        ]
        self._exporter.export(logs)
        lines = self._stream.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        rl = ResourceLogs.from_json(lines[0])
        total_logs = sum(len(sl.log_records) for sl in rl.scope_logs)
        self.assertEqual(total_logs, 2)

    def test_export_logs_different_resources(self):
        logs = [
            _make_log_record("from-a", resource_attrs={"host": "a"}),
            _make_log_record("from-b", resource_attrs={"host": "b"}),
        ]
        self._exporter.export(logs)
        lines = self._stream.getvalue().splitlines()
        self.assertEqual(len(lines), 2)
        bodies = {
            ResourceLogs.from_json(line)
            .scope_logs[0]
            .log_records[0]
            .body.string_value  # type: ignore
            for line in lines
        }
        self.assertEqual(bodies, {"from-a", "from-b"})

    def test_stream_flushed_after_export(self):
        mock_stream = Mock()
        exporter = FileLogExporter(stream=mock_stream)
        exporter.export([_make_log_record()])
        mock_stream.flush.assert_called_once()

    def test_custom_formatter(self):
        formatter = Mock(return_value="formatted\n")
        exporter = FileLogExporter(stream=self._stream, formatter=formatter)
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

    def test_export_stream_error(self):
        mock_stream = Mock()
        mock_stream.writelines.side_effect = OSError("disk full")
        exporter = FileLogExporter(stream=mock_stream)
        with self.assertLogs(_LOGGER_NAME, level="ERROR"):
            result = exporter.export([_make_log_record()])
        self.assertEqual(result, LogRecordExportResult.FAILURE)

    def test_export_with_path(self):
        tmp_dir = tempfile.TemporaryDirectory()
        path = os.path.join(tmp_dir.name, "output.jsonl")
        exporter = FileLogExporter(path)
        exporter.export([_make_log_record("hello from path")])
        exporter.shutdown()
        with open(path) as f:
            rl = ResourceLogs.from_json(f.read().splitlines()[0])
        self.assertEqual(
            rl.scope_logs[0].log_records[0].body.string_value,  # type: ignore
            "hello from path",
        )
        tmp_dir.cleanup()

    def test_path_and_stream_raises(self):
        with self.assertRaises(ValueError):
            FileLogExporter("output.jsonl", stream=self._stream)  # type: ignore

    def test_default_stream_is_stdout(self):
        exporter = FileLogExporter()
        self.assertIs(exporter._stream, sys.stdout)


class TestFileLogExporterRoundTrip(unittest.TestCase):
    def setUp(self):
        self._stream = io.StringIO()
        self._file_exporter = FileLogExporter(stream=self._stream)
        self._in_memory = InMemoryLogRecordExporter()
        provider = LoggerProvider()
        provider.add_log_record_processor(
            SimpleLogRecordProcessor(self._file_exporter)
        )
        provider.add_log_record_processor(
            SimpleLogRecordProcessor(self._in_memory)
        )
        self._logger = provider.get_logger("test.integration")

    def _expected(self) -> str:
        return "".join(
            _format_line(rl.to_dict())
            for record in self._in_memory.get_finished_logs()
            for rl in encode_logs([record]).resource_logs
        )

    def test_single_log_matches_in_memory(self):
        self._logger.emit(
            LogRecord(
                body="hello from integration",
                severity_number=SeverityNumber.INFO,
            )
        )
        self.assertEqual(self._stream.getvalue(), self._expected())

    def test_multiple_logs_match_in_memory(self):
        self._logger.emit(
            LogRecord(
                body="first message", severity_number=SeverityNumber.INFO
            )
        )
        self._logger.emit(
            LogRecord(
                body="second message", severity_number=SeverityNumber.WARN
            )
        )
        self.assertEqual(self._stream.getvalue(), self._expected())
