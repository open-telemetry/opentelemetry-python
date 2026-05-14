import logging
from collections.abc import Callable
from os import environ
from typing import IO

from opentelemetry.exporter.otlp.json.file._internal import _format_line
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
from opentelemetry.sdk.metrics._internal.aggregation import (
    Aggregation,
    AggregationTemporality,
    ExplicitBucketHistogramAggregation,
    ExponentialBucketHistogramAggregation,
)
from opentelemetry.sdk.metrics._internal.export import MetricExporter, MetricExportResult
from opentelemetry.sdk.metrics._internal.point import MetricsData

_logger = logging.getLogger(__name__)


class FileMetricExporter(MetricExporter):
    def __init__(
        self,
        stream: IO[str],
        preferred_temporality: dict[type, AggregationTemporality]
        | None = None,
        preferred_aggregation: dict[type, Aggregation] | None = None,
        *,
        _formatter: Callable[[dict], str] | None = None,
    ) -> None:
        MetricExporter.__init__(
            self,
            preferred_temporality=_get_temporality(preferred_temporality),
            preferred_aggregation=_get_aggregation(preferred_aggregation),
        )
        self._stream = stream
        self._formatter = _formatter or _format_line
        self._shutdown = False

    def export(self, metrics_data: MetricsData, timeout_millis: float = 10_000, **kwargs) -> MetricExportResult:
        pass

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        pass

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        pass



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
        instrument_class_temporality = {
            Counter: AggregationTemporality.DELTA,
            UpDownCounter: AggregationTemporality.CUMULATIVE,
            Histogram: AggregationTemporality.DELTA,
            ObservableCounter: AggregationTemporality.DELTA,
            ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
            ObservableGauge: AggregationTemporality.CUMULATIVE,
        }

    elif temporality_preference == "LOWMEMORY":
        instrument_class_temporality = {
            Counter: AggregationTemporality.DELTA,
            UpDownCounter: AggregationTemporality.CUMULATIVE,
            Histogram: AggregationTemporality.DELTA,
            ObservableCounter: AggregationTemporality.CUMULATIVE,
            ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
            ObservableGauge: AggregationTemporality.CUMULATIVE,
        }

    else:
        if temporality_preference != ("CUMULATIVE"):
            _logger.warning(
                "Unrecognized OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE"
                " value found: "
                "%s, "
                "using CUMULATIVE",
                temporality_preference,
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

    if default_histogram_aggregation == ("base2_exponential_bucket_histogram"):
        instrument_class_aggregation = {
            Histogram: ExponentialBucketHistogramAggregation(),
        }

    else:
        if default_histogram_aggregation != ("explicit_bucket_histogram"):
            _logger.warning(
                (
                    "Invalid value for %s: %s, using explicit bucket "
                    "histogram aggregation"
                ),
                OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION,
                default_histogram_aggregation,
            )

        instrument_class_aggregation = {
            Histogram: ExplicitBucketHistogramAggregation(),
        }

    instrument_class_aggregation.update(preferred_aggregation or {})
    return instrument_class_aggregation
