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

from opentelemetry.attributes import BoundedAttributes
from opentelemetry.exporter.http.transport._urllib3 import (
    Urllib3HTTPTransport,
)
from opentelemetry.exporter.otlp.common.http import Compression
from opentelemetry.exporter.otlp.json.common._internal.metrics_encoder import (
    split_metrics_data,
)
from opentelemetry.exporter.otlp.json.common.metrics_encoder import (
    encode_metrics,
)
from opentelemetry.exporter.otlp.json.http._internal import _build_transport
from opentelemetry.exporter.otlp.json.http.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE,
    OTEL_EXPORTER_OTLP_METRICS_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_METRICS_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_METRICS_ENDPOINT,
    OTEL_EXPORTER_OTLP_METRICS_HEADERS,
    OTEL_EXPORTER_OTLP_METRICS_TIMEOUT,
    OTEL_EXPORTER_OTLP_TIMEOUT,
)
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    Metric,
    MetricExportResult,
    MetricsData,
    NumberDataPoint,
    ResourceMetrics,
    ScopeMetrics,
    Sum,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.test.metrictestutil import (
    _generate_gauge,
    _generate_histogram,
    _generate_sum,
)

from . import _mock_clock

_TEST_ENDPOINT = "http://localhost:4318/v1/metrics"
_LOGGER_NAME = "opentelemetry.exporter.otlp.json.http.metric_exporter"


def _make_metrics_data(
    metric: Metric | None = None,
    resource_attrs: dict | None = None,
) -> MetricsData:
    return MetricsData(
        resource_metrics=[
            ResourceMetrics(
                resource=Resource(resource_attrs or {"service.name": "test"}),
                scope_metrics=[
                    ScopeMetrics(
                        scope=InstrumentationScope("test-scope", "1.0"),
                        metrics=[metric or _generate_sum("requests", 42)],
                        schema_url="",
                    )
                ],
                schema_url="",
            )
        ]
    )


class TestOTLPMetricExporter(unittest.TestCase):
    def setUp(self):
        env_patcher = patch.dict(os.environ, {}, clear=True)
        env_patcher.start()
        self.addCleanup(env_patcher.stop)

    @staticmethod
    def _mocked_shutdown_event() -> Mock:
        shutdown_event = Mock(spec=threading.Event)
        shutdown_event.is_set.return_value = False
        return shutdown_event

    @mocketize
    def test_export_single_metric(self):
        Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)
        exporter = OTLPMetricExporter(endpoint=_TEST_ENDPOINT)
        metrics_data = _make_metrics_data()

        result = exporter.export(metrics_data)

        self.assertEqual(result, MetricExportResult.SUCCESS)
        request = Mocket.last_request()
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.path, "/v1/metrics")
        self.assertEqual(
            json.loads(request.body), encode_metrics(metrics_data).to_dict()
        )

    @mocketize
    def test_export_multiple_metrics_same_resource(self):
        Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)
        exporter = OTLPMetricExporter(endpoint=_TEST_ENDPOINT)
        metrics_data = MetricsData(
            resource_metrics=[
                ResourceMetrics(
                    resource=Resource({"service.name": "test"}),
                    scope_metrics=[
                        ScopeMetrics(
                            scope=InstrumentationScope("test-scope", "1.0"),
                            metrics=[
                                _generate_sum("counter", 1),
                                _generate_gauge("gauge", 2),
                            ],
                            schema_url="",
                        )
                    ],
                    schema_url="",
                )
            ]
        )

        result = exporter.export(metrics_data)

        self.assertEqual(result, MetricExportResult.SUCCESS)
        self.assertEqual(len(Mocket.request_list()), 1)
        body = json.loads(Mocket.last_request().body)
        self.assertEqual(body, encode_metrics(metrics_data).to_dict())
        total_metrics = sum(
            len(sm["metrics"])
            for rm in body["resourceMetrics"]
            for sm in rm["scopeMetrics"]
        )
        self.assertEqual(total_metrics, 2)

    @mocketize
    def test_export_metrics_different_resources(self):
        Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)
        exporter = OTLPMetricExporter(endpoint=_TEST_ENDPOINT)
        metrics_data = MetricsData(
            resource_metrics=[
                ResourceMetrics(
                    resource=Resource({"host": "a"}),
                    scope_metrics=[
                        ScopeMetrics(
                            scope=InstrumentationScope("test-scope", "1.0"),
                            metrics=[_generate_sum("from-a", 1)],
                            schema_url="",
                        )
                    ],
                    schema_url="",
                ),
                ResourceMetrics(
                    resource=Resource({"host": "b"}),
                    scope_metrics=[
                        ScopeMetrics(
                            scope=InstrumentationScope("test-scope", "1.0"),
                            metrics=[_generate_sum("from-b", 1)],
                            schema_url="",
                        )
                    ],
                    schema_url="",
                ),
            ]
        )

        result = exporter.export(metrics_data)

        self.assertEqual(result, MetricExportResult.SUCCESS)
        body = json.loads(Mocket.last_request().body)
        self.assertEqual(body, encode_metrics(metrics_data).to_dict())
        self.assertEqual(len(body["resourceMetrics"]), 2)

    @mocketize
    def test_export_rich_metrics(self):
        Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)
        exporter = OTLPMetricExporter(endpoint=_TEST_ENDPOINT)
        metrics_data = _make_metrics_data(
            _generate_histogram(
                "req.duration",
                attributes=BoundedAttributes(
                    attributes={
                        "http.method": "GET",
                        "http.status_code": 200,
                    }
                ),
            )
        )

        result = exporter.export(metrics_data)

        self.assertEqual(result, MetricExportResult.SUCCESS)
        body = json.loads(Mocket.last_request().body)
        self.assertEqual(body, encode_metrics(metrics_data).to_dict())

    @mocketize
    def test_export_empty_metrics_data(self):
        Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)
        exporter = OTLPMetricExporter(endpoint=_TEST_ENDPOINT)
        metrics_data = MetricsData(resource_metrics=[])

        result = exporter.export(metrics_data)

        self.assertEqual(result, MetricExportResult.SUCCESS)
        body = json.loads(Mocket.last_request().body)
        self.assertEqual(body, encode_metrics(metrics_data).to_dict())

    @mocketize
    def test_default_endpoint_and_headers(self):
        Entry.single_register(
            Entry.POST, "http://localhost:4318/v1/metrics", status=200
        )
        exporter = OTLPMetricExporter()

        result = exporter.export(_make_metrics_data())

        self.assertEqual(result, MetricExportResult.SUCCESS)
        headers = Mocket.last_request().headers
        self.assertEqual(headers["content-type"], "application/json")
        self.assertTrue(
            headers["user-agent"].startswith("OTel-OTLP-JSON-Exporter-Python/")
        )

    def test_custom_endpoint(self):
        url = "http://custom.example:9999/v1/metrics"
        cases = (
            ("constructor", {}, {"endpoint": url}),
            (
                "generic_env",
                {OTEL_EXPORTER_OTLP_ENDPOINT: "http://custom.example:9999"},
                {},
            ),
            (
                "per_signal_env",
                {OTEL_EXPORTER_OTLP_METRICS_ENDPOINT: url},
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
                exporter = OTLPMetricExporter(**kwargs)

                result = exporter.export(_make_metrics_data())

                self.assertEqual(result, MetricExportResult.SUCCESS)

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
                {OTEL_EXPORTER_OTLP_METRICS_HEADERS: "x-api-key=secret"},
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
                exporter = OTLPMetricExporter(
                    endpoint=_TEST_ENDPOINT, **kwargs
                )

                exporter.export(_make_metrics_data())

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
            "opentelemetry.exporter.otlp.json.http.metric_exporter._build_transport"
        ) as mock_build_transport:
            exporter = OTLPMetricExporter(
                endpoint=_TEST_ENDPOINT, _transport=custom_transport
            )

        mock_build_transport.assert_not_called()
        self.assertIs(exporter._client._transport, custom_transport)

        result = exporter.export(_make_metrics_data())

        self.assertEqual(result, MetricExportResult.SUCCESS)
        self.assertEqual(len(Mocket.request_list()), 1)

    def test_custom_timeout(self):
        cases = (
            ("constructor", {}, {"timeout": 7.5}),
            ("generic_env", {OTEL_EXPORTER_OTLP_TIMEOUT: "7.5"}, {}),
            (
                "per_signal_env",
                {OTEL_EXPORTER_OTLP_METRICS_TIMEOUT: "7.5"},
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
                exporter = OTLPMetricExporter(
                    endpoint=_TEST_ENDPOINT, **kwargs
                )

                with patch.object(
                    exporter._client._transport,
                    "request",
                    wraps=exporter._client._transport.request,
                ) as mock_request:
                    result = exporter.export(_make_metrics_data())

                self.assertEqual(result, MetricExportResult.SUCCESS)
                self.assertAlmostEqual(
                    mock_request.call_args.kwargs["timeout"], 7.5, delta=0.5
                )

    @mocketize
    def test_certificate_args(self):
        Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)

        with patch(
            "opentelemetry.exporter.otlp.json.http.metric_exporter._build_transport",
            wraps=_build_transport,
        ) as mock_build_transport:
            exporter = OTLPMetricExporter(
                endpoint=_TEST_ENDPOINT,
                certificate_file="ca.pem",
                client_key_file="client-key.pem",
                client_certificate_file="client-cert.pem",
            )

        mock_build_transport.assert_called_once_with(
            "ca.pem",
            "client-key.pem",
            "client-cert.pem",
            OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE,
            OTEL_EXPORTER_OTLP_METRICS_CLIENT_KEY,
            OTEL_EXPORTER_OTLP_METRICS_CLIENT_CERTIFICATE,
        )

        result = exporter.export(_make_metrics_data())

        self.assertEqual(result, MetricExportResult.SUCCESS)

    def test_compression_options(self):
        cases = (
            (Compression.NONE, None, lambda data: data),
            (Compression.GZIP, "gzip", gzip.decompress),
            (Compression.DEFLATE, "deflate", zlib.decompress),
        )
        for compression, expected_encoding, decompress in cases:
            with self.subTest(compression=compression), Mocketizer():
                Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)
                exporter = OTLPMetricExporter(
                    endpoint=_TEST_ENDPOINT, compression=compression
                )
                transport = exporter._client._transport
                metrics_data = _make_metrics_data()

                with patch.object(
                    transport, "request", wraps=transport.request
                ) as mock_request:
                    result = exporter.export(metrics_data)

                self.assertEqual(result, MetricExportResult.SUCCESS)
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
                    json.loads(decompressed),
                    encode_metrics(metrics_data).to_dict(),
                )

    @mocketize
    def test_export_batch_splitting(self):
        Entry.register(
            Entry.POST,
            _TEST_ENDPOINT,
            Response(status=200),
            Response(status=200),
            Response(status=200),
        )
        exporter = OTLPMetricExporter(
            endpoint=_TEST_ENDPOINT, max_export_batch_size=2
        )
        data_points = [
            NumberDataPoint(
                attributes=BoundedAttributes(attributes={"i": i}),
                start_time_unix_nano=1641946015139533244,
                time_unix_nano=1641946016139533244,
                value=i,
            )
            for i in range(5)
        ]
        metric = Metric(
            name="requests",
            description="foo",
            unit="s",
            data=Sum(
                data_points=data_points,
                aggregation_temporality=AggregationTemporality.CUMULATIVE,
                is_monotonic=True,
            ),
        )
        metrics_data = _make_metrics_data(metric)
        expected_batches = [
            batch.to_dict()
            for batch in split_metrics_data(encode_metrics(metrics_data), 2)
        ]

        result = exporter.export(metrics_data)

        self.assertEqual(result, MetricExportResult.SUCCESS)
        requests = Mocket.request_list()
        self.assertEqual(len(requests), len(expected_batches))
        self.assertEqual(
            [json.loads(request.body) for request in requests],
            expected_batches,
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
                exporter = OTLPMetricExporter(
                    endpoint=_TEST_ENDPOINT, timeout=30.0
                )
                shutdown_event = self._mocked_shutdown_event()
                exporter._client._shutdown_event = shutdown_event

                with _mock_clock(shutdown_event):
                    result = exporter.export(_make_metrics_data())

                self.assertEqual(result, MetricExportResult.SUCCESS)
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
                exporter = OTLPMetricExporter(endpoint=_TEST_ENDPOINT)

                result = exporter.export(_make_metrics_data())

                self.assertEqual(result, MetricExportResult.FAILURE)
                self.assertEqual(len(Mocket.request_list()), 1)

    @mocketize
    def test_export_max_retries(self):
        Entry.register(
            Entry.POST,
            _TEST_ENDPOINT,
            *[Response(status=503)] * 6,
        )
        exporter = OTLPMetricExporter(endpoint=_TEST_ENDPOINT, timeout=1000.0)
        shutdown_event = self._mocked_shutdown_event()
        exporter._client._shutdown_event = shutdown_event

        with _mock_clock(shutdown_event):
            result = exporter.export(_make_metrics_data())

        self.assertEqual(result, MetricExportResult.FAILURE)
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
        exporter = OTLPMetricExporter(endpoint=_TEST_ENDPOINT, timeout=60.0)
        shutdown_event = self._mocked_shutdown_event()
        shutdown_event.wait.return_value = False
        exporter._client._shutdown_event = shutdown_event

        result = exporter.export(_make_metrics_data())

        self.assertEqual(result, MetricExportResult.SUCCESS)
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
        exporter = OTLPMetricExporter(endpoint=_TEST_ENDPOINT, timeout=120.0)
        shutdown_event = self._mocked_shutdown_event()
        shutdown_event.wait.return_value = False
        exporter._client._shutdown_event = shutdown_event

        with patch(
            "opentelemetry.exporter.otlp.common.http.time.time",
            return_value=base,
        ):
            result = exporter.export(_make_metrics_data())

        self.assertEqual(result, MetricExportResult.SUCCESS)
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
        exporter = OTLPMetricExporter(endpoint=_TEST_ENDPOINT, timeout=5.0)

        result = exporter.export(_make_metrics_data())

        self.assertEqual(result, MetricExportResult.SUCCESS)
        self.assertEqual(len(Mocket.request_list()), 2)

    @mocketize
    def test_export_after_shutdown(self):
        exporter = OTLPMetricExporter(endpoint=_TEST_ENDPOINT)
        exporter.shutdown()

        with self.assertLogs(_LOGGER_NAME, level="WARNING"):
            result = exporter.export(_make_metrics_data())

        self.assertEqual(result, MetricExportResult.FAILURE)
        self.assertIsNone(Mocket.last_request())

    def test_shutdown_idempotent(self):
        exporter = OTLPMetricExporter(endpoint=_TEST_ENDPOINT)
        exporter.shutdown()

        with self.assertLogs(_LOGGER_NAME, level="WARNING"):
            exporter.shutdown()

    # pylint: disable-next=no-self-use
    def test_shutdown_closes_transport(self):
        exporter = OTLPMetricExporter(endpoint=_TEST_ENDPOINT)

        with patch.object(exporter._client._transport, "close") as mock_close:
            exporter.shutdown()

        mock_close.assert_called_once()

    @mocketize
    def test_force_flush(self):
        Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)
        exporter = OTLPMetricExporter(endpoint=_TEST_ENDPOINT)

        self.assertTrue(exporter.force_flush())
        exporter.export(_make_metrics_data())
        self.assertTrue(exporter.force_flush())

    @mocketize
    def test_export_encoding_failure(self):
        exporter = OTLPMetricExporter(endpoint=_TEST_ENDPOINT)

        with (
            patch(
                "opentelemetry.exporter.otlp.json.http.metric_exporter.encode_metrics",
                side_effect=ValueError("boom"),
            ),
            self.assertLogs(_LOGGER_NAME, level="ERROR"),
        ):
            result = exporter.export(_make_metrics_data())

        self.assertEqual(result, MetricExportResult.FAILURE)
        self.assertIsNone(Mocket.last_request())
