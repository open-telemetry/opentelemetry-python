# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=protected-access

import unittest
from unittest.mock import patch
from urllib.error import URLError

from opentelemetry.exporter.otlp.proto.http import Compression
from opentelemetry.exporter.otlp.proto.http._log_exporter import (
    DEFAULT_ENDPOINT,
    DEFAULT_LOGS_EXPORT_PATH,
    DEFAULT_TIMEOUT,
    OTLPLogExporter,
    _append_logs_path,
)
from opentelemetry.sdk._logs.export import LogRecordExportResult

_UNIFORM = "opentelemetry.exporter.otlp.proto.http._log_exporter.uniform"


def _ok():
    return (200, "OK")


def _503():
    return (503, "Service Unavailable")


def _404():
    return (404, "Not Found")


class TestOTLPLogExporter(unittest.TestCase):

    # ── constructor ───────────────────────────────────────────────────────────

    def test_constructor_defaults(self):
        exporter = OTLPLogExporter()
        self.assertEqual(
            exporter._endpoint,
            DEFAULT_ENDPOINT + DEFAULT_LOGS_EXPORT_PATH,
        )
        self.assertEqual(exporter._timeout, DEFAULT_TIMEOUT)
        self.assertEqual(exporter._compression, Compression.NoCompression)
        self.assertEqual(
            exporter._request_headers["Content-Type"], "application/x-protobuf"
        )
        self.assertFalse(exporter._shutdown)
        exporter.shutdown()

    def test_generic_endpoint_env_var(self):
        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://collector:4318"}):
            exporter = OTLPLogExporter()
        self.assertEqual(exporter._endpoint, "http://collector:4318/v1/logs")
        exporter.shutdown()

    def test_logs_endpoint_overrides_generic(self):
        with patch.dict("os.environ", {
            "OTEL_EXPORTER_OTLP_ENDPOINT": "http://generic:4318",
            "OTEL_EXPORTER_OTLP_LOGS_ENDPOINT": "http://logs:4318/v1/logs",
        }):
            exporter = OTLPLogExporter()
        self.assertEqual(exporter._endpoint, "http://logs:4318/v1/logs")
        exporter.shutdown()

    def test_constructor_arg_overrides_env(self):
        with patch.dict("os.environ", {
            "OTEL_EXPORTER_OTLP_LOGS_ENDPOINT": "http://env:4318/v1/logs",
        }):
            exporter = OTLPLogExporter(endpoint="http://arg:4318/v1/logs")
        self.assertEqual(exporter._endpoint, "http://arg:4318/v1/logs")
        exporter.shutdown()

    def test_timeout_generic_env_var(self):
        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_TIMEOUT": "20"}):
            exporter = OTLPLogExporter()
        self.assertEqual(exporter._timeout, 20.0)
        exporter.shutdown()

    def test_timeout_logs_env_var_overrides_generic(self):
        with patch.dict("os.environ", {
            "OTEL_EXPORTER_OTLP_TIMEOUT": "20",
            "OTEL_EXPORTER_OTLP_LOGS_TIMEOUT": "5",
        }):
            exporter = OTLPLogExporter()
        self.assertEqual(exporter._timeout, 5.0)
        exporter.shutdown()

    def test_timeout_arg_overrides_env(self):
        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_LOGS_TIMEOUT": "99"}):
            exporter = OTLPLogExporter(timeout=3)
        self.assertEqual(exporter._timeout, 3)
        exporter.shutdown()

    def test_compression_env_var_gzip(self):
        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_COMPRESSION": "gzip"}):
            exporter = OTLPLogExporter()
        self.assertEqual(exporter._compression, Compression.Gzip)
        self.assertEqual(exporter._request_headers.get("Content-Encoding"), "gzip")
        exporter.shutdown()

    def test_compression_env_var_deflate(self):
        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_COMPRESSION": "deflate"}):
            exporter = OTLPLogExporter()
        self.assertEqual(exporter._compression, Compression.Deflate)
        self.assertEqual(exporter._request_headers.get("Content-Encoding"), "deflate")
        exporter.shutdown()

    def test_compression_logs_env_overrides_generic(self):
        with patch.dict("os.environ", {
            "OTEL_EXPORTER_OTLP_COMPRESSION": "gzip",
            "OTEL_EXPORTER_OTLP_LOGS_COMPRESSION": "deflate",
        }):
            exporter = OTLPLogExporter()
        self.assertEqual(exporter._compression, Compression.Deflate)
        exporter.shutdown()

    def test_compression_arg_gzip(self):
        exporter = OTLPLogExporter(compression=Compression.Gzip)
        self.assertEqual(exporter._compression, Compression.Gzip)
        self.assertEqual(exporter._request_headers.get("Content-Encoding"), "gzip")
        exporter.shutdown()

    def test_no_compression_header_for_none_compression(self):
        exporter = OTLPLogExporter(compression=Compression.NoCompression)
        self.assertNotIn("Content-Encoding", exporter._request_headers)
        exporter.shutdown()

    # ── export ────────────────────────────────────────────────────────────────

    def test_export_success(self):
        exporter = OTLPLogExporter()
        with patch.object(exporter, "_export", return_value=_ok()):
            result = exporter.export([])
        self.assertEqual(result, LogRecordExportResult.SUCCESS)
        exporter.shutdown()

    def test_export_after_shutdown_returns_failure(self):
        exporter = OTLPLogExporter()
        exporter.shutdown()
        result = exporter.export([])
        self.assertEqual(result, LogRecordExportResult.FAILURE)

    def test_export_non_retryable_failure(self):
        exporter = OTLPLogExporter()
        with patch.object(exporter, "_export", return_value=_404()):
            result = exporter.export([])
        self.assertEqual(result, LogRecordExportResult.FAILURE)
        exporter.shutdown()

    def test_export_retry_then_deadline_exceeded(self):
        exporter = OTLPLogExporter(timeout=0.01)
        with patch.object(exporter, "_export", return_value=_503()):
            with patch(_UNIFORM, return_value=100.0):
                result = exporter.export([])
        self.assertEqual(result, LogRecordExportResult.FAILURE)
        exporter.shutdown()

    def test_export_max_retries_exhausted(self):
        exporter = OTLPLogExporter(timeout=100)
        with patch.object(exporter, "_export", return_value=_503()):
            with patch(_UNIFORM, return_value=0.0001):
                with patch.object(exporter._shutdown_is_occuring, "wait", return_value=False):
                    result = exporter.export([])
        self.assertEqual(result, LogRecordExportResult.FAILURE)
        exporter.shutdown()

    def test_shutdown_interrupts_retry(self):
        exporter = OTLPLogExporter(timeout=100)
        with patch.object(exporter, "_export", return_value=_503()):
            with patch(_UNIFORM, return_value=0.0001):
                with patch.object(exporter._shutdown_is_occuring, "wait", return_value=True):
                    result = exporter.export([])
        self.assertEqual(result, LogRecordExportResult.FAILURE)
        exporter.shutdown()

    def test_connection_error_is_retryable(self):
        exporter = OTLPLogExporter(timeout=0.01)
        with patch.object(exporter, "_export", side_effect=URLError("refused")):
            with patch(_UNIFORM, return_value=100.0):
                result = exporter.export([])
        self.assertEqual(result, LogRecordExportResult.FAILURE)
        exporter.shutdown()

    # ── shutdown ──────────────────────────────────────────────────────────────

    def test_shutdown_sets_flag(self):
        exporter = OTLPLogExporter()
        self.assertFalse(exporter._shutdown)
        exporter.shutdown()
        self.assertTrue(exporter._shutdown)

    def test_shutdown_twice_logs_warning(self):
        exporter = OTLPLogExporter()
        exporter.shutdown()
        with self.assertLogs(level="WARNING") as cm:
            exporter.shutdown()
        self.assertTrue(any("already shutdown" in msg for msg in cm.output))

    def test_force_flush_returns_true(self):
        exporter = OTLPLogExporter()
        self.assertTrue(exporter.force_flush())
        exporter.shutdown()


class TestAppendLogsPath(unittest.TestCase):
    def test_with_trailing_slash(self):
        self.assertEqual(
            _append_logs_path("http://localhost:4318/"),
            "http://localhost:4318/v1/logs",
        )

    def test_without_trailing_slash(self):
        self.assertEqual(
            _append_logs_path("http://localhost:4318"),
            "http://localhost:4318/v1/logs",
        )
