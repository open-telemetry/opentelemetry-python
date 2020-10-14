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
from typing import List, Sequence, Type, TypeVar

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
    AggregationTemporality,
    DoubleDataPoint,
    DoubleGauge,
    DoubleSum,
    InstrumentationLibraryMetrics,
    IntDataPoint,
    IntGauge,
    IntSum,
)
from opentelemetry.proto.metrics.v1.metrics_pb2 import Metric as OTLPMetric
from opentelemetry.proto.metrics.v1.metrics_pb2 import ResourceMetrics
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
DataPointT = TypeVar("DataPointT", IntDataPoint, DoubleDataPoint)


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
                        start_time_unix_nano=(
                            view_data.aggregator.last_checkpoint_timestamp
                        ),
                        time_unix_nano=(
                            view_data.aggregator.last_update_timestamp
                        ),
                    )
                )
                break

    return data_points


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

    # pylint: disable=no-self-use
    def _translate_data(
        self, data: Sequence[MetricRecord]
    ) -> ExportMetricsServiceRequest:
        # pylint: disable=too-many-locals,no-member
        # pylint: disable=attribute-defined-outside-init

        sdk_resource_instrumentation_library_metrics = {}

        # The criteria to decide how to translate data is based on this table
        # taken directly from OpenTelemetry Proto v0.5.0:

        # TODO: Update table after the decision on:
        # https://github.com/open-telemetry/opentelemetry-specification/issues/731.
        # By default, metrics recording using the OpenTelemetry API are exported as
        # (the table does not include MeasurementValueType to avoid extra rows):
        #
        #   Instrument         Type
        #   ----------------------------------------------
        #   Counter            Sum(aggregation_temporality=delta;is_monotonic=true)
        #   UpDownCounter      Sum(aggregation_temporality=delta;is_monotonic=false)
        #   ValueRecorder      TBD
        #   SumObserver        Sum(aggregation_temporality=cumulative;is_monotonic=true)
        #   UpDownSumObserver  Sum(aggregation_temporality=cumulative;is_monotonic=false)
        #   ValueObserver      Gauge()
        for sdk_metric in data:

            if sdk_metric.resource not in (
                sdk_resource_instrumentation_library_metrics.keys()
            ):
                sdk_resource_instrumentation_library_metrics[
                    sdk_metric.resource
                ] = InstrumentationLibraryMetrics()

            type_class = {
                int: {
                    "sum": {"class": IntSum, "argument": "int_sum"},
                    "gauge": {"class": IntGauge, "argument": "int_gauge"},
                    "data_point_class": IntDataPoint,
                },
                float: {
                    "sum": {"class": DoubleSum, "argument": "double_sum"},
                    "gauge": {
                        "class": DoubleGauge,
                        "argument": "double_gauge",
                    },
                    "data_point_class": DoubleDataPoint,
                },
            }

            value_type = sdk_metric.instrument.value_type

            sum_class = type_class[value_type]["sum"]["class"]
            gauge_class = type_class[value_type]["gauge"]["class"]
            data_point_class = type_class[value_type]["data_point_class"]

            if isinstance(sdk_metric.instrument, Counter):
                otlp_metric_data = sum_class(
                    data_points=_get_data_points(sdk_metric, data_point_class),
                    aggregation_temporality=(
                        AggregationTemporality.AGGREGATION_TEMPORALITY_DELTA
                    ),
                    is_monotonic=True,
                )
                argument = type_class[value_type]["sum"]["argument"]

            elif isinstance(sdk_metric.instrument, UpDownCounter):
                otlp_metric_data = sum_class(
                    data_points=_get_data_points(sdk_metric, data_point_class),
                    aggregation_temporality=(
                        AggregationTemporality.AGGREGATION_TEMPORALITY_DELTA
                    ),
                    is_monotonic=False,
                )
                argument = type_class[value_type]["sum"]["argument"]

            elif isinstance(sdk_metric.instrument, (ValueRecorder)):
                logger.warning("Skipping exporting of ValueRecorder metric")
                continue

            elif isinstance(sdk_metric.instrument, SumObserver):
                otlp_metric_data = sum_class(
                    data_points=_get_data_points(sdk_metric, data_point_class),
                    aggregation_temporality=(
                        AggregationTemporality.AGGREGATION_TEMPORALITY_CUMULATIVE
                    ),
                    is_monotonic=True,
                )
                argument = type_class[value_type]["sum"]["argument"]

            elif isinstance(sdk_metric.instrument, UpDownSumObserver):
                otlp_metric_data = sum_class(
                    data_points=_get_data_points(sdk_metric, data_point_class),
                    aggregation_temporality=(
                        AggregationTemporality.AGGREGATION_TEMPORALITY_CUMULATIVE
                    ),
                    is_monotonic=False,
                )
                argument = type_class[value_type]["sum"]["argument"]

            elif isinstance(sdk_metric.instrument, (ValueObserver)):
                otlp_metric_data = gauge_class(
                    data_points=_get_data_points(sdk_metric, data_point_class)
                )
                argument = type_class[value_type]["gauge"]["argument"]

            sdk_resource_instrumentation_library_metrics[
                sdk_metric.resource
            ].metrics.append(
                OTLPMetric(
                    **{
                        "name": sdk_metric.instrument.name,
                        "description": sdk_metric.instrument.description,
                        "unit": sdk_metric.instrument.unit,
                        argument: otlp_metric_data,
                    }
                )
            )

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
