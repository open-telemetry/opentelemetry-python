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
from typing import TYPE_CHECKING, Optional, Set, Type

from opentelemetry import metrics
from opentelemetry.sdk._configuration._common import _parse_headers
from opentelemetry.sdk._configuration._exceptions import ConfigurationError
from opentelemetry.sdk._configuration.models import (
    Aggregation as AggregationConfig,
)
from opentelemetry.sdk._configuration.models import (
    ConsoleMetricExporter as ConsoleMetricExporterConfig,
)
from opentelemetry.sdk._configuration.models import (
    ExemplarFilter as ExemplarFilterConfig,
)
from opentelemetry.sdk._configuration.models import (
    ExporterDefaultHistogramAggregation,
    ExporterTemporalityPreference,
    InstrumentType,
)
from opentelemetry.sdk._configuration.models import (
    MeterProvider as MeterProviderConfig,
)
from opentelemetry.sdk._configuration.models import (
    MetricReader as MetricReaderConfig,
)
from opentelemetry.sdk._configuration.models import (
    OtlpGrpcMetricExporter as OtlpGrpcMetricExporterConfig,
)
from opentelemetry.sdk._configuration.models import (
    OtlpHttpMetricExporter as OtlpHttpMetricExporterConfig,
)
from opentelemetry.sdk._configuration.models import (
    PeriodicMetricReader as PeriodicMetricReaderConfig,
)
from opentelemetry.sdk._configuration.models import (
    PushMetricExporter as PushMetricExporterConfig,
)
from opentelemetry.sdk._configuration.models import (
    View as ViewConfig,
)
from opentelemetry.sdk.metrics import (
    AlwaysOffExemplarFilter,
    AlwaysOnExemplarFilter,
    Counter,
    Histogram,
    MeterProvider,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    TraceBasedExemplarFilter,
    UpDownCounter,
    _Gauge,
)
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    ConsoleMetricExporter,
    MetricExporter,
    MetricReader,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.metrics.view import (
    Aggregation,
    DefaultAggregation,
    DropAggregation,
    ExplicitBucketHistogramAggregation,
    ExponentialBucketHistogramAggregation,
    LastValueAggregation,
    SumAggregation,
    View,
)

if TYPE_CHECKING:
    from opentelemetry.sdk.resources import Resource

_logger = logging.getLogger(__name__)


# Default interval/timeout per OTel spec (milliseconds).
_DEFAULT_EXPORT_INTERVAL_MILLIS = 60000
_DEFAULT_EXPORT_TIMEOUT_MILLIS = 30000

# Instrument type → SDK instrument class mapping (for View selectors).
_INSTRUMENT_TYPE_MAP: dict[InstrumentType, Type] = {
    InstrumentType.counter: Counter,
    InstrumentType.up_down_counter: UpDownCounter,
    InstrumentType.histogram: Histogram,
    InstrumentType.gauge: _Gauge,
    InstrumentType.observable_counter: ObservableCounter,
    InstrumentType.observable_gauge: ObservableGauge,
    InstrumentType.observable_up_down_counter: ObservableUpDownCounter,
}


def _map_temporality(
    pref: Optional[ExporterTemporalityPreference],
) -> dict[type, AggregationTemporality]:
    """Map a temporality preference to an explicit preferred_temporality dict.

    Always returns an explicit dict to suppress OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE.
    Default (None or cumulative) → all instruments CUMULATIVE.
    """
    if pref is None or pref == ExporterTemporalityPreference.cumulative:
        return {
            Counter: AggregationTemporality.CUMULATIVE,
            UpDownCounter: AggregationTemporality.CUMULATIVE,
            Histogram: AggregationTemporality.CUMULATIVE,
            ObservableCounter: AggregationTemporality.CUMULATIVE,
            ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
            ObservableGauge: AggregationTemporality.CUMULATIVE,
        }
    if pref == ExporterTemporalityPreference.delta:
        return {
            Counter: AggregationTemporality.DELTA,
            UpDownCounter: AggregationTemporality.CUMULATIVE,
            Histogram: AggregationTemporality.DELTA,
            ObservableCounter: AggregationTemporality.DELTA,
            ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
            ObservableGauge: AggregationTemporality.CUMULATIVE,
        }
    if pref == ExporterTemporalityPreference.low_memory:
        return {
            Counter: AggregationTemporality.DELTA,
            UpDownCounter: AggregationTemporality.CUMULATIVE,
            Histogram: AggregationTemporality.DELTA,
            ObservableCounter: AggregationTemporality.CUMULATIVE,
            ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
            ObservableGauge: AggregationTemporality.CUMULATIVE,
        }
    raise ConfigurationError(
        f"Unsupported temporality preference '{pref}'. "
        "Supported values: cumulative, delta, low_memory."
    )


def _map_histogram_aggregation(
    pref: Optional[ExporterDefaultHistogramAggregation],
) -> dict[type, Aggregation]:
    """Map a histogram aggregation preference to an explicit preferred_aggregation dict.

    Always returns an explicit dict to suppress
    OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION.
    Default (None or explicit_bucket_histogram) → ExplicitBucketHistogramAggregation.
    """
    if (
        pref is None
        or pref
        == ExporterDefaultHistogramAggregation.explicit_bucket_histogram
    ):
        return {Histogram: ExplicitBucketHistogramAggregation()}
    if (
        pref
        == ExporterDefaultHistogramAggregation.base2_exponential_bucket_histogram
    ):
        return {Histogram: ExponentialBucketHistogramAggregation()}
    raise ConfigurationError(
        f"Unsupported default histogram aggregation '{pref}'. "
        "Supported values: explicit_bucket_histogram, base2_exponential_bucket_histogram."
    )


def _create_aggregation(config: AggregationConfig) -> Aggregation:
    """Create an SDK Aggregation from config, passing through detail parameters."""
    if config.default is not None:
        return DefaultAggregation()
    if config.drop is not None:
        return DropAggregation()
    if config.explicit_bucket_histogram is not None:
        return ExplicitBucketHistogramAggregation(
            boundaries=config.explicit_bucket_histogram.boundaries,
            record_min_max=(
                config.explicit_bucket_histogram.record_min_max
                if config.explicit_bucket_histogram.record_min_max is not None
                else True
            ),
        )
    if config.base2_exponential_bucket_histogram is not None:
        kwargs = {}
        if config.base2_exponential_bucket_histogram.max_size is not None:
            kwargs["max_size"] = (
                config.base2_exponential_bucket_histogram.max_size
            )
        if config.base2_exponential_bucket_histogram.max_scale is not None:
            kwargs["max_scale"] = (
                config.base2_exponential_bucket_histogram.max_scale
            )
        return ExponentialBucketHistogramAggregation(**kwargs)
    if config.last_value is not None:
        return LastValueAggregation()
    if config.sum is not None:
        return SumAggregation()
    raise ConfigurationError(
        f"Unknown or unsupported aggregation type in config: {config!r}. "
        "Supported types: default, drop, explicit_bucket_histogram, "
        "base2_exponential_bucket_histogram, last_value, sum."
    )


def _create_view(config: ViewConfig) -> View:
    """Create an SDK View from config."""
    selector = config.selector
    stream = config.stream

    instrument_type = None
    if selector.instrument_type is not None:
        instrument_type = _INSTRUMENT_TYPE_MAP.get(selector.instrument_type)
        if instrument_type is None:
            raise ConfigurationError(
                f"Unknown instrument type: {selector.instrument_type!r}"
            )

    attribute_keys: Optional[Set[str]] = None
    if stream.attribute_keys is not None:
        if stream.attribute_keys.excluded:
            _logger.warning(
                "attribute_keys.excluded is not supported by the Python SDK View; "
                "the exclusion list will be ignored."
            )
        if stream.attribute_keys.included is not None:
            attribute_keys = set(stream.attribute_keys.included)

    aggregation = None
    if stream.aggregation is not None:
        aggregation = _create_aggregation(stream.aggregation)

    return View(
        instrument_type=instrument_type,
        instrument_name=selector.instrument_name,
        meter_name=selector.meter_name,
        meter_version=selector.meter_version,
        meter_schema_url=selector.meter_schema_url,
        instrument_unit=selector.unit,
        name=stream.name,
        description=stream.description,
        attribute_keys=attribute_keys,
        aggregation=aggregation,
    )


def _create_console_metric_exporter(
    config: ConsoleMetricExporterConfig,
) -> MetricExporter:
    """Create a ConsoleMetricExporter from config."""
    preferred_temporality = _map_temporality(config.temporality_preference)
    preferred_aggregation = _map_histogram_aggregation(
        config.default_histogram_aggregation
    )
    return ConsoleMetricExporter(
        preferred_temporality=preferred_temporality,
        preferred_aggregation=preferred_aggregation,
    )


def _map_compression_metric(
    value: Optional[str], compression_enum: type
) -> Optional[object]:
    """Map a compression string to the given Compression enum value."""
    if value is None or value.lower() == "none":
        return None
    if value.lower() == "gzip":
        return compression_enum.Gzip  # type: ignore[attr-defined]
    raise ConfigurationError(
        f"Unsupported compression value '{value}'. Supported values: 'gzip', 'none'."
    )


def _create_otlp_http_metric_exporter(
    config: OtlpHttpMetricExporterConfig,
) -> MetricExporter:
    """Create an OTLP HTTP metric exporter from config."""
    try:
        # pylint: disable=import-outside-toplevel,no-name-in-module
        from opentelemetry.exporter.otlp.proto.http import (  # type: ignore[import-untyped]  # noqa: PLC0415
            Compression,
        )
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import (  # type: ignore[import-untyped]  # noqa: PLC0415
            OTLPMetricExporter,
        )
    except ImportError as exc:
        raise ConfigurationError(
            "otlp_http metric exporter requires 'opentelemetry-exporter-otlp-proto-http'. "
            "Install it with: pip install opentelemetry-exporter-otlp-proto-http"
        ) from exc

    compression = _map_compression_metric(config.compression, Compression)
    headers = _parse_headers(config.headers, config.headers_list)
    timeout = (config.timeout / 1000.0) if config.timeout is not None else None
    preferred_temporality = _map_temporality(config.temporality_preference)
    preferred_aggregation = _map_histogram_aggregation(
        config.default_histogram_aggregation
    )

    return OTLPMetricExporter(  # type: ignore[return-value]
        endpoint=config.endpoint,
        headers=headers,
        timeout=timeout,
        compression=compression,  # type: ignore[arg-type]
        preferred_temporality=preferred_temporality,
        preferred_aggregation=preferred_aggregation,
    )


def _create_otlp_grpc_metric_exporter(
    config: OtlpGrpcMetricExporterConfig,
) -> MetricExporter:
    """Create an OTLP gRPC metric exporter from config."""
    try:
        # pylint: disable=import-outside-toplevel,no-name-in-module
        import grpc  # type: ignore[import-untyped]  # noqa: PLC0415

        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (  # type: ignore[import-untyped]  # noqa: PLC0415
            OTLPMetricExporter,
        )
    except ImportError as exc:
        raise ConfigurationError(
            "otlp_grpc metric exporter requires 'opentelemetry-exporter-otlp-proto-grpc'. "
            "Install it with: pip install opentelemetry-exporter-otlp-proto-grpc"
        ) from exc

    compression = _map_compression_metric(config.compression, grpc.Compression)
    headers = _parse_headers(config.headers, config.headers_list)
    timeout = (config.timeout / 1000.0) if config.timeout is not None else None
    preferred_temporality = _map_temporality(config.temporality_preference)
    preferred_aggregation = _map_histogram_aggregation(
        config.default_histogram_aggregation
    )

    return OTLPMetricExporter(  # type: ignore[return-value]
        endpoint=config.endpoint,
        headers=headers,
        timeout=timeout,
        compression=compression,  # type: ignore[arg-type]
        preferred_temporality=preferred_temporality,
        preferred_aggregation=preferred_aggregation,
    )


def _create_push_metric_exporter(
    config: PushMetricExporterConfig,
) -> MetricExporter:
    """Create a push metric exporter from config."""
    if config.console is not None:
        return _create_console_metric_exporter(config.console)
    if config.otlp_http is not None:
        return _create_otlp_http_metric_exporter(config.otlp_http)
    if config.otlp_grpc is not None:
        return _create_otlp_grpc_metric_exporter(config.otlp_grpc)
    if config.otlp_file_development is not None:
        raise ConfigurationError(
            "otlp_file_development metric exporter is experimental and not yet supported."
        )
    raise ConfigurationError(
        "No exporter type specified in push metric exporter config. "
        "Supported types: console, otlp_http, otlp_grpc."
    )


def _create_periodic_metric_reader(
    config: PeriodicMetricReaderConfig,
) -> PeriodicExportingMetricReader:
    """Create a PeriodicExportingMetricReader from config.

    Passes explicit interval/timeout defaults to suppress env var reading.
    """
    exporter = _create_push_metric_exporter(config.exporter)
    interval = (
        config.interval
        if config.interval is not None
        else _DEFAULT_EXPORT_INTERVAL_MILLIS
    )
    timeout = (
        config.timeout
        if config.timeout is not None
        else _DEFAULT_EXPORT_TIMEOUT_MILLIS
    )
    return PeriodicExportingMetricReader(
        exporter=exporter,
        export_interval_millis=float(interval),
        export_timeout_millis=float(timeout),
    )


def _create_metric_reader(config: MetricReaderConfig) -> MetricReader:
    """Create a MetricReader from config."""
    if config.periodic is not None:
        return _create_periodic_metric_reader(config.periodic)
    if config.pull is not None:
        raise ConfigurationError(
            "Pull metric readers (e.g. Prometheus) are experimental and not yet supported "
            "by declarative config. Use the SDK API directly to configure pull readers."
        )
    raise ConfigurationError(
        "No reader type specified in metric reader config. "
        "Supported types: periodic."
    )


def _create_exemplar_filter(
    value: ExemplarFilterConfig,
) -> object:
    """Create an SDK exemplar filter from config enum value."""
    if value == ExemplarFilterConfig.always_on:
        return AlwaysOnExemplarFilter()
    if value == ExemplarFilterConfig.always_off:
        return AlwaysOffExemplarFilter()
    if value == ExemplarFilterConfig.trace_based:
        return TraceBasedExemplarFilter()
    raise ConfigurationError(
        f"Unknown exemplar filter value: {value!r}. "
        "Supported values: always_on, always_off, trace_based."
    )


def create_meter_provider(
    config: Optional[MeterProviderConfig],
    resource: Optional[Resource] = None,
) -> MeterProvider:
    """Create an SDK MeterProvider from declarative config.

    Does NOT read OTEL_METRIC_EXPORT_INTERVAL, OTEL_METRICS_EXEMPLAR_FILTER,
    or any other env vars for values explicitly controlled by the config.
    Absent config values use OTel spec defaults, matching Java SDK behavior.

    Args:
        config: MeterProvider config from the parsed config file, or None.
        resource: Resource to attach to the provider.

    Returns:
        A configured MeterProvider.
    """
    # Always pass an explicit exemplar filter to suppress env var reading.
    # Spec default is trace_based.
    exemplar_filter: object = TraceBasedExemplarFilter()
    if config is not None and config.exemplar_filter is not None:
        exemplar_filter = _create_exemplar_filter(config.exemplar_filter)

    readers: list[MetricReader] = []
    views: list[View] = []

    if config is not None:
        for reader_config in config.readers:
            readers.append(_create_metric_reader(reader_config))
        if config.views:
            for view_config in config.views:
                views.append(_create_view(view_config))

    return MeterProvider(
        resource=resource,
        metric_readers=readers,
        exemplar_filter=exemplar_filter,  # type: ignore[arg-type]
        views=views,
    )


def configure_meter_provider(
    config: Optional[MeterProviderConfig],
    resource: Optional[Resource] = None,
) -> None:
    """Configure the global MeterProvider from declarative config.

    When config is None (meter_provider section absent from config file),
    the global is not set — matching Java/JS SDK behavior.

    Args:
        config: MeterProvider config from the parsed config file, or None.
        resource: Resource to attach to the provider.
    """
    if config is None:
        return
    metrics.set_meter_provider(create_meter_provider(config, resource))
