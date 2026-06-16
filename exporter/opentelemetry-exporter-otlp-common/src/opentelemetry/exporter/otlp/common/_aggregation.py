# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
import os

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

_logger = logging.getLogger(__name__)


def _get_temporality(
    preferred_temporality: dict[type, AggregationTemporality] | None,
) -> dict[type, AggregationTemporality]:
    temporality_preference = (
        os.environ.get(
            OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE,
            "CUMULATIVE",
        )
        .upper()
        .strip()
    )

    match temporality_preference:
        case "DELTA":
            instrument_class_temporality: dict[
                type, AggregationTemporality
            ] = {
                Counter: AggregationTemporality.DELTA,
                UpDownCounter: AggregationTemporality.CUMULATIVE,
                Histogram: AggregationTemporality.DELTA,
                ObservableCounter: AggregationTemporality.DELTA,
                ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
                ObservableGauge: AggregationTemporality.CUMULATIVE,
            }
        case "LOWMEMORY":
            instrument_class_temporality: dict[
                type, AggregationTemporality
            ] = {
                Counter: AggregationTemporality.DELTA,
                UpDownCounter: AggregationTemporality.CUMULATIVE,
                Histogram: AggregationTemporality.DELTA,
                ObservableCounter: AggregationTemporality.CUMULATIVE,
                ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
                ObservableGauge: AggregationTemporality.CUMULATIVE,
            }
        case _:
            if temporality_preference != "CUMULATIVE":
                _logger.warning(
                    (
                        "Invalid value for %s: %s, using cumulative "
                        "temporality aggregation"
                    ),
                    OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE,
                    temporality_preference,
                )
            instrument_class_temporality: dict[
                type, AggregationTemporality
            ] = {
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
    default_histogram_aggregation = (
        os.environ.get(
            OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION,
            "explicit_bucket_histogram",
        )
        .upper()
        .strip()
    )

    match default_histogram_aggregation:
        case "BASE2_EXPONENTIAL_BUCKET_HISTOGRAM":
            instrument_class_aggregation: dict[type, Aggregation] = {
                Histogram: ExponentialBucketHistogramAggregation(),
            }
        case _:
            if default_histogram_aggregation != "EXPLICIT_BUCKET_HISTOGRAM":
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
