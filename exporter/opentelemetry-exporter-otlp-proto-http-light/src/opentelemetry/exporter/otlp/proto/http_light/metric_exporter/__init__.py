# Copyright The OpenTelemetry Authors
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
from typing import (  # noqa: F401
    Dict,
    Iterable,
    List,
    Optional,
)
from urllib.parse import urlparse

from opentelemetry.exporter.otlp.proto.common._exporter_metrics import (
    ExporterMetrics,
)
from opentelemetry.exporter.otlp.proto.common._internal.metrics_encoder import (
    OTLPMetricExporterMixin,
)
from opentelemetry.exporter.otlp.proto.common.metrics_encoder import (
    encode_metrics,
)
from opentelemetry.exporter.otlp.proto.http_light import Compression
from opentelemetry.exporter.otlp.proto.http_light._common import (
    _OTLPHTTPExporterBase,
    _SignalConfig,
)
from opentelemetry.metrics import MeterProvider
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (  # noqa: F401
    ExportMetricsServiceRequest,
)
from opentelemetry.proto.metrics.v1 import metrics_pb2 as pb2
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE,
    OTEL_EXPORTER_OTLP_METRICS_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_METRICS_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_METRICS_COMPRESSION,
    OTEL_EXPORTER_OTLP_METRICS_ENDPOINT,
    OTEL_EXPORTER_OTLP_METRICS_HEADERS,
    OTEL_EXPORTER_OTLP_METRICS_TIMEOUT,
)
from opentelemetry.sdk.metrics._internal.aggregation import Aggregation
from opentelemetry.sdk.metrics.export import (  # noqa: F401
    AggregationTemporality,
    MetricExporter,
    MetricExportResult,
    MetricsData,
)
from opentelemetry.semconv._incubating.attributes.otel_attributes import (
    OtelComponentTypeValues,
)

DEFAULT_METRICS_EXPORT_PATH = "v1/metrics"

_logger = logging.getLogger(__name__)

_METRICS_SIGNAL_CONFIG = _SignalConfig(
    endpoint_env_var=OTEL_EXPORTER_OTLP_METRICS_ENDPOINT,
    certificate_env_var=OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE,
    client_key_env_var=OTEL_EXPORTER_OTLP_METRICS_CLIENT_KEY,
    client_certificate_env_var=OTEL_EXPORTER_OTLP_METRICS_CLIENT_CERTIFICATE,
    headers_env_var=OTEL_EXPORTER_OTLP_METRICS_HEADERS,
    timeout_env_var=OTEL_EXPORTER_OTLP_METRICS_TIMEOUT,
    compression_env_var=OTEL_EXPORTER_OTLP_METRICS_COMPRESSION,
    default_path="v1/metrics",
    metrics_component_type=OtelComponentTypeValues.OTLP_HTTP_METRIC_EXPORTER,
    metrics_signal="metrics",
)


class OTLPMetricExporter(
    MetricExporter, OTLPMetricExporterMixin, _OTLPHTTPExporterBase
):
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
        *,
        meter_provider: Optional[MeterProvider] = None,
    ):
        _OTLPHTTPExporterBase.__init__(
            self,
            endpoint=endpoint,
            certificate_file=certificate_file,
            client_key_file=client_key_file,
            client_certificate_file=client_certificate_file,
            headers=headers,
            timeout=timeout,
            compression=compression,
            meter_provider=meter_provider,
            signal_config=_METRICS_SIGNAL_CONFIG,
        )
        self._common_configuration(
            preferred_temporality, preferred_aggregation
        )
        self._max_export_batch_size: int | None = max_export_batch_size

    def _export_with_retries(
        self,
        export_request: ExportMetricsServiceRequest,
        num_items: int,
    ) -> MetricExportResult:
        serialized_data = export_request.SerializeToString()
        success = self._export_with_retry(
            serialized_data, num_items, "metrics"
        )
        return (
            MetricExportResult.SUCCESS
            if success
            else MetricExportResult.FAILURE
        )

    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: Optional[float] = 10000,
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

        if self._max_export_batch_size is None:
            return self._export_with_retries(export_request, num_items)

        batched_export_requests = _split_metrics_data(
            export_request, self._max_export_batch_size
        )

        for split_metrics_data in batched_export_requests:
            export_result = self._export_with_retries(
                split_metrics_data, num_items
            )
            if export_result != MetricExportResult.SUCCESS:
                return MetricExportResult.FAILURE

        return MetricExportResult.SUCCESS

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        self._do_shutdown()

    @property
    def _exporting(self) -> str:
        return "metrics"

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        """Nothing is buffered in this exporter, so this method does nothing."""
        return True

    def set_meter_provider(self, meter_provider: MeterProvider) -> None:
        self._metrics = ExporterMetrics(
            OtelComponentTypeValues.OTLP_HTTP_METRIC_EXPORTER,
            "metrics",
            urlparse(self._endpoint),
            meter_provider,
        )


def _split_metrics_data(
    metrics_data: ExportMetricsServiceRequest,
    max_export_batch_size: int | None = None,
) -> Iterable[ExportMetricsServiceRequest]:
    if not max_export_batch_size:
        return metrics_data

    batch_size: int = 0
    split_resource_metrics = []

    for resource_metrics in metrics_data.resource_metrics:
        split_scope_metrics = []
        split_resource_metrics.append(
            {
                "resource": resource_metrics.resource,
                "schema_url": resource_metrics.schema_url,
                "scope_metrics": split_scope_metrics,
            }
        )

        for scope_metrics in resource_metrics.scope_metrics:
            split_metrics = []
            split_scope_metrics.append(
                {
                    "scope": scope_metrics.scope,
                    "schema_url": scope_metrics.schema_url,
                    "metrics": split_metrics,
                }
            )

            for metric in scope_metrics.metrics:
                split_data_points = []
                field_name = metric.WhichOneof("data")
                if not field_name:
                    _logger.warning(
                        "Tried to split and export an unsupported metric type. Skipping."
                    )
                    continue

                data_container = getattr(metric, field_name)
                metric_dict = {
                    "name": metric.name,
                    "description": metric.description,
                    "unit": metric.unit,
                    field_name: {
                        "data_points": split_data_points,
                    },
                }
                if hasattr(data_container, "aggregation_temporality"):
                    metric_dict[field_name]["aggregation_temporality"] = (
                        data_container.aggregation_temporality
                    )
                if hasattr(data_container, "is_monotonic"):
                    metric_dict[field_name]["is_monotonic"] = (
                        data_container.is_monotonic
                    )
                split_metrics.append(metric_dict)

                current_data_points = data_container.data_points
                for data_point in current_data_points:
                    split_data_points.append(data_point)
                    batch_size += 1

                    if batch_size >= max_export_batch_size:
                        yield ExportMetricsServiceRequest(
                            resource_metrics=_get_split_resource_metrics_pb2(
                                split_resource_metrics
                            )
                        )

                        batch_size = 0
                        split_data_points = []

                        field_name = metric.WhichOneof("data")
                        if field_name is None:
                            _logger.warning(
                                "Tried to split and export an unsupported metric type. Skipping."
                            )
                            continue
                        data_container = getattr(metric, field_name)
                        metric_dict = {
                            "name": metric.name,
                            "description": metric.description,
                            "unit": metric.unit,
                            field_name: {
                                "data_points": split_data_points,
                            },
                        }
                        if hasattr(data_container, "aggregation_temporality"):
                            metric_dict[field_name][
                                "aggregation_temporality"
                            ] = data_container.aggregation_temporality
                        if hasattr(data_container, "is_monotonic"):
                            metric_dict[field_name]["is_monotonic"] = (
                                data_container.is_monotonic
                            )

                        split_metrics = [metric_dict]
                        split_scope_metrics = [
                            {
                                "scope": scope_metrics.scope,
                                "schema_url": scope_metrics.schema_url,
                                "metrics": split_metrics,
                            }
                        ]
                        split_resource_metrics = [
                            {
                                "resource": resource_metrics.resource,
                                "schema_url": resource_metrics.schema_url,
                                "scope_metrics": split_scope_metrics,
                            }
                        ]

                if not split_data_points:
                    split_metrics.pop()

            if not split_metrics:
                split_scope_metrics.pop()

        if not split_scope_metrics:
            split_resource_metrics.pop()

    if batch_size > 0:
        yield ExportMetricsServiceRequest(
            resource_metrics=_get_split_resource_metrics_pb2(
                split_resource_metrics
            )
        )


def _get_split_resource_metrics_pb2(
    split_resource_metrics: List[Dict],
) -> List[pb2.ResourceMetrics]:
    split_resource_metrics_pb = []
    for resource_metrics in split_resource_metrics:
        new_resource_metrics = pb2.ResourceMetrics(
            resource=resource_metrics.get("resource"),
            scope_metrics=[],
            schema_url=resource_metrics.get("schema_url") or "",
        )
        for scope_metrics in resource_metrics.get("scope_metrics", []):
            new_scope_metrics = pb2.ScopeMetrics(
                scope=scope_metrics.get("scope"),
                metrics=[],
                schema_url=scope_metrics.get("schema_url") or "",
            )

            for metric in scope_metrics.get("metrics", []):
                new_metric = None
                data_points = []

                if "sum" in metric:
                    new_metric = pb2.Metric(
                        name=metric.get("name"),
                        description=metric.get("description"),
                        unit=metric.get("unit"),
                        sum=pb2.Sum(
                            data_points=[],
                            aggregation_temporality=metric.get("sum").get(
                                "aggregation_temporality"
                            ),
                            is_monotonic=metric.get("sum").get("is_monotonic"),
                        ),
                    )
                    data_points = metric.get("sum").get("data_points")
                elif "histogram" in metric:
                    new_metric = pb2.Metric(
                        name=metric.get("name"),
                        description=metric.get("description"),
                        unit=metric.get("unit"),
                        histogram=pb2.Histogram(
                            data_points=[],
                            aggregation_temporality=metric.get(
                                "histogram"
                            ).get("aggregation_temporality"),
                        ),
                    )
                    data_points = metric.get("histogram").get("data_points")
                elif "exponential_histogram" in metric:
                    new_metric = pb2.Metric(
                        name=metric.get("name"),
                        description=metric.get("description"),
                        unit=metric.get("unit"),
                        exponential_histogram=pb2.ExponentialHistogram(
                            data_points=[],
                            aggregation_temporality=metric.get(
                                "exponential_histogram"
                            ).get("aggregation_temporality"),
                        ),
                    )
                    data_points = metric.get("exponential_histogram").get(
                        "data_points"
                    )
                elif "gauge" in metric:
                    new_metric = pb2.Metric(
                        name=metric.get("name"),
                        description=metric.get("description"),
                        unit=metric.get("unit"),
                        gauge=pb2.Gauge(
                            data_points=[],
                        ),
                    )
                    data_points = metric.get("gauge").get("data_points")
                elif "summary" in metric:
                    new_metric = pb2.Metric(
                        name=metric.get("name"),
                        description=metric.get("description"),
                        unit=metric.get("unit"),
                        summary=pb2.Summary(
                            data_points=[],
                        ),
                    )
                    data_points = metric.get("summary").get("data_points")
                else:
                    _logger.warning(
                        "Tried to split and export an unsupported metric type. Skipping."
                    )
                    continue

                for field_name in [
                    "sum",
                    "histogram",
                    "exponential_histogram",
                    "gauge",
                    "summary",
                ]:
                    if field_name in metric:
                        metric_data_container = getattr(new_metric, field_name)
                        for data_point in data_points:
                            metric_data_container.data_points.append(
                                data_point
                            )
                        break

                new_scope_metrics.metrics.append(new_metric)
            new_resource_metrics.scope_metrics.append(new_scope_metrics)
        split_resource_metrics_pb.append(new_resource_metrics)
    return split_resource_metrics_pb
