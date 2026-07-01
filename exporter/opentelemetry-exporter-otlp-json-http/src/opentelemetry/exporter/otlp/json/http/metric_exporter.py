# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import logging
import os
from collections.abc import Mapping
from typing import overload

from opentelemetry.exporter.http.transport._base import BaseHTTPTransport
from opentelemetry.exporter.http.transport._urllib3 import Urllib3HTTPTransport
from opentelemetry.exporter.otlp.common import Compression
from opentelemetry.exporter.otlp.common._aggregation import (
    _get_aggregation,
    _get_temporality,
)
from opentelemetry.exporter.otlp.common._http import OTLPHTTPClient
from opentelemetry.exporter.otlp.json.common._internal.metrics_encoder import (
    encode_metrics,
    split_metrics_data,
)
from opentelemetry.exporter.otlp.json.http._internal import (
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
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    MetricExporter,
    MetricExportResult,
    MetricsData,
)
from opentelemetry.sdk.metrics.view import Aggregation

_DEFAULT_METRICS_EXPORT_PATH = "v1/metrics"

_logger = logging.getLogger(__name__)


class OTLPMetricExporter(MetricExporter):
    @overload
    def __init__(
        self,
        endpoint: str | None = None,
        certificate_file: str | None = None,
        client_key_file: str | None = None,
        client_certificate_file: str | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
        compression: Compression | None = None,
        preferred_temporality: dict[type, AggregationTemporality]
        | None = None,
        preferred_aggregation: dict[type, Aggregation] | None = None,
        max_export_batch_size: int | None = None,
    ) -> None: ...

    @overload
    def __init__(
        self,
        endpoint: str | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
        compression: Compression | None = None,
        preferred_temporality: dict[type, AggregationTemporality]
        | None = None,
        preferred_aggregation: dict[type, Aggregation] | None = None,
        max_export_batch_size: int | None = None,
        *,
        _transport: BaseHTTPTransport,
    ) -> None: ...

    def __init__(
        self,
        endpoint: str | None = None,
        certificate_file: str | None = None,
        client_key_file: str | None = None,
        client_certificate_file: str | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
        compression: Compression | None = None,
        preferred_temporality: dict[type, AggregationTemporality]
        | None = None,
        preferred_aggregation: dict[type, Aggregation] | None = None,
        max_export_batch_size: int | None = None,
        *,
        _transport: BaseHTTPTransport | None = None,
    ) -> None:
        MetricExporter.__init__(
            self,
            preferred_temporality=_get_temporality(preferred_temporality),
            preferred_aggregation=_get_aggregation(preferred_aggregation),
        )
        certificate_file = certificate_file or os.environ.get(
            OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE,
            os.environ.get(OTEL_EXPORTER_OTLP_CERTIFICATE, True),
        )
        client_key_file = client_key_file or os.environ.get(
            OTEL_EXPORTER_OTLP_METRICS_CLIENT_KEY,
            os.environ.get(OTEL_EXPORTER_OTLP_CLIENT_KEY),
        )
        client_certificate_file = client_certificate_file or os.environ.get(
            OTEL_EXPORTER_OTLP_METRICS_CLIENT_CERTIFICATE,
            os.environ.get(OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE),
        )
        transport = (
            _transport
            if _transport
            else Urllib3HTTPTransport(
                verify=certificate_file,
                cert=(client_certificate_file, client_key_file)
                if client_certificate_file and client_key_file
                else client_certificate_file,
            )
        )
        self._client = OTLPHTTPClient(
            transport=transport,
            endpoint=endpoint
            or _resolve_endpoint(
                OTEL_EXPORTER_OTLP_METRICS_ENDPOINT,
                _DEFAULT_METRICS_EXPORT_PATH,
            ),
            kind="metrics",
            timeout=timeout
            if timeout is not None
            else _resolve_timeout(OTEL_EXPORTER_OTLP_METRICS_TIMEOUT),
            compression=compression
            if compression is not None
            else _resolve_compression(OTEL_EXPORTER_OTLP_METRICS_COMPRESSION),
            headers=_resolve_headers(
                headers, OTEL_EXPORTER_OTLP_METRICS_HEADERS
            ),
            logger=_logger,
        )
        self._max_export_batch_size = max_export_batch_size
        self._shutdown = False

    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> MetricExportResult:
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring batch")
            return MetricExportResult.FAILURE
        try:
            export_request = encode_metrics(metrics_data)
        # pylint: disable-next=broad-exception-caught
        except Exception as error:
            _logger.error("Failed to encode metrics: %s", error)
            return MetricExportResult.FAILURE
        for request in split_metrics_data(
            export_request, self._max_export_batch_size
        ):
            export_result = self._client.export(request.to_json().encode())
            if not export_result.success:
                return MetricExportResult.FAILURE
        return MetricExportResult.SUCCESS

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring call")
            return
        self._shutdown = True
        self._client.shutdown()

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        return True
