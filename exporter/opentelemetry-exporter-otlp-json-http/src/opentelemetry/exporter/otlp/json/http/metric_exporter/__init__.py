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

from __future__ import annotations

import logging
import time
from os import environ

from opentelemetry.exporter.otlp.json.common._internal.metrics_encoder import (
    _get_aggregation,
    _get_temporality,
)
from opentelemetry.exporter.otlp.json.common.metrics_encoder import (
    encode_metrics,
    split_metrics_data,
)
from opentelemetry.exporter.otlp.json.http import Compression
from opentelemetry.exporter.otlp.json.http._internal import (
    _OTLPHttpClient,
    _resolve_compression,
    _resolve_endpoint,
    _resolve_headers,
    _resolve_timeout,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE,
    OTEL_EXPORTER_OTLP_METRICS_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_METRICS_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_METRICS_COMPRESSION,
    OTEL_EXPORTER_OTLP_METRICS_ENDPOINT,
    OTEL_EXPORTER_OTLP_METRICS_HEADERS,
    OTEL_EXPORTER_OTLP_METRICS_TIMEOUT,
)
from opentelemetry.sdk.metrics._internal.aggregation import Aggregation
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    MetricExporter,
    MetricExportResult,
    MetricsData,
)

_logger = logging.getLogger(__name__)

DEFAULT_METRICS_EXPORT_PATH = "v1/metrics"


class OTLPMetricExporter(MetricExporter):
    def __init__(
        self,
        endpoint: str | None = None,
        certificate_file: str | None = None,
        client_key_file: str | None = None,
        client_certificate_file: str | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        compression: Compression | None = None,
        preferred_temporality: dict[type, AggregationTemporality]
        | None = None,
        preferred_aggregation: dict[type, Aggregation] | None = None,
        max_export_batch_size: int | None = None,
    ):
        MetricExporter.__init__(
            self,
            preferred_temporality=_get_temporality(preferred_temporality),
            preferred_aggregation=_get_aggregation(preferred_aggregation),
        )
        self._shutdown = False
        self._max_export_batch_size: int | None = max_export_batch_size
        self._certificate_file = certificate_file or environ.get(
            OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE,
            environ.get(OTEL_EXPORTER_OTLP_CERTIFICATE),
        )
        self._client_key_file = client_key_file or environ.get(
            OTEL_EXPORTER_OTLP_METRICS_CLIENT_KEY,
            environ.get(OTEL_EXPORTER_OTLP_CLIENT_KEY),
        )
        self._client_certificate_file = client_certificate_file or environ.get(
            OTEL_EXPORTER_OTLP_METRICS_CLIENT_CERTIFICATE,
            environ.get(OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE),
        )
        self._timeout = _resolve_timeout(
            timeout, OTEL_EXPORTER_OTLP_METRICS_TIMEOUT
        )
        self._client = _OTLPHttpClient(
            endpoint=endpoint
            or _resolve_endpoint(
                OTEL_EXPORTER_OTLP_METRICS_ENDPOINT,
                DEFAULT_METRICS_EXPORT_PATH,
            ),
            headers=_resolve_headers(
                headers, OTEL_EXPORTER_OTLP_METRICS_HEADERS
            ),
            timeout=self._timeout,
            compression=_resolve_compression(
                compression, OTEL_EXPORTER_OTLP_METRICS_COMPRESSION
            ),
            certificate=self._certificate_file,
            client_key_file=self._client_key_file,
            client_certificate_file=self._client_certificate_file,
        )

    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: float | None = 10_000,
        **kwargs,
    ) -> MetricExportResult:
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring batch")
            return MetricExportResult.FAILURE

        export_request = encode_metrics(metrics_data)
        timeout = (
            self._timeout
            if timeout_millis is None
            else min(self._timeout, timeout_millis / 1000)
        )
        deadline = time.time() + timeout
        for batch in split_metrics_data(
            export_request, self._max_export_batch_size
        ):
            if not self._client.export(
                batch.to_json().encode(), timeout=deadline - time.time()
            ):
                return MetricExportResult.FAILURE

        return MetricExportResult.SUCCESS

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring call")
            return
        self._shutdown = True
        self._client.shutdown()

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        """Nothing is buffered in this exporter, so this method does nothing."""
        return True
