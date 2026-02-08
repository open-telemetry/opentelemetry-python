# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
from collections import defaultdict
from typing import Optional, Sequence

from opentelemetry.exporter.otlp.json.common._internal import (
    _encode_attributes,
    _encode_instrumentation_scope,
    _encode_resource,
    _encode_span_id,
    _encode_trace_id,
)
from opentelemetry.proto_json.collector.trace.v1.trace_service import (
    ExportTraceServiceRequest as JSONExportTraceServiceRequest,
)
from opentelemetry.proto_json.trace.v1.trace import (
    ResourceSpans as JSONResourceSpans,
)
from opentelemetry.proto_json.trace.v1.trace import (
    ScopeSpans as JSONScopeSpans,
)
from opentelemetry.proto_json.trace.v1.trace import Span as JSONSpan
from opentelemetry.proto_json.trace.v1.trace import (
    SpanFlags as JSONSpanFlags,
)
from opentelemetry.proto_json.trace.v1.trace import Status as JSONStatus
from opentelemetry.sdk.trace import Event, ReadableSpan
from opentelemetry.trace import Link, SpanKind
from opentelemetry.trace.span import SpanContext, Status, TraceState

# pylint: disable=E1101
_SPAN_KIND_MAP = {
    SpanKind.INTERNAL: JSONSpan.SpanKind.SPAN_KIND_INTERNAL,
    SpanKind.SERVER: JSONSpan.SpanKind.SPAN_KIND_SERVER,
    SpanKind.CLIENT: JSONSpan.SpanKind.SPAN_KIND_CLIENT,
    SpanKind.PRODUCER: JSONSpan.SpanKind.SPAN_KIND_PRODUCER,
    SpanKind.CONSUMER: JSONSpan.SpanKind.SPAN_KIND_CONSUMER,
}

_logger = logging.getLogger(__name__)


def encode_spans(
    sdk_spans: Sequence[ReadableSpan],
) -> JSONExportTraceServiceRequest:
    return JSONExportTraceServiceRequest(
        resource_spans=_encode_resource_spans(sdk_spans)
    )


def _encode_resource_spans(
    sdk_spans: Sequence[ReadableSpan],
) -> list[JSONResourceSpans]:
    sdk_resource_spans = defaultdict(lambda: defaultdict(list))

    for sdk_span in sdk_spans:
        sdk_resource = sdk_span.resource
        sdk_instrumentation = sdk_span.instrumentation_scope or None
        json_span = _encode_span(sdk_span)

        sdk_resource_spans[sdk_resource][sdk_instrumentation].append(json_span)

    json_resource_spans = []

    for sdk_resource, sdk_instrumentations in sdk_resource_spans.items():
        scope_spans = []
        for sdk_instrumentation, json_spans in sdk_instrumentations.items():
            scope_spans.append(
                JSONScopeSpans(
                    scope=(_encode_instrumentation_scope(sdk_instrumentation)),
                    spans=json_spans,
                    schema_url=sdk_instrumentation.schema_url
                    if sdk_instrumentation
                    else None,
                )
            )
        json_resource_spans.append(
            JSONResourceSpans(
                resource=_encode_resource(sdk_resource),
                scope_spans=scope_spans,
                schema_url=sdk_resource.schema_url,
            )
        )

    return json_resource_spans


def _span_flags(parent_span_context: Optional[SpanContext]) -> int:
    flags = JSONSpanFlags.SPAN_FLAGS_CONTEXT_HAS_IS_REMOTE_MASK
    if parent_span_context and parent_span_context.is_remote:
        flags |= JSONSpanFlags.SPAN_FLAGS_CONTEXT_IS_REMOTE_MASK
    return int(flags)


def _encode_span(sdk_span: ReadableSpan) -> JSONSpan:
    span_context = sdk_span.get_span_context()
    return JSONSpan(
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


def _encode_events(
    events: Sequence[Event],
) -> Optional[list[JSONSpan.Event]]:
    return (
        [
            JSONSpan.Event(
                name=event.name,
                time_unix_nano=event.timestamp,
                attributes=_encode_attributes(event.attributes),
                dropped_attributes_count=event.dropped_attributes,
            )
            for event in events
        ]
        if events
        else None
    )


def _encode_links(links: Sequence[Link]) -> list[JSONSpan.Link]:
    return (
        [
            JSONSpan.Link(
                trace_id=_encode_trace_id(link.context.trace_id),
                span_id=_encode_span_id(link.context.span_id),
                attributes=_encode_attributes(link.attributes),
                dropped_attributes_count=link.dropped_attributes,
                flags=_span_flags(link.context),
            )
            for link in links
        ]
        if links
        else None
    )


def _encode_status(status: Status) -> Optional[JSONStatus]:
    return (
        JSONStatus(
            code=JSONStatus.StatusCode(status.status_code.value),
            message=status.description,
        )
        if status is not None
        else None
    )


def _encode_trace_state(trace_state: TraceState) -> Optional[str]:
    return (
        ",".join([f"{key}={value}" for key, value in (trace_state.items())])
        if trace_state is not None
        else None
    )


def _encode_parent_id(context: Optional[SpanContext]) -> Optional[bytes]:
    return _encode_span_id(context.span_id) if context else None
