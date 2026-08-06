from opentelemetry.proto.common.v1.common_pb2 import (
    AnyValue as ProtoAnyValue,
    InstrumentationScope as ProtoInstrumentationScope,
    KeyValue as ProtoKeyValue,
)
from opentelemetry.proto.resource.v1.resource_pb2 import Resource as ProtoResource
from opentelemetry.proto.trace.v1.trace_pb2 import (
    ResourceSpans as ProtoResourceSpans,
    ScopeSpans as ProtoScopeSpans,
    Span as ProtoSpan,
    Status as ProtoStatus,
)

from opentelemetry._proto.common.v1.common_pb2 import (
    AnyValue,
    InstrumentationScope,
    KeyValue,
)
from opentelemetry._proto.resource.v1.resource_pb2 import Resource
from opentelemetry._proto.trace.v1.trace_pb2 import (
    ResourceSpans,
    ScopeSpans,
    Span,
    Status,
)


# ── Status ────────────────────────────────────────────────────────────────────

def test_status_empty() -> None:
    assert Status().SerializeToString() == b""


def test_status_empty_matches_proto() -> None:
    assert Status().SerializeToString() == ProtoStatus().SerializeToString()


def test_status_code() -> None:
    our = Status(code=2)
    proto = ProtoStatus(code=2)
    assert our.SerializeToString() == proto.SerializeToString()


def test_status_code_and_message() -> None:
    our = Status(code=2, message="internal error")
    proto = ProtoStatus(code=2, message="internal error")
    assert our.SerializeToString() == proto.SerializeToString()


# ── Span.Event ────────────────────────────────────────────────────────────────

def test_span_event_empty() -> None:
    assert Span.Event().SerializeToString() == b""


def test_span_event_empty_matches_proto() -> None:
    assert Span.Event().SerializeToString() == ProtoSpan.Event().SerializeToString()


def test_span_event_name_and_time() -> None:
    our = Span.Event(name="button.click", time_unix_nano=1_000_000)
    proto = ProtoSpan.Event(name="button.click", time_unix_nano=1_000_000)
    assert our.SerializeToString() == proto.SerializeToString()


def test_span_event_with_attributes() -> None:
    attr = KeyValue(key="k", value=AnyValue(string_value="v"))
    proto_attr = ProtoKeyValue(key="k", value=ProtoAnyValue(string_value="v"))
    our = Span.Event(name="evt", attributes=[attr], dropped_attributes_count=1)
    proto = ProtoSpan.Event(name="evt", attributes=[proto_attr], dropped_attributes_count=1)
    assert our.SerializeToString() == proto.SerializeToString()


# ── Span.Link ─────────────────────────────────────────────────────────────────

def test_span_link_empty() -> None:
    assert Span.Link().SerializeToString() == b""


def test_span_link_empty_matches_proto() -> None:
    assert Span.Link().SerializeToString() == ProtoSpan.Link().SerializeToString()


def test_span_link_with_ids() -> None:
    trace_id = b"\x01" * 16
    span_id = b"\x02" * 8
    our = Span.Link(trace_id=trace_id, span_id=span_id, trace_state="k=v")
    proto = ProtoSpan.Link(trace_id=trace_id, span_id=span_id, trace_state="k=v")
    assert our.SerializeToString() == proto.SerializeToString()


def test_span_link_with_flags() -> None:
    trace_id = b"\x01" * 16
    span_id = b"\x02" * 8
    our = Span.Link(trace_id=trace_id, span_id=span_id, flags=1)
    proto = ProtoSpan.Link(trace_id=trace_id, span_id=span_id, flags=1)
    assert our.SerializeToString() == proto.SerializeToString()


# ── Span ──────────────────────────────────────────────────────────────────────

def test_span_empty() -> None:
    assert Span().SerializeToString() == b""


def test_span_empty_matches_proto() -> None:
    assert Span().SerializeToString() == ProtoSpan().SerializeToString()


def test_span_basic() -> None:
    trace_id = b"\x01" * 16
    span_id = b"\x02" * 8
    our = Span(
        trace_id=trace_id,
        span_id=span_id,
        name="my-span",
        start_time_unix_nano=1_000_000_000,
        end_time_unix_nano=2_000_000_000,
    )
    proto = ProtoSpan(
        trace_id=trace_id,
        span_id=span_id,
        name="my-span",
        start_time_unix_nano=1_000_000_000,
        end_time_unix_nano=2_000_000_000,
    )
    assert our.SerializeToString() == proto.SerializeToString()


def test_span_with_status() -> None:
    our = Span(name="err-span", status=Status(code=2, message="error"))
    proto = ProtoSpan(name="err-span", status=ProtoStatus(code=2, message="error"))
    assert our.SerializeToString() == proto.SerializeToString()


def test_span_with_attributes() -> None:
    trace_id = b"\x01" * 16
    span_id = b"\x02" * 8
    attr = KeyValue(key="http.method", value=AnyValue(string_value="GET"))
    proto_attr = ProtoKeyValue(key="http.method", value=ProtoAnyValue(string_value="GET"))
    our = Span(
        trace_id=trace_id,
        span_id=span_id,
        name="http-span",
        attributes=[attr],
        dropped_attributes_count=2,
    )
    proto = ProtoSpan(
        trace_id=trace_id,
        span_id=span_id,
        name="http-span",
        attributes=[proto_attr],
        dropped_attributes_count=2,
    )
    assert our.SerializeToString() == proto.SerializeToString()


def test_span_with_events_and_links() -> None:
    trace_id = b"\x01" * 16
    span_id = b"\x02" * 8
    our = Span(
        trace_id=trace_id,
        span_id=span_id,
        name="parent",
        events=[Span.Event(name="click", time_unix_nano=500)],
        links=[Span.Link(trace_id=trace_id, span_id=span_id)],
        dropped_events_count=1,
        dropped_links_count=2,
    )
    proto = ProtoSpan(
        trace_id=trace_id,
        span_id=span_id,
        name="parent",
        events=[ProtoSpan.Event(name="click", time_unix_nano=500)],
        links=[ProtoSpan.Link(trace_id=trace_id, span_id=span_id)],
        dropped_events_count=1,
        dropped_links_count=2,
    )
    assert our.SerializeToString() == proto.SerializeToString()


def test_span_kind() -> None:
    our = Span(name="server", kind=2)
    proto = ProtoSpan(name="server", kind=2)
    assert our.SerializeToString() == proto.SerializeToString()


# ── ScopeSpans ────────────────────────────────────────────────────────────────

def test_scope_spans_empty() -> None:
    assert ScopeSpans().SerializeToString() == b""


def test_scope_spans_empty_matches_proto() -> None:
    assert ScopeSpans().SerializeToString() == ProtoScopeSpans().SerializeToString()


def test_scope_spans_schema_url() -> None:
    our = ScopeSpans(schema_url="https://example.com")
    proto = ProtoScopeSpans(schema_url="https://example.com")
    assert our.SerializeToString() == proto.SerializeToString()


def test_scope_spans_with_scope_and_span() -> None:
    scope = InstrumentationScope(name="mylib", version="1.0")
    proto_scope = ProtoInstrumentationScope(name="mylib", version="1.0")
    span = Span(name="test-span")
    proto_span = ProtoSpan(name="test-span")
    our = ScopeSpans(scope=scope, spans=[span], schema_url="s")
    proto = ProtoScopeSpans(scope=proto_scope, spans=[proto_span], schema_url="s")
    assert our.SerializeToString() == proto.SerializeToString()


# ── ResourceSpans ─────────────────────────────────────────────────────────────

def test_resource_spans_empty() -> None:
    assert ResourceSpans().SerializeToString() == b""


def test_resource_spans_empty_matches_proto() -> None:
    assert ResourceSpans().SerializeToString() == ProtoResourceSpans().SerializeToString()


def test_resource_spans_schema_url() -> None:
    our = ResourceSpans(schema_url="https://example.com")
    proto = ProtoResourceSpans(schema_url="https://example.com")
    assert our.SerializeToString() == proto.SerializeToString()


def test_resource_spans_with_resource() -> None:
    res = Resource(attributes=[KeyValue(key="k", value=AnyValue(string_value="v"))])
    proto_res = ProtoResource(attributes=[ProtoKeyValue(key="k", value=ProtoAnyValue(string_value="v"))])
    our = ResourceSpans(resource=res, schema_url="s")
    proto = ProtoResourceSpans(resource=proto_res, schema_url="s")
    assert our.SerializeToString() == proto.SerializeToString()


def test_resource_spans_with_scope_spans() -> None:
    span = Span(name="s")
    proto_span = ProtoSpan(name="s")
    ss = ScopeSpans(spans=[span])
    proto_ss = ProtoScopeSpans(spans=[proto_span])
    our = ResourceSpans(scope_spans=[ss])
    proto = ProtoResourceSpans(scope_spans=[proto_ss])
    assert our.SerializeToString() == proto.SerializeToString()
