# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=protected-access,too-many-public-methods

import gzip
import os
import threading
import time
import unittest
import zlib
from unittest.mock import Mock, patch

import requests
import urllib3.exceptions
from mocket import Mocket, Mocketizer, mocketize
from mocket.mocks.mockhttp import Entry, Response

from opentelemetry._logs import LogRecord, SeverityNumber
from opentelemetry.exporter.http.transport._requests import (
    RequestsHTTPTransport,
)
from opentelemetry.exporter.http.transport._urllib3 import (
    Urllib3HTTPTransport,
)
from opentelemetry.exporter.otlp.common._http import (
    Compression as CommonCompression,
)
from opentelemetry.exporter.otlp.proto.common._log_encoder import encode_logs
from opentelemetry.exporter.otlp.proto.http import Compression
from opentelemetry.exporter.otlp.proto.http._internal import _build_transport
from opentelemetry.exporter.otlp.proto.http._log_exporter import (
    DEFAULT_ENDPOINT,
    DEFAULT_LOGS_EXPORT_PATH,
    OTLPLogExporter,
)
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceRequest,
)
from opentelemetry.sdk._logs import ReadWriteLogRecord
from opentelemetry.sdk._logs.export import LogRecordExportResult
from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_EXPORTER_OTLP_HTTP_LOGS_CREDENTIAL_PROVIDER,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE,
    OTEL_EXPORTER_OTLP_LOGS_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_LOGS_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_LOGS_ENDPOINT,
    OTEL_EXPORTER_OTLP_LOGS_HEADERS,
    OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.resources import Resource as SDKResource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.test.mock_test_classes import IterEntryPoint

from . import _mock_clock

_TEST_ENDPOINT = "http://localhost:4318/v1/logs"
_LOGGER_NAME = "opentelemetry.exporter.otlp.proto.http._log_exporter"


def _decode_body(body: bytes) -> ExportLogsServiceRequest:
    return ExportLogsServiceRequest.FromString(body)


def _make_log_record() -> ReadWriteLogRecord:
    return ReadWriteLogRecord(
        LogRecord(
            timestamp=1644650195189786182,
            severity_text="WARN",
            severity_number=SeverityNumber.WARN,
            body="a log message",
            attributes={"a": 1, "b": "c"},
        ),
        resource=SDKResource({"first_resource": "value"}),
        instrumentation_scope=InstrumentationScope("name", "version"),
    )


class TestOTLPHTTPLogExporter(unittest.TestCase):
    def setUp(self):
        env_patcher = patch.dict(os.environ, {}, clear=True)
        env_patcher.start()
        self.addCleanup(env_patcher.stop)

        self.metric_reader = InMemoryMetricReader()
        self.meter_provider = MeterProvider(
            metric_readers=[self.metric_reader]
        )

    @staticmethod
    def _mocked_shutdown_event() -> Mock:
        shutdown_event = Mock(spec=threading.Event)
        shutdown_event.is_set.return_value = False
        return shutdown_event

    def assert_standard_metric_attrs(self, attributes):
        self.assertEqual(
            attributes["otel.component.type"], "otlp_http_log_exporter"
        )
        self.assertTrue(
            attributes["otel.component.name"].startswith(
                "otlp_http_log_exporter/"
            )
        )
        self.assertEqual(attributes["server.address"], "localhost")
        self.assertEqual(attributes["server.port"], 4318)

    # -- construction / transport selection --------------------------------

    def test_constructor_default_uses_urllib3_transport(self):
        exporter = OTLPLogExporter()

        self.assertEqual(
            exporter._endpoint, DEFAULT_ENDPOINT + DEFAULT_LOGS_EXPORT_PATH
        )
        self.assertIs(exporter._compression, CommonCompression.NONE)
        self.assertIsNone(exporter._session)
        self.assertIsInstance(
            exporter._client._transport, Urllib3HTTPTransport
        )

    def test_explicit_session_uses_requests_transport(self):
        session = requests.Session()
        exporter = OTLPLogExporter(session=session)

        self.assertIs(exporter._session, session)
        self.assertIsInstance(
            exporter._client._transport, RequestsHTTPTransport
        )
        self.assertIs(exporter._client._transport._session, session)

    @patch("opentelemetry.exporter.otlp.proto.http._common.entry_points")
    def test_credential_provider_uses_requests_transport(
        self, mock_entry_point
    ):
        credential = requests.Session()
        mock_entry_point.configure_mock(
            return_value=[
                IterEntryPoint("custom_credential", lambda: credential)
            ]
        )
        with patch.dict(
            os.environ,
            {
                _OTEL_PYTHON_EXPORTER_OTLP_HTTP_LOGS_CREDENTIAL_PROVIDER: "custom_credential",
            },
        ):
            exporter = OTLPLogExporter()

        self.assertIs(exporter._session, credential)
        self.assertIsInstance(
            exporter._client._transport, RequestsHTTPTransport
        )

    @patch("opentelemetry.exporter.otlp.proto.http._common.entry_points")
    def test_exception_raised_when_entrypoint_returns_wrong_type(
        self, mock_entry_point
    ):
        mock_entry_point.configure_mock(
            return_value=[IterEntryPoint("bad_credential", lambda: 1)]
        )
        with (
            patch.dict(
                os.environ,
                {
                    _OTEL_PYTHON_EXPORTER_OTLP_HTTP_LOGS_CREDENTIAL_PROVIDER: "bad_credential",
                },
            ),
            self.assertRaises(RuntimeError),
        ):
            OTLPLogExporter()

    @patch("opentelemetry.exporter.otlp.proto.http._common.entry_points")
    def test_exception_raised_when_entrypoint_does_not_exist(
        self, mock_entry_point
    ):
        mock_entry_point.configure_mock(return_value=[])
        with (
            patch.dict(
                os.environ,
                {
                    _OTEL_PYTHON_EXPORTER_OTLP_HTTP_LOGS_CREDENTIAL_PROVIDER: "missing",
                },
            ),
            self.assertRaises(RuntimeError),
        ):
            OTLPLogExporter()

    def test_compression_dual_enum_acceptance(self):
        for compression in (Compression.Gzip, CommonCompression.GZIP):
            with self.subTest(compression=compression):
                exporter = OTLPLogExporter(compression=compression)
                self.assertIs(exporter._compression, CommonCompression.GZIP)

    # -- export / wire format ------------------------------------------------

    @mocketize
    def test_export_single_log(self):
        Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)
        exporter = OTLPLogExporter(endpoint=_TEST_ENDPOINT)
        logs = [_make_log_record()]
        transport = exporter._client._transport

        with patch.object(
            transport, "request", wraps=transport.request
        ) as mock_request:
            result = exporter.export(logs)

        self.assertEqual(result, LogRecordExportResult.SUCCESS)
        request = Mocket.last_request()
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.path, "/v1/logs")
        sent_data = mock_request.call_args.kwargs["data"]
        self.assertEqual(_decode_body(sent_data), encode_logs(logs))

    @mocketize
    def test_default_endpoint_and_headers(self):
        Entry.single_register(
            Entry.POST, "http://localhost:4318/v1/logs", status=200
        )
        exporter = OTLPLogExporter()

        result = exporter.export([_make_log_record()])

        self.assertEqual(result, LogRecordExportResult.SUCCESS)
        headers = Mocket.last_request().headers
        self.assertEqual(headers["content-type"], "application/x-protobuf")
        self.assertTrue(
            headers["user-agent"].startswith("OTel-OTLP-Exporter-Python/")
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
            ("per_signal_env", {OTEL_EXPORTER_OTLP_LOGS_ENDPOINT: url}, {}),
        )
        for label, env, kwargs in cases:
            with (
                self.subTest(label),
                patch.dict(os.environ, env, clear=True),
                Mocketizer(),
            ):
                Entry.single_register(Entry.POST, url, status=200)
                exporter = OTLPLogExporter(**kwargs)

                result = exporter.export([_make_log_record()])

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

                exporter.export([_make_log_record()])

                headers = Mocket.last_request().headers
                self.assertEqual(headers["x-api-key"], "secret")

    @mocketize
    def test_custom_transport(self):
        Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)
        custom_transport = Urllib3HTTPTransport()

        with patch(
            "opentelemetry.exporter.otlp.proto.http._log_exporter._build_transport"
        ) as mock_build_transport:
            exporter = OTLPLogExporter(
                endpoint=_TEST_ENDPOINT, _transport=custom_transport
            )

        mock_build_transport.assert_not_called()
        self.assertIs(exporter._client._transport, custom_transport)

        result = exporter.export([_make_log_record()])
        self.assertEqual(result, LogRecordExportResult.SUCCESS)

    @mocketize
    def test_certificate_args(self):
        Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)

        with patch(
            "opentelemetry.exporter.otlp.proto.http._log_exporter._build_transport",
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
            session=None,
        )

        result = exporter.export([_make_log_record()])
        self.assertEqual(result, LogRecordExportResult.SUCCESS)

    def test_compression_options(self):
        cases = (
            (Compression.NoCompression, None, lambda data: data),
            (Compression.Gzip, "gzip", gzip.decompress),
            (Compression.Deflate, "deflate", zlib.decompress),
        )
        for compression, expected_encoding, decompress in cases:
            with self.subTest(compression=compression), Mocketizer():
                Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)
                exporter = OTLPLogExporter(
                    endpoint=_TEST_ENDPOINT, compression=compression
                )
                transport = exporter._client._transport
                logs = [_make_log_record()]

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
                self.assertEqual(_decode_body(decompressed), encode_logs(logs))

    # -- retry / backoff ------------------------------------------------------

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

                with _mock_clock(shutdown_event):
                    result = exporter.export([_make_log_record()])

                self.assertEqual(result, LogRecordExportResult.SUCCESS)
                self.assertEqual(len(Mocket.request_list()), 2)

    def test_export_non_retryable_status_codes(self):
        for status_code in (400, 401, 403, 404, 408, 500, 501):
            with self.subTest(status_code=status_code), Mocketizer():
                Entry.single_register(
                    Entry.POST, _TEST_ENDPOINT, status=status_code
                )
                exporter = OTLPLogExporter(endpoint=_TEST_ENDPOINT)

                result = exporter.export([_make_log_record()])

                self.assertEqual(result, LogRecordExportResult.FAILURE)
                self.assertEqual(len(Mocket.request_list()), 1)

    @mocketize
    def test_export_connection_error(self):
        Entry.register(
            Entry.POST,
            _TEST_ENDPOINT,
            urllib3.exceptions.ProtocolError("simulated reset"),
            Response(status=200),
        )
        exporter = OTLPLogExporter(endpoint=_TEST_ENDPOINT, timeout=5.0)

        result = exporter.export([_make_log_record()])

        self.assertEqual(result, LogRecordExportResult.SUCCESS)
        self.assertEqual(len(Mocket.request_list()), 2)

    @mocketize
    def test_shutdown_interrupts_retry_backoff(self):
        Entry.register(
            Entry.POST,
            _TEST_ENDPOINT,
            *[Response(status=503)] * 6,
        )
        exporter = OTLPLogExporter(endpoint=_TEST_ENDPOINT, timeout=1.5)
        thread = threading.Thread(
            target=exporter.export, args=([_make_log_record()],)
        )
        before = time.time()
        thread.start()
        time.sleep(0.05)
        exporter.shutdown()
        thread.join()
        after = time.time()

        self.assertLess(after - before, 0.5)

    # -- self-observability metrics -------------------------------------------

    @mocketize
    def test_exporter_metrics_disabled_by_default(self):
        Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)
        exporter = OTLPLogExporter(
            endpoint=_TEST_ENDPOINT, meter_provider=self.meter_provider
        )

        self.assertEqual(
            exporter.export([_make_log_record()]),
            LogRecordExportResult.SUCCESS,
        )
        self.assertIsNone(self.metric_reader.get_metrics_data())

    @patch.dict(
        "os.environ", {OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED: "true"}
    )
    def test_retry_timeout_records_metrics(self):
        with Mocketizer():
            Entry.register(
                Entry.POST,
                _TEST_ENDPOINT,
                Response(status=503),
                Response(status=503),
            )
            exporter = OTLPLogExporter(
                endpoint=_TEST_ENDPOINT,
                timeout=1.5,
                meter_provider=self.meter_provider,
            )
            shutdown_event = self._mocked_shutdown_event()
            exporter._client._shutdown_event = shutdown_event

            with _mock_clock(shutdown_event):
                result = exporter.export([_make_log_record()])

        self.assertEqual(result, LogRecordExportResult.FAILURE)

        metrics_data = self.metric_reader.get_metrics_data()
        scope_metrics = metrics_data.resource_metrics[0].scope_metrics[0]
        metrics = sorted(scope_metrics.metrics, key=lambda m: m.name)
        self.assertEqual(len(metrics), 3)
        names = [m.name for m in metrics]
        self.assertIn("otel.sdk.exporter.log.exported", names)
        self.assertIn("otel.sdk.exporter.log.inflight", names)
        self.assertIn("otel.sdk.exporter.operation.duration", names)
        duration_metric = next(
            m
            for m in metrics
            if m.name == "otel.sdk.exporter.operation.duration"
        )
        self.assert_standard_metric_attrs(
            duration_metric.data.data_points[0].attributes
        )
        self.assertEqual(
            duration_metric.data.data_points[0].attributes[
                "http.response.status_code"
            ],
            503,
        )

    # -- misc -----------------------------------------------------------------

    @mocketize
    def test_export_after_shutdown(self):
        exporter = OTLPLogExporter(endpoint=_TEST_ENDPOINT)
        exporter.shutdown()

        with self.assertLogs(_LOGGER_NAME, level="WARNING"):
            result = exporter.export([_make_log_record()])

        self.assertEqual(result, LogRecordExportResult.FAILURE)
        self.assertIsNone(Mocket.last_request())

    def test_shutdown_idempotent(self):
        exporter = OTLPLogExporter(endpoint=_TEST_ENDPOINT)
        exporter.shutdown()

        with self.assertLogs(_LOGGER_NAME, level="WARNING"):
            exporter.shutdown()

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
        exporter.export([_make_log_record()])
        self.assertTrue(exporter.force_flush())

    @mocketize
    def test_export_encoding_failure(self):
        exporter = OTLPLogExporter(endpoint=_TEST_ENDPOINT)

        with (
            patch(
                "opentelemetry.exporter.otlp.proto.http._log_exporter.encode_logs",
                side_effect=ValueError("boom"),
            ),
            self.assertLogs(_LOGGER_NAME, level="ERROR"),
        ):
            result = exporter.export([_make_log_record()])

        self.assertEqual(result, LogRecordExportResult.FAILURE)
        self.assertIsNone(Mocket.last_request())


if __name__ == "__main__":
    unittest.main()
