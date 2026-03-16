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

import logging
import os
from typing import Optional

from opentelemetry.exporter.otlp.json.common._internal.metrics_encoder import (
    encode_metrics,
)
from opentelemetry.exporter.otlp.json.http import Compression
from opentelemetry.exporter.otlp.json.http._internal import (
    _OTLPHttpClient,
    _resolve_compression,
    _resolve_endpoint,
    _resolve_headers,
    _resolve_timeout,
    _resolve_tls_file,
    _DEFAULT_JITTER,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE,
    OTEL_EXPORTER_OTLP_METRICS_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_METRICS_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_METRICS_COMPRESSION,
    OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION,
    OTEL_EXPORTER_OTLP_METRICS_ENDPOINT,
    OTEL_EXPORTER_OTLP_METRICS_HEADERS,
    OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE,
    OTEL_EXPORTER_OTLP_METRICS_TIMEOUT,
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
    MetricExporter,
    MetricExportResult,
    MetricsData,
)
from opentelemetry.sdk.metrics.view import (
    Aggregation,
    ExplicitBucketHistogramAggregation,
    ExponentialBucketHistogramAggregation,
)

_logger = logging.getLogger(__name__)


class OTLPJSONMetricExporter(MetricExporter):
    """OTLP JSON exporter for metrics using urllib3."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        certificate_file: Optional[str] = None,
        client_key_file: Optional[str] = None,
        client_certificate_file: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        compression: Optional[Compression] = None,
        preferred_temporality: Optional[
            dict[type, AggregationTemporality]
        ] = None,
        preferred_aggregation: Optional[dict[type, Aggregation]] = None,
        jitter: float = _DEFAULT_JITTER,
    ):
        self._endpoint = endpoint or _resolve_endpoint(
            "v1/metrics", OTEL_EXPORTER_OTLP_METRICS_ENDPOINT
        )

        self._certificate_file = _resolve_tls_file(
            certificate_file,
            OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE,
            OTEL_EXPORTER_OTLP_CERTIFICATE,
            default=True,
        )
        self._client_key_file = _resolve_tls_file(
            client_key_file,
            OTEL_EXPORTER_OTLP_METRICS_CLIENT_KEY,
            OTEL_EXPORTER_OTLP_CLIENT_KEY,
        )
        self._client_certificate_file = _resolve_tls_file(
            client_certificate_file,
            OTEL_EXPORTER_OTLP_METRICS_CLIENT_CERTIFICATE,
            OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE,
        )

        self._headers = _resolve_headers(
            OTEL_EXPORTER_OTLP_METRICS_HEADERS, headers
        )

        self._timeout = _resolve_timeout(
            OTEL_EXPORTER_OTLP_METRICS_TIMEOUT, timeout
        )
        self._compression = _resolve_compression(
            OTEL_EXPORTER_OTLP_METRICS_COMPRESSION, compression
        )

        self._client = _OTLPHttpClient(
            endpoint=self._endpoint,
            headers=self._headers,
            timeout=self._timeout,
            compression=self._compression,
            certificate_file=self._certificate_file,
            client_key_file=self._client_key_file,
            client_certificate_file=self._client_certificate_file,
            jitter=jitter,
        )

        super().__init__(
            preferred_temporality=self._get_temporality(preferred_temporality),
            preferred_aggregation=self._get_aggregation(preferred_aggregation),
        )

    def _get_temporality(
        self,
        preferred_temporality: Optional[dict[type, AggregationTemporality]],
    ) -> dict[type, AggregationTemporality]:
        otel_exporter_otlp_metrics_temporality_preference = (
            os.environ.get(
                OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE,
                "CUMULATIVE",
            )
            .upper()
            .strip()
        )

        if otel_exporter_otlp_metrics_temporality_preference == "DELTA":
            instrument_class_temporality = {
                Counter: AggregationTemporality.DELTA,
                UpDownCounter: AggregationTemporality.CUMULATIVE,
                Histogram: AggregationTemporality.DELTA,
                ObservableCounter: AggregationTemporality.DELTA,
                ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
                ObservableGauge: AggregationTemporality.CUMULATIVE,
            }

        elif otel_exporter_otlp_metrics_temporality_preference == "LOWMEMORY":
            instrument_class_temporality = {
                Counter: AggregationTemporality.DELTA,
                UpDownCounter: AggregationTemporality.CUMULATIVE,
                Histogram: AggregationTemporality.DELTA,
                ObservableCounter: AggregationTemporality.CUMULATIVE,
                ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
                ObservableGauge: AggregationTemporality.CUMULATIVE,
            }

        else:
            if (
                otel_exporter_otlp_metrics_temporality_preference
                != "CUMULATIVE"
            ):
                _logger.warning(
                    "Unrecognized OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE"
                    " value found: %s, using CUMULATIVE",
                    otel_exporter_otlp_metrics_temporality_preference,
                )
            instrument_class_temporality = {
                Counter: AggregationTemporality.CUMULATIVE,
                UpDownCounter: AggregationTemporality.CUMULATIVE,
                Histogram: AggregationTemporality.CUMULATIVE,
                ObservableCounter: AggregationTemporality.CUMULATIVE,
                ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
                ObservableGauge: AggregationTemporality.CUMULATIVE,
            }

        instrument_class_temporality.update(preferred_temporality or {})
        return instrument_class_temporality

    def _get_aggregation(
        self,
        preferred_aggregation: Optional[dict[type, Aggregation]],
    ) -> dict[type, Aggregation]:
        otel_exporter_otlp_metrics_default_histogram_aggregation = (
            os.environ.get(
                OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION,
                "explicit_bucket_histogram",
            )
        )

        if otel_exporter_otlp_metrics_default_histogram_aggregation == (
            "base2_exponential_bucket_histogram"
        ):
            instrument_class_aggregation = {
                Histogram: ExponentialBucketHistogramAggregation(),
            }

        else:
            if (
                otel_exporter_otlp_metrics_default_histogram_aggregation
                != "explicit_bucket_histogram"
            ):
                _logger.warning(
                    "Invalid value for %s: %s, using explicit bucket "
                    "histogram aggregation",
                    OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION,
                    otel_exporter_otlp_metrics_default_histogram_aggregation,
                )

            instrument_class_aggregation = {
                Histogram: ExplicitBucketHistogramAggregation(),
            }

        instrument_class_aggregation.update(preferred_aggregation or {})
        return instrument_class_aggregation

    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: Optional[float] = None,
        **kwargs,
    ) -> MetricExportResult:
        encoded_request = encode_metrics(metrics_data)
        body = encoded_request.to_json().encode("utf-8")

        timeout_sec = (
            timeout_millis / 1000.0 if timeout_millis is not None else None
        )

        if self._client.export(body, timeout_sec=timeout_sec):
            return MetricExportResult.SUCCESS
        return MetricExportResult.FAILURE

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        self._client.shutdown()

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        return True
