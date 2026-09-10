# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# AUTO-GENERATED from "opentelemetry/proto/collector/trace/v1/trace_service.proto"
# DO NOT EDIT MANUALLY
from __future__ import annotations

from opentelemetry._proto._pyprotobuf.fields import msg, string, u64
from opentelemetry._proto._pyprotobuf.message import Message
from opentelemetry._proto.trace.v1.trace_pb2 import ResourceSpans

class ExportTraceServiceRequest(Message):
    def __init__(self, resource_spans: list[ResourceSpans] | None = None) -> None:
        self.resource_spans = list(resource_spans) if resource_spans else []

    def SerializeToString(self) -> bytes:
        result = b""
        result += b"".join(msg(1, _v.SerializeToString()) for _v in self.resource_spans)
        return result


class ExportTraceServiceResponse(Message):
    def __init__(self, partial_success: ExportTracePartialSuccess | None = None) -> None:
        if isinstance(partial_success, dict):
            partial_success = ExportTracePartialSuccess(**partial_success)
        self.partial_success = partial_success

    def SerializeToString(self) -> bytes:
        result = b""
        if self.partial_success is not None:
            result += msg(1, self.partial_success.SerializeToString())
        return result


class ExportTracePartialSuccess(Message):
    def __init__(self, rejected_spans: int | None = 0, error_message: str | None = "") -> None:
        self.rejected_spans = rejected_spans
        self.error_message = error_message

    def SerializeToString(self) -> bytes:
        result = b""
        result += u64(1, self.rejected_spans)
        result += string(2, self.error_message)
        return result
global___ExportTraceServiceRequest = ExportTraceServiceRequest
global___ExportTraceServiceResponse = ExportTraceServiceResponse
global___ExportTracePartialSuccess = ExportTracePartialSuccess
