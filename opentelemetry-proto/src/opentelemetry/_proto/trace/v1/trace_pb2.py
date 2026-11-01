# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# AUTO-GENERATED from "opentelemetry/proto/trace/v1/trace.proto"
# DO NOT EDIT MANUALLY
from __future__ import annotations

from enum import IntEnum

from opentelemetry._proto._pyprotobuf.fields import byt, fix32, fix64, msg, string, u64
from opentelemetry._proto._pyprotobuf.message import Message
from opentelemetry._proto.common.v1.common_pb2 import InstrumentationScope
from opentelemetry._proto.common.v1.common_pb2 import KeyValue
from opentelemetry._proto.resource.v1.resource_pb2 import Resource

class SpanFlags(IntEnum):
    SPAN_FLAGS_DO_NOT_USE = 0
    SPAN_FLAGS_TRACE_FLAGS_MASK = 255
    SPAN_FLAGS_CONTEXT_HAS_IS_REMOTE_MASK = 256
    SPAN_FLAGS_CONTEXT_IS_REMOTE_MASK = 512


class TracesData(Message):
    def __init__(self, resource_spans: list[ResourceSpans] | None = None) -> None:
        self.resource_spans = list(resource_spans) if resource_spans else []

    def SerializeToString(self) -> bytes:
        result = b""
        result += b"".join(msg(1, _v.SerializeToString()) for _v in self.resource_spans)
        return result


class ResourceSpans(Message):
    def __init__(self, resource: Resource | None = None, scope_spans: list[ScopeSpans] | None = None, schema_url: str | None = "") -> None:
        if isinstance(resource, dict):
            resource = Resource(**resource)
        self.resource = resource
        self.scope_spans = list(scope_spans) if scope_spans else []
        self.schema_url = schema_url

    def SerializeToString(self) -> bytes:
        result = b""
        if self.resource is not None:
            result += msg(1, self.resource.SerializeToString())
        result += b"".join(msg(2, _v.SerializeToString()) for _v in self.scope_spans)
        result += string(3, self.schema_url)
        return result


class ScopeSpans(Message):
    def __init__(self, scope: InstrumentationScope | None = None, spans: list[Span] | None = None, schema_url: str | None = "") -> None:
        if isinstance(scope, dict):
            scope = InstrumentationScope(**scope)
        self.scope = scope
        self.spans = list(spans) if spans else []
        self.schema_url = schema_url

    def SerializeToString(self) -> bytes:
        result = b""
        if self.scope is not None:
            result += msg(1, self.scope.SerializeToString())
        result += b"".join(msg(2, _v.SerializeToString()) for _v in self.spans)
        result += string(3, self.schema_url)
        return result


class Span(Message):
    class SpanKind(IntEnum):
        SPAN_KIND_UNSPECIFIED = 0
        SPAN_KIND_INTERNAL = 1
        SPAN_KIND_SERVER = 2
        SPAN_KIND_CLIENT = 3
        SPAN_KIND_PRODUCER = 4
        SPAN_KIND_CONSUMER = 5

    SPAN_KIND_UNSPECIFIED = SpanKind.SPAN_KIND_UNSPECIFIED
    SPAN_KIND_INTERNAL = SpanKind.SPAN_KIND_INTERNAL
    SPAN_KIND_SERVER = SpanKind.SPAN_KIND_SERVER
    SPAN_KIND_CLIENT = SpanKind.SPAN_KIND_CLIENT
    SPAN_KIND_PRODUCER = SpanKind.SPAN_KIND_PRODUCER
    SPAN_KIND_CONSUMER = SpanKind.SPAN_KIND_CONSUMER

    class Event(Message):
        def __init__(self, time_unix_nano: int | None = 0, name: str | None = "", attributes: list[KeyValue] | None = None, dropped_attributes_count: int | None = 0) -> None:
            self.time_unix_nano = time_unix_nano
            self.name = name
            self.attributes = list(attributes) if attributes else []
            self.dropped_attributes_count = dropped_attributes_count

        def SerializeToString(self) -> bytes:
            result = b""
            result += fix64(1, self.time_unix_nano)
            result += string(2, self.name)
            result += b"".join(msg(3, _v.SerializeToString()) for _v in self.attributes)
            result += u64(4, self.dropped_attributes_count)
            return result

    class Link(Message):
        def __init__(self, trace_id: bytes | None = b"", span_id: bytes | None = b"", trace_state: str | None = "", attributes: list[KeyValue] | None = None, dropped_attributes_count: int | None = 0, flags: int | None = 0) -> None:
            self.trace_id = trace_id
            self.span_id = span_id
            self.trace_state = trace_state
            self.attributes = list(attributes) if attributes else []
            self.dropped_attributes_count = dropped_attributes_count
            self.flags = flags

        def SerializeToString(self) -> bytes:
            result = b""
            result += byt(1, self.trace_id)
            result += byt(2, self.span_id)
            result += string(3, self.trace_state)
            result += b"".join(msg(4, _v.SerializeToString()) for _v in self.attributes)
            result += u64(5, self.dropped_attributes_count)
            result += fix32(6, self.flags)
            return result

    def __init__(self, trace_id: bytes | None = b"", span_id: bytes | None = b"", trace_state: str | None = "", parent_span_id: bytes | None = b"", flags: int | None = 0, name: str | None = "", kind: Span.SpanKind | None = 0, start_time_unix_nano: int | None = 0, end_time_unix_nano: int | None = 0, attributes: list[KeyValue] | None = None, dropped_attributes_count: int | None = 0, events: list[Span.Event] | None = None, dropped_events_count: int | None = 0, links: list[Span.Link] | None = None, dropped_links_count: int | None = 0, status: Status | None = None) -> None:
        self.trace_id = trace_id
        self.span_id = span_id
        self.trace_state = trace_state
        self.parent_span_id = parent_span_id
        self.flags = flags
        self.name = name
        self.kind = kind
        self.start_time_unix_nano = start_time_unix_nano
        self.end_time_unix_nano = end_time_unix_nano
        self.attributes = list(attributes) if attributes else []
        self.dropped_attributes_count = dropped_attributes_count
        self.events = list(events) if events else []
        self.dropped_events_count = dropped_events_count
        self.links = list(links) if links else []
        self.dropped_links_count = dropped_links_count
        if isinstance(status, dict):
            status = Status(**status)
        self.status = status

    def SerializeToString(self) -> bytes:
        result = b""
        result += byt(1, self.trace_id)
        result += byt(2, self.span_id)
        result += string(3, self.trace_state)
        result += byt(4, self.parent_span_id)
        result += string(5, self.name)
        result += u64(6, self.kind)
        result += fix64(7, self.start_time_unix_nano)
        result += fix64(8, self.end_time_unix_nano)
        result += b"".join(msg(9, _v.SerializeToString()) for _v in self.attributes)
        result += u64(10, self.dropped_attributes_count)
        result += b"".join(msg(11, _v.SerializeToString()) for _v in self.events)
        result += u64(12, self.dropped_events_count)
        result += b"".join(msg(13, _v.SerializeToString()) for _v in self.links)
        result += u64(14, self.dropped_links_count)
        if self.status is not None:
            result += msg(15, self.status.SerializeToString())
        result += fix32(16, self.flags)
        return result


class Status(Message):
    class StatusCode(IntEnum):
        STATUS_CODE_UNSET = 0
        STATUS_CODE_OK = 1
        STATUS_CODE_ERROR = 2

    STATUS_CODE_UNSET = StatusCode.STATUS_CODE_UNSET
    STATUS_CODE_OK = StatusCode.STATUS_CODE_OK
    STATUS_CODE_ERROR = StatusCode.STATUS_CODE_ERROR

    def __init__(self, message: str | None = "", code: Status.StatusCode | None = 0) -> None:
        self.message = message
        self.code = code

    def SerializeToString(self) -> bytes:
        result = b""
        result += string(2, self.message)
        result += u64(3, self.code)
        return result
SPAN_FLAGS_DO_NOT_USE = SpanFlags.SPAN_FLAGS_DO_NOT_USE
SPAN_FLAGS_TRACE_FLAGS_MASK = SpanFlags.SPAN_FLAGS_TRACE_FLAGS_MASK
SPAN_FLAGS_CONTEXT_HAS_IS_REMOTE_MASK = SpanFlags.SPAN_FLAGS_CONTEXT_HAS_IS_REMOTE_MASK
SPAN_FLAGS_CONTEXT_IS_REMOTE_MASK = SpanFlags.SPAN_FLAGS_CONTEXT_IS_REMOTE_MASK

global___SpanFlags = SpanFlags

global___TracesData = TracesData
global___ResourceSpans = ResourceSpans
global___ScopeSpans = ScopeSpans
global___Span = Span
global___Status = Status
