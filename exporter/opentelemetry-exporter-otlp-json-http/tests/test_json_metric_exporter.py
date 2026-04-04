# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint: disable=too-many-public-methods

from __future__ import annotations

import unittest
from logging import WARNING
from unittest.mock import patch

import urllib3

from opentelemetry.exporter.otlp.json.http import Compression
from opentelemetry.exporter.otlp.json.http._internal import (
    _DEFAULT_ENDPOINT,
    _DEFAULT_TIMEOUT,
)
from opentelemetry.exporter.otlp.json.http.metric_exporter import (
    DEFAULT_METRICS_EXPORT_PATH,
    OTLPMetricExporter,
)
from opentelemetry.exporter.otlp.json.http.version import __version__
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE,
    OTEL_EXPORTER_OTLP_METRICS_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_METRICS_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_METRICS_COMPRESSION,
    OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION,
    OTEL_EXPORTER_OTLP_METRICS_ENDPOINT,
    OTEL_EXPORTER_OTLP_METRICS_HEADERS,
    OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE,
    OTEL_EXPORTER_OTLP_METRICS_TIMEOUT,
    OTEL_EXPORTER_OTLP_TIMEOUT,
)
from opentelemetry.sdk.metrics import (
    Counter,
    Histogram,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    MetricExportResult,
    MetricsData,
    ResourceMetrics,
    ScopeMetrics,
)
from opentelemetry.sdk.metrics.view import (
    ExplicitBucketHistogramAggregation,
    ExponentialBucketHistogramAggregation,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.test.metrictestutil import _generate_sum

from .helpers import CountdownEvent, _build_mock_response, mock_clock

_DEFAULT_METRICS_ENDPOINT = (
    _DEFAULT_ENDPOINT.rstrip("/") + "/" + DEFAULT_METRICS_EXPORT_PATH
)

_SCOPE = InstrumentationScope("test")
_RESOURCE = Resource.create({})


def _build_metrics_data(num_data_points: int = 1) -> MetricsData:
    """Create a minimal MetricsData with a single Sum metric."""
    return MetricsData(
        resource_metrics=[
            ResourceMetrics(
                resource=_RESOURCE,
                scope_metrics=[
                    ScopeMetrics(
                        scope=_SCOPE,
                        metrics=[
                            _generate_sum("test_sum", i)
                            for i in range(num_data_points)
                        ],
                        schema_url="",
                    )
                ],
                schema_url="",
            )
        ]
    )


# pylint: disable=protected-access
class TestOTLPMetricExporter(unittest.TestCase):
    def test_constructor_default(self):
        exporter = OTLPMetricExporter()

        self.assertEqual(exporter._client._endpoint, _DEFAULT_METRICS_ENDPOINT)
        self.assertIsNone(exporter._certificate_file)
        self.assertIsNone(exporter._client_key_file)
        self.assertIsNone(exporter._client_certificate_file)
        self.assertEqual(exporter._client._timeout, _DEFAULT_TIMEOUT)
        self.assertIs(
            exporter._client._compression, Compression.NO_COMPRESSION
        )
        self.assertEqual(
            exporter._client._headers.get("Content-Type"), "application/json"
        )
        self.assertEqual(
            exporter._client._headers.get("User-Agent"),
            "OTel-OTLP-JSON-Exporter-Python/" + __version__,
        )

    @patch.dict(
        "os.environ",
        {
            OTEL_EXPORTER_OTLP_CERTIFICATE: "os/env/base.crt",
            OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE: "os/env/client-cert.pem",
            OTEL_EXPORTER_OTLP_CLIENT_KEY: "os/env/client-key.pem",
            OTEL_EXPORTER_OTLP_COMPRESSION: Compression.GZIP.value,
            OTEL_EXPORTER_OTLP_ENDPOINT: "http://os.env.base",
            OTEL_EXPORTER_OTLP_HEADERS: "envHeader1=val1,envHeader2=val2",
            OTEL_EXPORTER_OTLP_TIMEOUT: "30",
            OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE: "metrics/certificate.env",
            OTEL_EXPORTER_OTLP_METRICS_CLIENT_CERTIFICATE: "metrics/client-cert.pem",
            OTEL_EXPORTER_OTLP_METRICS_CLIENT_KEY: "metrics/client-key.pem",
            OTEL_EXPORTER_OTLP_METRICS_COMPRESSION: Compression.DEFLATE.value,
            OTEL_EXPORTER_OTLP_METRICS_ENDPOINT: "https://metrics.endpoint.env",
            OTEL_EXPORTER_OTLP_METRICS_HEADERS: "metricsEnv1=val1,metricsEnv2=val2",
            OTEL_EXPORTER_OTLP_METRICS_TIMEOUT: "40",
        },
    )
    def test_metrics_env_take_priority(self):
        exporter = OTLPMetricExporter()

        self.assertEqual(
            exporter._client._endpoint, "https://metrics.endpoint.env"
        )
        self.assertEqual(exporter._certificate_file, "metrics/certificate.env")
        self.assertEqual(
            exporter._client_certificate_file, "metrics/client-cert.pem"
        )
        self.assertEqual(exporter._client_key_file, "metrics/client-key.pem")
        self.assertEqual(exporter._client._timeout, 40)
        self.assertIs(exporter._client._compression, Compression.DEFLATE)
        self.assertEqual(exporter._client._headers.get("metricsenv1"), "val1")
        self.assertEqual(exporter._client._headers.get("metricsenv2"), "val2")
        self.assertNotIn("envheader1", exporter._client._headers)

    @patch.dict(
        "os.environ",
        {
            OTEL_EXPORTER_OTLP_ENDPOINT: "http://os.env.base",
            OTEL_EXPORTER_OTLP_TIMEOUT: "30",
            OTEL_EXPORTER_OTLP_METRICS_ENDPOINT: "https://metrics.endpoint.env",
        },
    )
    def test_constructor_args_take_priority(self):
        exporter = OTLPMetricExporter(
            endpoint="https://custom.endpoint/metrics",
            certificate_file="path/to/service.crt",
            client_key_file="path/to/client-key.pem",
            client_certificate_file="path/to/client-cert.pem",
            timeout=20,
            compression=Compression.NO_COMPRESSION,
        )

        self.assertEqual(
            exporter._client._endpoint, "https://custom.endpoint/metrics"
        )
        self.assertEqual(exporter._certificate_file, "path/to/service.crt")
        self.assertEqual(
            exporter._client_certificate_file, "path/to/client-cert.pem"
        )
        self.assertEqual(exporter._client_key_file, "path/to/client-key.pem")
        self.assertEqual(exporter._client._timeout, 20)
        self.assertIs(
            exporter._client._compression, Compression.NO_COMPRESSION
        )

    def test_endpoint_env_slash_normalization(self):
        for endpoint in ("http://os.env.base", "http://os.env.base/"):
            with self.subTest(endpoint=endpoint):
                with patch.dict(
                    "os.environ",
                    {OTEL_EXPORTER_OTLP_ENDPOINT: endpoint},
                ):
                    exporter = OTLPMetricExporter()
                    self.assertEqual(
                        exporter._client._endpoint,
                        f"http://os.env.base/{DEFAULT_METRICS_EXPORT_PATH}",
                    )

    @patch.dict(
        "os.environ",
        {OTEL_EXPORTER_OTLP_HEADERS: "envHeader1=val1,missingValue"},
    )
    def test_headers_parse_from_env(self):
        with self.assertLogs(level=WARNING):
            OTLPMetricExporter()

    def test_temporality_default_cumulative(self):
        exporter = OTLPMetricExporter()
        for instrument_class in (
            Counter,
            UpDownCounter,
            Histogram,
            ObservableCounter,
            ObservableUpDownCounter,
            ObservableGauge,
        ):
            with self.subTest(instrument_class=instrument_class.__name__):
                self.assertEqual(
                    exporter._preferred_temporality[instrument_class],
                    AggregationTemporality.CUMULATIVE,
                )

    @patch.dict(
        "os.environ",
        {OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE: "DELTA"},
    )
    def test_temporality_delta(self):
        exporter = OTLPMetricExporter()
        cases = [
            (Counter, AggregationTemporality.DELTA),
            (UpDownCounter, AggregationTemporality.CUMULATIVE),
            (Histogram, AggregationTemporality.DELTA),
            (ObservableCounter, AggregationTemporality.DELTA),
            (ObservableUpDownCounter, AggregationTemporality.CUMULATIVE),
            (ObservableGauge, AggregationTemporality.CUMULATIVE),
        ]
        for instrument_class, expected in cases:
            with self.subTest(instrument_class=instrument_class.__name__):
                self.assertEqual(
                    exporter._preferred_temporality[instrument_class], expected
                )

    @patch.dict(
        "os.environ",
        {OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE: "LOWMEMORY"},
    )
    def test_temporality_lowmemory(self):
        exporter = OTLPMetricExporter()
        cases = [
            (Counter, AggregationTemporality.DELTA),
            (UpDownCounter, AggregationTemporality.CUMULATIVE),
            (Histogram, AggregationTemporality.DELTA),
            (ObservableCounter, AggregationTemporality.CUMULATIVE),
            (ObservableUpDownCounter, AggregationTemporality.CUMULATIVE),
            (ObservableGauge, AggregationTemporality.CUMULATIVE),
        ]
        for instrument_class, expected in cases:
            with self.subTest(instrument_class=instrument_class.__name__):
                self.assertEqual(
                    exporter._preferred_temporality[instrument_class], expected
                )

    def test_temporality_constructor_override(self):
        exporter = OTLPMetricExporter(
            preferred_temporality={Counter: AggregationTemporality.DELTA}
        )
        self.assertEqual(
            exporter._preferred_temporality[Counter],
            AggregationTemporality.DELTA,
        )

    def test_aggregation_default_explicit_bucket(self):
        exporter = OTLPMetricExporter()
        self.assertIsInstance(
            exporter._preferred_aggregation[Histogram],
            ExplicitBucketHistogramAggregation,
        )

    @patch.dict(
        "os.environ",
        {
            OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION: "base2_exponential_bucket_histogram"
        },
    )
    def test_aggregation_exponential_bucket(self):
        exporter = OTLPMetricExporter()
        self.assertIsInstance(
            exporter._preferred_aggregation[Histogram],
            ExponentialBucketHistogramAggregation,
        )

    @patch.object(urllib3.PoolManager, "request")
    def test_2xx_status_code(self, mock_request):
        mock_request.return_value = _build_mock_response(200)
        metrics_data = _build_metrics_data()
        result = OTLPMetricExporter().export(metrics_data)
        self.assertEqual(result, MetricExportResult.SUCCESS)

    @patch.object(urllib3.PoolManager, "request")
    def test_retry_timeout(self, mock_request):
        exporter = OTLPMetricExporter(timeout=1.5)
        exporter._client._jitter = 0
        mock_request.return_value = _build_mock_response(503)
        metrics_data = _build_metrics_data()

        with mock_clock() as now, self.assertLogs(level=WARNING) as warning:
            result = exporter.export(metrics_data)

        self.assertEqual(result, MetricExportResult.FAILURE)
        self.assertEqual(mock_request.call_count, 2)
        self.assertEqual(now(), 1.0)
        self.assertIn("Transient error", warning.records[0].message)

    @patch.object(urllib3.PoolManager, "request")
    def test_export_retryable_timeout_error(self, mock_request):
        exporter = OTLPMetricExporter(timeout=1.5)
        exporter._client._jitter = 0
        mock_request.side_effect = urllib3.exceptions.TimeoutError()
        metrics_data = _build_metrics_data()

        with mock_clock() as now, self.assertLogs(level=WARNING):
            result = exporter.export(metrics_data)

        self.assertEqual(result, MetricExportResult.FAILURE)
        self.assertEqual(mock_request.call_count, 2)
        self.assertEqual(now(), 1.0)

    @patch.object(urllib3.PoolManager, "request")
    def test_shutdown_interrupts_retry_backoff(self, mock_request):
        exporter = OTLPMetricExporter(timeout=100.0)
        exporter._client._jitter = 0
        exporter._client._shutdown_in_progress = CountdownEvent(
            trigger_after=2
        )
        mock_request.return_value = _build_mock_response(503)
        metrics_data = _build_metrics_data()

        with mock_clock(), self.assertLogs(level=WARNING):
            result = exporter.export(metrics_data)

        self.assertEqual(result, MetricExportResult.FAILURE)
        self.assertEqual(mock_request.call_count, 2)

    def test_force_flush(self):
        self.assertTrue(OTLPMetricExporter().force_flush())

    @patch.object(urllib3.PoolManager, "request")
    def test_export_with_max_batch_size(self, mock_request):
        mock_request.return_value = _build_mock_response(200)
        # 5 metrics (each with 1 data point), batch size 2 -> 3 export calls
        metrics_data = _build_metrics_data(5)
        exporter = OTLPMetricExporter(max_export_batch_size=2)
        result = exporter.export(metrics_data)
        self.assertEqual(result, MetricExportResult.SUCCESS)
        self.assertEqual(mock_request.call_count, 3)

    @patch.object(urllib3.PoolManager, "request")
    def test_export_with_max_batch_size_failure_stops_early(
        self, mock_request
    ):
        # First batch succeeds, second fails
        mock_request.side_effect = [
            _build_mock_response(200),
            _build_mock_response(400),
        ]
        metrics_data = _build_metrics_data(4)
        exporter = OTLPMetricExporter(max_export_batch_size=2)
        with self.assertLogs(level=WARNING):
            result = exporter.export(metrics_data)
        self.assertEqual(result, MetricExportResult.FAILURE)
