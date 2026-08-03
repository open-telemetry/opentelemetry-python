# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=protected-access

import unittest
from unittest.mock import patch

from opentelemetry.exporter.otlp._proto.grpc._pygrpc import api as grpc
from opentelemetry.exporter.otlp._proto.grpc._pygrpc.api import Compression, StatusCode

from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs.export import LogRecordExportResult

_INSECURE_CH = "opentelemetry.exporter.otlp.proto.grpc.exporter.insecure_channel"


class _FakeRpcError(grpc.RpcError):
    def __init__(self, code, details=""):
        self._code = code
        self._details = details

    def code(self):
        return self._code

    def details(self):
        return self._details


def _make_exporter(**kwargs):
    with patch(_INSECURE_CH):
        exporter = OTLPLogExporter(insecure=True, **kwargs)
    return exporter


class TestOTLPLogExporterConstructor(unittest.TestCase):

    def test_defaults(self):
        with patch(_INSECURE_CH) as mock_ch:
            exporter = OTLPLogExporter(insecure=True)
        args, _ = mock_ch.call_args
        self.assertEqual(args[0], "localhost:4317")
        self.assertEqual(exporter._timeout, 10.0)
        self.assertFalse(exporter._shutdown)
        exporter.shutdown()

    def test_logs_endpoint_env_var(self):
        with patch.dict("os.environ", {
            "OTEL_EXPORTER_OTLP_LOGS_ENDPOINT": "http://logs-host:4317",
        }):
            with patch(_INSECURE_CH) as mock_ch:
                OTLPLogExporter(insecure=True)
        args, _ = mock_ch.call_args
        self.assertEqual(args[0], "logs-host:4317")

    def test_logs_endpoint_overrides_generic(self):
        with patch.dict("os.environ", {
            "OTEL_EXPORTER_OTLP_ENDPOINT": "http://generic:4317",
            "OTEL_EXPORTER_OTLP_LOGS_ENDPOINT": "http://logs:4317",
        }):
            with patch(_INSECURE_CH) as mock_ch:
                OTLPLogExporter(insecure=True)
        args, _ = mock_ch.call_args
        self.assertEqual(args[0], "logs:4317")

    def test_logs_timeout_env_var(self):
        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_LOGS_TIMEOUT": "12"}):
            exporter = _make_exporter()
        self.assertEqual(exporter._timeout, 12.0)
        exporter.shutdown()

    def test_logs_insecure_env_var_true(self):
        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_LOGS_INSECURE": "true"}):
            with patch(_INSECURE_CH) as mock_insecure:
                OTLPLogExporter()
        mock_insecure.assert_called_once()

    def test_logs_headers_env_var(self):
        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_LOGS_HEADERS": "x-log=yes"}):
            exporter = _make_exporter()
        self.assertIn(("x-log", "yes"), exporter._headers)
        exporter.shutdown()

    def test_logs_compression_env_var_gzip(self):
        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_LOGS_COMPRESSION": "gzip"}):
            with patch(_INSECURE_CH) as mock_ch:
                OTLPLogExporter(insecure=True)
        _, kwargs = mock_ch.call_args
        self.assertEqual(kwargs.get("compression"), Compression.Gzip)

    def test_arg_endpoint_overrides_env(self):
        with patch.dict("os.environ", {
            "OTEL_EXPORTER_OTLP_LOGS_ENDPOINT": "http://env:4317",
        }):
            with patch(_INSECURE_CH) as mock_ch:
                OTLPLogExporter(insecure=True, endpoint="http://arg:4317")
        args, _ = mock_ch.call_args
        self.assertEqual(args[0], "arg:4317")

    def test_exporting_property(self):
        exporter = _make_exporter()
        self.assertEqual(exporter._exporting, "logs")
        exporter.shutdown()


class TestOTLPLogExporterExport(unittest.TestCase):

    def test_export_success(self):
        exporter = _make_exporter()
        result = exporter.export([])
        self.assertEqual(result, LogRecordExportResult.SUCCESS)
        exporter.shutdown()

    def test_export_failure_non_retryable(self):
        exporter = _make_exporter()
        exporter._client.Export.side_effect = _FakeRpcError(StatusCode.PERMISSION_DENIED)
        result = exporter.export([])
        self.assertEqual(result, LogRecordExportResult.FAILURE)
        exporter.shutdown()

    def test_export_after_shutdown(self):
        exporter = _make_exporter()
        exporter.shutdown()
        result = exporter.export([])
        self.assertEqual(result, LogRecordExportResult.FAILURE)

    def test_force_flush_returns_true(self):
        exporter = _make_exporter()
        self.assertTrue(exporter.force_flush())
        exporter.shutdown()

    def test_shutdown_sets_flag(self):
        exporter = _make_exporter()
        self.assertFalse(exporter._shutdown)
        exporter.shutdown()
        self.assertTrue(exporter._shutdown)
