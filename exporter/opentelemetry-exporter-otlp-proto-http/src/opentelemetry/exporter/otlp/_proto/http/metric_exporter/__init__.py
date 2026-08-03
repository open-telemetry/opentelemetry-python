# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import os
from collections.abc import Iterable
from gzip import GzipFile
from io import BytesIO
from logging import getLogger
from os import environ
from random import uniform
from threading import Event
from time import time
from urllib.error import URLError
from urllib.parse import urlparse
from zlib import compress

from opentelemetry.exporter.otlp._proto.common._internal import (
    _get_resource_data,
)
from opentelemetry.exporter.otlp._proto.common._exporter_metrics import (
    create_exporter_metrics,
)
from opentelemetry.exporter.otlp._proto.common._internal.metrics_encoder import (
    OTLPMetricExporterMixin,
    encode_metrics,
)
from opentelemetry.exporter.otlp._proto.http import (
    _OTLP_HTTP_HEADERS,
    Compression,
)
from opentelemetry.exporter.otlp._proto.http._common import (
    _build_ssl_context,
    _is_retryable,
    _post,
)
from opentelemetry.metrics import MeterProvider
from opentelemetry._proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
)
from opentelemetry._proto.metrics.v1.metrics_pb2 import (
    ExponentialHistogram,
    Gauge,
    Histogram,
    Metric,
    ResourceMetrics,
    ScopeMetrics,
    Sum,
    Summary,
)
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
    OTEL_EXPORTER_OTLP_METRICS_ENDPOINT,
    OTEL_EXPORTER_OTLP_METRICS_HEADERS,
    OTEL_EXPORTER_OTLP_METRICS_TIMEOUT,
    OTEL_EXPORTER_OTLP_TIMEOUT,
    OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED,
)
from opentelemetry.sdk.metrics._internal.aggregation import Aggregation
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    MetricExporter,
    MetricExportResult,
    MetricsData,
)
from opentelemetry.semconv._incubating.attributes.otel_attributes import (
    OtelComponentTypeValues,
)
from opentelemetry.semconv.attributes.http_attributes import (
    HTTP_RESPONSE_STATUS_CODE,
)
from opentelemetry.util.re import parse_env_headers

_logger = getLogger(__name__)

DEFAULT_COMPRESSION = Compression.NoCompression
DEFAULT_ENDPOINT = "http://localhost:4318/"
DEFAULT_METRICS_EXPORT_PATH = "v1/metrics"
DEFAULT_TIMEOUT = 10
_MAX_RETRYS = 6


class OTLPMetricExporter(MetricExporter, OTLPMetricExporterMixin):
    def __init__(
        self,
        endpoint: str | None = None,
        certificate_file: str | None = None,
        client_key_file: str | None = None,
        client_certificate_file: str | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        compression: Compression | None = None,
        session: object | None = None,
        preferred_temporality: dict[type, AggregationTemporality] | None = None,
        preferred_aggregation: dict[type, Aggregation] | None = None,
        max_export_batch_size: int | None = None,
        *,
        meter_provider: MeterProvider | None = None,
    ):
        if session is not None:
            _logger.warning(
                "session is not supported by the pure-Python OTLP HTTP "
                "exporter and will be ignored"
            )
        self._shutdown_in_progress = Event()
        self._endpoint = endpoint or environ.get(
            OTEL_EXPORTER_OTLP_METRICS_ENDPOINT,
            _append_metrics_path(
                environ.get(OTEL_EXPORTER_OTLP_ENDPOINT, DEFAULT_ENDPOINT)
            ),
        )
        self._certificate_file = certificate_file or environ.get(
            OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE,
            environ.get(OTEL_EXPORTER_OTLP_CERTIFICATE, True),
        )
        self._client_key_file = client_key_file or environ.get(
            OTEL_EXPORTER_OTLP_METRICS_CLIENT_KEY,
            environ.get(OTEL_EXPORTER_OTLP_CLIENT_KEY, None),
        )
        self._client_certificate_file = client_certificate_file or environ.get(
            OTEL_EXPORTER_OTLP_METRICS_CLIENT_CERTIFICATE,
            environ.get(OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE, None),
        )
        self._client_cert = (
            (self._client_certificate_file, self._client_key_file)
            if self._client_certificate_file and self._client_key_file
            else self._client_certificate_file
        )
        headers_string = environ.get(
            OTEL_EXPORTER_OTLP_METRICS_HEADERS,
            environ.get(OTEL_EXPORTER_OTLP_HEADERS, ""),
        )
        self._headers = headers or parse_env_headers(headers_string, liberal=True)
        self._timeout = timeout or float(
            environ.get(
                OTEL_EXPORTER_OTLP_METRICS_TIMEOUT,
                environ.get(OTEL_EXPORTER_OTLP_TIMEOUT, DEFAULT_TIMEOUT),
            )
        )
        self._compression = compression or _compression_from_env()
        self._request_headers = {**_OTLP_HTTP_HEADERS, **self._headers}
        if self._compression is not Compression.NoCompression:
            self._request_headers["Content-Encoding"] = self._compression.value
        self._ssl_context = _build_ssl_context(
            self._certificate_file, self._client_cert
        )
        self._common_configuration(preferred_temporality, preferred_aggregation)
        self._max_export_batch_size = max_export_batch_size
        self._shutdown = False

        self._metrics = create_exporter_metrics(
            OtelComponentTypeValues.OTLP_HTTP_METRIC_EXPORTER,
            "metrics",
            urlparse(self._endpoint),
            meter_provider,
            os.environ.get(OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED, "")
            .strip()
            .lower()
            == "true",
        )

    def _export(self, serialized_data: bytes, timeout_sec: float | None = None):
        data = serialized_data
        if self._compression == Compression.Gzip:
            gzip_data = BytesIO()
            with GzipFile(fileobj=gzip_data, mode="w") as gzip_stream:
                gzip_stream.write(serialized_data)
            data = gzip_data.getvalue()
        elif self._compression == Compression.Deflate:
            data = compress(serialized_data)
        if timeout_sec is None:
            timeout_sec = self._timeout
        try:
            return _post(
                self._endpoint,
                data,
                self._request_headers,
                timeout_sec,
                self._ssl_context,
            )
        except URLError:
            return _post(
                self._endpoint,
                data,
                self._request_headers,
                timeout_sec,
                self._ssl_context,
            )

    def _export_with_retries(
        self,
        export_request: ExportMetricsServiceRequest,
        deadline_sec: float,
        num_items: int,
    ) -> MetricExportResult:
        with self._metrics.export_operation(num_items) as result:
            serialized_data = export_request.SerializeToString()
            for retry_num in range(_MAX_RETRYS):
                backoff_seconds = 2**retry_num * uniform(0.8, 1.2)
                export_error: Exception | None = None
                try:
                    status_code, reason = self._export(
                        serialized_data, deadline_sec - time()
                    )
                    if status_code < 400:
                        return MetricExportResult.SUCCESS
                    retryable = _is_retryable(status_code)
                except URLError as error:
                    reason = error.reason
                    export_error = error
                    retryable = True
                    status_code = None

                if not retryable:
                    _logger.error(
                        "Failed to export metrics batch code: %s, reason: %s",
                        status_code,
                        reason,
                    )
                    error_attrs = (
                        {HTTP_RESPONSE_STATUS_CODE: status_code}
                        if status_code is not None
                        else None
                    )
                    result.error = export_error
                    result.error_attrs = error_attrs
                    return MetricExportResult.FAILURE

                if (
                    retry_num + 1 == _MAX_RETRYS
                    or backoff_seconds > (deadline_sec - time())
                    or self._shutdown
                ):
                    _logger.error(
                        "Failed to export metrics batch due to timeout, max retries or shutdown."
                    )
                    error_attrs = (
                        {HTTP_RESPONSE_STATUS_CODE: status_code}
                        if status_code is not None
                        else None
                    )
                    result.error = export_error
                    result.error_attrs = error_attrs
                    return MetricExportResult.FAILURE

                _logger.warning(
                    "Transient error %s encountered while exporting metrics batch, retrying in %.2fs.",
                    reason,
                    backoff_seconds,
                )
                if self._shutdown_in_progress.wait(backoff_seconds):
                    _logger.warning("Shutdown in progress, aborting retry.")
                    break
            return MetricExportResult.FAILURE

    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: float | None = 10000,
        **kwargs,
    ) -> MetricExportResult:
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring batch")
            return MetricExportResult.FAILURE

        num_items = 0
        for resource_metrics in metrics_data.resource_metrics:
            for scope_metrics in resource_metrics.scope_metrics:
                for metric in scope_metrics.metrics:
                    num_items += len(metric.data.data_points)

        export_request = encode_metrics(metrics_data)
        deadline_sec = time() + self._timeout

        if self._max_export_batch_size is None:
            return self._export_with_retries(export_request, deadline_sec, num_items)

        for split_request in _split_metrics_data(export_request, self._max_export_batch_size):
            if self._export_with_retries(split_request, deadline_sec, num_items) != MetricExportResult.SUCCESS:
                return MetricExportResult.FAILURE

        return MetricExportResult.SUCCESS

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring call")
            return
        self._shutdown = True
        self._shutdown_in_progress.set()

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        return True

    def set_meter_provider(self, meter_provider: MeterProvider) -> None:
        self._metrics = create_exporter_metrics(
            OtelComponentTypeValues.OTLP_HTTP_METRIC_EXPORTER,
            "metrics",
            urlparse(self._endpoint),
            meter_provider,
            os.environ.get(OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED, "")
            .strip()
            .lower()
            == "true",
        )

    @property
    def _exporting(self) -> str:
        return "metrics"


def _split_metrics_data(
    metrics_data: ExportMetricsServiceRequest,
    max_export_batch_size: int,
) -> Iterable[ExportMetricsServiceRequest]:
    if not max_export_batch_size:
        yield metrics_data
        return

    batch_size = 0
    split_resource_metrics: list[dict] = []

    for resource_metrics in metrics_data.resource_metrics:
        split_scope_metrics: list[dict] = []
        split_resource_metrics.append({
            "resource": resource_metrics.resource,
            "schema_url": resource_metrics.schema_url,
            "scope_metrics": split_scope_metrics,
        })

        for scope_metrics in resource_metrics.scope_metrics:
            split_metrics: list[dict] = []
            split_scope_metrics.append({
                "scope": scope_metrics.scope,
                "schema_url": scope_metrics.schema_url,
                "metrics": split_metrics,
            })

            for metric in scope_metrics.metrics:
                split_data_points: list = []
                field_name = metric.WhichOneof("data")
                if not field_name:
                    _logger.warning("Tried to split an unsupported metric type. Skipping.")
                    continue

                data_container = getattr(metric, field_name)
                metric_dict: dict = {
                    "name": metric.name,
                    "description": metric.description,
                    "unit": metric.unit,
                    field_name: {"data_points": split_data_points},
                }
                if hasattr(data_container, "aggregation_temporality"):
                    metric_dict[field_name]["aggregation_temporality"] = data_container.aggregation_temporality
                if hasattr(data_container, "is_monotonic"):
                    metric_dict[field_name]["is_monotonic"] = data_container.is_monotonic
                split_metrics.append(metric_dict)

                for data_point in data_container.data_points:
                    split_data_points.append(data_point)
                    batch_size += 1

                    if batch_size >= max_export_batch_size:
                        yield ExportMetricsServiceRequest(
                            resource_metrics=_build_resource_metrics(split_resource_metrics)
                        )
                        batch_size = 0
                        split_data_points = []

                        field_name = metric.WhichOneof("data")
                        if field_name is None:
                            _logger.warning("Tried to split an unsupported metric type. Skipping.")
                            continue
                        data_container = getattr(metric, field_name)
                        metric_dict = {
                            "name": metric.name,
                            "description": metric.description,
                            "unit": metric.unit,
                            field_name: {"data_points": split_data_points},
                        }
                        if hasattr(data_container, "aggregation_temporality"):
                            metric_dict[field_name]["aggregation_temporality"] = data_container.aggregation_temporality
                        if hasattr(data_container, "is_monotonic"):
                            metric_dict[field_name]["is_monotonic"] = data_container.is_monotonic

                        split_metrics = [metric_dict]
                        split_scope_metrics = [{
                            "scope": scope_metrics.scope,
                            "schema_url": scope_metrics.schema_url,
                            "metrics": split_metrics,
                        }]
                        split_resource_metrics = [{
                            "resource": resource_metrics.resource,
                            "schema_url": resource_metrics.schema_url,
                            "scope_metrics": split_scope_metrics,
                        }]

                if not split_data_points:
                    split_metrics.pop()

            if not split_metrics:
                split_scope_metrics.pop()

        if not split_scope_metrics:
            split_resource_metrics.pop()

    if batch_size > 0:
        yield ExportMetricsServiceRequest(
            resource_metrics=_build_resource_metrics(split_resource_metrics)
        )


def _build_resource_metrics(split_resource_metrics: list[dict]) -> list[ResourceMetrics]:
    result = []
    for rm in split_resource_metrics:
        scope_metrics_list = []
        for sm in rm.get("scope_metrics", []):
            metrics_list = []
            for metric in sm.get("metrics", []):
                new_metric = _build_metric(metric)
                if new_metric is not None:
                    metrics_list.append(new_metric)
            scope_metrics_list.append(ScopeMetrics(
                scope=sm.get("scope"),
                metrics=metrics_list,
                schema_url=sm.get("schema_url") or "",
            ))
        result.append(ResourceMetrics(
            resource=rm.get("resource"),
            scope_metrics=scope_metrics_list,
            schema_url=rm.get("schema_url") or "",
        ))
    return result


def _build_metric(metric: dict) -> Metric | None:
    kwargs: dict = dict(
        name=metric.get("name"),
        description=metric.get("description"),
        unit=metric.get("unit"),
    )
    if "sum" in metric:
        d = metric["sum"]
        kwargs["sum"] = Sum(
            data_points=list(d.get("data_points", [])),
            aggregation_temporality=d.get("aggregation_temporality", 0),
            is_monotonic=d.get("is_monotonic", False),
        )
    elif "histogram" in metric:
        d = metric["histogram"]
        kwargs["histogram"] = Histogram(
            data_points=list(d.get("data_points", [])),
            aggregation_temporality=d.get("aggregation_temporality", 0),
        )
    elif "exponential_histogram" in metric:
        d = metric["exponential_histogram"]
        kwargs["exponential_histogram"] = ExponentialHistogram(
            data_points=list(d.get("data_points", [])),
            aggregation_temporality=d.get("aggregation_temporality", 0),
        )
    elif "gauge" in metric:
        d = metric["gauge"]
        kwargs["gauge"] = Gauge(data_points=list(d.get("data_points", [])))
    elif "summary" in metric:
        d = metric["summary"]
        kwargs["summary"] = Summary(data_points=list(d.get("data_points", [])))
    else:
        _logger.warning("Tried to build an unsupported metric type. Skipping.")
        return None
    return Metric(**kwargs)


def _compression_from_env() -> Compression:
    return Compression(
        environ.get(
            OTEL_EXPORTER_OTLP_METRICS_COMPRESSION,
            environ.get(OTEL_EXPORTER_OTLP_COMPRESSION, "none"),
        )
        .lower()
        .strip()
    )


def _append_metrics_path(endpoint: str) -> str:
    if endpoint.endswith("/"):
        return endpoint + DEFAULT_METRICS_EXPORT_PATH
    return endpoint + f"/{DEFAULT_METRICS_EXPORT_PATH}"


def get_resource_data(sdk_resource_scope_data, resource_class, name):
    return _get_resource_data(sdk_resource_scope_data, resource_class, name)
