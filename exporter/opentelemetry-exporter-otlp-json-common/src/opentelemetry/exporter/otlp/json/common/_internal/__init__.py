# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pyright: reportCallIssue=false

from __future__ import annotations

import logging
from collections.abc import Collection, Mapping, Sequence
from os import environ
from typing import (
    Any,
    cast,
)

from opentelemetry.proto_json.common.v1.common import AnyValue as JSONAnyValue
from opentelemetry.proto_json.common.v1.common import (
    ArrayValue as JSONArrayValue,
)
from opentelemetry.proto_json.common.v1.common import (
    InstrumentationScope as JSONInstrumentationScope,
)
from opentelemetry.proto_json.common.v1.common import KeyValue as JSONKeyValue
from opentelemetry.proto_json.common.v1.common import (
    KeyValueList as JSONKeyValueList,
)
from opentelemetry.proto_json.resource.v1.resource import (
    Resource as JSONResource,
)
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
from opentelemetry.sdk.metrics.export import AggregationTemporality
from opentelemetry.sdk.metrics.view import (
    Aggregation,
    ExplicitBucketHistogramAggregation,
    ExponentialBucketHistogramAggregation,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.util.types import Attributes

_logger = logging.getLogger(__name__)


def _encode_instrumentation_scope(
    instrumentation_scope: InstrumentationScope | None,
) -> JSONInstrumentationScope:
    return (
        JSONInstrumentationScope(
            name=instrumentation_scope.name,
            version=instrumentation_scope.version,
            attributes=_encode_attributes(instrumentation_scope.attributes),
        )
        if instrumentation_scope is not None
        else JSONInstrumentationScope()
    )


def _encode_resource(resource: Resource) -> JSONResource:
    return JSONResource(attributes=_encode_attributes(resource.attributes))


# pylint: disable-next=too-many-return-statements
def _encode_value(value: Any, allow_null: bool = False) -> JSONAnyValue | None:
    if allow_null and value is None:
        return None
    if isinstance(value, bool):
        return JSONAnyValue(bool_value=value)
    if isinstance(value, str):
        return JSONAnyValue(string_value=value)
    if isinstance(value, int):
        return JSONAnyValue(int_value=value)
    if isinstance(value, float):
        return JSONAnyValue(double_value=value)
    if isinstance(value, bytes):
        return JSONAnyValue(bytes_value=value)
    if isinstance(value, Sequence):
        return JSONAnyValue(
            array_value=JSONArrayValue(
                values=cast(
                    list[JSONAnyValue],
                    _encode_array(value, allow_null=allow_null),
                )
            )
        )
    if isinstance(value, Mapping):
        return JSONAnyValue(
            kvlist_value=JSONKeyValueList(
                values=[
                    _encode_key_value(str(k), v, allow_null=allow_null)
                    for k, v in value.items()
                ]
            )
        )
    raise TypeError(f"Invalid type {type(value)} of value {value}")


def _encode_key_value(
    key: str, value: Any, allow_null: bool = False
) -> JSONKeyValue:
    return JSONKeyValue(
        key=key, value=_encode_value(value, allow_null=allow_null)
    )


def _encode_array(
    array: Collection[Any], allow_null: bool = False
) -> list[JSONAnyValue | None]:
    if not allow_null:
        # Let the exception get raised by _encode_value()
        return [_encode_value(v, allow_null=allow_null) for v in array]

    return [
        _encode_value(v, allow_null=allow_null)
        if v is not None
        else JSONAnyValue()
        for v in array
    ]


def _encode_span_id(span_id: int) -> bytes:
    return span_id.to_bytes(length=8, byteorder="big", signed=False)


def _encode_trace_id(trace_id: int) -> bytes:
    return trace_id.to_bytes(length=16, byteorder="big", signed=False)


def _encode_attributes(
    attributes: Attributes | None,
    allow_null: bool = False,
) -> list[JSONKeyValue]:
    if not attributes:
        return []
    json_attributes = []
    for key, value in attributes.items():
        # pylint: disable=broad-exception-caught
        try:
            json_attributes.append(
                _encode_key_value(key, value, allow_null=allow_null)
            )
        except Exception as error:
            _logger.exception("Failed to encode key %s: %s", key, error)
    return json_attributes


def _get_temporality(
    preferred_temporality: dict[type, AggregationTemporality] | None,
) -> dict[type, AggregationTemporality]:
    temporality_preference = (
        environ.get(
            OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE,
            "CUMULATIVE",
        )
        .upper()
        .strip()
    )

    if temporality_preference == "DELTA":
        instrument_class_temporality: dict[type, AggregationTemporality] = {
            Counter: AggregationTemporality.DELTA,
            UpDownCounter: AggregationTemporality.CUMULATIVE,
            Histogram: AggregationTemporality.DELTA,
            ObservableCounter: AggregationTemporality.DELTA,
            ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
            ObservableGauge: AggregationTemporality.CUMULATIVE,
        }

    elif temporality_preference == "LOWMEMORY":
        instrument_class_temporality: dict[type, AggregationTemporality] = {
            Counter: AggregationTemporality.DELTA,
            UpDownCounter: AggregationTemporality.CUMULATIVE,
            Histogram: AggregationTemporality.DELTA,
            ObservableCounter: AggregationTemporality.CUMULATIVE,
            ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
            ObservableGauge: AggregationTemporality.CUMULATIVE,
        }

    else:
        if temporality_preference != "CUMULATIVE":
            _logger.warning(
                "Unrecognized OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE"
                " value found: "
                "%s, "
                "using CUMULATIVE",
                temporality_preference,
            )
        instrument_class_temporality: dict[type, AggregationTemporality] = {
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
                (
                    "Invalid value for %s: %s, using explicit bucket "
                    "histogram aggregation"
                ),
                OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION,
                default_histogram_aggregation,
            )

        instrument_class_aggregation: dict[type, Aggregation] = {
            Histogram: ExplicitBucketHistogramAggregation(),
        }

    instrument_class_aggregation.update(preferred_aggregation or {})
    return instrument_class_aggregation
