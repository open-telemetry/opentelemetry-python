"""Pure-Python equivalents of opentelemetry/proto/trace/v1/trace_pb2.py.

Field numbers:
    Status         message=2  code=3
    Span.Event     time_unix_nano=1  name=2  attributes=3  dropped_attrs_count=4
    Span.Link      trace_id=1  span_id=2  trace_state=3  attributes=4
                   dropped_attrs_count=5  flags=6
    Span           trace_id=1  span_id=2  trace_state=3  parent_span_id=4
                   flags=16  name=5  kind=6  start_time_unix_nano=7
                   end_time_unix_nano=8  attributes=9  dropped_attrs_count=10
                   events=11  dropped_events_count=12  links=13
                   dropped_links_count=14  status=15
    ScopeSpans     scope=1  spans=2  schema_url=3
    ResourceSpans  resource=1  scope_spans=2  schema_url=3
"""

from __future__ import annotations

from opentelemetry._proto.common.v1.common_pb2 import (
    InstrumentationScope,
    KeyValue,
)
from opentelemetry._proto.resource.v1.resource_pb2 import Resource
from opentelemetry._proto._pyprotobuf.fields import (
    byt,
    fix32,
    fix64,
    msg,
    string,
    u64,
)


class Status:
    def __init__(self, message: str = "", code: int = 0):
        self.message = message
        self.code = code

    def SerializeToString(self) -> bytes:
        return string(2, self.message) + u64(3, self.code)


class Span:
    class Event:
        def __init__(
            self,
            time_unix_nano: int = 0,
            name: str = "",
            attributes: list[KeyValue] | None = None,
            dropped_attributes_count: int = 0,
        ):
            self.time_unix_nano = time_unix_nano
            self.name = name
            self.attributes: list[KeyValue] = list(attributes) if attributes else []
            self.dropped_attributes_count = dropped_attributes_count

        def SerializeToString(self) -> bytes:
            return (
                fix64(1, self.time_unix_nano)
                + string(2, self.name)
                + b"".join(msg(3, kv.SerializeToString()) for kv in self.attributes)
                + u64(4, self.dropped_attributes_count)
            )

    class Link:
        def __init__(
            self,
            trace_id: bytes = b"",
            span_id: bytes = b"",
            trace_state: str = "",
            attributes: list[KeyValue] | None = None,
            dropped_attributes_count: int = 0,
            flags: int = 0,
        ):
            self.trace_id = trace_id
            self.span_id = span_id
            self.trace_state = trace_state
            self.attributes: list[KeyValue] = list(attributes) if attributes else []
            self.dropped_attributes_count = dropped_attributes_count
            self.flags = flags

        def SerializeToString(self) -> bytes:
            return (
                byt(1, self.trace_id)
                + byt(2, self.span_id)
                + string(3, self.trace_state)
                + b"".join(msg(4, kv.SerializeToString()) for kv in self.attributes)
                + u64(5, self.dropped_attributes_count)
                + fix32(6, self.flags)
            )

    def __init__(
        self,
        trace_id: bytes = b"",
        span_id: bytes = b"",
        trace_state: str = "",
        parent_span_id: bytes = b"",
        flags: int = 0,
        name: str = "",
        kind: int = 0,
        start_time_unix_nano: int = 0,
        end_time_unix_nano: int = 0,
        attributes: list[KeyValue] | None = None,
        dropped_attributes_count: int = 0,
        events: list["Span.Event"] | None = None,
        dropped_events_count: int = 0,
        links: list["Span.Link"] | None = None,
        dropped_links_count: int = 0,
        status: Status | None = None,
    ):
        self.trace_id = trace_id
        self.span_id = span_id
        self.trace_state = trace_state
        self.parent_span_id = parent_span_id
        self.flags = flags
        self.name = name
        self.kind = kind
        self.start_time_unix_nano = start_time_unix_nano
        self.end_time_unix_nano = end_time_unix_nano
        self.attributes: list[KeyValue] = list(attributes) if attributes else []
        self.dropped_attributes_count = dropped_attributes_count
        self.events: list[Span.Event] = list(events) if events else []
        self.dropped_events_count = dropped_events_count
        self.links: list[Span.Link] = list(links) if links else []
        self.dropped_links_count = dropped_links_count
        self.status = status

    def SerializeToString(self) -> bytes:
        result = (
            byt(1, self.trace_id)
            + byt(2, self.span_id)
            + string(3, self.trace_state)
            + byt(4, self.parent_span_id)
            + string(5, self.name)
            + u64(6, self.kind)
            + fix64(7, self.start_time_unix_nano)
            + fix64(8, self.end_time_unix_nano)
            + b"".join(msg(9, kv.SerializeToString()) for kv in self.attributes)
            + u64(10, self.dropped_attributes_count)
            + b"".join(msg(11, ev.SerializeToString()) for ev in self.events)
            + u64(12, self.dropped_events_count)
            + b"".join(msg(13, lk.SerializeToString()) for lk in self.links)
            + u64(14, self.dropped_links_count)
        )
        if self.status is not None:
            result += msg(15, self.status.SerializeToString())
        result += fix32(16, self.flags)
        return result


class ScopeSpans:
    def __init__(
        self,
        scope: InstrumentationScope | None = None,
        spans: list[Span] | None = None,
        schema_url: str = "",
    ):
        self.scope = scope
        self.spans: list[Span] = list(spans) if spans else []
        self.schema_url = schema_url

    def SerializeToString(self) -> bytes:
        result = b""
        if self.scope is not None:
            result += msg(1, self.scope.SerializeToString())
        result += b"".join(msg(2, sp.SerializeToString()) for sp in self.spans)
        result += string(3, self.schema_url)
        return result


class ResourceSpans:
    def __init__(
        self,
        resource: Resource | None = None,
        scope_spans: list[ScopeSpans] | None = None,
        schema_url: str = "",
    ):
        self.resource = resource
        self.scope_spans: list[ScopeSpans] = list(scope_spans) if scope_spans else []
        self.schema_url = schema_url

    def SerializeToString(self) -> bytes:
        result = b""
        if self.resource is not None:
            result += msg(1, self.resource.SerializeToString())
        result += b"".join(msg(2, ss.SerializeToString()) for ss in self.scope_spans)
        result += string(3, self.schema_url)
        return result
