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

import logging
from typing import Dict, Sequence, Any, Callable, List, Mapping

from opentelemetry.exporter.otlp.proto.http.encoder import (
    _ProtobufEncoderMixin,
)

from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
)
from opentelemetry.proto.common.v1.common_pb2 import (
    AnyValue,
    ArrayValue,
    KeyValue,
    KeyValueList,
)
from opentelemetry.proto.common.v1.common_pb2 import InstrumentationScope
from opentelemetry.proto.resource.v1.resource_pb2 import Resource
from opentelemetry.proto.metrics.v1 import metrics_pb2 as pb2
from opentelemetry.sdk.metrics.export import (
    Gauge,
    Histogram as HistogramType,
    MetricsData,
    Sum,
)
from opentelemetry.sdk.resources import Resource as SDKResource

_logger = logging.getLogger(__name__)


class _ProtobufEncoder(
    _ProtobufEncoderMixin[MetricsData, ExportMetricsServiceRequest]
):
    @classmethod
    def serialize(cls, metrics_data: MetricsData) -> str:
        return cls.encode(metrics_data).SerializeToString()

    @staticmethod
    def encode(metrics_data: MetricsData) -> ExportMetricsServiceRequest:
        return ExportMetricsServiceRequest(
            resource_metrics=_translate_data(metrics_data)
        )


def _translate_data(data: MetricsData) -> List[Resource]:

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
                            attributes=_translate_attributes(
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
                            attributes=_translate_attributes(
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
                            attributes=_translate_attributes(
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
                        pb2_metric.sum.is_monotonic = metric.data.is_monotonic
                        pb2_metric.sum.data_points.append(pt)
                else:
                    _logger.warn("unsupported datapoint type %s", metric.point)
                    continue

                pb2_scope_metrics.metrics.append(pb2_metric)

    return get_resource_data(
        resource_metrics_dict,
        pb2.ResourceMetrics,
        "metrics",
    )


def _translate_attributes(attributes) -> Sequence[KeyValue]:
    output = []
    if attributes:

        for key, value in attributes.items():
            try:
                output.append(_translate_key_values(key, value))
            except Exception as error:  # pylint: disable=broad-except
                _logger.exception(error)
    return output


def get_resource_data(
    sdk_resource_scope_data: Dict[SDKResource, Any],  # ResourceDataT?
    resource_class: Callable[..., Resource],
    name: str,
) -> List[Resource]:

    resource_data = []

    for (
        sdk_resource,
        scope_data,
    ) in sdk_resource_scope_data.items():

        collector_resource = Resource()

        for key, value in sdk_resource.attributes.items():

            try:
                # pylint: disable=no-member
                collector_resource.attributes.append(
                    _translate_key_values(key, value)
                )
            except Exception as error:  # pylint: disable=broad-except
                _logger.exception(error)

        resource_data.append(
            resource_class(
                **{
                    "resource": collector_resource,
                    "scope_{}".format(name): scope_data.values(),
                }
            )
        )

    return resource_data


def _translate_key_values(key: str, value: Any) -> KeyValue:
    return KeyValue(key=key, value=_translate_value(value))


def _translate_value(value: Any) -> KeyValue:

    if isinstance(value, bool):
        any_value = AnyValue(bool_value=value)

    elif isinstance(value, str):
        any_value = AnyValue(string_value=value)

    elif isinstance(value, int):
        any_value = AnyValue(int_value=value)

    elif isinstance(value, float):
        any_value = AnyValue(double_value=value)

    elif isinstance(value, Sequence):
        any_value = AnyValue(
            array_value=ArrayValue(values=[_translate_value(v) for v in value])
        )

    elif isinstance(value, Mapping):
        any_value = AnyValue(
            kvlist_value=KeyValueList(
                values=[
                    _translate_key_values(str(k), v) for k, v in value.items()
                ]
            )
        )

    else:
        raise Exception(f"Invalid type {type(value)} of value {value}")

    return any_value
