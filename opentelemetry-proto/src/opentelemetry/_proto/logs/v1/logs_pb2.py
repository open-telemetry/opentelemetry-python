# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# AUTO-GENERATED from "opentelemetry/proto/logs/v1/logs.proto"
# DO NOT EDIT MANUALLY
from __future__ import annotations

from enum import IntEnum

from opentelemetry._proto._pyprotobuf.fields import byt, fix32, fix64, msg, string, u64
from opentelemetry._proto._pyprotobuf.message import Message
from opentelemetry._proto.common.v1.common_pb2 import AnyValue
from opentelemetry._proto.common.v1.common_pb2 import InstrumentationScope
from opentelemetry._proto.common.v1.common_pb2 import KeyValue
from opentelemetry._proto.resource.v1.resource_pb2 import Resource

class SeverityNumber(IntEnum):
    SEVERITY_NUMBER_UNSPECIFIED = 0
    SEVERITY_NUMBER_TRACE = 1
    SEVERITY_NUMBER_TRACE2 = 2
    SEVERITY_NUMBER_TRACE3 = 3
    SEVERITY_NUMBER_TRACE4 = 4
    SEVERITY_NUMBER_DEBUG = 5
    SEVERITY_NUMBER_DEBUG2 = 6
    SEVERITY_NUMBER_DEBUG3 = 7
    SEVERITY_NUMBER_DEBUG4 = 8
    SEVERITY_NUMBER_INFO = 9
    SEVERITY_NUMBER_INFO2 = 10
    SEVERITY_NUMBER_INFO3 = 11
    SEVERITY_NUMBER_INFO4 = 12
    SEVERITY_NUMBER_WARN = 13
    SEVERITY_NUMBER_WARN2 = 14
    SEVERITY_NUMBER_WARN3 = 15
    SEVERITY_NUMBER_WARN4 = 16
    SEVERITY_NUMBER_ERROR = 17
    SEVERITY_NUMBER_ERROR2 = 18
    SEVERITY_NUMBER_ERROR3 = 19
    SEVERITY_NUMBER_ERROR4 = 20
    SEVERITY_NUMBER_FATAL = 21
    SEVERITY_NUMBER_FATAL2 = 22
    SEVERITY_NUMBER_FATAL3 = 23
    SEVERITY_NUMBER_FATAL4 = 24


class LogRecordFlags(IntEnum):
    LOG_RECORD_FLAGS_DO_NOT_USE = 0
    LOG_RECORD_FLAGS_TRACE_FLAGS_MASK = 255


class LogsData(Message):
    def __init__(self, resource_logs: list[ResourceLogs] | None = None) -> None:
        self.resource_logs = list(resource_logs) if resource_logs else []

    def SerializeToString(self) -> bytes:
        result = b""
        result += b"".join(msg(1, _v.SerializeToString()) for _v in self.resource_logs)
        return result


class ResourceLogs(Message):
    def __init__(self, resource: Resource | None = None, scope_logs: list[ScopeLogs] | None = None, schema_url: str | None = "") -> None:
        if isinstance(resource, dict):
            resource = Resource(**resource)
        self.resource = resource
        self.scope_logs = list(scope_logs) if scope_logs else []
        self.schema_url = schema_url

    def SerializeToString(self) -> bytes:
        result = b""
        if self.resource is not None:
            result += msg(1, self.resource.SerializeToString())
        result += b"".join(msg(2, _v.SerializeToString()) for _v in self.scope_logs)
        result += string(3, self.schema_url)
        return result


class ScopeLogs(Message):
    def __init__(self, scope: InstrumentationScope | None = None, log_records: list[LogRecord] | None = None, schema_url: str | None = "") -> None:
        if isinstance(scope, dict):
            scope = InstrumentationScope(**scope)
        self.scope = scope
        self.log_records = list(log_records) if log_records else []
        self.schema_url = schema_url

    def SerializeToString(self) -> bytes:
        result = b""
        if self.scope is not None:
            result += msg(1, self.scope.SerializeToString())
        result += b"".join(msg(2, _v.SerializeToString()) for _v in self.log_records)
        result += string(3, self.schema_url)
        return result


class LogRecord(Message):
    def __init__(self, time_unix_nano: int | None = 0, observed_time_unix_nano: int | None = 0, severity_number: SeverityNumber | None = 0, severity_text: str | None = "", body: AnyValue | None = None, attributes: list[KeyValue] | None = None, dropped_attributes_count: int | None = 0, flags: int | None = 0, trace_id: bytes | None = b"", span_id: bytes | None = b"", event_name: str | None = "") -> None:
        self.time_unix_nano = time_unix_nano
        self.observed_time_unix_nano = observed_time_unix_nano
        self.severity_number = severity_number
        self.severity_text = severity_text
        if isinstance(body, dict):
            body = AnyValue(**body)
        self.body = body
        self.attributes = list(attributes) if attributes else []
        self.dropped_attributes_count = dropped_attributes_count
        self.flags = flags
        self.trace_id = trace_id
        self.span_id = span_id
        self.event_name = event_name

    def SerializeToString(self) -> bytes:
        result = b""
        result += fix64(1, self.time_unix_nano)
        result += u64(2, self.severity_number)
        result += string(3, self.severity_text)
        if self.body is not None:
            result += msg(5, self.body.SerializeToString())
        result += b"".join(msg(6, _v.SerializeToString()) for _v in self.attributes)
        result += u64(7, self.dropped_attributes_count)
        result += fix32(8, self.flags)
        result += byt(9, self.trace_id)
        result += byt(10, self.span_id)
        result += fix64(11, self.observed_time_unix_nano)
        result += string(12, self.event_name)
        return result
SEVERITY_NUMBER_UNSPECIFIED = SeverityNumber.SEVERITY_NUMBER_UNSPECIFIED
SEVERITY_NUMBER_TRACE = SeverityNumber.SEVERITY_NUMBER_TRACE
SEVERITY_NUMBER_TRACE2 = SeverityNumber.SEVERITY_NUMBER_TRACE2
SEVERITY_NUMBER_TRACE3 = SeverityNumber.SEVERITY_NUMBER_TRACE3
SEVERITY_NUMBER_TRACE4 = SeverityNumber.SEVERITY_NUMBER_TRACE4
SEVERITY_NUMBER_DEBUG = SeverityNumber.SEVERITY_NUMBER_DEBUG
SEVERITY_NUMBER_DEBUG2 = SeverityNumber.SEVERITY_NUMBER_DEBUG2
SEVERITY_NUMBER_DEBUG3 = SeverityNumber.SEVERITY_NUMBER_DEBUG3
SEVERITY_NUMBER_DEBUG4 = SeverityNumber.SEVERITY_NUMBER_DEBUG4
SEVERITY_NUMBER_INFO = SeverityNumber.SEVERITY_NUMBER_INFO
SEVERITY_NUMBER_INFO2 = SeverityNumber.SEVERITY_NUMBER_INFO2
SEVERITY_NUMBER_INFO3 = SeverityNumber.SEVERITY_NUMBER_INFO3
SEVERITY_NUMBER_INFO4 = SeverityNumber.SEVERITY_NUMBER_INFO4
SEVERITY_NUMBER_WARN = SeverityNumber.SEVERITY_NUMBER_WARN
SEVERITY_NUMBER_WARN2 = SeverityNumber.SEVERITY_NUMBER_WARN2
SEVERITY_NUMBER_WARN3 = SeverityNumber.SEVERITY_NUMBER_WARN3
SEVERITY_NUMBER_WARN4 = SeverityNumber.SEVERITY_NUMBER_WARN4
SEVERITY_NUMBER_ERROR = SeverityNumber.SEVERITY_NUMBER_ERROR
SEVERITY_NUMBER_ERROR2 = SeverityNumber.SEVERITY_NUMBER_ERROR2
SEVERITY_NUMBER_ERROR3 = SeverityNumber.SEVERITY_NUMBER_ERROR3
SEVERITY_NUMBER_ERROR4 = SeverityNumber.SEVERITY_NUMBER_ERROR4
SEVERITY_NUMBER_FATAL = SeverityNumber.SEVERITY_NUMBER_FATAL
SEVERITY_NUMBER_FATAL2 = SeverityNumber.SEVERITY_NUMBER_FATAL2
SEVERITY_NUMBER_FATAL3 = SeverityNumber.SEVERITY_NUMBER_FATAL3
SEVERITY_NUMBER_FATAL4 = SeverityNumber.SEVERITY_NUMBER_FATAL4

global___SeverityNumber = SeverityNumber

LOG_RECORD_FLAGS_DO_NOT_USE = LogRecordFlags.LOG_RECORD_FLAGS_DO_NOT_USE
LOG_RECORD_FLAGS_TRACE_FLAGS_MASK = LogRecordFlags.LOG_RECORD_FLAGS_TRACE_FLAGS_MASK

global___LogRecordFlags = LogRecordFlags

global___LogsData = LogsData
global___ResourceLogs = ResourceLogs
global___ScopeLogs = ScopeLogs
global___LogRecord = LogRecord
