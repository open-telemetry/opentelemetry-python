# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# TODO: This file should be removed once the exporter specific
# metrics become stable (i.e. they are no longer incubating)

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from opentelemetry.metrics import Counter, Histogram, Meter, UpDownCounter


class OtelComponentTypeValues(Enum):
    OTLP_GRPC_SPAN_EXPORTER = "otlp_grpc_span_exporter"
    OTLP_HTTP_SPAN_EXPORTER = "otlp_http_span_exporter"
    OTLP_HTTP_JSON_SPAN_EXPORTER = "otlp_http_json_span_exporter"
    ZIPKIN_HTTP_SPAN_EXPORTER = "zipkin_http_span_exporter"
    OTLP_GRPC_LOG_EXPORTER = "otlp_grpc_log_exporter"
    OTLP_HTTP_LOG_EXPORTER = "otlp_http_log_exporter"
    OTLP_HTTP_JSON_LOG_EXPORTER = "otlp_http_json_log_exporter"
    OTLP_GRPC_METRIC_EXPORTER = "otlp_grpc_metric_exporter"
    OTLP_HTTP_METRIC_EXPORTER = "otlp_http_metric_exporter"
    OTLP_HTTP_JSON_METRIC_EXPORTER = "otlp_http_json_metric_exporter"
    PROMETHEUS_HTTP_TEXT_METRIC_EXPORTER = (
        "prometheus_http_text_metric_exporter"
    )


_OTEL_COMPONENT_NAME: Final[str] = "otel.component.name"
_OTEL_COMPONENT_TYPE: Final[str] = "otel.component.type"

# TODO: Remove these attributes once "opentelemetry-semantic-conventions"
# becomes stable (i.e. reaches 1.x.y)
_ERROR_TYPE: Final[str] = "error.type"
_SERVER_ADDRESS: Final[str] = "server.address"
_SERVER_PORT: Final[str] = "server.port"

_OTEL_SDK_EXPORTER_SPAN_EXPORTED: Final[str] = (
    "otel.sdk.exporter.span.exported"
)
_OTEL_SDK_EXPORTER_SPAN_INFLIGHT: Final[str] = (
    "otel.sdk.exporter.span.inflight"
)
_OTEL_SDK_EXPORTER_LOG_EXPORTED: Final[str] = "otel.sdk.exporter.log.exported"
_OTEL_SDK_EXPORTER_LOG_INFLIGHT: Final[str] = "otel.sdk.exporter.log.inflight"
_OTEL_SDK_EXPORTER_METRIC_DATA_POINT_EXPORTED: Final[str] = (
    "otel.sdk.exporter.metric_data_point.exported"
)
_OTEL_SDK_EXPORTER_METRIC_DATA_POINT_INFLIGHT: Final[str] = (
    "otel.sdk.exporter.metric_data_point.inflight"
)
_OTEL_SDK_EXPORTER_OPERATION_DURATION: Final[str] = (
    "otel.sdk.exporter.operation.duration"
)


def _create_otel_sdk_exporter_span_exported(meter: Meter) -> Counter:
    return meter.create_counter(
        name=_OTEL_SDK_EXPORTER_SPAN_EXPORTED,
        description="The number of spans for which the export has finished, either successful or failed.",
        unit="{span}",
    )


def _create_otel_sdk_exporter_span_inflight(meter: Meter) -> UpDownCounter:
    return meter.create_up_down_counter(
        name=_OTEL_SDK_EXPORTER_SPAN_INFLIGHT,
        description="The number of spans which were passed to the exporter, but that have not been exported yet (neither successful, nor failed).",
        unit="{span}",
    )


def _create_otel_sdk_exporter_log_exported(meter: Meter) -> Counter:
    return meter.create_counter(
        name=_OTEL_SDK_EXPORTER_LOG_EXPORTED,
        description="The number of log records for which the export has finished, either successful or failed.",
        unit="{log_record}",
    )


def _create_otel_sdk_exporter_log_inflight(meter: Meter) -> UpDownCounter:
    return meter.create_up_down_counter(
        name=_OTEL_SDK_EXPORTER_LOG_INFLIGHT,
        description="The number of log records which were passed to the exporter, but that have not been exported yet (neither successful, nor failed).",
        unit="{log_record}",
    )


def _create_otel_sdk_exporter_metric_data_point_exported(
    meter: Meter,
) -> Counter:
    return meter.create_counter(
        name=_OTEL_SDK_EXPORTER_METRIC_DATA_POINT_EXPORTED,
        description="The number of metric data points for which the export has finished, either successful or failed.",
        unit="{data_point}",
    )


def _create_otel_sdk_exporter_metric_data_point_inflight(
    meter: Meter,
) -> UpDownCounter:
    return meter.create_up_down_counter(
        name=_OTEL_SDK_EXPORTER_METRIC_DATA_POINT_INFLIGHT,
        description="The number of metric data points which were passed to the exporter, but that have not been exported yet (neither successful, nor failed).",
        unit="{data_point}",
    )


def _create_otel_sdk_exporter_operation_duration(meter: Meter) -> Histogram:
    return meter.create_histogram(
        name=_OTEL_SDK_EXPORTER_OPERATION_DURATION,
        description="The duration of exporting a batch of telemetry records.",
        unit="s",
    )
