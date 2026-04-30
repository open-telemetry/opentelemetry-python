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

# pyright: reportCallIssue=false

from __future__ import annotations

import logging
from collections.abc import Collection

from opentelemetry.exporter.otlp.json.common._internal import (
    _encode_attributes,
    _encode_instrumentation_scope,
    _encode_span_id,
    _encode_trace_id,
)
from opentelemetry.proto_json.collector.metrics.v1.metrics_service import (
    ExportMetricsServiceRequest as JSONExportMetricsServiceRequest,
)
from opentelemetry.proto_json.metrics.v1.metrics import (
    Exemplar as JSONExemplar,
)
from opentelemetry.proto_json.metrics.v1.metrics import (
    ExponentialHistogram as JSONExponentialHistogram,
)
from opentelemetry.proto_json.metrics.v1.metrics import (
    ExponentialHistogramDataPoint as JSONExponentialHistogramDataPoint,
)
from opentelemetry.proto_json.metrics.v1.metrics import Gauge as JSONGauge
from opentelemetry.proto_json.metrics.v1.metrics import (
    Histogram as JSONHistogram,
)
from opentelemetry.proto_json.metrics.v1.metrics import (
    HistogramDataPoint as JSONHistogramDataPoint,
)
from opentelemetry.proto_json.metrics.v1.metrics import Metric as JSONMetric
from opentelemetry.proto_json.metrics.v1.metrics import (
    NumberDataPoint as JSONNumberDataPoint,
)
from opentelemetry.proto_json.metrics.v1.metrics import (
    ResourceMetrics as JSONResourceMetrics,
)
from opentelemetry.proto_json.metrics.v1.metrics import (
    ScopeMetrics as JSONScopeMetrics,
)
from opentelemetry.proto_json.metrics.v1.metrics import Sum as JSONSum
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
    ExponentialHistogram,
    Gauge,
    Histogram,
    MetricsData,
    Sum,
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
) -> JSONResourceMetrics:
    return JSONResourceMetrics(
        resource=JSONResource(
            attributes=_encode_attributes(rm.resource.attributes)
        ),
        scope_metrics=[_encode_scope_metrics(sm) for sm in rm.scope_metrics],
        schema_url=rm.resource.schema_url,
    )


def _encode_scope_metrics(
    sm: ScopeMetrics,
) -> JSONScopeMetrics:
    return JSONScopeMetrics(
        scope=_encode_instrumentation_scope(sm.scope),
        schema_url=sm.scope.schema_url,
        metrics=[_encode_metric(m) for m in sm.metrics],
    )


def _encode_metric(metric: Metric) -> JSONMetric:
    json_metric = JSONMetric(
        name=metric.name,
        description=metric.description,
        unit=metric.unit,
    )
    if isinstance(metric.data, Gauge):
        json_metric.gauge = JSONGauge(
            data_points=[
                _encode_gauge_data_point(pt) for pt in metric.data.data_points
            ]
        )
    elif isinstance(metric.data, Histogram):
        json_metric.histogram = JSONHistogram(
            data_points=[
                _encode_histogram_data_point(pt)
                for pt in metric.data.data_points
            ],
            aggregation_temporality=metric.data.aggregation_temporality,
        )
    elif isinstance(metric.data, Sum):
        json_metric.sum = JSONSum(
            data_points=[
                _encode_sum_data_point(pt) for pt in metric.data.data_points
            ],
            aggregation_temporality=metric.data.aggregation_temporality,
            is_monotonic=metric.data.is_monotonic,
        )
    elif isinstance(metric.data, ExponentialHistogram):
        json_metric.exponential_histogram = JSONExponentialHistogram(
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
) -> JSONNumberDataPoint:
    pt = JSONNumberDataPoint(
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
) -> JSONNumberDataPoint:
    pt = JSONNumberDataPoint(
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
) -> JSONHistogramDataPoint:
    return JSONHistogramDataPoint(
        attributes=_encode_attributes(data_point.attributes),
        time_unix_nano=data_point.time_unix_nano,
        start_time_unix_nano=data_point.start_time_unix_nano,
        exemplars=_encode_exemplars(data_point.exemplars),
        count=data_point.count,
        sum=data_point.sum,
        bucket_counts=list(data_point.bucket_counts),
        explicit_bounds=list(data_point.explicit_bounds),
        max=data_point.max,
        min=data_point.min,
    )


def _encode_exponential_histogram_data_point(
    data_point: ExponentialHistogramDataPoint,
) -> JSONExponentialHistogramDataPoint:
    return JSONExponentialHistogramDataPoint(
        attributes=_encode_attributes(data_point.attributes),
        time_unix_nano=data_point.time_unix_nano,
        start_time_unix_nano=data_point.start_time_unix_nano,
        exemplars=_encode_exemplars(data_point.exemplars),
        count=data_point.count,
        sum=data_point.sum,
        scale=data_point.scale,
        zero_count=data_point.zero_count,
        positive=(
            JSONExponentialHistogramDataPoint.Buckets(
                offset=data_point.positive.offset,
                bucket_counts=list(data_point.positive.bucket_counts),
            )
            if data_point.positive.bucket_counts
            else None
        ),
        negative=(
            JSONExponentialHistogramDataPoint.Buckets(
                offset=data_point.negative.offset,
                bucket_counts=list(data_point.negative.bucket_counts),
            )
            if data_point.negative.bucket_counts
            else None
        ),
        flags=data_point.flags,
        max=data_point.max,
        min=data_point.min,
    )


def _encode_exemplars(
    sdk_exemplars: Collection[Exemplar],
) -> list[JSONExemplar]:
    json_exemplars = []
    for sdk_exemplar in sdk_exemplars:
        if (
            sdk_exemplar.span_id is not None
            and sdk_exemplar.trace_id is not None
        ):
            json_exemplar = JSONExemplar(
                time_unix_nano=sdk_exemplar.time_unix_nano,
                span_id=_encode_span_id(sdk_exemplar.span_id),
                trace_id=_encode_trace_id(sdk_exemplar.trace_id),
                filtered_attributes=_encode_attributes(
                    sdk_exemplar.filtered_attributes
                ),
            )
        else:
            json_exemplar = JSONExemplar(
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
