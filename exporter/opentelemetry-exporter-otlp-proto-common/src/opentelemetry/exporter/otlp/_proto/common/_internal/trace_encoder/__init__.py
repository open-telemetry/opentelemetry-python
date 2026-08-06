# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from logging import getLogger
from collections import defaultdict
from collections.abc import Sequence

from opentelemetry.exporter.otlp._proto.common._internal import (
    _encode_attributes,
    _encode_instrumentation_scope,
    _encode_resource,
    _encode_span_id,
    _encode_trace_id,
)
from opentelemetry._proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)
from opentelemetry._proto.trace.v1.trace_pb2 import (
    ResourceSpans,
    ScopeSpans,
    Span,
    Status,
)
from opentelemetry.sdk.trace import Event, ReadableSpan
from opentelemetry.trace import Link, SpanKind
from opentelemetry.trace.span import SpanContext, TraceState

# Map SDK SpanKind (0-4) to proto SpanKind (1-5)
_SPAN_KIND_MAP = {
    SpanKind.INTERNAL: 1,
    SpanKind.SERVER: 2,
    SpanKind.CLIENT: 3,
    SpanKind.PRODUCER: 4,
    SpanKind.CONSUMER: 5,
}

# proto SpanFlags values
_SPAN_FLAGS_CONTEXT_HAS_IS_REMOTE_MASK = 0x00000100
_SPAN_FLAGS_CONTEXT_IS_REMOTE_MASK = 0x00000200

_logger = getLogger(__name__)


def encode_spans(sdk_spans: Sequence[ReadableSpan]) -> ExportTraceServiceRequest:
    return ExportTraceServiceRequest(
        resource_spans=_encode_resource_spans(sdk_spans)
    )


def _encode_resource_spans(
    sdk_spans: Sequence[ReadableSpan],
) -> list[ResourceSpans]:
    sdk_resource_spans: dict = defaultdict(lambda: defaultdict(list))

    for sdk_span in sdk_spans:
        sdk_resource = sdk_span.resource
        sdk_instrumentation = sdk_span.instrumentation_scope or None
        pb2_span = _encode_span(sdk_span)
        sdk_resource_spans[sdk_resource][sdk_instrumentation].append(pb2_span)

    pb2_resource_spans = []
    for sdk_resource, sdk_instrumentations in sdk_resource_spans.items():
        scope_spans = []
        for sdk_instrumentation, pb2_spans in sdk_instrumentations.items():
            scope_spans.append(
                ScopeSpans(
                    scope=_encode_instrumentation_scope(sdk_instrumentation),
                    spans=pb2_spans,
                    schema_url=sdk_instrumentation.schema_url
                    if sdk_instrumentation
                    else "",
                )
            )
        pb2_resource_spans.append(
            ResourceSpans(
                resource=_encode_resource(sdk_resource),
                scope_spans=scope_spans,
                schema_url=sdk_resource.schema_url,
            )
        )
    return pb2_resource_spans


def _span_flags(parent_span_context: SpanContext | None) -> int:
    flags = _SPAN_FLAGS_CONTEXT_HAS_IS_REMOTE_MASK
    if parent_span_context and parent_span_context.is_remote:
        flags |= _SPAN_FLAGS_CONTEXT_IS_REMOTE_MASK
    return flags


def _encode_span(sdk_span: ReadableSpan) -> Span:
    span_context = sdk_span.get_span_context()
    return Span(
        trace_id=_encode_trace_id(span_context.trace_id),
        span_id=_encode_span_id(span_context.span_id),
        trace_state=_encode_trace_state(span_context.trace_state),
        parent_span_id=_encode_parent_id(sdk_span.parent),
        name=sdk_span.name,
        kind=_SPAN_KIND_MAP[sdk_span.kind],
        start_time_unix_nano=sdk_span.start_time,
        end_time_unix_nano=sdk_span.end_time,
        attributes=_encode_attributes(sdk_span.attributes),
        events=_encode_events(sdk_span.events),
        links=_encode_links(sdk_span.links),
        status=_encode_status(sdk_span.status),
        dropped_attributes_count=sdk_span.dropped_attributes,
        dropped_events_count=sdk_span.dropped_events,
        dropped_links_count=sdk_span.dropped_links,
        flags=_span_flags(sdk_span.parent),
    )


def _encode_events(events: Sequence[Event]) -> list[Span.Event] | None:
    if not events:
        return None
    return [
        Span.Event(
            name=event.name,
            time_unix_nano=event.timestamp,
            attributes=_encode_attributes(event.attributes),
            dropped_attributes_count=event.dropped_attributes,
        )
        for event in events
    ]


def _encode_links(links: Sequence[Link]) -> list[Span.Link] | None:
    if not links:
        return None
    return [
        Span.Link(
            trace_id=_encode_trace_id(link.context.trace_id),
            span_id=_encode_span_id(link.context.span_id),
            attributes=_encode_attributes(link.attributes),
            dropped_attributes_count=link.dropped_attributes,
            flags=_span_flags(link.context),
        )
        for link in links
    ]


def _encode_status(status) -> Status | None:
    if status is None:
        return None
    return Status(
        code=status.status_code.value,
        message=status.description or "",
    )


def _encode_trace_state(trace_state: TraceState) -> str:
    if trace_state is None:
        return ""
    return ",".join(f"{key}={value}" for key, value in trace_state.items())


def _encode_parent_id(context: SpanContext | None) -> bytes:
    if context:
        return _encode_span_id(context.span_id)
    return b""
