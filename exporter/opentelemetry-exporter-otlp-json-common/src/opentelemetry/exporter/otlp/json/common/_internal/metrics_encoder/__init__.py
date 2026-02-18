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
from __future__ import annotations

import logging
from collections.abc import Iterable

from opentelemetry.exporter.otlp.json.common._internal import (
    _encode_attributes,
    _encode_instrumentation_scope,
    _encode_span_id,
    _encode_trace_id,
)
from opentelemetry.proto_json.collector.metrics.v1.metrics_service import (
    ExportMetricsServiceRequest as JSONExportMetricsServiceRequest,
)
from opentelemetry.proto_json.metrics.v1 import metrics as json_metrics
from opentelemetry.proto_json.resource.v1.resource import (
    Resource as JSONResource,
)
from opentelemetry.sdk.metrics import (
    Exemplar,
)
from opentelemetry.sdk.metrics._internal.point import (
    ExponentialHistogramDataPoint,
    HistogramDataPoint,
    Metric,
    NumberDataPoint,
    ResourceMetrics,
    ScopeMetrics,
)
from opentelemetry.sdk.metrics.export import (
    ExponentialHistogram as ExponentialHistogramType,
)
from opentelemetry.sdk.metrics.export import (
    Gauge,
    MetricsData,
    Sum,
)
from opentelemetry.sdk.metrics.export import (
    Histogram as HistogramType,
)

_logger = logging.getLogger(__name__)


def encode_metrics(data: MetricsData) -> JSONExportMetricsServiceRequest:
    return JSONExportMetricsServiceRequest(
        resource_metrics=[
            _encode_resource_metrics(rm) for rm in data.resource_metrics
        ]
    )


def _encode_resource_metrics(
    rm: ResourceMetrics,
) -> json_metrics.ResourceMetrics:
    return json_metrics.ResourceMetrics(
        resource=JSONResource(
            attributes=_encode_attributes(rm.resource.attributes)
        ),
        scope_metrics=[_encode_scope_metrics(sm) for sm in rm.scope_metrics],
        schema_url=rm.resource.schema_url,
    )


def _encode_scope_metrics(
    sm: ScopeMetrics,
) -> json_metrics.ScopeMetrics:
    return json_metrics.ScopeMetrics(
        scope=_encode_instrumentation_scope(sm.scope),
        schema_url=sm.scope.schema_url,
        metrics=[_encode_metric(m) for m in sm.metrics],
    )


def _encode_metric(metric: Metric) -> json_metrics.Metric:
    json_metric = json_metrics.Metric(
        name=metric.name,
        description=metric.description,
        unit=metric.unit,
    )
    if isinstance(metric.data, Gauge):
        json_metric.gauge = json_metrics.Gauge(
            data_points=[
                _encode_gauge_data_point(pt) for pt in metric.data.data_points
            ]
        )
    elif isinstance(metric.data, HistogramType):
        json_metric.histogram = json_metrics.Histogram(
            data_points=[
                _encode_histogram_data_point(pt)
                for pt in metric.data.data_points
            ],
            aggregation_temporality=metric.data.aggregation_temporality,
        )
    elif isinstance(metric.data, Sum):
        json_metric.sum = json_metrics.Sum(
            data_points=[
                _encode_sum_data_point(pt) for pt in metric.data.data_points
            ],
            aggregation_temporality=metric.data.aggregation_temporality,
            is_monotonic=metric.data.is_monotonic,
        )
    elif isinstance(metric.data, ExponentialHistogramType):
        json_metric.exponential_histogram = json_metrics.ExponentialHistogram(
            data_points=[
                _encode_exponential_histogram_data_point(pt)
                for pt in metric.data.data_points
            ],
            aggregation_temporality=metric.data.aggregation_temporality,
        )
    else:
        _logger.warning(
            "unsupported data type %s",
            metric.data.__class__.__name__,
        )
    return json_metric


def _encode_gauge_data_point(
    data_point: NumberDataPoint,
) -> json_metrics.NumberDataPoint:
    pt = json_metrics.NumberDataPoint(
        attributes=_encode_attributes(data_point.attributes),
        time_unix_nano=data_point.time_unix_nano,
        exemplars=_encode_exemplars(data_point.exemplars),
    )
    if isinstance(data_point.value, int):
        pt.as_int = data_point.value
    else:
        pt.as_double = data_point.value
    return pt


def _encode_sum_data_point(
    data_point: NumberDataPoint,
) -> json_metrics.NumberDataPoint:
    pt = json_metrics.NumberDataPoint(
        attributes=_encode_attributes(data_point.attributes),
        start_time_unix_nano=data_point.start_time_unix_nano,
        time_unix_nano=data_point.time_unix_nano,
        exemplars=_encode_exemplars(data_point.exemplars),
    )
    if isinstance(data_point.value, int):
        pt.as_int = data_point.value
    else:
        pt.as_double = data_point.value
    return pt


def _encode_histogram_data_point(
    data_point: HistogramDataPoint,
) -> json_metrics.HistogramDataPoint:
    return json_metrics.HistogramDataPoint(
        attributes=_encode_attributes(data_point.attributes),
        time_unix_nano=data_point.time_unix_nano,
        start_time_unix_nano=data_point.start_time_unix_nano,
        exemplars=_encode_exemplars(data_point.exemplars),
        count=data_point.count,
        sum=data_point.sum,
        bucket_counts=data_point.bucket_counts,
        explicit_bounds=data_point.explicit_bounds,
        max=data_point.max,
        min=data_point.min,
    )


def _encode_exponential_histogram_data_point(
    data_point: ExponentialHistogramDataPoint,
) -> json_metrics.ExponentialHistogramDataPoint:
    return json_metrics.ExponentialHistogramDataPoint(
        attributes=_encode_attributes(data_point.attributes),
        time_unix_nano=data_point.time_unix_nano,
        start_time_unix_nano=data_point.start_time_unix_nano,
        exemplars=_encode_exemplars(data_point.exemplars),
        count=data_point.count,
        sum=data_point.sum,
        scale=data_point.scale,
        zero_count=data_point.zero_count,
        positive=(
            json_metrics.ExponentialHistogramDataPoint.Buckets(
                offset=data_point.positive.offset,
                bucket_counts=data_point.positive.bucket_counts,
            )
            if data_point.positive.bucket_counts
            else None
        ),
        negative=(
            json_metrics.ExponentialHistogramDataPoint.Buckets(
                offset=data_point.negative.offset,
                bucket_counts=data_point.negative.bucket_counts,
            )
            if data_point.negative.bucket_counts
            else None
        ),
        flags=data_point.flags,
        max=data_point.max,
        min=data_point.min,
    )


def _encode_exemplars(
    sdk_exemplars: Iterable[Exemplar],
) -> list[json_metrics.Exemplar]:
    """
    Converts a list of SDK Exemplars into a list of json proto Exemplars.

    Args:
        sdk_exemplars: An iterable of exemplars from the OpenTelemetry SDK.

    Returns:
        list: A list of json proto exemplars.
    """
    json_exemplars = []
    for sdk_exemplar in sdk_exemplars:
        if (
            sdk_exemplar.span_id is not None
            and sdk_exemplar.trace_id is not None
        ):
            json_exemplar = json_metrics.Exemplar(
                time_unix_nano=sdk_exemplar.time_unix_nano,
                span_id=_encode_span_id(sdk_exemplar.span_id),
                trace_id=_encode_trace_id(sdk_exemplar.trace_id),
                filtered_attributes=_encode_attributes(
                    sdk_exemplar.filtered_attributes
                ),
            )
        else:
            json_exemplar = json_metrics.Exemplar(
                time_unix_nano=sdk_exemplar.time_unix_nano,
                filtered_attributes=_encode_attributes(
                    sdk_exemplar.filtered_attributes
                ),
            )

        # Assign the value based on its type in the SDK exemplar
        if isinstance(sdk_exemplar.value, float):
            json_exemplar.as_double = sdk_exemplar.value
        elif isinstance(sdk_exemplar.value, int):
            json_exemplar.as_int = sdk_exemplar.value
        else:
            raise ValueError("Exemplar value must be an int or float")
        json_exemplars.append(json_exemplar)

    return json_exemplars
