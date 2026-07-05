# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=protected-access,too-many-public-methods

import gzip
import os
import threading
import time
import unittest
import zlib
from datetime import datetime, timezone
from email.utils import format_datetime
from unittest.mock import Mock, patch

import requests
import urllib3.exceptions
from mocket import Mocket, Mocketizer, mocketize
from mocket.mocks.mockhttp import Entry, Response

from opentelemetry.exporter.http.transport._requests import (
    RequestsHTTPTransport,
)
from opentelemetry.exporter.http.transport._urllib3 import (
    Urllib3HTTPTransport,
)
from opentelemetry.exporter.otlp.common import _http
from opentelemetry.exporter.otlp.proto.common.trace_encoder import (
    encode_spans,
)
from opentelemetry.exporter.otlp.proto.http import Compression
from opentelemetry.exporter.otlp.proto.http._common import _build_transport
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    DEFAULT_ENDPOINT,
    DEFAULT_TRACES_EXPORT_PATH,
    OTLPSpanExporter,
)
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)
from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_EXPORTER_OTLP_HTTP_TRACES_CREDENTIAL_PROVIDER,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE,
    OTEL_EXPORTER_OTLP_TRACES_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_TRACES_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_TRACES_ENDPOINT,
    OTEL_EXPORTER_OTLP_TRACES_HEADERS,
    OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    SimpleSpanProcessor,
    SpanExportResult,
)
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from opentelemetry.test.mock_test_classes import IterEntryPoint

from . import _mock_clock

_TEST_ENDPOINT = "http://localhost:4318/v1/traces"
_LOGGER_NAME = "opentelemetry.exporter.otlp.proto.http.trace_exporter"


def _decode_body(body: bytes) -> ExportTraceServiceRequest:
    return ExportTraceServiceRequest.FromString(body)


class TestOTLPSpanExporter(unittest.TestCase):
    def setUp(self):
        env_patcher = patch.dict(os.environ, {}, clear=True)
        env_patcher.start()
        self.addCleanup(env_patcher.stop)

        self._in_memory = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(self._in_memory))
        self._tracer = provider.get_tracer(__name__)

        self.metric_reader = InMemoryMetricReader()
        self.meter_provider = MeterProvider(
            metric_readers=[self.metric_reader]
        )

    def _finished_spans(self):
        return list(self._in_memory.get_finished_spans())

    def _make_span(self, name: str = "test-span"):
        with self._tracer.start_as_current_span(name):
            pass
        return self._finished_spans()

    @staticmethod
    def _mocked_shutdown_event() -> Mock:
        shutdown_event = Mock(spec=threading.Event)
        shutdown_event.is_set.return_value = False
        return shutdown_event

    def assert_standard_metric_attrs(self, attributes):
        self.assertEqual(
            attributes["otel.component.type"], "otlp_http_span_exporter"
        )
        self.assertTrue(
            attributes["otel.component.name"].startswith(
                "otlp_http_span_exporter/"
            )
        )
        self.assertEqual(attributes["server.address"], "localhost")
        self.assertEqual(attributes["server.port"], 4318)

    def test_default_transport_is_urllib3(self):
        exporter = OTLPSpanExporter()

        self.assertEqual(
            exporter._endpoint, DEFAULT_ENDPOINT + DEFAULT_TRACES_EXPORT_PATH
        )
        self.assertIs(exporter._compression, _http.Compression.NONE)
        self.assertIsInstance(
            exporter._client._transport, Urllib3HTTPTransport
        )

    def test_session_uses_requests_transport(self):
        session = requests.Session()
        exporter = OTLPSpanExporter(session=session)

        self.assertIsInstance(
            exporter._client._transport, RequestsHTTPTransport
        )
        self.assertIs(exporter._client._transport._session, session)

    @patch.dict(
        os.environ,
        {
            _OTEL_PYTHON_EXPORTER_OTLP_HTTP_TRACES_CREDENTIAL_PROVIDER: "custom_credential",
        },
    )
    @patch("opentelemetry.exporter.otlp.proto.http._common.entry_points")
    def test_credential_provider_uses_requests(self, mock_entry_point):
        credential = requests.Session()
        mock_entry_point.configure_mock(
            return_value=[
                IterEntryPoint("custom_credential", lambda: credential)
            ]
        )
        exporter = OTLPSpanExporter()

        self.assertIsInstance(
            exporter._client._transport, RequestsHTTPTransport
        )
        self.assertIs(exporter._client._transport._session, credential)

    @patch.dict(
        os.environ,
        {
            _OTEL_PYTHON_EXPORTER_OTLP_HTTP_TRACES_CREDENTIAL_PROVIDER: "bad_credential",
        },
    )
    @patch("opentelemetry.exporter.otlp.proto.http._common.entry_points")
    def test_entrypoint_wrong_type_raises(self, mock_entry_point):
        mock_entry_point.configure_mock(
            return_value=[IterEntryPoint("bad_credential", lambda: 1)]
        )
        with self.assertRaises(RuntimeError):
            OTLPSpanExporter()

    @patch.dict(
        os.environ,
        {
            _OTEL_PYTHON_EXPORTER_OTLP_HTTP_TRACES_CREDENTIAL_PROVIDER: "missing",
        },
    )
    @patch("opentelemetry.exporter.otlp.proto.http._common.entry_points")
    def test_entrypoint_missing_raises(self, mock_entry_point):
        mock_entry_point.configure_mock(return_value=[])
        with self.assertRaises(RuntimeError):
            OTLPSpanExporter()

    def test_compression_dual_enum_acceptance(self):
        cases = (
            (Compression.NoCompression, _http.Compression.NONE),
            (Compression.Deflate, _http.Compression.DEFLATE),
            (Compression.Gzip, _http.Compression.GZIP),
            (_http.Compression.NONE, _http.Compression.NONE),
            (_http.Compression.DEFLATE, _http.Compression.DEFLATE),
            (_http.Compression.GZIP, _http.Compression.GZIP),
        )
        for compression, expected in cases:
            with self.subTest(compression=compression):
                exporter = OTLPSpanExporter(compression=compression)
                self.assertIs(exporter._compression, expected)
                self.assertIs(exporter._client._compression, expected)

    @mocketize
    def test_export_single_span(self):
        Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)
        exporter = OTLPSpanExporter(endpoint=_TEST_ENDPOINT)
        spans = self._make_span("my-span")
        transport = exporter._client._transport

        with patch.object(
            transport, "request", wraps=transport.request
        ) as mock_request:
            result = exporter.export(spans)

        self.assertEqual(result, SpanExportResult.SUCCESS)
        request = Mocket.last_request()
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.path, "/v1/traces")
        sent_data = mock_request.call_args.kwargs["data"]
        self.assertEqual(_decode_body(sent_data), encode_spans(spans))

    @mocketize
    def test_export_spans_different_resources(self):
        Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)
        exporter = OTLPSpanExporter(endpoint=_TEST_ENDPOINT)
        transport = exporter._client._transport
        spans = []
        for name, host in (("from-a", "a"), ("from-b", "b")):
            in_memory = InMemorySpanExporter()
            provider = TracerProvider(resource=Resource({"host": host}))
            provider.add_span_processor(SimpleSpanProcessor(in_memory))
            tracer = provider.get_tracer(__name__)
            with tracer.start_as_current_span(name):
                pass
            spans.extend(in_memory.get_finished_spans())

        with patch.object(
            transport, "request", wraps=transport.request
        ) as mock_request:
            result = exporter.export(spans)

        self.assertEqual(result, SpanExportResult.SUCCESS)
        sent_data = mock_request.call_args.kwargs["data"]
        body = _decode_body(sent_data)
        self.assertEqual(body, encode_spans(spans))
        self.assertEqual(len(body.resource_spans), 2)

    @mocketize
    def test_default_endpoint_and_headers(self):
        Entry.single_register(
            Entry.POST, "http://localhost:4318/v1/traces", status=200
        )
        exporter = OTLPSpanExporter()

        result = exporter.export(self._make_span())

        self.assertEqual(result, SpanExportResult.SUCCESS)
        headers = Mocket.last_request().headers
        self.assertEqual(headers["content-type"], "application/x-protobuf")
        self.assertTrue(
            headers["user-agent"].startswith("OTel-OTLP-Exporter-Python/")
        )

    def test_custom_endpoint(self):
        url = "http://custom.example:9999/v1/traces"
        cases = (
            ("constructor", {}, {"endpoint": url}),
            (
                "generic_env",
                {OTEL_EXPORTER_OTLP_ENDPOINT: "http://custom.example:9999"},
                {},
            ),
            ("per_signal_env", {OTEL_EXPORTER_OTLP_TRACES_ENDPOINT: url}, {}),
        )
        for label, env, kwargs in cases:
            with (
                self.subTest(label),
                patch.dict(os.environ, env, clear=True),
                Mocketizer(),
            ):
                Entry.single_register(Entry.POST, url, status=200)
                exporter = OTLPSpanExporter(**kwargs)
                self._in_memory.clear()

                result = exporter.export(self._make_span())

                self.assertEqual(result, SpanExportResult.SUCCESS)

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
                {OTEL_EXPORTER_OTLP_TRACES_HEADERS: "x-api-key=secret"},
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
                exporter = OTLPSpanExporter(endpoint=_TEST_ENDPOINT, **kwargs)
                self._in_memory.clear()

                exporter.export(self._make_span())

                headers = Mocket.last_request().headers
                self.assertEqual(headers["x-api-key"], "secret")

    @mocketize
    @patch(
        "opentelemetry.exporter.otlp.proto.http.trace_exporter._build_transport"
    )
    def test_custom_transport(self, mock_build_transport):
        Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)
        custom_transport = Urllib3HTTPTransport()

        exporter = OTLPSpanExporter(
            endpoint=_TEST_ENDPOINT, _transport=custom_transport
        )

        mock_build_transport.assert_not_called()
        self.assertIs(exporter._client._transport, custom_transport)

        result = exporter.export(self._make_span())
        self.assertEqual(result, SpanExportResult.SUCCESS)

    @mocketize
    @patch(
        "opentelemetry.exporter.otlp.proto.http.trace_exporter._build_transport",
        wraps=_build_transport,
    )
    def test_certificate_args(self, mock_build_transport):
        Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)

        exporter = OTLPSpanExporter(
            endpoint=_TEST_ENDPOINT,
            certificate_file="ca.pem",
            client_key_file="client-key.pem",
            client_certificate_file="client-cert.pem",
        )

        mock_build_transport.assert_called_once_with(
            "ca.pem",
            "client-key.pem",
            "client-cert.pem",
            OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE,
            OTEL_EXPORTER_OTLP_TRACES_CLIENT_KEY,
            OTEL_EXPORTER_OTLP_TRACES_CLIENT_CERTIFICATE,
            session=None,
        )

        result = exporter.export(self._make_span())
        self.assertEqual(result, SpanExportResult.SUCCESS)

    def test_compression_options(self):
        cases = (
            (Compression.NoCompression, None, lambda data: data),
            (Compression.Gzip, "gzip", gzip.decompress),
            (Compression.Deflate, "deflate", zlib.decompress),
            (_http.Compression.NONE, None, lambda data: data),
            (_http.Compression.GZIP, "gzip", gzip.decompress),
            (_http.Compression.DEFLATE, "deflate", zlib.decompress),
        )
        for compression, expected_encoding, decompress in cases:
            with self.subTest(compression=compression), Mocketizer():
                Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)
                exporter = OTLPSpanExporter(
                    endpoint=_TEST_ENDPOINT, compression=compression
                )
                transport = exporter._client._transport
                self._in_memory.clear()
                spans = self._make_span()

                with patch.object(
                    transport, "request", wraps=transport.request
                ) as mock_request:
                    result = exporter.export(spans)

                self.assertEqual(result, SpanExportResult.SUCCESS)
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
                    _decode_body(decompressed), encode_spans(spans)
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
                exporter = OTLPSpanExporter(
                    endpoint=_TEST_ENDPOINT, timeout=30.0
                )
                shutdown_event = self._mocked_shutdown_event()
                exporter._client._shutdown_event = shutdown_event
                self._in_memory.clear()

                with _mock_clock(shutdown_event):
                    result = exporter.export(self._make_span())

                self.assertEqual(result, SpanExportResult.SUCCESS)
                self.assertEqual(len(Mocket.request_list()), 2)

    def test_export_non_retryable_status_codes(self):
        for status_code in (400, 401, 403, 404, 408, 500, 501):
            with self.subTest(status_code=status_code), Mocketizer():
                Entry.single_register(
                    Entry.POST, _TEST_ENDPOINT, status=status_code
                )
                exporter = OTLPSpanExporter(endpoint=_TEST_ENDPOINT)
                self._in_memory.clear()

                result = exporter.export(self._make_span())

                self.assertEqual(result, SpanExportResult.FAILURE)
                self.assertEqual(len(Mocket.request_list()), 1)

    @mocketize
    def test_export_max_retries(self):
        Entry.register(
            Entry.POST,
            _TEST_ENDPOINT,
            *[Response(status=503)] * 6,
        )
        exporter = OTLPSpanExporter(endpoint=_TEST_ENDPOINT, timeout=1000.0)
        shutdown_event = self._mocked_shutdown_event()
        exporter._client._shutdown_event = shutdown_event

        with _mock_clock(shutdown_event):
            result = exporter.export(self._make_span())

        self.assertEqual(result, SpanExportResult.FAILURE)
        self.assertEqual(len(Mocket.request_list()), 6)

    @mocketize
    def test_export_retry_after_header(self):
        Entry.register(
            Entry.POST,
            _TEST_ENDPOINT,
            Response(status=429, headers={"Retry-After": "5"}),
            Response(status=200),
        )
        exporter = OTLPSpanExporter(endpoint=_TEST_ENDPOINT, timeout=60.0)
        shutdown_event = self._mocked_shutdown_event()
        shutdown_event.wait.return_value = False
        exporter._client._shutdown_event = shutdown_event

        result = exporter.export(self._make_span())

        self.assertEqual(result, SpanExportResult.SUCCESS)
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
        exporter = OTLPSpanExporter(endpoint=_TEST_ENDPOINT, timeout=120.0)
        shutdown_event = self._mocked_shutdown_event()
        shutdown_event.wait.return_value = False
        exporter._client._shutdown_event = shutdown_event

        with patch(
            "opentelemetry.exporter.otlp.common._http.time.time",
            return_value=base,
        ):
            result = exporter.export(self._make_span())

        self.assertEqual(result, SpanExportResult.SUCCESS)
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
        exporter = OTLPSpanExporter(endpoint=_TEST_ENDPOINT, timeout=5.0)

        result = exporter.export(self._make_span())

        self.assertEqual(result, SpanExportResult.SUCCESS)
        self.assertEqual(len(Mocket.request_list()), 2)

    @mocketize
    def test_shutdown_interrupts_retry_backoff(self):
        Entry.register(
            Entry.POST,
            _TEST_ENDPOINT,
            *[Response(status=503)] * 6,
        )
        exporter = OTLPSpanExporter(endpoint=_TEST_ENDPOINT, timeout=1.5)
        thread = threading.Thread(
            target=exporter.export, args=(self._make_span(),)
        )
        before = time.time()
        thread.start()
        time.sleep(0.05)
        exporter.shutdown()
        thread.join()
        after = time.time()

        self.assertLess(after - before, 0.5)

    @mocketize
    def test_exporter_metrics_disabled_by_default(self):
        Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)
        exporter = OTLPSpanExporter(
            endpoint=_TEST_ENDPOINT, meter_provider=self.meter_provider
        )

        self.assertEqual(
            exporter.export(self._make_span()), SpanExportResult.SUCCESS
        )
        self.assertIsNone(self.metric_reader.get_metrics_data())

    @patch.dict(
        "os.environ", {OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED: " true "}
    )
    def test_retry_timeout_records_metrics(self):
        with Mocketizer():
            Entry.register(
                Entry.POST,
                _TEST_ENDPOINT,
                Response(status=503),
                Response(status=503),
            )
            exporter = OTLPSpanExporter(
                endpoint=_TEST_ENDPOINT,
                timeout=1.5,
                meter_provider=self.meter_provider,
            )
            shutdown_event = self._mocked_shutdown_event()
            exporter._client._shutdown_event = shutdown_event

            with _mock_clock(shutdown_event):
                result = exporter.export(self._make_span())

        self.assertEqual(result, SpanExportResult.FAILURE)

        metrics_data = self.metric_reader.get_metrics_data()
        scope_metrics = metrics_data.resource_metrics[0].scope_metrics[0]
        metrics = sorted(scope_metrics.metrics, key=lambda m: m.name)
        self.assertEqual(len(metrics), 3)
        self.assertEqual(
            metrics[0].name, "otel.sdk.exporter.operation.duration"
        )
        self.assert_standard_metric_attrs(
            metrics[0].data.data_points[0].attributes
        )
        self.assertEqual(
            metrics[0]
            .data.data_points[0]
            .attributes["http.response.status_code"],
            503,
        )
        self.assertEqual(metrics[1].name, "otel.sdk.exporter.span.exported")
        self.assertEqual(metrics[2].name, "otel.sdk.exporter.span.inflight")

    @patch.dict(
        "os.environ", {OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED: "true"}
    )
    @mocketize
    def test_export_connection_error_records_metrics(self):
        Entry.register(
            Entry.POST,
            _TEST_ENDPOINT,
            *([urllib3.exceptions.ProtocolError("boom")] * 6),
        )
        exporter = OTLPSpanExporter(
            endpoint=_TEST_ENDPOINT,
            timeout=1000.0,
            meter_provider=self.meter_provider,
        )
        shutdown_event = self._mocked_shutdown_event()
        exporter._client._shutdown_event = shutdown_event

        with _mock_clock(shutdown_event):
            result = exporter.export(self._make_span())

        self.assertEqual(result, SpanExportResult.FAILURE)

        metrics_data = self.metric_reader.get_metrics_data()
        scope_metrics = metrics_data.resource_metrics[0].scope_metrics[0]
        metrics = sorted(scope_metrics.metrics, key=lambda m: m.name)
        self.assertEqual(
            metrics[0].name, "otel.sdk.exporter.operation.duration"
        )
        self.assertIn("error.type", metrics[0].data.data_points[0].attributes)
        self.assertNotIn(
            "http.response.status_code",
            metrics[0].data.data_points[0].attributes,
        )

    @mocketize
    def test_export_after_shutdown(self):
        exporter = OTLPSpanExporter(endpoint=_TEST_ENDPOINT)
        exporter.shutdown()

        with self.assertLogs(_LOGGER_NAME, level="WARNING"):
            result = exporter.export(self._make_span())

        self.assertEqual(result, SpanExportResult.FAILURE)
        self.assertIsNone(Mocket.last_request())

    def test_shutdown_idempotent(self):
        exporter = OTLPSpanExporter(endpoint=_TEST_ENDPOINT)
        exporter.shutdown()

        with self.assertLogs(_LOGGER_NAME, level="WARNING"):
            exporter.shutdown()

    def test_shutdown_closes_transport(self):
        exporter = OTLPSpanExporter(endpoint=_TEST_ENDPOINT)

        with patch.object(exporter._client._transport, "close") as mock_close:
            exporter.shutdown()

        mock_close.assert_called_once()

    @mocketize
    def test_force_flush(self):
        Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)
        exporter = OTLPSpanExporter(endpoint=_TEST_ENDPOINT)

        self.assertTrue(exporter.force_flush())
        exporter.export(self._make_span())
        self.assertTrue(exporter.force_flush())

    @mocketize
    @patch(
        "opentelemetry.exporter.otlp.proto.http.trace_exporter.encode_spans",
        side_effect=ValueError("boom"),
    )
    def test_export_encoding_failure(self, mock_encode_spans):
        exporter = OTLPSpanExporter(endpoint=_TEST_ENDPOINT)

        with self.assertLogs(_LOGGER_NAME, level="ERROR"):
            result = exporter.export(self._make_span())

        self.assertEqual(result, SpanExportResult.FAILURE)
        self.assertIsNone(Mocket.last_request())
