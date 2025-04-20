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

"""JSON encoder for OpenTelemetry metrics to match the ProtoJSON format."""

import base64
import logging
from os import environ
from typing import Any, Dict, List, Optional, Sequence

from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION,
    OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE,
)
from opentelemetry.sdk.metrics import (
    Counter,
    Histogram,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    ExponentialHistogram,
    Gauge,
    Metric,
    MetricExporter,
    MetricsData,
    ScopeMetrics,
    Sum,
)
from opentelemetry.sdk.metrics.export import (
    Histogram as HistogramType,
)
from opentelemetry.sdk.metrics.view import (
    Aggregation,
    ExplicitBucketHistogramAggregation,
    ExponentialBucketHistogramAggregation,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.exporter.otlp.json.common._internal.encoder_utils import encode_id
from opentelemetry.exporter.otlp.json.common.encoding import IdEncoding

_logger = logging.getLogger(__name__)


class OTLPMetricExporterMixin:
    def _common_configuration(
        self,
        preferred_temporality: Optional[
            Dict[type, AggregationTemporality]
        ] = None,
        preferred_aggregation: Optional[Dict[type, Aggregation]] = None,
    ) -> None:
        MetricExporter.__init__(
            self,
            preferred_temporality=self._get_temporality(preferred_temporality),
            preferred_aggregation=self._get_aggregation(preferred_aggregation),
        )

    @staticmethod
    def _get_temporality(
        preferred_temporality: Dict[type, AggregationTemporality],
    ) -> Dict[type, AggregationTemporality]:
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
                Histogram: AggregationTemporality.DELTA,
                ObservableCounter: AggregationTemporality.DELTA,
                ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
                ObservableGauge: AggregationTemporality.CUMULATIVE,
            }

        elif otel_exporter_otlp_metrics_temporality_preference == "LOWMEMORY":
            instrument_class_temporality = {
                Counter: AggregationTemporality.DELTA,
                UpDownCounter: AggregationTemporality.CUMULATIVE,
                Histogram: AggregationTemporality.DELTA,
                ObservableCounter: AggregationTemporality.CUMULATIVE,
                ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
                ObservableGauge: AggregationTemporality.CUMULATIVE,
            }

        else:
            if otel_exporter_otlp_metrics_temporality_preference != (
                "CUMULATIVE"
            ):
                _logger.warning(
                    "Unrecognized OTEL_EXPORTER_METRICS_TEMPORALITY_PREFERENCE"
                    " value found: "
                    "%s, "
                    "using CUMULATIVE",
                    otel_exporter_otlp_metrics_temporality_preference,
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

    @staticmethod
    def _get_aggregation(
        preferred_aggregation: Dict[type, Aggregation],
    ) -> Dict[type, Aggregation]:
        otel_exporter_otlp_metrics_default_histogram_aggregation = environ.get(
            OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION,
            "explicit_bucket_histogram",
        )

        if otel_exporter_otlp_metrics_default_histogram_aggregation == (
            "base2_exponential_bucket_histogram"
        ):
            instrument_class_aggregation = {
                Histogram: ExponentialBucketHistogramAggregation(),
            }

        else:
            if otel_exporter_otlp_metrics_default_histogram_aggregation != (
                "explicit_bucket_histogram"
            ):
                _logger.warning(
                    (
                        "Invalid value for %s: %s, using explicit bucket "
                        "histogram aggregation"
                    ),
                    OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION,
                    otel_exporter_otlp_metrics_default_histogram_aggregation,
                )

            instrument_class_aggregation = {
                Histogram: ExplicitBucketHistogramAggregation(),
            }

        instrument_class_aggregation.update(preferred_aggregation or {})

        return instrument_class_aggregation


def encode_metrics(
        metrics_data: MetricsData,
        id_encoding: Optional[IdEncoding] = None) -> Dict[str, Any]:
    """Encodes metrics in the OTLP JSON format.

    Returns:
        A dict representing the metrics in OTLP JSON format as specified in the
        OpenTelemetry Protocol and ProtoJSON format.
    """
    id_encoding = id_encoding or IdEncoding.BASE64

    resource_metrics_list = []

    for resource_metrics in metrics_data.resource_metrics:
        resource_metrics_dict = {
            "resource": _encode_resource(resource_metrics.resource),
            "scopeMetrics": _encode_scope_metrics(
                resource_metrics.scope_metrics,
                id_encoding,
            ),
            "schemaUrl": resource_metrics.schema_url or "",
        }
        resource_metrics_list.append(resource_metrics_dict)

    return {"resourceMetrics": resource_metrics_list}


def _encode_resource(resource: Resource) -> Dict[str, Any]:
    """Encodes a resource into OTLP JSON format."""
    if not resource:
        return {"attributes": []}

    return {
        "attributes": _encode_attributes(resource.attributes),
        "droppedAttributesCount": 0,  # Not tracking dropped attributes yet
    }


def _encode_scope_metrics(
    scope_metrics_list: Sequence[ScopeMetrics],
    id_encoding: IdEncoding,
) -> List[Dict[str, Any]]:
    """Encodes a list of scope metrics into OTLP JSON format."""
    if not scope_metrics_list:
        return []

    result = []
    for scope_metrics in scope_metrics_list:
        result.append(
            {
                "scope": _encode_instrumentation_scope(scope_metrics.scope),
                "metrics": _encode_metrics_list(scope_metrics.metrics, id_encoding),
                "schemaUrl": scope_metrics.schema_url or "",
            }
        )

    return result


def _encode_instrumentation_scope(
    scope: Optional[InstrumentationScope],
) -> Dict[str, Any]:
    """Encodes an instrumentation scope into OTLP JSON format."""
    if scope is None:
        return {"name": "", "version": ""}

    return {
        "name": scope.name or "",
        "version": scope.version or "",
        "attributes": [],  # Not using attributes for scope yet
        "droppedAttributesCount": 0,
    }


def _encode_metrics_list(metrics: Sequence[Metric], id_encoding: IdEncoding) -> List[Dict[str, Any]]:
    """Encodes a list of metrics into OTLP JSON format."""
    if not metrics:
        return []

    result = []
    for metric in metrics:
        metric_dict = {
            "name": metric.name,
            "description": metric.description or "",
            "unit": metric.unit or "",
        }

        # Add data based on metric type
        if isinstance(metric.data, Sum):
            metric_dict["sum"] = _encode_sum(metric.data, id_encoding)
        elif isinstance(metric.data, Gauge):
            metric_dict["gauge"] = _encode_gauge(metric.data, id_encoding)
        elif isinstance(metric.data, HistogramType):
            metric_dict["histogram"] = _encode_histogram(metric.data, id_encoding)
        elif isinstance(metric.data, ExponentialHistogram):
            metric_dict["exponentialHistogram"] = (
                _encode_exponential_histogram(metric.data, id_encoding)
            )
        # Add other metric types as needed

        result.append(metric_dict)

    return result


def _encode_sum(sum_data: Sum, id_encoding: IdEncoding) -> Dict[str, Any]:
    """Encodes a Sum metric into OTLP JSON format."""
    result = {
        "dataPoints": _encode_number_data_points(sum_data.data_points, id_encoding),
        "aggregationTemporality": _get_aggregation_temporality(
            sum_data.aggregation_temporality
        ),
        "isMonotonic": sum_data.is_monotonic,
    }

    return result


def _encode_gauge(gauge_data: Gauge, id_encoding: IdEncoding) -> Dict[str, Any]:
    """Encodes a Gauge metric into OTLP JSON format."""
    return {
        "dataPoints": _encode_number_data_points(gauge_data.data_points, id_encoding),
    }


def _encode_histogram(histogram_data: HistogramType, id_encoding: IdEncoding) -> Dict[str, Any]:
    """Encodes a Histogram metric into OTLP JSON format."""
    data_points = []

    for point in histogram_data.data_points:
        point_dict = {
            "attributes": _encode_attributes(point.attributes),
            "startTimeUnixNano": str(point.start_time_unix_nano),
            "timeUnixNano": str(point.time_unix_nano),
            "count": str(point.count),
            "sum": point.sum if point.sum is not None else 0.0,
            "bucketCounts": [str(count) for count in point.bucket_counts],
            "explicitBounds": point.explicit_bounds,
        }

        # Add min/max if available
        if point.min is not None:
            point_dict["min"] = point.min

        if point.max is not None:
            point_dict["max"] = point.max

        # Optional exemplars field
        if hasattr(point, "exemplars") and point.exemplars:
            point_dict["exemplars"] = _encode_exemplars(point.exemplars, id_encoding)

        data_points.append(point_dict)

    return {
        "dataPoints": data_points,
        "aggregationTemporality": _get_aggregation_temporality(
            histogram_data.aggregation_temporality
        ),
    }


def _encode_exponential_histogram(
    histogram_data: ExponentialHistogram,
    id_encoding: IdEncoding,
) -> Dict[str, Any]:
    """Encodes an ExponentialHistogram metric into OTLP JSON format."""
    data_points = []

    for point in histogram_data.data_points:
        point_dict = {
            "attributes": _encode_attributes(point.attributes),
            "startTimeUnixNano": str(point.start_time_unix_nano),
            "timeUnixNano": str(point.time_unix_nano),
            "count": str(point.count),
            "sum": point.sum if point.sum is not None else 0.0,
            "scale": point.scale,
            "zeroCount": str(point.zero_count),
        }

        # Add positive buckets if available
        if point.positive and point.positive.bucket_counts:
            point_dict["positive"] = {
                "offset": point.positive.offset,
                "bucketCounts": [
                    str(count) for count in point.positive.bucket_counts
                ],
            }

        # Add negative buckets if available
        if point.negative and point.negative.bucket_counts:
            point_dict["negative"] = {
                "offset": point.negative.offset,
                "bucketCounts": [
                    str(count) for count in point.negative.bucket_counts
                ],
            }

        # Add min/max if available
        if point.min is not None:
            point_dict["min"] = point.min

        if point.max is not None:
            point_dict["max"] = point.max

        # Add flags if available
        if point.flags:
            point_dict["flags"] = point.flags

        # Add exemplars if available
        if hasattr(point, "exemplars") and point.exemplars:
            point_dict["exemplars"] = _encode_exemplars(point.exemplars, id_encoding)

        data_points.append(point_dict)

    return {
        "dataPoints": data_points,
        "aggregationTemporality": _get_aggregation_temporality(
            histogram_data.aggregation_temporality
        ),
    }


def _encode_number_data_points(
    data_points: Sequence[Any],
    id_encoding: IdEncoding
) -> List[Dict[str, Any]]:
    """Encodes number data points into OTLP JSON format."""
    result = []

    for point in data_points:
        point_dict = {
            "attributes": _encode_attributes(point.attributes),
            "startTimeUnixNano": str(point.start_time_unix_nano),
            "timeUnixNano": str(point.time_unix_nano),
        }

        # Add either int or double value based on point type
        if hasattr(point, "value") and isinstance(point.value, int):
            point_dict["asInt"] = str(
                point.value
            )  # int64 values as strings in JSON
        elif hasattr(point, "value"):
            point_dict["asDouble"] = float(point.value)

        # Optional exemplars field
        if hasattr(point, "exemplars") and point.exemplars:
            point_dict["exemplars"] = _encode_exemplars(point.exemplars, id_encoding)

        result.append(point_dict)

    return result


def _encode_exemplars(exemplars: Sequence[Any], id_encoding: IdEncoding) -> List[Dict[str, Any]]:
    """Encodes metric exemplars into OTLP JSON format."""
    result = []

    for exemplar in exemplars:
        exemplar_dict = {
            "filteredAttributes": _encode_attributes(
                exemplar.filtered_attributes
            ),
            "timeUnixNano": str(exemplar.time_unix_nano),
        }

        # Add trace info if available
        if hasattr(exemplar, "trace_id") and exemplar.trace_id:
            trace_id = encode_id(id_encoding, exemplar.trace_id, 16)
            exemplar_dict["traceId"] = trace_id

        if hasattr(exemplar, "span_id") and exemplar.span_id:
            span_id = encode_id(id_encoding, exemplar.span_id, 8)
            exemplar_dict["spanId"] = span_id

        # Add value based on type
        if hasattr(exemplar, "value") and isinstance(exemplar.value, int):
            exemplar_dict["asInt"] = str(exemplar.value)
        elif hasattr(exemplar, "value") and isinstance(exemplar.value, float):
            exemplar_dict["asDouble"] = exemplar.value

        result.append(exemplar_dict)

    return result


def _encode_attributes(attributes: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Encodes attributes into OTLP JSON format."""
    if not attributes:
        return []

    attribute_list = []
    for key, value in attributes.items():
        if value is None:
            continue

        attribute = {"key": key}
        attribute.update(_encode_attribute_value(value))
        attribute_list.append(attribute)

    return attribute_list


# pylint: disable=too-many-return-statements
def _encode_attribute_value(value: Any) -> Dict[str, Any]:
    """Encodes a single attribute value into OTLP JSON format."""
    if isinstance(value, bool):
        return {"value": {"boolValue": value}}
    if isinstance(value, int):
        return {"value": {"intValue": value}}
    if isinstance(value, float):
        return {"value": {"doubleValue": value}}
    if isinstance(value, str):
        return {"value": {"stringValue": value}}
    if isinstance(value, (list, tuple)):
        if not value:
            return {"value": {"arrayValue": {"values": []}}}

        array_value = {"values": []}
        for element in value:
            element_value = _encode_attribute_value(element)["value"]
            array_value["values"].append(element_value)

        return {"value": {"arrayValue": array_value}}
    if isinstance(value, bytes):
        return {
            "value": {"bytesValue": base64.b64encode(value).decode("ascii")}
        }
    # Convert anything else to string
    return {"value": {"stringValue": str(value)}}


def _get_aggregation_temporality(temporality) -> str:
    """Maps aggregation temporality to OTLP JSON string values."""
    if temporality == 1:  # DELTA
        return "AGGREGATION_TEMPORALITY_DELTA"
    if temporality == 2:  # CUMULATIVE
        return "AGGREGATION_TEMPORALITY_CUMULATIVE"
    return "AGGREGATION_TEMPORALITY_UNSPECIFIED"
