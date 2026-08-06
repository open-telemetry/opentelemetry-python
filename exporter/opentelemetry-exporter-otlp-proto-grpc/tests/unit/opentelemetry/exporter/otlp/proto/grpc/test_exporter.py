# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=protected-access

import unittest
from collections.abc import Sequence
from unittest.mock import Mock, patch, call

from opentelemetry.exporter.otlp._proto.grpc._pygrpc import api as grpc
from opentelemetry.exporter.otlp._proto.grpc._pygrpc.api import Compression, StatusCode

from opentelemetry.exporter.otlp.proto.grpc.exporter import (
    InvalidCompressionValueException,
    OTLPExporterMixin,
    _RETRYABLE_ERROR_CODES,
    environ_to_compression,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry._proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
from opentelemetry._proto.collector.trace.v1.trace_service_pb2_grpc import TraceServiceStub
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

_INSECURE_CH = "opentelemetry.exporter.otlp.proto.grpc.exporter.insecure_channel"
_SECURE_CH = "opentelemetry.exporter.otlp.proto.grpc.exporter.secure_channel"
_SSL_CREDS = "opentelemetry.exporter.otlp.proto.grpc.exporter.ssl_channel_credentials"
_UNIFORM = "opentelemetry.exporter.otlp.proto.grpc.exporter.random.uniform"


class _FakeRpcError(grpc.RpcError):
    def __init__(self, code, details=""):
        self._code = code
        self._details = details

    def code(self):
        return self._code

    def details(self):
        return self._details


def _make_exporter(**kwargs):
    """Create OTLPSpanExporter with a mock insecure channel, returning (exporter, mock_channel)."""
    with patch(_INSECURE_CH) as mock_ch:
        mock_channel = Mock()
        mock_ch.return_value = mock_channel
        exporter = OTLPSpanExporter(insecure=True, **kwargs)
    return exporter, mock_channel


class TestOTLPExporterMixinChannel(unittest.TestCase):

    def test_insecure_true_uses_insecure_channel(self):
        with patch(_INSECURE_CH) as mock_insecure:
            exporter = OTLPSpanExporter(insecure=True)
        mock_insecure.assert_called_once()
        exporter.shutdown()

    def test_http_scheme_implies_insecure(self):
        with patch(_INSECURE_CH) as mock_insecure:
            exporter = OTLPSpanExporter(endpoint="http://collector:4317")
        mock_insecure.assert_called_once()
        exporter.shutdown()

    def test_insecure_false_uses_secure_channel(self):
        with patch(_SSL_CREDS, return_value=Mock(spec=grpc.ChannelCredentials)):
            with patch(_SECURE_CH) as mock_secure:
                exporter = OTLPSpanExporter(insecure=False)
        mock_secure.assert_called_once()
        exporter.shutdown()

    def test_https_scheme_implies_secure(self):
        with patch(_SSL_CREDS, return_value=Mock(spec=grpc.ChannelCredentials)):
            with patch(_SECURE_CH) as mock_secure:
                exporter = OTLPSpanExporter(endpoint="https://collector:4317")
        mock_secure.assert_called_once()
        exporter.shutdown()

    def test_default_endpoint_is_localhost_4317(self):
        with patch(_INSECURE_CH) as mock_insecure:
            OTLPSpanExporter(insecure=True)
        args, _ = mock_insecure.call_args
        self.assertEqual(args[0], "localhost:4317")

    def test_endpoint_netloc_extracted(self):
        with patch(_INSECURE_CH) as mock_insecure:
            OTLPSpanExporter(insecure=True, endpoint="http://myhost:4317")
        args, _ = mock_insecure.call_args
        self.assertEqual(args[0], "myhost:4317")

    def test_generic_endpoint_env_var(self):
        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://env-host:4317"}):
            with patch(_INSECURE_CH) as mock_insecure:
                OTLPSpanExporter(insecure=True)
        args, _ = mock_insecure.call_args
        self.assertEqual(args[0], "env-host:4317")

    def test_insecure_env_var_true(self):
        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_INSECURE": "true"}):
            with patch(_INSECURE_CH) as mock_insecure:
                OTLPSpanExporter()
        mock_insecure.assert_called_once()

    def test_compression_gzip_passed_to_channel(self):
        with patch(_INSECURE_CH) as mock_insecure:
            OTLPSpanExporter(insecure=True, compression=Compression.Gzip)
        _, kwargs = mock_insecure.call_args
        self.assertEqual(kwargs.get("compression"), Compression.Gzip)


class TestOTLPExporterMixinHeaders(unittest.TestCase):

    def test_headers_dict_converted_to_tuple(self):
        exporter, _ = _make_exporter(headers={"x-my-header": "val"})
        self.assertIn(("x-my-header", "val"), exporter._headers)
        exporter.shutdown()

    def test_headers_str_parsed(self):
        exporter, _ = _make_exporter(headers="x-token=abc,x-env=xyz")
        self.assertIn(("x-token", "abc"), exporter._headers)
        self.assertIn(("x-env", "xyz"), exporter._headers)
        exporter.shutdown()

    def test_headers_env_var_parsed(self):
        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_HEADERS": "x-hdr=foo"}):
            exporter, _ = _make_exporter()
        self.assertIn(("x-hdr", "foo"), exporter._headers)
        exporter.shutdown()

    def test_no_headers_gives_empty_tuple(self):
        exporter, _ = _make_exporter()
        self.assertEqual(exporter._headers, tuple())
        exporter.shutdown()


class TestOTLPExporterMixinTimeout(unittest.TestCase):

    def test_default_timeout(self):
        exporter, _ = _make_exporter()
        self.assertEqual(exporter._timeout, 10.0)
        exporter.shutdown()

    def test_timeout_arg(self):
        exporter, _ = _make_exporter(timeout=42)
        self.assertEqual(exporter._timeout, 42.0)
        exporter.shutdown()

    def test_timeout_env_var(self):
        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_TIMEOUT": "25"}):
            exporter, _ = _make_exporter()
        self.assertEqual(exporter._timeout, 25.0)
        exporter.shutdown()


class TestOTLPExporterMixinRetryableCodes(unittest.TestCase):

    def test_default_retryable_codes(self):
        exporter, _ = _make_exporter()
        self.assertEqual(exporter._retryable_error_codes, _RETRYABLE_ERROR_CODES)
        exporter.shutdown()

    def test_custom_codes_from_arg(self):
        exporter, _ = _make_exporter(retryable_error_codes=[StatusCode.NOT_FOUND])
        self.assertIn(StatusCode.NOT_FOUND, exporter._retryable_error_codes)
        self.assertNotIn(StatusCode.UNAVAILABLE, exporter._retryable_error_codes)
        exporter.shutdown()

    def test_custom_codes_from_env_var(self):
        env = {"OTEL_PYTHON_EXPORTER_OTLP_GRPC_RETRYABLE_ERROR_CODES": "NOT_FOUND,UNKNOWN"}
        with patch.dict("os.environ", env):
            exporter, _ = _make_exporter()
        self.assertIn(StatusCode.NOT_FOUND, exporter._retryable_error_codes)
        self.assertIn(StatusCode.UNKNOWN, exporter._retryable_error_codes)
        exporter.shutdown()


class TestOTLPExporterMixinExport(unittest.TestCase):

    def _exporter_with_mock_client(self, **kwargs):
        exporter, mock_channel = _make_exporter(**kwargs)
        # TraceServiceStub.__init__ sets self.Export = channel.unary_unary(...)
        # mock_channel.unary_unary(...) returns a Mock, so _client.Export is that Mock
        return exporter, exporter._client.Export

    def test_export_success(self):
        exporter, mock_export = self._exporter_with_mock_client()
        result = exporter.export([])
        self.assertEqual(result, SpanExportResult.SUCCESS)
        mock_export.assert_called_once()
        exporter.shutdown()

    def test_export_after_shutdown_returns_failure(self):
        exporter, _ = self._exporter_with_mock_client()
        exporter.shutdown()
        result = exporter.export([])
        self.assertEqual(result, SpanExportResult.FAILURE)

    def test_export_non_retryable_error_fails_immediately(self):
        exporter, mock_export = self._exporter_with_mock_client()
        mock_export.side_effect = _FakeRpcError(StatusCode.NOT_FOUND, "not found")
        result = exporter.export([])
        self.assertEqual(result, SpanExportResult.FAILURE)
        # Should only attempt once (non-retryable)
        self.assertEqual(mock_export.call_count, 1)
        exporter.shutdown()

    def test_export_retryable_then_deadline_exceeded(self):
        # Large backoff immediately exceeds short timeout → exits after first attempt
        exporter, mock_export = self._exporter_with_mock_client(timeout=0.01)
        mock_export.side_effect = _FakeRpcError(StatusCode.UNAVAILABLE)
        with patch(_UNIFORM, return_value=100.0):
            with patch(_INSECURE_CH):  # reinit channel on UNAVAILABLE
                result = exporter.export([])
        self.assertEqual(result, SpanExportResult.FAILURE)
        exporter.shutdown()

    def test_export_max_retries_exhausted(self):
        # Use RESOURCE_EXHAUSTED — retryable but does not trigger channel reinit
        exporter, mock_export = self._exporter_with_mock_client(timeout=999)
        mock_export.side_effect = _FakeRpcError(StatusCode.RESOURCE_EXHAUSTED)
        with patch(_UNIFORM, return_value=0.00001):
            with patch.object(exporter._shutdown_in_progress, "wait", return_value=False):
                result = exporter.export([])
        self.assertEqual(result, SpanExportResult.FAILURE)
        exporter.shutdown()

    def test_shutdown_interrupts_retry(self):
        # Use RESOURCE_EXHAUSTED — retryable but does not trigger channel reinit
        exporter, mock_export = self._exporter_with_mock_client(timeout=999)
        mock_export.side_effect = _FakeRpcError(StatusCode.RESOURCE_EXHAUSTED)
        with patch(_UNIFORM, return_value=0.00001):
            with patch.object(exporter._shutdown_in_progress, "wait", return_value=True):
                result = exporter.export([])
        self.assertEqual(result, SpanExportResult.FAILURE)
        exporter.shutdown()

    def test_unavailable_triggers_channel_reinit(self):
        exporter, mock_export = self._exporter_with_mock_client(timeout=0.001)
        mock_export.side_effect = _FakeRpcError(StatusCode.UNAVAILABLE)
        with patch(_UNIFORM, return_value=100.0):
            with patch(_INSECURE_CH) as mock_new_channel:
                exporter.export([])
        # channel was reinitialized once on first UNAVAILABLE
        mock_new_channel.assert_called_once()
        exporter.shutdown()


class TestOTLPExporterMixinShutdown(unittest.TestCase):

    def test_shutdown_sets_flag_and_closes_channel(self):
        exporter, mock_channel = _make_exporter()
        self.assertFalse(exporter._shutdown)
        exporter.shutdown()
        self.assertTrue(exporter._shutdown)
        mock_channel.close.assert_called_once()

    def test_shutdown_twice_logs_warning(self):
        exporter, _ = _make_exporter()
        exporter.shutdown()
        with self.assertLogs(level="WARNING") as cm:
            exporter.shutdown()
        self.assertTrue(any("already shutdown" in msg for msg in cm.output))

    def test_force_flush_returns_true(self):
        exporter, _ = _make_exporter()
        self.assertTrue(exporter.force_flush())
        exporter.shutdown()


class TestEnvironToCompression(unittest.TestCase):

    def test_gzip(self):
        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_COMPRESSION": "gzip"}):
            result = environ_to_compression("OTEL_EXPORTER_OTLP_COMPRESSION")
        self.assertEqual(result, Compression.Gzip)

    def test_missing_env_returns_none(self):
        result = environ_to_compression("OTEL_EXPORTER_OTLP_COMPRESSION")
        self.assertIsNone(result)

    def test_invalid_value_raises(self):
        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_COMPRESSION": "zstd"}):
            with self.assertRaises(InvalidCompressionValueException):
                environ_to_compression("OTEL_EXPORTER_OTLP_COMPRESSION")
