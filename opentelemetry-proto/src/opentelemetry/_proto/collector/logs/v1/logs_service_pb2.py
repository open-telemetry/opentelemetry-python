# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# AUTO-GENERATED from "opentelemetry/proto/collector/logs/v1/logs_service.proto"
# DO NOT EDIT MANUALLY
from __future__ import annotations

from opentelemetry._proto._pyprotobuf.fields import msg, string, u64
from opentelemetry._proto._pyprotobuf.message import Message
from opentelemetry._proto.logs.v1.logs_pb2 import ResourceLogs

class ExportLogsServiceRequest(Message):
    def __init__(self, resource_logs: list[ResourceLogs] | None = None) -> None:
        self.resource_logs = list(resource_logs) if resource_logs else []

    def SerializeToString(self) -> bytes:
        result = b""
        result += b"".join(msg(1, _v.SerializeToString()) for _v in self.resource_logs)
        return result


class ExportLogsServiceResponse(Message):
    def __init__(self, partial_success: ExportLogsPartialSuccess | None = None) -> None:
        if isinstance(partial_success, dict):
            partial_success = ExportLogsPartialSuccess(**partial_success)
        self.partial_success = partial_success

    def SerializeToString(self) -> bytes:
        result = b""
        if self.partial_success is not None:
            result += msg(1, self.partial_success.SerializeToString())
        return result


class ExportLogsPartialSuccess(Message):
    def __init__(self, rejected_log_records: int | None = 0, error_message: str | None = "") -> None:
        self.rejected_log_records = rejected_log_records
        self.error_message = error_message

    def SerializeToString(self) -> bytes:
        result = b""
        result += u64(1, self.rejected_log_records)
        result += string(2, self.error_message)
        return result
global___ExportLogsServiceRequest = ExportLogsServiceRequest
global___ExportLogsServiceResponse = ExportLogsServiceResponse
global___ExportLogsPartialSuccess = ExportLogsPartialSuccess
