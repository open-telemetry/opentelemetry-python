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

from opentelemetry.ext.otlp.exporter import (
    OTLPExporterMixin,
    translate_key_values,
)
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
)
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2_grpc import (
    MetricsServiceStub,
)
from opentelemetry.proto.common.v1.common_pb2 import (
    AttributeKeyValue,
    StringKeyValue,
)
from opentelemetry.proto.metrics.v1.metrics_pb2 import (
    DoubleDataPoint,
    InstrumentationLibraryMetrics,
    Int64DataPoint,
    MetricDescriptor,
    ResourceMetrics,
    Metric as CollectorMetric,
)
from opentelemetry.proto.resource.v1.resource_pb2 import Resource
from opentelemetry.sdk.metrics import (
    Counter,
    SumObserver,
    UpDownCounter,
    UpDownSumObserver,
    ValueObserver,
    ValueRecorder,
)
from opentelemetry.sdk.metrics.export import (
    MetricsExporter,
    MetricsExportResult,
)

logger = logging.getLogger(__name__)


def _get_data_points(sdk_metric, data_point_class):

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
        data_points.append(
            data_point_class(
                labels=string_key_values,
                value=bound_counter.aggregator.current,
            )
        )

    return data_points


def _get_temporality(instrument):
    if isinstance(instrument, (Counter, UpDownCounter)):
        temporality = MetricDescriptor.Temporality.DELTA
    elif isinstance(
        instrument, (ValueRecorder, ValueObserver)
    ):
        temporality = MetricDescriptor.Temporality.INSTANTANEOUS
    elif isinstance(
        instrument, (SumObserver, UpDownSumObserver)
    ):
        temporality = MetricDescriptor.Temporality.CUMULATIVE
    else:
        raise Exception(
            "No temporality defined for instrument type {}".format(
                type(instrument)
            )
        )

    return temporality


def _get_type(value_type):
    if value_type is int:
        type_ = MetricDescriptor.Type.INT64

    elif value_type is float:
        type_ = MetricDescriptor.Type.DOUBLE

    # FIXME What are the types that correspond with
    # MetricDescriptor.Type.HISTOGRAM and
    # MetricDescriptor.Type.SUMMARY?
    else:
        raise Exception(
            "No type defined for valie type {}".format(
                type(value_type)
            )
        )

    return type_


class OTLPMetricsExporter(MetricsExporter, OTLPExporterMixin):
    """OTLP metrics exporter

    Args:
        endpoint: OpenTelemetry Collector receiver endpoint
        credentials: Credentials object for server authentication
        metadata: Metadata to send when exporting
    """

    _stub = MetricsServiceStub
    _result = MetricsExportResult

    def _translate_data(self, data):
        # pylint: disable=too-many-locals,no-member
        # pylint: disable=attribute-defined-outside-init

        resource_metrics = []

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

        resource_metrics = []

        for (
            sdk_resource,
            instrumentation_library_metrics,
        ) in sdk_resource_instrumentation_library_metrics.items():

            collector_resource = Resource()

            for key, value in sdk_resource.labels.items():

                try:
                    collector_resource.attributes.append(
                        AttributeKeyValue(**translate_key_values(key, value))
                    )
                except Exception as error:  # pylint: disable=broad-except
                    logger.exception(error)

            resource_metrics.append(
                ResourceMetrics(
                    resource=collector_resource,
                    instrumentation_library_metrics=[
                        instrumentation_library_metrics
                    ],
                )
            )

        return ExportMetricsServiceRequest(resource_metrics=resource_metrics)
