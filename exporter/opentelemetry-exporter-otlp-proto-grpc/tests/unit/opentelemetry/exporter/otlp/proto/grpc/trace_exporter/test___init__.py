# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=protected-access

import unittest
from unittest.mock import Mock, patch

from opentelemetry.exporter.otlp._proto.grpc._pygrpc import api as grpc
from opentelemetry.exporter.otlp._proto.grpc._pygrpc.api import Compression, StatusCode

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import SpanExportResult

_INSECURE_CH = "opentelemetry.exporter.otlp.proto.grpc.exporter.insecure_channel"
_SSL_CREDS = "opentelemetry.exporter.otlp.proto.grpc.exporter.ssl_channel_credentials"


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
        exporter = OTLPSpanExporter(insecure=True, **kwargs)
    return exporter


class TestOTLPSpanExporterConstructor(unittest.TestCase):

    def test_defaults(self):
        with patch(_INSECURE_CH) as mock_ch:
            exporter = OTLPSpanExporter(insecure=True)
        args, _ = mock_ch.call_args
        self.assertEqual(args[0], "localhost:4317")
        self.assertEqual(exporter._timeout, 10.0)
        self.assertFalse(exporter._shutdown)
        exporter.shutdown()

    def test_traces_endpoint_env_var(self):
        with patch.dict("os.environ", {
            "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT": "http://traces-host:4317",
        }):
            with patch(_INSECURE_CH) as mock_ch:
                OTLPSpanExporter(insecure=True)
        args, _ = mock_ch.call_args
        self.assertEqual(args[0], "traces-host:4317")

    def test_traces_endpoint_overrides_generic(self):
        with patch.dict("os.environ", {
            "OTEL_EXPORTER_OTLP_ENDPOINT": "http://generic:4317",
            "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT": "http://traces:4317",
        }):
            with patch(_INSECURE_CH) as mock_ch:
                OTLPSpanExporter(insecure=True)
        args, _ = mock_ch.call_args
        self.assertEqual(args[0], "traces:4317")

    def test_traces_timeout_env_var(self):
        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_TRACES_TIMEOUT": "7"}):
            exporter = _make_exporter()
        self.assertEqual(exporter._timeout, 7.0)
        exporter.shutdown()

    def test_traces_timeout_overrides_generic(self):
        with patch.dict("os.environ", {
            "OTEL_EXPORTER_OTLP_TIMEOUT": "20",
            "OTEL_EXPORTER_OTLP_TRACES_TIMEOUT": "3",
        }):
            exporter = _make_exporter()
        self.assertEqual(exporter._timeout, 3.0)
        exporter.shutdown()

    def test_traces_insecure_env_var_true(self):
        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_TRACES_INSECURE": "true"}):
            with patch(_INSECURE_CH) as mock_insecure:
                OTLPSpanExporter()
        mock_insecure.assert_called_once()

    def test_traces_compression_env_var_gzip(self):
        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_TRACES_COMPRESSION": "gzip"}):
            with patch(_INSECURE_CH) as mock_ch:
                OTLPSpanExporter(insecure=True)
        _, kwargs = mock_ch.call_args
        self.assertEqual(kwargs.get("compression"), Compression.Gzip)

    def test_traces_headers_env_var(self):
        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_TRACES_HEADERS": "x-trace=yes"}):
            exporter = _make_exporter()
        self.assertIn(("x-trace", "yes"), exporter._headers)
        exporter.shutdown()

    def test_arg_endpoint_overrides_env(self):
        with patch.dict("os.environ", {
            "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT": "http://env:4317",
        }):
            with patch(_INSECURE_CH) as mock_ch:
                OTLPSpanExporter(insecure=True, endpoint="http://arg:4317")
        args, _ = mock_ch.call_args
        self.assertEqual(args[0], "arg:4317")


class TestOTLPSpanExporterExport(unittest.TestCase):

    def test_export_success(self):
        exporter = _make_exporter()
        result = exporter.export([])
        self.assertEqual(result, SpanExportResult.SUCCESS)
        exporter.shutdown()

    def test_export_failure_non_retryable(self):
        exporter = _make_exporter()
        exporter._client.Export.side_effect = _FakeRpcError(StatusCode.PERMISSION_DENIED)
        result = exporter.export([])
        self.assertEqual(result, SpanExportResult.FAILURE)
        exporter.shutdown()

    def test_export_after_shutdown(self):
        exporter = _make_exporter()
        exporter.shutdown()
        result = exporter.export([])
        self.assertEqual(result, SpanExportResult.FAILURE)

    def test_force_flush_returns_true(self):
        exporter = _make_exporter()
        self.assertTrue(exporter.force_flush())
        exporter.shutdown()

    def test_exporting_property(self):
        exporter = _make_exporter()
        self.assertEqual(exporter._exporting, "traces")
        exporter.shutdown()
