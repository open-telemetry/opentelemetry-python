# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=protected-access,too-many-public-methods

import gzip
import json
import os
import threading
import unittest
import zlib
from datetime import datetime, timezone
from email.utils import format_datetime
from unittest.mock import Mock, patch

import urllib3.exceptions
from mocket import Mocket, Mocketizer, mocketize
from mocket.mocks.mockhttp import Entry, Response

from opentelemetry._logs import LogRecord, SeverityNumber
from opentelemetry.exporter.http.transport._urllib3 import (
    Urllib3HTTPTransport,
)
from opentelemetry.exporter.otlp.common.http import Compression
from opentelemetry.exporter.otlp.json.common._log_encoder import encode_logs
from opentelemetry.exporter.otlp.json.http._internal import _build_transport
from opentelemetry.exporter.otlp.json.http._log_exporter import (
    OTLPLogExporter,
)
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import (
    InMemoryLogRecordExporter,
    LogRecordExportResult,
    SimpleLogRecordProcessor,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE,
    OTEL_EXPORTER_OTLP_LOGS_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_LOGS_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_LOGS_ENDPOINT,
    OTEL_EXPORTER_OTLP_LOGS_HEADERS,
    OTEL_EXPORTER_OTLP_LOGS_TIMEOUT,
    OTEL_EXPORTER_OTLP_TIMEOUT,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import (
    NonRecordingSpan,
    SpanContext,
    TraceFlags,
    set_span_in_context,
)

from . import _mock_clock

_TEST_ENDPOINT = "http://localhost:4318/v1/logs"
_LOGGER_NAME = "opentelemetry.exporter.otlp.json.http._log_exporter"


class TestOTLPLogExporter(unittest.TestCase):
    def setUp(self):
        env_patcher = patch.dict(os.environ, {}, clear=True)
        env_patcher.start()
        self.addCleanup(env_patcher.stop)

        self._in_memory = InMemoryLogRecordExporter()
        provider = LoggerProvider()
        provider.add_log_record_processor(
            SimpleLogRecordProcessor(self._in_memory)
        )
        self._logger = provider.get_logger(__name__)

    def _finished_logs(self):
        return list(self._in_memory.get_finished_logs())

    def _make_log(self, body: str = "test-log"):
        self._logger.emit(
            LogRecord(body=body, severity_number=SeverityNumber.INFO)
        )
        return self._finished_logs()

    @staticmethod
    def _mocked_shutdown_event() -> Mock:
        shutdown_event = Mock(spec=threading.Event)
        shutdown_event.is_set.return_value = False
        return shutdown_event

    @mocketize
    def test_export_single_log(self):
        Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)
        exporter = OTLPLogExporter(endpoint=_TEST_ENDPOINT)
        logs = self._make_log("my-log")

        result = exporter.export(logs)

        self.assertEqual(result, LogRecordExportResult.SUCCESS)
        request = Mocket.last_request()
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.path, "/v1/logs")
        self.assertEqual(json.loads(request.body), encode_logs(logs).to_dict())

    @mocketize
    def test_export_multiple_logs_same_resource(self):
        Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)
        exporter = OTLPLogExporter(endpoint=_TEST_ENDPOINT)
        self._logger.emit(
            LogRecord(body="first", severity_number=SeverityNumber.INFO)
        )
        self._logger.emit(
            LogRecord(body="second", severity_number=SeverityNumber.INFO)
        )
        logs = self._finished_logs()

        result = exporter.export(logs)

        self.assertEqual(result, LogRecordExportResult.SUCCESS)
        self.assertEqual(len(Mocket.request_list()), 1)
        body = json.loads(Mocket.last_request().body)
        self.assertEqual(body, encode_logs(logs).to_dict())
        total_logs = sum(
            len(sl["logRecords"])
            for rl in body["resourceLogs"]
            for sl in rl["scopeLogs"]
        )
        self.assertEqual(total_logs, 2)

    @mocketize
    def test_export_logs_different_resources(self):
        Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)
        exporter = OTLPLogExporter(endpoint=_TEST_ENDPOINT)
        logs = []
        for body, host in (("from-a", "a"), ("from-b", "b")):
            in_memory = InMemoryLogRecordExporter()
            provider = LoggerProvider(resource=Resource({"host": host}))
            provider.add_log_record_processor(
                SimpleLogRecordProcessor(in_memory)
            )
            logger = provider.get_logger(__name__)
            logger.emit(
                LogRecord(body=body, severity_number=SeverityNumber.INFO)
            )
            logs.extend(in_memory.get_finished_logs())

        result = exporter.export(logs)

        self.assertEqual(result, LogRecordExportResult.SUCCESS)
        body = json.loads(Mocket.last_request().body)
        self.assertEqual(body, encode_logs(logs).to_dict())
        self.assertEqual(len(body["resourceLogs"]), 2)

    @mocketize
    def test_export_rich_log(self):
        Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)
        exporter = OTLPLogExporter(endpoint=_TEST_ENDPOINT)
        ctx = set_span_in_context(
            NonRecordingSpan(
                SpanContext(
                    trace_id=0x000000000000000000000000DEADBEEF,
                    span_id=0x00000000DEADBEF0,
                    is_remote=True,
                    trace_flags=TraceFlags(0x01),
                )
            )
        )
        self._logger.emit(
            LogRecord(
                body="rich-log",
                severity_text="ERROR",
                severity_number=SeverityNumber.ERROR,
                attributes={"http.method": "GET", "http.status_code": 500},
                context=ctx,
            )
        )
        logs = self._finished_logs()

        result = exporter.export(logs)

        self.assertEqual(result, LogRecordExportResult.SUCCESS)
        body = json.loads(Mocket.last_request().body)
        self.assertEqual(body, encode_logs(logs).to_dict())

    @mocketize
    def test_export_empty_sequence(self):
        Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)
        exporter = OTLPLogExporter(endpoint=_TEST_ENDPOINT)

        result = exporter.export([])

        self.assertEqual(result, LogRecordExportResult.SUCCESS)
        body = json.loads(Mocket.last_request().body)
        self.assertEqual(body, encode_logs([]).to_dict())

    @mocketize
    def test_default_endpoint_and_headers(self):
        Entry.single_register(
            Entry.POST, "http://localhost:4318/v1/logs", status=200
        )
        exporter = OTLPLogExporter()

        result = exporter.export(self._make_log())

        self.assertEqual(result, LogRecordExportResult.SUCCESS)
        headers = Mocket.last_request().headers
        self.assertEqual(headers["content-type"], "application/json")
        self.assertTrue(
            headers["user-agent"].startswith("OTel-OTLP-JSON-Exporter-Python/")
        )

    def test_custom_endpoint(self):
        url = "http://custom.example:9999/v1/logs"
        cases = (
            ("constructor", {}, {"endpoint": url}),
            (
                "generic_env",
                {OTEL_EXPORTER_OTLP_ENDPOINT: "http://custom.example:9999"},
                {},
            ),
            (
                "per_signal_env",
                {OTEL_EXPORTER_OTLP_LOGS_ENDPOINT: url},
                {},
            ),
        )
        for label, env, kwargs in cases:
            with (
                self.subTest(label),
                patch.dict(os.environ, env, clear=True),
                Mocketizer(),
            ):
                Entry.single_register(Entry.POST, url, status=200)
                exporter = OTLPLogExporter(**kwargs)
                self._in_memory.clear()

                result = exporter.export(self._make_log())

                self.assertEqual(result, LogRecordExportResult.SUCCESS)

    def test_custom_headers(self):
        cases = (
            ("constructor", {}, {"headers": {"x-api-key": "secret"}}),
            (
                "generic_env",
                {OTEL_EXPORTER_OTLP_HEADERS: "x-api-key=secret"},
                {},
            ),
            (
                "per_signal_env",
                {OTEL_EXPORTER_OTLP_LOGS_HEADERS: "x-api-key=secret"},
                {},
            ),
        )
        for label, env, kwargs in cases:
            with (
                self.subTest(label),
                patch.dict(os.environ, env, clear=True),
                Mocketizer(),
            ):
                Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)
                exporter = OTLPLogExporter(endpoint=_TEST_ENDPOINT, **kwargs)
                self._in_memory.clear()

                exporter.export(self._make_log())

                headers = Mocket.last_request().headers
                self.assertEqual(headers["x-api-key"], "secret")
                self.assertEqual(headers["content-type"], "application/json")
                self.assertTrue(
                    headers["user-agent"].startswith(
                        "OTel-OTLP-JSON-Exporter-Python/"
                    )
                )

    @mocketize
    def test_custom_transport(self):
        Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)
        custom_transport = Urllib3HTTPTransport()

        with patch(
            "opentelemetry.exporter.otlp.json.http._log_exporter._build_transport"
        ) as mock_build_transport:
            exporter = OTLPLogExporter(
                endpoint=_TEST_ENDPOINT, _transport=custom_transport
            )

        mock_build_transport.assert_not_called()
        self.assertIs(exporter._client._transport, custom_transport)

        result = exporter.export(self._make_log())

        self.assertEqual(result, LogRecordExportResult.SUCCESS)
        self.assertEqual(len(Mocket.request_list()), 1)

    def test_custom_timeout(self):
        cases = (
            ("constructor", {}, {"timeout": 7.5}),
            ("generic_env", {OTEL_EXPORTER_OTLP_TIMEOUT: "7.5"}, {}),
            (
                "per_signal_env",
                {OTEL_EXPORTER_OTLP_LOGS_TIMEOUT: "7.5"},
                {},
            ),
        )
        for label, env, kwargs in cases:
            with (
                self.subTest(label),
                patch.dict(os.environ, env, clear=True),
                Mocketizer(),
            ):
                Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)
                exporter = OTLPLogExporter(endpoint=_TEST_ENDPOINT, **kwargs)
                self._in_memory.clear()

                with patch.object(
                    exporter._client._transport,
                    "request",
                    wraps=exporter._client._transport.request,
                ) as mock_request:
                    result = exporter.export(self._make_log())

                self.assertEqual(result, LogRecordExportResult.SUCCESS)
                self.assertAlmostEqual(
                    mock_request.call_args.kwargs["timeout"], 7.5, delta=0.5
                )

    @mocketize
    def test_certificate_args(self):
        Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)

        with patch(
            "opentelemetry.exporter.otlp.json.http._log_exporter._build_transport",
            wraps=_build_transport,
        ) as mock_build_transport:
            exporter = OTLPLogExporter(
                endpoint=_TEST_ENDPOINT,
                certificate_file="ca.pem",
                client_key_file="client-key.pem",
                client_certificate_file="client-cert.pem",
            )

        mock_build_transport.assert_called_once_with(
            "ca.pem",
            "client-key.pem",
            "client-cert.pem",
            OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE,
            OTEL_EXPORTER_OTLP_LOGS_CLIENT_KEY,
            OTEL_EXPORTER_OTLP_LOGS_CLIENT_CERTIFICATE,
        )

        result = exporter.export(self._make_log())

        self.assertEqual(result, LogRecordExportResult.SUCCESS)

    def test_compression_options(self):
        cases = (
            (Compression.NONE, None, lambda data: data),
            (Compression.GZIP, "gzip", gzip.decompress),
            (Compression.DEFLATE, "deflate", zlib.decompress),
        )
        for compression, expected_encoding, decompress in cases:
            with self.subTest(compression=compression), Mocketizer():
                Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)
                exporter = OTLPLogExporter(
                    endpoint=_TEST_ENDPOINT, compression=compression
                )
                transport = exporter._client._transport
                self._in_memory.clear()
                logs = self._make_log()

                with patch.object(
                    transport, "request", wraps=transport.request
                ) as mock_request:
                    result = exporter.export(logs)

                self.assertEqual(result, LogRecordExportResult.SUCCESS)
                sent_headers = mock_request.call_args.kwargs["headers"]
                if expected_encoding is None:
                    self.assertNotIn("Content-Encoding", sent_headers)
                else:
                    self.assertEqual(
                        sent_headers["Content-Encoding"], expected_encoding
                    )
                sent_data = mock_request.call_args.kwargs["data"]
                decompressed = decompress(sent_data)
                self.assertEqual(
                    json.loads(decompressed), encode_logs(logs).to_dict()
                )

    def test_export_retryable_status_codes(self):
        for status_code in (429, 502, 503, 504):
            with self.subTest(status_code=status_code), Mocketizer():
                Entry.register(
                    Entry.POST,
                    _TEST_ENDPOINT,
                    Response(status=status_code),
                    Response(status=200),
                )
                exporter = OTLPLogExporter(
                    endpoint=_TEST_ENDPOINT, timeout=30.0
                )
                shutdown_event = self._mocked_shutdown_event()
                exporter._client._shutdown_event = shutdown_event
                self._in_memory.clear()

                with _mock_clock(shutdown_event):
                    result = exporter.export(self._make_log())

                self.assertEqual(result, LogRecordExportResult.SUCCESS)
                self.assertEqual(len(Mocket.request_list()), 2)
                shutdown_event.wait.assert_called_once()
                (wait_arg,) = shutdown_event.wait.call_args.args
                self.assertGreaterEqual(wait_arg, 0.8)
                self.assertLessEqual(wait_arg, 1.2)

    def test_export_non_retryable_status_codes(self):
        for status_code in (400, 401, 403, 404, 408, 500, 501):
            with self.subTest(status_code=status_code), Mocketizer():
                Entry.single_register(
                    Entry.POST, _TEST_ENDPOINT, status=status_code
                )
                exporter = OTLPLogExporter(endpoint=_TEST_ENDPOINT)
                self._in_memory.clear()

                result = exporter.export(self._make_log())

                self.assertEqual(result, LogRecordExportResult.FAILURE)
                self.assertEqual(len(Mocket.request_list()), 1)

    @mocketize
    def test_export_max_retries(self):
        Entry.register(
            Entry.POST,
            _TEST_ENDPOINT,
            *[Response(status=503)] * 6,
        )
        exporter = OTLPLogExporter(endpoint=_TEST_ENDPOINT, timeout=1000.0)
        shutdown_event = self._mocked_shutdown_event()
        exporter._client._shutdown_event = shutdown_event

        with _mock_clock(shutdown_event):
            result = exporter.export(self._make_log())

        self.assertEqual(result, LogRecordExportResult.FAILURE)
        self.assertEqual(len(Mocket.request_list()), 6)
        self.assertEqual(shutdown_event.wait.call_count, 5)

    @mocketize
    def test_export_retry_after_header(self):
        Entry.register(
            Entry.POST,
            _TEST_ENDPOINT,
            Response(status=429, headers={"Retry-After": "5"}),
            Response(status=200),
        )
        exporter = OTLPLogExporter(endpoint=_TEST_ENDPOINT, timeout=60.0)
        shutdown_event = self._mocked_shutdown_event()
        shutdown_event.wait.return_value = False
        exporter._client._shutdown_event = shutdown_event

        result = exporter.export(self._make_log())

        self.assertEqual(result, LogRecordExportResult.SUCCESS)
        self.assertEqual(len(Mocket.request_list()), 2)
        shutdown_event.wait.assert_called_once_with(5.0)

    @mocketize
    def test_export_retry_after_header_http_date(self):
        base = 1_700_000_000.0
        retry_at = format_datetime(
            datetime.fromtimestamp(base + 30, timezone.utc), usegmt=True
        )
        Entry.register(
            Entry.POST,
            _TEST_ENDPOINT,
            Response(status=503, headers={"Retry-After": retry_at}),
            Response(status=200),
        )
        exporter = OTLPLogExporter(endpoint=_TEST_ENDPOINT, timeout=120.0)
        shutdown_event = self._mocked_shutdown_event()
        shutdown_event.wait.return_value = False
        exporter._client._shutdown_event = shutdown_event

        with patch(
            "opentelemetry.exporter.otlp.common.http.time.time",
            return_value=base,
        ):
            result = exporter.export(self._make_log())

        self.assertEqual(result, LogRecordExportResult.SUCCESS)
        self.assertEqual(len(Mocket.request_list()), 2)
        shutdown_event.wait.assert_called_once_with(30.0)

    @mocketize
    def test_export_connection_error(self):
        Entry.register(
            Entry.POST,
            _TEST_ENDPOINT,
            urllib3.exceptions.ProtocolError("simulated reset"),
            Response(status=200),
        )
        exporter = OTLPLogExporter(endpoint=_TEST_ENDPOINT, timeout=5.0)

        result = exporter.export(self._make_log())

        self.assertEqual(result, LogRecordExportResult.SUCCESS)
        self.assertEqual(len(Mocket.request_list()), 2)

    @mocketize
    def test_export_after_shutdown(self):
        exporter = OTLPLogExporter(endpoint=_TEST_ENDPOINT)
        exporter.shutdown()

        with self.assertLogs(_LOGGER_NAME, level="WARNING"):
            result = exporter.export(self._make_log())

        self.assertEqual(result, LogRecordExportResult.FAILURE)
        self.assertIsNone(Mocket.last_request())

    def test_shutdown_idempotent(self):
        exporter = OTLPLogExporter(endpoint=_TEST_ENDPOINT)
        exporter.shutdown()

        with self.assertLogs(_LOGGER_NAME, level="WARNING"):
            exporter.shutdown()

    # pylint: disable-next=no-self-use
    def test_shutdown_closes_transport(self):
        exporter = OTLPLogExporter(endpoint=_TEST_ENDPOINT)

        with patch.object(exporter._client._transport, "close") as mock_close:
            exporter.shutdown()

        mock_close.assert_called_once()

    @mocketize
    def test_force_flush(self):
        Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)
        exporter = OTLPLogExporter(endpoint=_TEST_ENDPOINT)

        self.assertTrue(exporter.force_flush())
        exporter.export(self._make_log())
        self.assertTrue(exporter.force_flush())

    @mocketize
    def test_export_encoding_failure(self):
        exporter = OTLPLogExporter(endpoint=_TEST_ENDPOINT)

        with (
            patch(
                "opentelemetry.exporter.otlp.json.http._log_exporter.encode_logs",
                side_effect=ValueError("boom"),
            ),
            self.assertLogs(_LOGGER_NAME, level="ERROR"),
        ):
            result = exporter.export(self._make_log())

        self.assertEqual(result, LogRecordExportResult.FAILURE)
        self.assertIsNone(Mocket.last_request())
