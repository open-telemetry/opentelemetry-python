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
from typing import List, Optional, Sequence, Type, TypeVar

from grpc import ChannelCredentials

from opentelemetry.configuration import Configuration
from opentelemetry.exporter.otlp.exporter import (
    OTLPExporterMixin,
    _get_resource_data,
    _load_credential_from_file,
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
    ExportRecord,
    MetricsExporter,
    MetricsExportResult,
)
from opentelemetry.sdk.metrics.export.aggregate import (
    HistogramAggregator,
    LastValueAggregator,
    MinMaxSumCountAggregator,
    SumAggregator,
    ValueObserverAggregator,
)

logger = logging.getLogger(__name__)
DataPointT = TypeVar("DataPointT", IntDataPoint, DoubleDataPoint)


def _get_data_points(
    export_record: ExportRecord,
    data_point_class: Type[DataPointT],
    aggregation_temporality: int,
) -> List[DataPointT]:

    if isinstance(export_record.aggregator, SumAggregator):
        value = export_record.aggregator.checkpoint

    elif isinstance(export_record.aggregator, MinMaxSumCountAggregator):
        # FIXME: How are values to be interpreted from this aggregator?
        raise Exception("MinMaxSumCount aggregator data not supported")

    elif isinstance(export_record.aggregator, HistogramAggregator):
        # FIXME: How are values to be interpreted from this aggregator?
        raise Exception("Histogram aggregator data not supported")

    elif isinstance(export_record.aggregator, LastValueAggregator):
        value = export_record.aggregator.checkpoint

    elif isinstance(export_record.aggregator, ValueObserverAggregator):
        value = export_record.aggregator.checkpoint.last

    if aggregation_temporality == (
        AggregationTemporality.AGGREGATION_TEMPORALITY_CUMULATIVE
    ):
        start_time_unix_nano = export_record.aggregator.first_timestamp
    else:
        start_time_unix_nano = (
            export_record.aggregator.initial_checkpoint_timestamp
        )

    return [
        data_point_class(
            labels=[
                StringKeyValue(key=str(label_key), value=str(label_value))
                for label_key, label_value in export_record.labels
            ],
            value=value,
            start_time_unix_nano=start_time_unix_nano,
            time_unix_nano=(export_record.aggregator.last_update_timestamp),
        )
    ]


class OTLPMetricsExporter(
    MetricsExporter,
    OTLPExporterMixin[
        ExportRecord, ExportMetricsServiceRequest, MetricsExportResult
    ],
):
    # pylint: disable=unsubscriptable-object
    """OTLP metrics exporter

    Args:
        endpoint: OpenTelemetry Collector receiver endpoint
        insecure: Connection type
        credentials: Credentials object for server authentication
        headers: Headers to send when exporting
        timeout: Backend request timeout in seconds
    """

    _stub = MetricsServiceStub
    _result = MetricsExportResult

    def __init__(
        self,
        endpoint: Optional[str] = None,
        insecure: Optional[bool] = None,
        credentials: Optional[ChannelCredentials] = None,
        headers: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        if insecure is None:
            insecure = Configuration().EXPORTER_OTLP_METRIC_INSECURE

        if (
            not insecure
            and Configuration().EXPORTER_OTLP_METRIC_CERTIFICATE is not None
        ):
            credentials = credentials or _load_credential_from_file(
                Configuration().EXPORTER_OTLP_METRIC_CERTIFICATE
            )

        super().__init__(
            **{
                "endpoint": endpoint
                or Configuration().EXPORTER_OTLP_METRIC_ENDPOINT,
                "insecure": insecure,
                "credentials": credentials,
                "headers": headers
                or Configuration().EXPORTER_OTLP_METRIC_HEADERS,
                "timeout": timeout
                or Configuration().EXPORTER_OTLP_METRIC_TIMEOUT,
            }
        )

    # pylint: disable=no-self-use
    def _translate_data(
        self, export_records: Sequence[ExportRecord]
    ) -> ExportMetricsServiceRequest:
        # pylint: disable=too-many-locals,no-member
        # pylint: disable=attribute-defined-outside-init

        sdk_resource_instrumentation_library_metrics = {}

        # The criteria to decide how to translate export_records is based on this table
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
        for export_record in export_records:

            if export_record.resource not in (
                sdk_resource_instrumentation_library_metrics.keys()
            ):
                sdk_resource_instrumentation_library_metrics[
                    export_record.resource
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

            value_type = export_record.instrument.value_type

            sum_class = type_class[value_type]["sum"]["class"]
            gauge_class = type_class[value_type]["gauge"]["class"]
            data_point_class = type_class[value_type]["data_point_class"]

            if isinstance(export_record.instrument, Counter):

                aggregation_temporality = (
                    AggregationTemporality.AGGREGATION_TEMPORALITY_CUMULATIVE
                )

                otlp_metric_data = sum_class(
                    data_points=_get_data_points(
                        export_record,
                        data_point_class,
                        aggregation_temporality,
                    ),
                    aggregation_temporality=aggregation_temporality,
                    is_monotonic=True,
                )
                argument = type_class[value_type]["sum"]["argument"]

            elif isinstance(export_record.instrument, UpDownCounter):

                aggregation_temporality = (
                    AggregationTemporality.AGGREGATION_TEMPORALITY_CUMULATIVE
                )

                otlp_metric_data = sum_class(
                    data_points=_get_data_points(
                        export_record,
                        data_point_class,
                        aggregation_temporality,
                    ),
                    aggregation_temporality=aggregation_temporality,
                    is_monotonic=False,
                )
                argument = type_class[value_type]["sum"]["argument"]

            elif isinstance(export_record.instrument, (ValueRecorder)):
                logger.warning("Skipping exporting of ValueRecorder metric")
                continue

            elif isinstance(export_record.instrument, SumObserver):

                aggregation_temporality = (
                    AggregationTemporality.AGGREGATION_TEMPORALITY_CUMULATIVE
                )

                otlp_metric_data = sum_class(
                    data_points=_get_data_points(
                        export_record,
                        data_point_class,
                        aggregation_temporality,
                    ),
                    aggregation_temporality=aggregation_temporality,
                    is_monotonic=True,
                )
                argument = type_class[value_type]["sum"]["argument"]

            elif isinstance(export_record.instrument, UpDownSumObserver):

                aggregation_temporality = (
                    AggregationTemporality.AGGREGATION_TEMPORALITY_CUMULATIVE
                )

                otlp_metric_data = sum_class(
                    data_points=_get_data_points(
                        export_record,
                        data_point_class,
                        aggregation_temporality,
                    ),
                    aggregation_temporality=aggregation_temporality,
                    is_monotonic=False,
                )
                argument = type_class[value_type]["sum"]["argument"]

            elif isinstance(export_record.instrument, (ValueObserver)):
                otlp_metric_data = gauge_class(
                    data_points=_get_data_points(
                        export_record,
                        data_point_class,
                        AggregationTemporality.AGGREGATION_TEMPORALITY_DELTA,
                    )
                )
                argument = type_class[value_type]["gauge"]["argument"]

            instrumentation_library_metrics = sdk_resource_instrumentation_library_metrics[
                export_record.resource
            ]

            instrumentation_library_metrics.metrics.append(
                OTLPMetric(
                    **{
                        "name": export_record.instrument.name,
                        "description": (export_record.instrument.description),
                        "unit": export_record.instrument.unit,
                        argument: otlp_metric_data,
                    }
                )
            )

            instrumentation_library_metrics.instrumentation_library.name = (
                export_record.instrument.meter.instrumentation_info.name
            )

            version = (
                export_record.instrument.meter.instrumentation_info.version
            )

            if version:
                (
                    instrumentation_library_metrics.instrumentation_library.version
                ) = version

        return ExportMetricsServiceRequest(
            resource_metrics=_get_resource_data(
                sdk_resource_instrumentation_library_metrics,
                ResourceMetrics,
                "metrics",
            )
        )

    def export(self, metrics: Sequence[ExportRecord]) -> MetricsExportResult:
        # pylint: disable=arguments-differ
        return self._export(metrics)
