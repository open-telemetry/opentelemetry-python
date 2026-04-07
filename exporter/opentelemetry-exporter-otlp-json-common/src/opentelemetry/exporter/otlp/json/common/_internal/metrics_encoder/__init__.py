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
from collections.abc import Collection, Iterable
from dataclasses import replace
from os import environ

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
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION,
    OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE,
)
from opentelemetry.sdk.metrics import (
    Counter,
    Exemplar,
    Histogram,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.sdk.metrics._internal.aggregation import (
    Aggregation,
    AggregationTemporality,
    ExplicitBucketHistogramAggregation,
    ExponentialBucketHistogramAggregation,
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
    ExponentialHistogram as ExponentialHistogramMetricData,
)
from opentelemetry.sdk.metrics.export import (
    Gauge as GaugeMetricData,
)
from opentelemetry.sdk.metrics.export import (
    Histogram as HistogramMetricData,
)
from opentelemetry.sdk.metrics.export import (
    MetricsData,
)
from opentelemetry.sdk.metrics.export import (
    Sum as SumMetricData,
)

_logger = logging.getLogger(__name__)

_METRIC_DATA_FIELDS = (
    "gauge",
    "sum",
    "histogram",
    "exponential_histogram",
    "summary",
)


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
    if isinstance(metric.data, GaugeMetricData):
        json_metric.gauge = JSONGauge(
            data_points=[
                _encode_gauge_data_point(pt) for pt in metric.data.data_points
            ]
        )
    elif isinstance(metric.data, HistogramMetricData):
        json_metric.histogram = JSONHistogram(
            data_points=[
                _encode_histogram_data_point(pt)
                for pt in metric.data.data_points
            ],
            aggregation_temporality=metric.data.aggregation_temporality,
        )
    elif isinstance(metric.data, SumMetricData):
        json_metric.sum = JSONSum(
            data_points=[
                _encode_sum_data_point(pt) for pt in metric.data.data_points
            ],
            aggregation_temporality=metric.data.aggregation_temporality,
            is_monotonic=metric.data.is_monotonic,
        )
    elif isinstance(metric.data, ExponentialHistogramMetricData):
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


def split_metrics_data(
    metrics_data: JSONExportMetricsServiceRequest,
    max_export_batch_size: int | None,
) -> Iterable[JSONExportMetricsServiceRequest]:
    """Split an ExportMetricsServiceRequest into batches of at most
    max_export_batch_size data points, preserving resource/scope hierarchy.
    """
    if max_export_batch_size is None:
        yield metrics_data
        return

    batch_size: int = 0
    resource_metrics_batch: list[JSONResourceMetrics] = []
    scope_metrics_batch: list[JSONScopeMetrics] = []
    metrics_batch: list[JSONMetric] = []

    for (
        resource_metrics,
        scope_metrics,
        metric,
        field_name,
        data_points,
    ) in _iter_metric_data_points(metrics_data):
        if (
            not resource_metrics_batch
            or resource_metrics_batch[-1].resource
            is not resource_metrics.resource
        ):
            scope_metrics_batch = []
            resource_metrics_batch.append(
                replace(resource_metrics, scope_metrics=scope_metrics_batch)
            )

        if (
            not scope_metrics_batch
            or scope_metrics_batch[-1].scope is not scope_metrics.scope
        ):
            metrics_batch = []
            scope_metrics_batch.append(
                replace(scope_metrics, metrics=metrics_batch)
            )

        data_points_batch: list = []
        metrics_batch.append(
            _build_metric_with_data_points(
                metric, field_name, data_points_batch
            )
        )

        for data_point in data_points:
            if batch_size >= max_export_batch_size:
                yield JSONExportMetricsServiceRequest(
                    resource_metrics=resource_metrics_batch
                )
                (
                    resource_metrics_batch,
                    scope_metrics_batch,
                    metrics_batch,
                    data_points_batch,
                ) = _build_empty_metric_batches(
                    resource_metrics, scope_metrics, metric, field_name
                )
                batch_size = 0
            data_points_batch.append(data_point)
            batch_size += 1

    if batch_size > 0:
        yield JSONExportMetricsServiceRequest(
            resource_metrics=resource_metrics_batch
        )


def _get_metric_data_field_name(metric: JSONMetric) -> str | None:
    return next(
        (f for f in _METRIC_DATA_FIELDS if getattr(metric, f) is not None),
        None,
    )


def _iter_metric_data_points(
    metrics_data: JSONExportMetricsServiceRequest,
) -> Iterable[
    tuple[JSONResourceMetrics, JSONScopeMetrics, JSONMetric, str, list]
]:
    for resource_metrics in metrics_data.resource_metrics:
        for scope_metrics in resource_metrics.scope_metrics:
            for metric in scope_metrics.metrics:
                field_name = _get_metric_data_field_name(metric)
                if field_name is None:
                    _logger.warning(
                        "Tried to split and export an unsupported metric type. Skipping."
                    )
                    continue
                yield (
                    resource_metrics,
                    scope_metrics,
                    metric,
                    field_name,
                    getattr(metric, field_name).data_points,
                )


def _build_metric_with_data_points(
    metric: JSONMetric,
    field_name: str,
    data_points: list,
) -> JSONMetric:
    new_data = replace(getattr(metric, field_name), data_points=data_points)
    return replace(metric, **{field_name: new_data})


def _build_empty_metric_batches(
    resource_metrics: JSONResourceMetrics,
    scope_metrics: JSONScopeMetrics,
    metric: JSONMetric,
    field_name: str,
) -> tuple[
    list[JSONResourceMetrics], list[JSONScopeMetrics], list[JSONMetric], list
]:
    data_points_batch = []
    metrics_batch = [
        _build_metric_with_data_points(metric, field_name, data_points_batch)
    ]
    scope_metrics_batch = [replace(scope_metrics, metrics=metrics_batch)]
    resource_metrics_batch = [
        replace(resource_metrics, scope_metrics=scope_metrics_batch)
    ]
    return (
        resource_metrics_batch,
        scope_metrics_batch,
        metrics_batch,
        data_points_batch,
    )


def _get_temporality(
    preferred_temporality: dict[type, AggregationTemporality] | None,
) -> dict[type, AggregationTemporality]:
    preference = (
        environ.get(
            OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE, "CUMULATIVE"
        )
        .upper()
        .strip()
    )

    if preference == "DELTA":
        instrument_class_temporality = {
            Counter: AggregationTemporality.DELTA,
            UpDownCounter: AggregationTemporality.CUMULATIVE,
            Histogram: AggregationTemporality.DELTA,
            ObservableCounter: AggregationTemporality.DELTA,
            ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
            ObservableGauge: AggregationTemporality.CUMULATIVE,
        }
    elif preference == "LOWMEMORY":
        instrument_class_temporality = {
            Counter: AggregationTemporality.DELTA,
            UpDownCounter: AggregationTemporality.CUMULATIVE,
            Histogram: AggregationTemporality.DELTA,
            ObservableCounter: AggregationTemporality.CUMULATIVE,
            ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
            ObservableGauge: AggregationTemporality.CUMULATIVE,
        }
    else:
        if preference != "CUMULATIVE":
            _logger.warning(
                "Unrecognized OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE"
                " value found: %s, using CUMULATIVE",
                preference,
            )
        instrument_class_temporality = {
            Counter: AggregationTemporality.CUMULATIVE,
            UpDownCounter: AggregationTemporality.CUMULATIVE,
            Histogram: AggregationTemporality.CUMULATIVE,
            ObservableCounter: AggregationTemporality.CUMULATIVE,
            ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
            ObservableGauge: AggregationTemporality.CUMULATIVE,
        }

    instrument_class_temporality.update(preferred_temporality or {})
    return instrument_class_temporality


def _get_aggregation(
    preferred_aggregation: dict[type, Aggregation] | None,
) -> dict[type, Aggregation]:
    default_histogram_aggregation = environ.get(
        OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION,
        "explicit_bucket_histogram",
    )

    if default_histogram_aggregation == "base2_exponential_bucket_histogram":
        instrument_class_aggregation: dict[type, Aggregation] = {
            Histogram: ExponentialBucketHistogramAggregation(),
        }
    else:
        if default_histogram_aggregation != "explicit_bucket_histogram":
            _logger.warning(
                "Invalid value for %s: %s, using explicit bucket histogram aggregation",
                OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION,
                default_histogram_aggregation,
            )
        instrument_class_aggregation = {
            Histogram: ExplicitBucketHistogramAggregation(),
        }

    instrument_class_aggregation.update(preferred_aggregation or {})
    return instrument_class_aggregation
