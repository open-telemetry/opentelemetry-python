# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# AUTO-GENERATED from "opentelemetry/proto/collector/metrics/v1/metrics_service.proto"
# DO NOT EDIT MANUALLY
from __future__ import annotations

from opentelemetry._proto._pyprotobuf.fields import msg, string, u64
from opentelemetry._proto._pyprotobuf.message import Message
from opentelemetry._proto.metrics.v1.metrics_pb2 import ResourceMetrics

class ExportMetricsServiceRequest(Message):
    def __init__(self, resource_metrics: list[ResourceMetrics] | None = None) -> None:
        self.resource_metrics = list(resource_metrics) if resource_metrics else []

    def SerializeToString(self) -> bytes:
        result = b""
        result += b"".join(msg(1, _v.SerializeToString()) for _v in self.resource_metrics)
        return result


class ExportMetricsServiceResponse(Message):
    def __init__(self, partial_success: ExportMetricsPartialSuccess | None = None) -> None:
        if isinstance(partial_success, dict):
            partial_success = ExportMetricsPartialSuccess(**partial_success)
        self.partial_success = partial_success

    def SerializeToString(self) -> bytes:
        result = b""
        if self.partial_success is not None:
            result += msg(1, self.partial_success.SerializeToString())
        return result


class ExportMetricsPartialSuccess(Message):
    def __init__(self, rejected_data_points: int | None = 0, error_message: str | None = "") -> None:
        self.rejected_data_points = rejected_data_points
        self.error_message = error_message

    def SerializeToString(self) -> bytes:
        result = b""
        result += u64(1, self.rejected_data_points)
        result += string(2, self.error_message)
        return result
global___ExportMetricsServiceRequest = ExportMetricsServiceRequest
global___ExportMetricsServiceResponse = ExportMetricsServiceResponse
global___ExportMetricsPartialSuccess = ExportMetricsPartialSuccess
