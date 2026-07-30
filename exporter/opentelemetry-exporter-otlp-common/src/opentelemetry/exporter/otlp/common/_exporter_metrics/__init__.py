# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from time import perf_counter
from typing import TYPE_CHECKING, Protocol

from opentelemetry.exporter.otlp.common._exporter_metrics.semconv import (
    _ERROR_TYPE,
    _OTEL_COMPONENT_NAME,
    _OTEL_COMPONENT_TYPE,
    _SERVER_ADDRESS,
    _SERVER_PORT,
    OtelComponentTypeValues,
    _create_otel_sdk_exporter_log_exported,
    _create_otel_sdk_exporter_log_inflight,
    _create_otel_sdk_exporter_metric_data_point_exported,
    _create_otel_sdk_exporter_metric_data_point_inflight,
    _create_otel_sdk_exporter_operation_duration,
    _create_otel_sdk_exporter_span_exported,
    _create_otel_sdk_exporter_span_inflight,
)
from opentelemetry.metrics import MeterProvider, get_meter_provider

if TYPE_CHECKING:
    from typing import Literal
    from urllib.parse import ParseResult as UrlParseResult

    from opentelemetry.util.types import Attributes, AttributeValue

_component_counter = Counter()


@dataclass
class ExportResult:
    error: Exception | None = None
    error_attrs: Attributes = None


class ExporterMetricsT(Protocol):
    def export_operation(
        self, num_items: int
    ) -> AbstractContextManager[ExportResult]: ...


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
        endpoint: UrlParseResult,
        meter_provider: MeterProvider | None,
    ) -> None:
        port = endpoint.port
        if port is None:
            if endpoint.scheme == "https":
                port = 443
            elif endpoint.scheme == "http":
                port = 80

        component_type_value = (
            component_type.value if component_type else "unknown_otlp_exporter"
        )
        count = _component_counter[component_type_value]
        _component_counter[component_type_value] = count + 1
        self._standard_attrs: dict[str, AttributeValue] = {
            _OTEL_COMPONENT_TYPE: component_type_value,
            _OTEL_COMPONENT_NAME: f"{component_type_value}/{count}",
        }
        if endpoint.hostname:
            self._standard_attrs[_SERVER_ADDRESS] = endpoint.hostname
        if port is not None:
            self._standard_attrs[_SERVER_PORT] = port

        meter_provider = meter_provider or get_meter_provider()
        meter = meter_provider.get_meter("opentelemetry-sdk")
        self._duration = _create_otel_sdk_exporter_operation_duration(meter)
        match signal:
            case "traces":
                self._inflight = _create_otel_sdk_exporter_span_inflight(meter)
                self._exported = _create_otel_sdk_exporter_span_exported(meter)
            case "logs":
                self._inflight = _create_otel_sdk_exporter_log_inflight(meter)
                self._exported = _create_otel_sdk_exporter_log_exported(meter)
            case _:
                self._inflight = (
                    _create_otel_sdk_exporter_metric_data_point_inflight(meter)
                )
                self._exported = (
                    _create_otel_sdk_exporter_metric_data_point_exported(meter)
                )

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
                {**self._standard_attrs, _ERROR_TYPE: type(error).__qualname__}
                if error
                else self._standard_attrs
            )
            self._exported.add(num_items, exported_attrs)
            duration_attrs = (
                {**exported_attrs, **error_attrs}
                if error_attrs
                else exported_attrs
            )
            self._duration.record(end_time - start_time, duration_attrs)


def create_exporter_metrics(
    component_type: OtelComponentTypeValues | None,
    signal: Literal["traces", "metrics", "logs"],
    endpoint: UrlParseResult,
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
