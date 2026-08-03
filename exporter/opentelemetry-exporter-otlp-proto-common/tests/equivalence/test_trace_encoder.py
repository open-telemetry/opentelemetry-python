# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry.exporter.otlp.proto.common.trace_encoder import (
    encode_spans as proto_encode_spans,
)
from opentelemetry.exporter.otlp._proto.common._internal.trace_encoder import (
    encode_spans as pyproto_encode_spans,
)
from opentelemetry.sdk.trace import Event as SDKEvent
from opentelemetry.sdk.trace import Resource as SDKResource
from opentelemetry.sdk.trace import SpanContext as SDKSpanContext
from opentelemetry.sdk.trace import _Span as SDKSpan
from opentelemetry.sdk.util.instrumentation import (
    InstrumentationScope as SDKInstrumentationScope,
)
from opentelemetry.trace import Link as SDKLink
from opentelemetry.trace import SpanKind as SDKSpanKind
from opentelemetry.trace import TraceFlags as SDKTraceFlags
from opentelemetry.trace.status import Status as SDKStatus
from opentelemetry.trace.status import StatusCode as SDKStatusCode


def _make_exhaustive_spans() -> list[SDKSpan]:
    trace_id = 0x3E0C63257DE34C926F9EFCD03927272E

    base_time = 683647322 * 10**9
    start_times = (
        base_time,
        base_time + 150 * 10**6,
        base_time + 300 * 10**6,
        base_time + 400 * 10**6,
        base_time + 500 * 10**6,
        base_time + 600 * 10**6,
    )
    end_times = (
        start_times[0] + (50 * 10**6),
        start_times[1] + (100 * 10**6),
        start_times[2] + (200 * 10**6),
        start_times[3] + (300 * 10**6),
        start_times[4] + (400 * 10**6),
        start_times[5] + (500 * 10**6),
    )

    parent_span_context = SDKSpanContext(
        trace_id, 0x1111111111111111, is_remote=True
    )
    other_context = SDKSpanContext(
        trace_id, 0x2222222222222222, is_remote=False
    )

    span1 = SDKSpan(
        name="test-span-1",
        context=SDKSpanContext(
            trace_id,
            0x34BF92DEEFC58C92,
            is_remote=False,
            trace_flags=SDKTraceFlags(SDKTraceFlags.SAMPLED),
        ),
        parent=parent_span_context,
        events=(
            SDKEvent(
                name="event0",
                timestamp=base_time + 50 * 10**6,
                attributes={
                    "annotation_bool": True,
                    "annotation_string": "annotation_test",
                    "key_float": 0.3,
                },
            ),
        ),
        links=(
            SDKLink(context=other_context, attributes={"key_bool": True}),
        ),
        resource=SDKResource({}, "resource_schema_url"),
    )
    span1.start(start_time=start_times[0])
    span1.set_attribute("key_bool", False)
    span1.set_attribute("key_string", "hello_world")
    span1.set_attribute("key_float", 111.22)
    span1.set_status(SDKStatus(SDKStatusCode.ERROR, "Example description"))
    span1.end(end_time=end_times[0])

    span2 = SDKSpan(
        name="test-span-2",
        context=parent_span_context,
        parent=None,
        resource=SDKResource(attributes={"key_resource": "some_resource"}),
    )
    span2.start(start_time=start_times[1])
    span2.end(end_time=end_times[1])

    span3 = SDKSpan(
        name="test-span-3",
        context=other_context,
        parent=None,
        resource=SDKResource(attributes={"key_resource": "some_resource"}),
    )
    span3.start(start_time=start_times[2])
    span3.set_attribute("key_string", "hello_world")
    span3.end(end_time=end_times[2])

    span4 = SDKSpan(
        name="test-span-4",
        context=other_context,
        parent=None,
        resource=SDKResource({}, "resource_schema_url"),
        instrumentation_scope=SDKInstrumentationScope(
            name="name", version="version"
        ),
    )
    span4.start(start_time=start_times[3])
    span4.end(end_time=end_times[3])

    span5 = SDKSpan(
        name="test-span-5",
        context=other_context,
        parent=None,
        resource=SDKResource(
            attributes={"key_resource": "another_resource"},
            schema_url="resource_schema_url",
        ),
        instrumentation_scope=SDKInstrumentationScope(
            name="scope_1_name",
            version="scope_1_version",
            schema_url="scope_1_schema_url",
        ),
    )
    span5.start(start_time=start_times[4])
    span5.end(end_time=end_times[4])

    span6 = SDKSpan(
        name="test-span-6",
        context=other_context,
        parent=None,
        resource=SDKResource(
            attributes={"key_resource": "another_resource"},
            schema_url="resource_schema_url",
        ),
        instrumentation_scope=SDKInstrumentationScope(
            name="scope_2_name",
            version="scope_2_version",
            schema_url="scope_2_schema_url",
            attributes={"one": "1", "two": 2},
        ),
    )
    span6.start(start_time=start_times[5])
    span6.end(end_time=end_times[5])

    return [span1, span2, span3, span4, span5, span6]


def test_encode_spans_single_minimal() -> None:
    span = SDKSpan(
        name="hello",
        context=SDKSpanContext(
            0x3E0C63257DE34C926F9EFCD03927272E,
            0x34BF92DEEFC58C92,
            is_remote=False,
            trace_flags=SDKTraceFlags(SDKTraceFlags.SAMPLED),
        ),
        parent=None,
        resource=SDKResource({}),
    )
    span.start(start_time=1_000_000_000)
    span.end(end_time=2_000_000_000)
    spans = [span]
    assert pyproto_encode_spans(spans).SerializeToString() == proto_encode_spans(spans).SerializeToString()


def test_encode_spans_with_attributes_and_status() -> None:
    spans = _make_exhaustive_spans()[:1]  # span1 has attributes, events, links, status
    assert pyproto_encode_spans(spans).SerializeToString() == proto_encode_spans(spans).SerializeToString()


def test_encode_spans_multiple_resources() -> None:
    spans = _make_exhaustive_spans()
    assert pyproto_encode_spans(spans).SerializeToString() == proto_encode_spans(spans).SerializeToString()


def test_encode_spans_with_instrumentation_scope() -> None:
    spans = _make_exhaustive_spans()[3:4]  # span4 has instrumentation scope
    assert pyproto_encode_spans(spans).SerializeToString() == proto_encode_spans(spans).SerializeToString()


def test_encode_spans_with_scope_attributes() -> None:
    spans = _make_exhaustive_spans()[5:6]  # span6 has scope with attributes
    assert pyproto_encode_spans(spans).SerializeToString() == proto_encode_spans(spans).SerializeToString()


def test_encode_spans_empty_list() -> None:
    assert pyproto_encode_spans([]).SerializeToString() == proto_encode_spans([]).SerializeToString()


def test_encode_spans_exhaustive_matches_proto() -> None:
    spans = _make_exhaustive_spans()
    assert pyproto_encode_spans(spans).SerializeToString() == proto_encode_spans(spans).SerializeToString()
