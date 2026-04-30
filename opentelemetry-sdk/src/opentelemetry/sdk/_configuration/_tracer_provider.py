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
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk._configuration._common import (
    _parse_headers,
    load_entry_point,
)
from opentelemetry.sdk._configuration._exceptions import ConfigurationError
from opentelemetry.sdk._configuration.models import (
    OtlpGrpcExporter as OtlpGrpcExporterConfig,
)
from opentelemetry.sdk._configuration.models import (
    OtlpHttpExporter as OtlpHttpExporterConfig,
)
from opentelemetry.sdk._configuration.models import (
    ParentBasedSampler as ParentBasedSamplerConfig,
)
from opentelemetry.sdk._configuration.models import (
    Sampler as SamplerConfig,
)
from opentelemetry.sdk._configuration.models import (
    SpanExporter as SpanExporterConfig,
)
from opentelemetry.sdk._configuration.models import (
    SpanLimits as SpanLimitsConfig,
)
from opentelemetry.sdk._configuration.models import (
    SpanProcessor as SpanProcessorConfig,
)
from opentelemetry.sdk._configuration.models import (
    TracerProvider as TracerProviderConfig,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import (
    _DEFAULT_OTEL_EVENT_ATTRIBUTE_COUNT_LIMIT,
    _DEFAULT_OTEL_LINK_ATTRIBUTE_COUNT_LIMIT,
    _DEFAULT_OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT,
    _DEFAULT_OTEL_SPAN_EVENT_COUNT_LIMIT,
    _DEFAULT_OTEL_SPAN_LINK_COUNT_LIMIT,
    SpanLimits,
    TracerProvider,
)
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
    SpanExporter,
)
from opentelemetry.sdk.trace.sampling import (
    ALWAYS_OFF,
    ALWAYS_ON,
    ParentBased,
    Sampler,
    TraceIdRatioBased,
)

_logger = logging.getLogger(__name__)

# Default sampler per the OTel spec: parent_based with always_on root.
_DEFAULT_SAMPLER = ParentBased(root=ALWAYS_ON)


def _create_otlp_http_span_exporter(
    config: OtlpHttpExporterConfig,
) -> SpanExporter:
    """Create an OTLP HTTP span exporter from config."""
    try:
        # pylint: disable=import-outside-toplevel,no-name-in-module
        from opentelemetry.exporter.otlp.proto.http import (  # type: ignore[import-untyped]  # noqa: PLC0415
            Compression,
        )
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (  # type: ignore[import-untyped]  # noqa: PLC0415
            OTLPSpanExporter,
        )
    except ImportError as exc:
        raise ConfigurationError(
            "otlp_http span exporter requires 'opentelemetry-exporter-otlp-proto-http'. "
            "Install it with: pip install opentelemetry-exporter-otlp-proto-http"
        ) from exc

    compression = _map_compression(config.compression, Compression)
    headers = _parse_headers(config.headers, config.headers_list)
    timeout = (config.timeout / 1000.0) if config.timeout is not None else None

    return OTLPSpanExporter(  # type: ignore[return-value]
        endpoint=config.endpoint,
        headers=headers,
        timeout=timeout,
        compression=compression,  # type: ignore[arg-type]
    )


def _map_compression(
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


def _create_otlp_grpc_span_exporter(
    config: OtlpGrpcExporterConfig,
) -> SpanExporter:
    """Create an OTLP gRPC span exporter from config."""
    try:
        # pylint: disable=import-outside-toplevel,no-name-in-module
        import grpc  # type: ignore[import-untyped]  # noqa: PLC0415

        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # type: ignore[import-untyped]  # noqa: PLC0415
            OTLPSpanExporter,
        )
    except ImportError as exc:
        raise ConfigurationError(
            "otlp_grpc span exporter requires 'opentelemetry-exporter-otlp-proto-grpc'. "
            "Install it with: pip install opentelemetry-exporter-otlp-proto-grpc"
        ) from exc

    compression = _map_compression(config.compression, grpc.Compression)
    headers = _parse_headers(config.headers, config.headers_list)
    timeout = (config.timeout / 1000.0) if config.timeout is not None else None

    return OTLPSpanExporter(  # type: ignore[return-value]
        endpoint=config.endpoint,
        headers=headers,
        timeout=timeout,
        compression=compression,  # type: ignore[arg-type]
    )


_SPAN_EXPORTER_REGISTRY: dict = {
    "otlp_http": _create_otlp_http_span_exporter,
    "otlp_grpc": _create_otlp_grpc_span_exporter,
    "console": lambda _: ConsoleSpanExporter(),
}


def _create_span_exporter(config: SpanExporterConfig) -> SpanExporter:
    """Create a span exporter from config.

    Known exporter types are checked via typed fields on the SpanExporter
    dataclass. Unknown exporter names captured in additional_properties
    by the @_additional_properties decorator are loaded via the
    ``opentelemetry_traces_exporter`` entry point group.
    """
    for name, factory in _SPAN_EXPORTER_REGISTRY.items():
        value = getattr(config, name, None)
        if value is not None:
            return factory(value)
    if config.additional_properties:
        name = next(iter(config.additional_properties))
        return load_entry_point("opentelemetry_traces_exporter", name)()
    raise ConfigurationError(
        "No exporter type specified in span exporter config. "
        "Supported types: otlp_http, otlp_grpc, console."
    )


def _create_span_processor(
    config: SpanProcessorConfig,
) -> BatchSpanProcessor | SimpleSpanProcessor:
    """Create a span processor from config."""
    if config.batch is not None:
        exporter = _create_span_exporter(config.batch.exporter)
        return BatchSpanProcessor(
            exporter,
            max_queue_size=config.batch.max_queue_size,
            schedule_delay_millis=config.batch.schedule_delay,
            max_export_batch_size=config.batch.max_export_batch_size,
            export_timeout_millis=config.batch.export_timeout,
        )
    if config.simple is not None:
        return SimpleSpanProcessor(
            _create_span_exporter(config.simple.exporter)
        )
    raise ConfigurationError(
        "No processor type specified in span processor config. "
        "Supported types: batch, simple."
    )


def _create_sampler(config: SamplerConfig) -> Sampler:
    """Create a sampler from config."""
    if config.always_on is not None:
        return ALWAYS_ON
    if config.always_off is not None:
        return ALWAYS_OFF
    if config.trace_id_ratio_based is not None:
        ratio = config.trace_id_ratio_based.ratio
        return TraceIdRatioBased(ratio if ratio is not None else 1.0)
    if config.parent_based is not None:
        return _create_parent_based_sampler(config.parent_based)
    raise ConfigurationError(
        f"Unknown or unsupported sampler type in config: {config!r}. "
        "Supported types: always_on, always_off, trace_id_ratio_based, parent_based."
    )


def _create_parent_based_sampler(config: ParentBasedSamplerConfig) -> Sampler:
    """Create a ParentBased sampler from config, applying SDK defaults for absent delegates."""
    root = (
        _create_sampler(config.root) if config.root is not None else ALWAYS_ON
    )
    kwargs: dict = {"root": root}
    if config.remote_parent_sampled is not None:
        kwargs["remote_parent_sampled"] = _create_sampler(
            config.remote_parent_sampled
        )
    if config.remote_parent_not_sampled is not None:
        kwargs["remote_parent_not_sampled"] = _create_sampler(
            config.remote_parent_not_sampled
        )
    if config.local_parent_sampled is not None:
        kwargs["local_parent_sampled"] = _create_sampler(
            config.local_parent_sampled
        )
    if config.local_parent_not_sampled is not None:
        kwargs["local_parent_not_sampled"] = _create_sampler(
            config.local_parent_not_sampled
        )
    return ParentBased(**kwargs)


def _create_span_limits(config: SpanLimitsConfig) -> SpanLimits:
    """Create SpanLimits from config.

    Absent fields use the OTel spec defaults (128 for counts, unlimited for lengths).
    Explicit values suppress env-var reading — matching Java SDK behavior.
    """
    return SpanLimits(
        max_span_attributes=(
            config.attribute_count_limit
            if config.attribute_count_limit is not None
            else _DEFAULT_OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT
        ),
        max_events=(
            config.event_count_limit
            if config.event_count_limit is not None
            else _DEFAULT_OTEL_SPAN_EVENT_COUNT_LIMIT
        ),
        max_links=(
            config.link_count_limit
            if config.link_count_limit is not None
            else _DEFAULT_OTEL_SPAN_LINK_COUNT_LIMIT
        ),
        max_event_attributes=(
            config.event_attribute_count_limit
            if config.event_attribute_count_limit is not None
            else _DEFAULT_OTEL_EVENT_ATTRIBUTE_COUNT_LIMIT
        ),
        max_link_attributes=(
            config.link_attribute_count_limit
            if config.link_attribute_count_limit is not None
            else _DEFAULT_OTEL_LINK_ATTRIBUTE_COUNT_LIMIT
        ),
        max_attribute_length=config.attribute_value_length_limit,
    )


def create_tracer_provider(
    config: Optional[TracerProviderConfig],
    resource: Optional[Resource] = None,
) -> TracerProvider:
    """Create an SDK TracerProvider from declarative config.

    Does NOT read OTEL_TRACES_SAMPLER, OTEL_SPAN_*_LIMIT, or any other env vars
    for values that are explicitly controlled by the config. Absent config values
    use OTel spec defaults (not env vars), matching Java SDK behavior.

    Args:
        config: TracerProvider config from the parsed config file, or None.
        resource: Resource to attach to the provider.

    Returns:
        A configured TracerProvider.
    """
    sampler = (
        _create_sampler(config.sampler)
        if config is not None and config.sampler is not None
        else _DEFAULT_SAMPLER
    )
    span_limits = (
        _create_span_limits(config.limits)
        if config is not None and config.limits is not None
        else SpanLimits(
            max_span_attributes=_DEFAULT_OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT,
            max_events=_DEFAULT_OTEL_SPAN_EVENT_COUNT_LIMIT,
            max_links=_DEFAULT_OTEL_SPAN_LINK_COUNT_LIMIT,
            max_event_attributes=_DEFAULT_OTEL_EVENT_ATTRIBUTE_COUNT_LIMIT,
            max_link_attributes=_DEFAULT_OTEL_LINK_ATTRIBUTE_COUNT_LIMIT,
        )
    )

    provider = TracerProvider(
        resource=resource,
        sampler=sampler,
        span_limits=span_limits,
    )

    if config is not None:
        for proc_config in config.processors:
            provider.add_span_processor(_create_span_processor(proc_config))

    return provider


def configure_tracer_provider(
    config: Optional[TracerProviderConfig],
    resource: Optional[Resource] = None,
) -> None:
    """Configure the global TracerProvider from declarative config.

    When config is None (tracer_provider section absent from config file),
    the global is not set — matching Java/JS SDK behavior and the spec's
    "a noop tracer provider is used" default.

    Args:
        config: TracerProvider config from the parsed config file, or None.
        resource: Resource to attach to the provider.
    """
    if config is None:
        return
    trace.set_tracer_provider(create_tracer_provider(config, resource))
