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

"""OTLP Metrics Exporter"""

import logging
from typing import Any, List, Sequence, Type, TypeVar

# pylint: disable=duplicate-code
from opentelemetry.exporter.otlp.exporter import (
    OTLPExporterMixin,
    _get_resource_data,
)
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
)
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2_grpc import (
    MetricsServiceStub,
)
from opentelemetry.proto.common.v1.common_pb2 import StringKeyValue
from opentelemetry.proto.metrics.v1.metrics_pb2 import (
    DoubleDataPoint,
    InstrumentationLibraryMetrics,
    Int64DataPoint,
)
from opentelemetry.proto.metrics.v1.metrics_pb2 import (
    Metric as CollectorMetric,
)
from opentelemetry.proto.metrics.v1.metrics_pb2 import (
    MetricDescriptor,
    ResourceMetrics,
)
from opentelemetry.sdk.metrics import (
    Counter,
    SumObserver,
    UpDownCounter,
    UpDownSumObserver,
    ValueObserver,
    ValueRecorder,
)
from opentelemetry.sdk.metrics.export import (
    MetricRecord,
    MetricsExporter,
    MetricsExportResult,
)

logger = logging.getLogger(__name__)
DataPointT = TypeVar("DataPointT", Int64DataPoint, DoubleDataPoint)


def _get_data_points(
    sdk_metric: MetricRecord, data_point_class: Type[DataPointT]
) -> List[DataPointT]:

    data_points = []

    for (
        label,
        bound_counter,
    ) in sdk_metric.instrument.bound_instruments.items():

        string_key_values = []

        for label_key, label_value in label:
            string_key_values.append(
                StringKeyValue(key=label_key, value=label_value)
            )

        for view_data in bound_counter.view_datas:

            if view_data.labels == label:

                data_points.append(
                    data_point_class(
                        labels=string_key_values,
                        value=view_data.aggregator.current,
                    )
                )
                break

    return data_points


def _get_temporality(instrument: Any):
    # pylint: disable=no-member
    if isinstance(instrument, (Counter, UpDownCounter)):
        temporality = MetricDescriptor.Temporality.DELTA
    elif isinstance(instrument, (ValueRecorder, ValueObserver)):
        temporality = MetricDescriptor.Temporality.INSTANTANEOUS
    elif isinstance(instrument, (SumObserver, UpDownSumObserver)):
        temporality = MetricDescriptor.Temporality.CUMULATIVE
    else:
        raise Exception(
            "No temporality defined for instrument type {}".format(
                type(instrument)
            )
        )

    return temporality


def _get_type(value_type: Any):
    # pylint: disable=no-member
    if value_type is int:
        type_ = MetricDescriptor.Type.INT64

    elif value_type is float:
        type_ = MetricDescriptor.Type.DOUBLE

    # FIXME What are the types that correspond with
    # MetricDescriptor.Type.HISTOGRAM and
    # MetricDescriptor.Type.SUMMARY?
    else:
        raise Exception(
            "No type defined for valie type {}".format(type(value_type))
        )

    return type_


class OTLPMetricsExporter(
    MetricsExporter,
    OTLPExporterMixin[
        MetricRecord, ExportMetricsServiceRequest, MetricsExportResult
    ],
):
    # pylint: disable=unsubscriptable-object
    """OTLP metrics exporter

    Args:
        endpoint: OpenTelemetry Collector receiver endpoint
        credentials: Credentials object for server authentication
        metadata: Metadata to send when exporting
    """

    _stub = MetricsServiceStub
    _result = MetricsExportResult

    def _translate_data(
        self, data: Sequence[MetricRecord]
    ) -> ExportMetricsServiceRequest:
        # pylint: disable=too-many-locals,no-member
        # pylint: disable=attribute-defined-outside-init

        sdk_resource_instrumentation_library_metrics = {}

        for sdk_metric in data:

            if sdk_metric.instrument.meter.resource not in (
                sdk_resource_instrumentation_library_metrics.keys()
            ):
                sdk_resource_instrumentation_library_metrics[
                    sdk_metric.instrument.meter.resource
                ] = InstrumentationLibraryMetrics()

            self._metric_descriptor_kwargs = {}

            metric_descriptor = MetricDescriptor(
                name=sdk_metric.instrument.name,
                description=sdk_metric.instrument.description,
                unit=sdk_metric.instrument.unit,
                type=_get_type(sdk_metric.instrument.value_type),
                temporality=_get_temporality(sdk_metric.instrument),
            )

            if metric_descriptor.type == MetricDescriptor.Type.INT64:

                collector_metric = CollectorMetric(
                    metric_descriptor=metric_descriptor,
                    int64_data_points=_get_data_points(
                        sdk_metric, Int64DataPoint
                    ),
                )

            elif metric_descriptor.type == MetricDescriptor.Type.DOUBLE:

                collector_metric = CollectorMetric(
                    metric_descriptor=metric_descriptor,
                    double_data_points=_get_data_points(
                        sdk_metric, DoubleDataPoint
                    ),
                )

            sdk_resource_instrumentation_library_metrics[
                sdk_metric.instrument.meter.resource
            ].metrics.append(collector_metric)

        return ExportMetricsServiceRequest(
            resource_metrics=_get_resource_data(
                sdk_resource_instrumentation_library_metrics,
                ResourceMetrics,
                "metrics",
            )
        )

    def export(self, metrics: Sequence[MetricRecord]) -> MetricsExportResult:
        # pylint: disable=arguments-differ
        return self._export(metrics)
