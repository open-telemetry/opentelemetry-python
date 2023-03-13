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
import logging

from opentelemetry.exporter.otlp.proto.common._internal import (
    _encode_attributes,
)
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
)
from opentelemetry.proto.common.v1.common_pb2 import InstrumentationScope
from opentelemetry.proto.metrics.v1 import metrics_pb2 as pb2
from opentelemetry.sdk.metrics.export import (
    MetricsData,
    Gauge,
    Histogram,
    Sum,
    ExponentialHistogram as ExponentialHistogramType,
)
from opentelemetry.proto.resource.v1.resource_pb2 import (
    Resource as PB2Resource,
)

_logger = logging.getLogger(__name__)


def encode_metrics(data: MetricsData) -> ExportMetricsServiceRequest:
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
                            attributes=_encode_attributes(
                                data_point.attributes
                            ),
                            time_unix_nano=data_point.time_unix_nano,
                        )
                        if isinstance(data_point.value, int):
                            pt.as_int = data_point.value
                        else:
                            pt.as_double = data_point.value
                        pb2_metric.gauge.data_points.append(pt)

                elif isinstance(metric.data, Histogram):
                    for data_point in metric.data.data_points:
                        pt = pb2.HistogramDataPoint(
                            attributes=_encode_attributes(
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
                            attributes=_encode_attributes(
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

                elif isinstance(metric.data, ExponentialHistogramType):
                    for data_point in metric.data.data_points:

                        if data_point.positive.bucket_counts:
                            positive = pb2.ExponentialHistogramDataPoint.Buckets(
                                offset=data_point.positive.offset,
                                bucket_counts=data_point.positive.bucket_counts,
                            )
                        else:
                            positive = None

                        if data_point.negative.bucket_counts:
                            negative = pb2.ExponentialHistogramDataPoint.Buckets(
                                offset=data_point.negative.offset,
                                bucket_counts=data_point.negative.bucket_counts,
                            )
                        else:
                            negative = None

                        pt = pb2.ExponentialHistogramDataPoint(
                            attributes=_encode_attributes(
                                data_point.attributes
                            ),
                            time_unix_nano=data_point.time_unix_nano,
                            start_time_unix_nano=(
                                data_point.start_time_unix_nano
                            ),
                            count=data_point.count,
                            sum=data_point.sum,
                            scale=data_point.scale,
                            zero_count=data_point.zero_count,
                            positive=positive,
                            negative=negative,
                            flags=data_point.flags,
                            max=data_point.max,
                            min=data_point.min,
                        )
                        pb2_metric.exponential_histogram.aggregation_temporality = (
                            metric.data.aggregation_temporality
                        )
                        pb2_metric.exponential_histogram.data_points.append(pt)

                else:
                    _logger.warning(
                        "unsupported data type %s",
                        metric.data.__class__.__name__,
                    )
                    continue

                pb2_scope_metrics.metrics.append(pb2_metric)

    resource_data = []
    for (
        sdk_resource,
        scope_data,
    ) in resource_metrics_dict.items():
        resource_data.append(
            pb2.ResourceMetrics(
                resource=PB2Resource(
                    attributes=_encode_attributes(sdk_resource.attributes)
                ),
                scope_metrics=scope_data.values(),
            )
        )
    resource_metrics = resource_data
    return ExportMetricsServiceRequest(resource_metrics=resource_metrics)
