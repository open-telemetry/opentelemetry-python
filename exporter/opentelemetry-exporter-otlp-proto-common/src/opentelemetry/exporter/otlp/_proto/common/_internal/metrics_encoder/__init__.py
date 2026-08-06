# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from logging import getLogger
from os import environ

from opentelemetry.exporter.otlp._proto.common._internal import (
    _encode_attributes,
    _encode_instrumentation_scope,
    _encode_span_id,
    _encode_trace_id,
)
from opentelemetry._proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
)
from opentelemetry._proto.metrics.v1.metrics_pb2 import (
    Exemplar,
    ExponentialHistogram,
    ExponentialHistogramDataPoint,
    Gauge,
    Histogram,
    HistogramDataPoint,
    Metric,
    NumberDataPoint,
    ResourceMetrics,
    ScopeMetrics,
    Sum,
)
from opentelemetry._proto.resource.v1.resource_pb2 import Resource as PB2Resource
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION,
    OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE,
)
from opentelemetry.sdk.metrics import (
    Counter,
    Exemplar as SDKExemplar,
    Histogram as SDKHistogram,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    Gauge as SDKGauge,
    MetricExporter,
    MetricsData,
    Sum as SDKSum,
)
from opentelemetry.sdk.metrics.export import (
    ExponentialHistogram as ExponentialHistogramType,
)
from opentelemetry.sdk.metrics.export import (
    Histogram as HistogramType,
)
from opentelemetry.sdk.metrics.view import (
    Aggregation,
    ExplicitBucketHistogramAggregation,
    ExponentialBucketHistogramAggregation,
)

_logger = getLogger(__name__)


class OTLPMetricExporterMixin:
    def _common_configuration(
        self,
        preferred_temporality: dict[type, AggregationTemporality] | None = None,
        preferred_aggregation: dict[type, Aggregation] | None = None,
    ) -> None:
        MetricExporter.__init__(
            self,
            preferred_temporality=self._get_temporality(preferred_temporality),
            preferred_aggregation=self._get_aggregation(preferred_aggregation),
        )

    def _get_temporality(
        self, preferred_temporality: dict[type, AggregationTemporality]
    ) -> dict[type, AggregationTemporality]:
        otel_exporter_otlp_metrics_temporality_preference = (
            environ.get(
                OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE,
                "CUMULATIVE",
            )
            .upper()
            .strip()
        )

        if otel_exporter_otlp_metrics_temporality_preference == "DELTA":
            instrument_class_temporality = {
                Counter: AggregationTemporality.DELTA,
                UpDownCounter: AggregationTemporality.CUMULATIVE,
                SDKHistogram: AggregationTemporality.DELTA,
                ObservableCounter: AggregationTemporality.DELTA,
                ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
                ObservableGauge: AggregationTemporality.CUMULATIVE,
            }
        elif otel_exporter_otlp_metrics_temporality_preference == "LOWMEMORY":
            instrument_class_temporality = {
                Counter: AggregationTemporality.DELTA,
                UpDownCounter: AggregationTemporality.CUMULATIVE,
                SDKHistogram: AggregationTemporality.DELTA,
                ObservableCounter: AggregationTemporality.CUMULATIVE,
                ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
                ObservableGauge: AggregationTemporality.CUMULATIVE,
            }
        else:
            if otel_exporter_otlp_metrics_temporality_preference != "CUMULATIVE":
                _logger.warning(
                    "Unrecognized OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE"
                    " value found: %s, using CUMULATIVE",
                    otel_exporter_otlp_metrics_temporality_preference,
                )
            instrument_class_temporality = {
                Counter: AggregationTemporality.CUMULATIVE,
                UpDownCounter: AggregationTemporality.CUMULATIVE,
                SDKHistogram: AggregationTemporality.CUMULATIVE,
                ObservableCounter: AggregationTemporality.CUMULATIVE,
                ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
                ObservableGauge: AggregationTemporality.CUMULATIVE,
            }

        instrument_class_temporality.update(preferred_temporality or {})
        return instrument_class_temporality

    def _get_aggregation(
        self, preferred_aggregation: dict[type, Aggregation]
    ) -> dict[type, Aggregation]:
        otel_exporter_otlp_metrics_default_histogram_aggregation = environ.get(
            OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION,
            "explicit_bucket_histogram",
        )

        if otel_exporter_otlp_metrics_default_histogram_aggregation == (
            "base2_exponential_bucket_histogram"
        ):
            instrument_class_aggregation: dict[type, Aggregation] = {
                SDKHistogram: ExponentialBucketHistogramAggregation(),
            }
        else:
            if otel_exporter_otlp_metrics_default_histogram_aggregation != (
                "explicit_bucket_histogram"
            ):
                _logger.warning(
                    "Invalid value for %s: %s, using explicit bucket histogram aggregation",
                    OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION,
                    otel_exporter_otlp_metrics_default_histogram_aggregation,
                )
            instrument_class_aggregation = {
                SDKHistogram: ExplicitBucketHistogramAggregation(),
            }

        instrument_class_aggregation.update(preferred_aggregation or {})
        return instrument_class_aggregation


class EncodingException(Exception):
    def __init__(self, original_exception, metric):
        super().__init__()
        self.original_exception = original_exception
        self.metric = metric

    def __str__(self):
        return f"{self.metric}\n{self.original_exception}"


def encode_metrics(data: MetricsData) -> ExportMetricsServiceRequest:
    resource_metrics_list = []

    for resource_metrics in data.resource_metrics:
        scope_metrics_list = []
        sdk_resource = resource_metrics.resource

        for scope_metrics in resource_metrics.scope_metrics:
            instrumentation_scope = scope_metrics.scope
            pb2_scope_metrics = ScopeMetrics(
                scope=_encode_instrumentation_scope(instrumentation_scope),
                schema_url=instrumentation_scope.schema_url,
            )

            for metric in scope_metrics.metrics:
                try:
                    pb2_metric = _encode_metric(metric)
                except Exception as ex:
                    raise EncodingException(ex, metric) from None
                if pb2_metric is not None:
                    pb2_scope_metrics.metrics.append(pb2_metric)

            scope_metrics_list.append(pb2_scope_metrics)

        resource_metrics_list.append(
            ResourceMetrics(
                resource=PB2Resource(
                    attributes=_encode_attributes(sdk_resource.attributes)
                ),
                scope_metrics=scope_metrics_list,
                schema_url=sdk_resource.schema_url,
            )
        )

    return ExportMetricsServiceRequest(resource_metrics=resource_metrics_list)


def _encode_metric(metric) -> Metric | None:
    kwargs: dict = dict(
        name=metric.name,
        description=metric.description,
        unit=metric.unit,
    )

    if isinstance(metric.data, SDKGauge):
        data_points = []
        for dp in metric.data.data_points:
            pt_kwargs: dict = dict(
                attributes=_encode_attributes(dp.attributes),
                time_unix_nano=dp.time_unix_nano,
                exemplars=_encode_exemplars(dp.exemplars),
            )
            if isinstance(dp.value, int):
                pt_kwargs["as_int"] = dp.value
            else:
                pt_kwargs["as_double"] = dp.value
            data_points.append(NumberDataPoint(**pt_kwargs))
        kwargs["gauge"] = Gauge(data_points=data_points)

    elif isinstance(metric.data, HistogramType):
        data_points = []
        for dp in metric.data.data_points:
            data_points.append(
                HistogramDataPoint(
                    attributes=_encode_attributes(dp.attributes),
                    time_unix_nano=dp.time_unix_nano,
                    start_time_unix_nano=dp.start_time_unix_nano,
                    exemplars=_encode_exemplars(dp.exemplars),
                    count=dp.count,
                    sum=dp.sum,
                    bucket_counts=list(dp.bucket_counts) if dp.bucket_counts else [],
                    explicit_bounds=list(dp.explicit_bounds) if dp.explicit_bounds else [],
                    max=dp.max,
                    min=dp.min,
                )
            )
        kwargs["histogram"] = Histogram(
            data_points=data_points,
            aggregation_temporality=metric.data.aggregation_temporality,
        )

    elif isinstance(metric.data, SDKSum):
        data_points = []
        for dp in metric.data.data_points:
            pt_kwargs = dict(
                attributes=_encode_attributes(dp.attributes),
                start_time_unix_nano=dp.start_time_unix_nano,
                time_unix_nano=dp.time_unix_nano,
                exemplars=_encode_exemplars(dp.exemplars),
            )
            if isinstance(dp.value, int):
                pt_kwargs["as_int"] = dp.value
            else:
                pt_kwargs["as_double"] = dp.value
            data_points.append(NumberDataPoint(**pt_kwargs))
        kwargs["sum"] = Sum(
            data_points=data_points,
            aggregation_temporality=metric.data.aggregation_temporality,
            is_monotonic=metric.data.is_monotonic,
        )

    elif isinstance(metric.data, ExponentialHistogramType):
        data_points = []
        for dp in metric.data.data_points:
            positive = negative = None
            if dp.positive.bucket_counts:
                positive = ExponentialHistogramDataPoint.Buckets(
                    offset=dp.positive.offset,
                    bucket_counts=list(dp.positive.bucket_counts),
                )
            if dp.negative.bucket_counts:
                negative = ExponentialHistogramDataPoint.Buckets(
                    offset=dp.negative.offset,
                    bucket_counts=list(dp.negative.bucket_counts),
                )
            data_points.append(
                ExponentialHistogramDataPoint(
                    attributes=_encode_attributes(dp.attributes),
                    time_unix_nano=dp.time_unix_nano,
                    start_time_unix_nano=dp.start_time_unix_nano,
                    exemplars=_encode_exemplars(dp.exemplars),
                    count=dp.count,
                    sum=dp.sum,
                    scale=dp.scale,
                    zero_count=dp.zero_count,
                    positive=positive,
                    negative=negative,
                    flags=dp.flags,
                    max=dp.max,
                    min=dp.min,
                )
            )
        kwargs["exponential_histogram"] = ExponentialHistogram(
            data_points=data_points,
            aggregation_temporality=metric.data.aggregation_temporality,
        )

    else:
        _logger.warning("unsupported data type %s", metric.data.__class__.__name__)
        return None

    return Metric(**kwargs)


def _encode_exemplars(sdk_exemplars: list[SDKExemplar]) -> list[Exemplar]:
    result = []
    for sdk_exemplar in sdk_exemplars:
        ex_kwargs: dict = dict(
            time_unix_nano=sdk_exemplar.time_unix_nano,
            filtered_attributes=_encode_attributes(sdk_exemplar.filtered_attributes),
        )
        if (
            sdk_exemplar.span_id is not None
            and sdk_exemplar.trace_id is not None
        ):
            ex_kwargs["span_id"] = _encode_span_id(sdk_exemplar.span_id)
            ex_kwargs["trace_id"] = _encode_trace_id(sdk_exemplar.trace_id)

        if isinstance(sdk_exemplar.value, float):
            ex_kwargs["as_double"] = sdk_exemplar.value
        elif isinstance(sdk_exemplar.value, int):
            ex_kwargs["as_int"] = sdk_exemplar.value
        else:
            raise ValueError("Exemplar value must be an int or float")

        result.append(Exemplar(**ex_kwargs))
    return result
