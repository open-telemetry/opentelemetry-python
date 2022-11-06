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

import dataclasses
from logging import getLogger
from os import environ
from typing import Dict, Iterable, List, Optional, Sequence
from grpc import ChannelCredentials, Compression
from opentelemetry.sdk.metrics._internal.aggregation import Aggregation
from opentelemetry.exporter.otlp.proto.grpc.exporter import (
    OTLPExporterMixin,
    get_resource_data,
    _get_credentials,
    environ_to_compression,
)
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
)
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2_grpc import (
    MetricsServiceStub,
)
from opentelemetry.proto.common.v1.common_pb2 import InstrumentationScope
from opentelemetry.proto.metrics.v1 import metrics_pb2 as pb2
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE,
    OTEL_EXPORTER_OTLP_METRICS_COMPRESSION,
    OTEL_EXPORTER_OTLP_METRICS_ENDPOINT,
    OTEL_EXPORTER_OTLP_METRICS_HEADERS,
    OTEL_EXPORTER_OTLP_METRICS_INSECURE,
    OTEL_EXPORTER_OTLP_METRICS_TIMEOUT,
    OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE,
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
    DataPointT,
    Gauge,
    Histogram as HistogramType,
    Metric,
    MetricExporter,
    MetricExportResult,
    MetricsData,
    ResourceMetrics,
    ScopeMetrics,
    Sum,
)

_logger = getLogger(__name__)


class OTLPMetricExporter(
    MetricExporter,
    OTLPExporterMixin[Metric, ExportMetricsServiceRequest, MetricExportResult],
):
    """OTLP metric exporter

    Args:
        endpoint: Target URL to which the exporter is going to send metrics
        max_export_batch_size: Maximum number of data points to export in a single request. This is to deal with
            gRPC's 4MB message size limit. If not set there is no limit to the number of data points in a request.
            If it is set and the number of data points exceeds the max, the request will be split.
    """

    _result = MetricExportResult
    _stub = MetricsServiceStub

    def __init__(
        self,
        endpoint: Optional[str] = None,
        insecure: Optional[bool] = None,
        credentials: Optional[ChannelCredentials] = None,
        headers: Optional[Sequence] = None,
        timeout: Optional[int] = None,
        compression: Optional[Compression] = None,
        preferred_temporality: Dict[type, AggregationTemporality] = None,
        preferred_aggregation: Dict[type, Aggregation] = None,
        max_export_batch_size: Optional[int] = None,
    ):

        if insecure is None:
            insecure = environ.get(OTEL_EXPORTER_OTLP_METRICS_INSECURE)
            if insecure is not None:
                insecure = insecure.lower() == "true"

        if (
            not insecure
            and environ.get(OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE) is not None
        ):
            credentials = _get_credentials(
                credentials, OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE
            )

        environ_timeout = environ.get(OTEL_EXPORTER_OTLP_METRICS_TIMEOUT)
        environ_timeout = (
            int(environ_timeout) if environ_timeout is not None else None
        )

        compression = (
            environ_to_compression(OTEL_EXPORTER_OTLP_METRICS_COMPRESSION)
            if compression is None
            else compression
        )

        instrument_class_temporality = {}
        if (
            environ.get(
                OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE,
                "CUMULATIVE",
            )
            .upper()
            .strip()
            == "DELTA"
        ):
            instrument_class_temporality = {
                Counter: AggregationTemporality.DELTA,
                UpDownCounter: AggregationTemporality.CUMULATIVE,
                Histogram: AggregationTemporality.DELTA,
                ObservableCounter: AggregationTemporality.DELTA,
                ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
                ObservableGauge: AggregationTemporality.CUMULATIVE,
            }
        else:
            instrument_class_temporality = {
                Counter: AggregationTemporality.CUMULATIVE,
                UpDownCounter: AggregationTemporality.CUMULATIVE,
                Histogram: AggregationTemporality.CUMULATIVE,
                ObservableCounter: AggregationTemporality.CUMULATIVE,
                ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
                ObservableGauge: AggregationTemporality.CUMULATIVE,
            }
        instrument_class_temporality.update(preferred_temporality or {})

        MetricExporter.__init__(
            self,
            preferred_temporality=instrument_class_temporality,
            preferred_aggregation=preferred_aggregation,
        )

        OTLPExporterMixin.__init__(
            self,
            endpoint=endpoint
            or environ.get(OTEL_EXPORTER_OTLP_METRICS_ENDPOINT),
            insecure=insecure,
            credentials=credentials,
            headers=headers or environ.get(OTEL_EXPORTER_OTLP_METRICS_HEADERS),
            timeout=timeout or environ_timeout,
            compression=compression,
        )

        self._max_export_batch_size: Optional[int] = max_export_batch_size

    def _translate_data(
        self, data: MetricsData
    ) -> ExportMetricsServiceRequest:

        resource_metrics_dict = {}

        for resource_metrics in data.resource_metrics:

            resource = resource_metrics.resource

            # It is safe to assume that each entry in data.resource_metrics is
            # associated with an unique resource.
            scope_metrics_dict = {}

            resource_metrics_dict[resource] = scope_metrics_dict

            for scope_metrics in resource_metrics.scope_metrics:

                instrumentation_scope = scope_metrics.scope

                # The SDK groups metrics in instrumentation scopes already so
                # there is no need to check for existing instrumentation scopes
                # here.
                pb2_scope_metrics = pb2.ScopeMetrics(
                    scope=InstrumentationScope(
                        name=instrumentation_scope.name,
                        version=instrumentation_scope.version,
                    )
                )

                scope_metrics_dict[instrumentation_scope] = pb2_scope_metrics

                for metric in scope_metrics.metrics:
                    pb2_metric = pb2.Metric(
                        name=metric.name,
                        description=metric.description,
                        unit=metric.unit,
                    )

                    if isinstance(metric.data, Gauge):
                        for data_point in metric.data.data_points:
                            pt = pb2.NumberDataPoint(
                                attributes=self._translate_attributes(
                                    data_point.attributes
                                ),
                                time_unix_nano=data_point.time_unix_nano,
                            )
                            if isinstance(data_point.value, int):
                                pt.as_int = data_point.value
                            else:
                                pt.as_double = data_point.value
                            pb2_metric.gauge.data_points.append(pt)

                    elif isinstance(metric.data, HistogramType):
                        for data_point in metric.data.data_points:
                            pt = pb2.HistogramDataPoint(
                                attributes=self._translate_attributes(
                                    data_point.attributes
                                ),
                                time_unix_nano=data_point.time_unix_nano,
                                start_time_unix_nano=(
                                    data_point.start_time_unix_nano
                                ),
                                count=data_point.count,
                                sum=data_point.sum,
                                bucket_counts=data_point.bucket_counts,
                                explicit_bounds=data_point.explicit_bounds,
                                max=data_point.max,
                                min=data_point.min,
                            )
                            pb2_metric.histogram.aggregation_temporality = (
                                metric.data.aggregation_temporality
                            )
                            pb2_metric.histogram.data_points.append(pt)

                    elif isinstance(metric.data, Sum):
                        for data_point in metric.data.data_points:
                            pt = pb2.NumberDataPoint(
                                attributes=self._translate_attributes(
                                    data_point.attributes
                                ),
                                start_time_unix_nano=(
                                    data_point.start_time_unix_nano
                                ),
                                time_unix_nano=data_point.time_unix_nano,
                            )
                            if isinstance(data_point.value, int):
                                pt.as_int = data_point.value
                            else:
                                pt.as_double = data_point.value
                            # note that because sum is a message type, the
                            # fields must be set individually rather than
                            # instantiating a pb2.Sum and setting it once
                            pb2_metric.sum.aggregation_temporality = (
                                metric.data.aggregation_temporality
                            )
                            pb2_metric.sum.is_monotonic = (
                                metric.data.is_monotonic
                            )
                            pb2_metric.sum.data_points.append(pt)
                    else:
                        _logger.warning(
                            "unsupported data type %s",
                            metric.data.__class__.__name__,
                        )
                        continue

                    pb2_scope_metrics.metrics.append(pb2_metric)

        return ExportMetricsServiceRequest(
            resource_metrics=get_resource_data(
                resource_metrics_dict,
                pb2.ResourceMetrics,
                "metrics",
            )
        )

    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> MetricExportResult:
        # TODO(#2663): OTLPExporterMixin should pass timeout to gRPC
        if self._max_export_batch_size is None:
            return self._export(data=metrics_data)

        export_result = MetricExportResult.SUCCESS

        for split_metrics_data in self._split_metrics_data(metrics_data):
            split_export_result = self._export(data=split_metrics_data)

            if split_export_result is MetricExportResult.FAILURE:
                export_result = MetricExportResult.FAILURE

        return export_result

    def _split_metrics_data(
        self,
        metrics_data: MetricsData,
    ) -> Iterable[MetricsData]:
        batch_size: int = 0
        split_resource_metrics: List[ResourceMetrics] = []

        for resource_metrics in metrics_data.resource_metrics:
            split_scope_metrics: List[ScopeMetrics] = []
            split_resource_metrics.append(
                dataclasses.replace(
                    resource_metrics,
                    scope_metrics=split_scope_metrics,
                )
            )
            for scope_metrics in resource_metrics.scope_metrics:
                split_metrics: List[Metric] = []
                split_scope_metrics.append(
                    dataclasses.replace(
                        scope_metrics,
                        metrics=split_metrics,
                    )
                )
                for metric in scope_metrics.metrics:
                    split_data_points: List[DataPointT] = []
                    split_metrics.append(
                        dataclasses.replace(
                            metric,
                            data=dataclasses.replace(
                                metric.data,
                                data_points=split_data_points,
                            ),
                        )
                    )

                    for data_point in metric.data.data_points:
                        split_data_points.append(data_point)
                        batch_size += 1

                        if batch_size >= self._max_export_batch_size:
                            yield MetricsData(
                                resource_metrics=split_resource_metrics
                            )
                            # Reset all the variables
                            batch_size = 0
                            split_data_points = []
                            split_metrics = [
                                dataclasses.replace(
                                    metric,
                                    data=dataclasses.replace(
                                        metric.data,
                                        data_points=split_data_points,
                                    ),
                                )
                            ]
                            split_scope_metrics = [
                                dataclasses.replace(
                                    scope_metrics,
                                    metrics=split_metrics,
                                )
                            ]
                            split_resource_metrics = [
                                dataclasses.replace(
                                    resource_metrics,
                                    scope_metrics=split_scope_metrics,
                                )
                            ]

                    if not split_data_points:
                        # If data_points is empty remove the whole metric
                        split_metrics.pop()

                if not split_metrics:
                    # If metrics is empty remove the whole scope_metrics
                    split_scope_metrics.pop()

            if not split_scope_metrics:
                # If scope_metrics is empty remove the whole resource_metrics
                split_resource_metrics.pop()

        if batch_size > 0:
            yield MetricsData(resource_metrics=split_resource_metrics)

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        pass

    @property
    def _exporting(self) -> str:
        return "metrics"

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        return True
