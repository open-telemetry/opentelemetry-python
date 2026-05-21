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

from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from time import perf_counter
from typing import TYPE_CHECKING, Iterator

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
    from urllib.parse import ParseResult as UrlParseResult

    from opentelemetry.util.types import Attributes, AttributeValue

_component_counter = Counter()


@dataclass
class ExportResult:
    error: Exception | None = None
    error_attrs: Attributes = None


class ExporterMetrics:
    def __init__(
        self,
        component_type: OtelComponentTypeValues | None,
        signal: Literal["traces", "metrics", "logs"],
        endpoint: UrlParseResult,
        meter_provider: MeterProvider | None,
    ) -> None:
        if signal == "traces":
            create_exported = create_otel_sdk_exporter_span_exported
            create_inflight = create_otel_sdk_exporter_span_inflight
        elif signal == "logs":
            create_exported = create_otel_sdk_exporter_log_exported
            create_inflight = create_otel_sdk_exporter_log_inflight
        else:
            create_exported = (
                create_otel_sdk_exporter_metric_data_point_exported
            )
            create_inflight = (
                create_otel_sdk_exporter_metric_data_point_inflight
            )

        port = endpoint.port
        if port is None:
            if endpoint.scheme == "https":
                port = 443
            elif endpoint.scheme == "http":
                port = 80

        component_type = (
            component_type or OtelComponentTypeValues("unknown_otlp_exporter")
        ).value
        count = _component_counter[component_type]
        _component_counter[component_type] = count + 1
        self._standard_attrs: dict[str, AttributeValue] = {
            OTEL_COMPONENT_TYPE: component_type,
            OTEL_COMPONENT_NAME: f"{component_type}/{count}",
        }
        if endpoint.hostname:
            self._standard_attrs[SERVER_ADDRESS] = endpoint.hostname
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
                {**self._standard_attrs, ERROR_TYPE: type(error).__qualname__}
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
