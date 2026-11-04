# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from time import perf_counter
from typing import TYPE_CHECKING, Protocol
from urllib.parse import urlparse

from opentelemetry.metrics import MeterProvider, get_meter_provider
from opentelemetry.semconv._incubating.attributes.otel_attributes import (
    OTEL_COMPONENT_NAME,
    OTEL_COMPONENT_TYPE,
    OtelComponentTypeValues,
)
from opentelemetry.semconv._incubating.metrics.otel_metrics import (
    create_otel_sdk_exporter_log_exported,
    create_otel_sdk_exporter_log_inflight,
    create_otel_sdk_exporter_metric_data_point_exported,
    create_otel_sdk_exporter_metric_data_point_inflight,
    create_otel_sdk_exporter_operation_duration,
    create_otel_sdk_exporter_span_exported,
    create_otel_sdk_exporter_span_inflight,
)
from opentelemetry.semconv.attributes.error_attributes import ERROR_TYPE
from opentelemetry.semconv.attributes.server_attributes import (
    SERVER_ADDRESS,
    SERVER_PORT,
)

if TYPE_CHECKING:
    from typing import Literal

    from opentelemetry.util.types import AnyValue, Attributes

_component_counter = Counter()

_GRPC_COMPONENT_TYPES = frozenset(
    {
        OtelComponentTypeValues.OTLP_GRPC_SPAN_EXPORTER,
        OtelComponentTypeValues.OTLP_GRPC_LOG_EXPORTER,
        OtelComponentTypeValues.OTLP_GRPC_METRIC_EXPORTER,
    }
)


@dataclass
class ExportResult:
    error: Exception | None = None
    error_attrs: Attributes = None


class ExporterMetricsT(Protocol):
    def export_operation(self, num_items: int) -> AbstractContextManager[ExportResult]: ...


class NoOpExporterMetrics:
    @contextmanager
    # pylint: disable-next=no-self-use
    def export_operation(self, num_items: int) -> Iterator[ExportResult]:
        yield ExportResult()


class ExporterMetrics:
    def __init__(
        self,
        component_type: OtelComponentTypeValues | None,
        signal: Literal["traces", "metrics", "logs"],
        endpoint: str,
        meter_provider: MeterProvider | None,
    ) -> None:
        if signal == "traces":
            create_exported = create_otel_sdk_exporter_span_exported
            create_inflight = create_otel_sdk_exporter_span_inflight
        elif signal == "logs":
            create_exported = create_otel_sdk_exporter_log_exported
            create_inflight = create_otel_sdk_exporter_log_inflight
        else:
            create_exported = create_otel_sdk_exporter_metric_data_point_exported
            create_inflight = create_otel_sdk_exporter_metric_data_point_inflight

        if not endpoint.startswith("//") and "://" not in endpoint:
            endpoint = f"//{endpoint}"
        parsed_endpoint = urlparse(endpoint)

        port = parsed_endpoint.port
        if port is None:
            if component_type in _GRPC_COMPONENT_TYPES or parsed_endpoint.scheme == "https":
                port = 443
            elif parsed_endpoint.scheme == "http":
                port = 80

        component_type_value = component_type.value if component_type else "unknown_otlp_exporter"
        count = _component_counter[component_type_value]
        _component_counter[component_type_value] = count + 1
        self._standard_attrs: dict[str, AnyValue] = {
            OTEL_COMPONENT_TYPE: component_type_value,
            OTEL_COMPONENT_NAME: f"{component_type_value}/{count}",
        }
        if parsed_endpoint.hostname:
            self._standard_attrs[SERVER_ADDRESS] = parsed_endpoint.hostname
        if port is not None:
            self._standard_attrs[SERVER_PORT] = port

        meter_provider = meter_provider or get_meter_provider()
        meter = meter_provider.get_meter("opentelemetry-sdk")
        self._inflight = create_inflight(meter)
        self._exported = create_exported(meter)
        self._duration = create_otel_sdk_exporter_operation_duration(meter)

    @contextmanager
    def export_operation(self, num_items: int) -> Iterator[ExportResult]:
        start_time = perf_counter()
        self._inflight.add(num_items, self._standard_attrs)

        result = ExportResult()
        try:
            yield result
        finally:
            error = result.error
            error_attrs = result.error_attrs

            end_time = perf_counter()
            self._inflight.add(-num_items, self._standard_attrs)
            exported_attrs = (
                {**self._standard_attrs, ERROR_TYPE: type(error).__qualname__} if error else self._standard_attrs
            )
            self._exported.add(num_items, exported_attrs)
            duration_attrs = {**exported_attrs, **error_attrs} if error_attrs else exported_attrs
            self._duration.record(end_time - start_time, duration_attrs)


def create_exporter_metrics(
    component_type: OtelComponentTypeValues | None,
    signal: Literal["traces", "metrics", "logs"],
    endpoint: str,
    meter_provider: MeterProvider | None,
    enabled: bool,
) -> ExporterMetricsT:
    if not enabled:
        return NoOpExporterMetrics()

    return ExporterMetrics(
        component_type,
        signal,
        endpoint,
        meter_provider,
    )
