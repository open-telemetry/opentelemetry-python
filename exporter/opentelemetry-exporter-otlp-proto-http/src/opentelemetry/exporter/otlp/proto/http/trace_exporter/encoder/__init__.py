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
from collections import abc
from typing import Any, List, Optional, Sequence

from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest as PB2ExportTraceServiceRequest,
)
from opentelemetry.proto.common.v1.common_pb2 import AnyValue as PB2AnyValue
from opentelemetry.proto.common.v1.common_pb2 import (
    ArrayValue as PB2ArrayValue,
)
from opentelemetry.proto.common.v1.common_pb2 import (
    InstrumentationScope as PB2InstrumentationScope,
)
from opentelemetry.proto.common.v1.common_pb2 import KeyValue as PB2KeyValue
from opentelemetry.proto.resource.v1.resource_pb2 import (
    Resource as PB2Resource,
)
from opentelemetry.proto.trace.v1.trace_pb2 import (
    ScopeSpans as PB2ScopeSpans,
)
from opentelemetry.proto.trace.v1.trace_pb2 import (
    ResourceSpans as PB2ResourceSpans,
)
from opentelemetry.proto.trace.v1.trace_pb2 import Span as PB2SPan
from opentelemetry.proto.trace.v1.trace_pb2 import Status as PB2Status
from opentelemetry.sdk.trace import Event
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.sdk.trace import Resource
from opentelemetry.sdk.trace import Span as SDKSpan
from opentelemetry.trace import Link
from opentelemetry.trace import SpanKind
from opentelemetry.trace.span import SpanContext, TraceState, Status
from opentelemetry.util.types import Attributes

# pylint: disable=E1101
_SPAN_KIND_MAP = {
    SpanKind.INTERNAL: PB2SPan.SpanKind.SPAN_KIND_INTERNAL,
    SpanKind.SERVER: PB2SPan.SpanKind.SPAN_KIND_SERVER,
    SpanKind.CLIENT: PB2SPan.SpanKind.SPAN_KIND_CLIENT,
    SpanKind.PRODUCER: PB2SPan.SpanKind.SPAN_KIND_PRODUCER,
    SpanKind.CONSUMER: PB2SPan.SpanKind.SPAN_KIND_CONSUMER,
}

_logger = logging.getLogger(__name__)


class _ProtobufEncoder:
    _CONTENT_TYPE = "application/x-protobuf"

    @classmethod
    def serialize(cls, sdk_spans: Sequence[SDKSpan]) -> str:
        return cls.encode(sdk_spans).SerializeToString()

    @staticmethod
    def encode(sdk_spans: Sequence[SDKSpan]) -> PB2ExportTraceServiceRequest:
        return PB2ExportTraceServiceRequest(
            resource_spans=_encode_resource_spans(sdk_spans)
        )


def _encode_resource_spans(
    sdk_spans: Sequence[SDKSpan],
) -> List[PB2ResourceSpans]:
    # We need to inspect the spans and group + structure them as:
    #
    #   Resource
    #     Instrumentation Library
    #       Spans
    #
    # First loop organizes the SDK spans in this structure. Protobuf messages
    # are not hashable so we stick with SDK data in this phase.
    #
    # Second loop encodes the data into Protobuf format.
    #
    sdk_resource_spans = {}

    for sdk_span in sdk_spans:
        sdk_resource = sdk_span.resource
        sdk_instrumentation = sdk_span.instrumentation_scope or None
        pb2_span = _encode_span(sdk_span)

        if sdk_resource not in sdk_resource_spans.keys():
            sdk_resource_spans[sdk_resource] = {
                sdk_instrumentation: [pb2_span]
            }
        elif (
            sdk_instrumentation not in sdk_resource_spans[sdk_resource].keys()
        ):
            sdk_resource_spans[sdk_resource][sdk_instrumentation] = [pb2_span]
        else:
            sdk_resource_spans[sdk_resource][sdk_instrumentation].append(
                pb2_span
            )

    pb2_resource_spans = []

    for sdk_resource, sdk_instrumentations in sdk_resource_spans.items():
        scope_spans = []
        for sdk_instrumentation, pb2_spans in sdk_instrumentations.items():
            scope_spans.append(
                PB2ScopeSpans(
                    scope=(_encode_instrumentation_scope(sdk_instrumentation)),
                    spans=pb2_spans,
                )
            )
        pb2_resource_spans.append(
            PB2ResourceSpans(
                resource=_encode_resource(sdk_resource),
                scope_spans=scope_spans,
            )
        )

    return pb2_resource_spans


def _encode_span(sdk_span: SDKSpan) -> PB2SPan:
    span_context = sdk_span.get_span_context()
    return PB2SPan(
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
    )


def _encode_events(
    events: Sequence[Event],
) -> Optional[List[PB2SPan.Event]]:
    pb2_events = None
    if events:
        pb2_events = []
        for event in events:
            encoded_event = PB2SPan.Event(
                name=event.name,
                time_unix_nano=event.timestamp,
            )
            for key, value in event.attributes.items():
                try:
                    encoded_event.attributes.append(
                        _encode_key_value(key, value)
                    )
                # pylint: disable=broad-except
                except Exception as error:
                    _logger.exception(error)
            pb2_events.append(encoded_event)
    return pb2_events


def _encode_links(links: List[Link]) -> List[PB2SPan.Link]:
    pb2_links = None
    if links:
        pb2_links = []
        for link in links:
            encoded_link = PB2SPan.Link(
                trace_id=_encode_trace_id(link.context.trace_id),
                span_id=_encode_span_id(link.context.span_id),
            )
            for key, value in link.attributes.items():
                try:
                    encoded_link.attributes.append(
                        _encode_key_value(key, value)
                    )
                # pylint: disable=broad-except
                except Exception as error:
                    _logger.exception(error)
            pb2_links.append(encoded_link)
    return pb2_links


def _encode_status(status: Status) -> Optional[PB2Status]:
    pb2_status = None
    if status is not None:
        pb2_status = PB2Status(
            code=status.status_code.value,
            message=status.description,
        )
    return pb2_status


def _encode_trace_state(trace_state: TraceState) -> Optional[str]:
    pb2_trace_state = None
    if trace_state is not None:
        pb2_trace_state = ",".join(
            [f"{key}={value}" for key, value in (trace_state.items())]
        )
    return pb2_trace_state


def _encode_parent_id(context: Optional[SpanContext]) -> Optional[bytes]:
    if isinstance(context, SpanContext):
        encoded_parent_id = _encode_span_id(context.span_id)
    else:
        encoded_parent_id = None
    return encoded_parent_id


def _encode_attributes(
    attributes: Attributes,
) -> Optional[List[PB2KeyValue]]:
    if attributes:
        pb2_attributes = []
        for key, value in attributes.items():
            try:
                pb2_attributes.append(_encode_key_value(key, value))
            except Exception as error:  # pylint: disable=broad-except
                _logger.exception(error)
    else:
        pb2_attributes = None
    return pb2_attributes


def _encode_resource(resource: Resource) -> PB2Resource:
    pb2_resource = PB2Resource()
    for key, value in resource.attributes.items():
        try:
            # pylint: disable=no-member
            pb2_resource.attributes.append(_encode_key_value(key, value))
        except Exception as error:  # pylint: disable=broad-except
            _logger.exception(error)
    return pb2_resource


def _encode_instrumentation_scope(
    instrumentation_scope: InstrumentationScope,
) -> PB2InstrumentationScope:
    if instrumentation_scope is None:
        pb2_instrumentation_scope = PB2InstrumentationScope()
    else:
        pb2_instrumentation_scope = PB2InstrumentationScope(
            name=instrumentation_scope.name,
            version=instrumentation_scope.version,
        )
    return pb2_instrumentation_scope


def _encode_value(value: Any) -> PB2AnyValue:
    if isinstance(value, bool):
        any_value = PB2AnyValue(bool_value=value)
    elif isinstance(value, str):
        any_value = PB2AnyValue(string_value=value)
    elif isinstance(value, int):
        any_value = PB2AnyValue(int_value=value)
    elif isinstance(value, float):
        any_value = PB2AnyValue(double_value=value)
    elif isinstance(value, abc.Sequence):
        any_value = PB2AnyValue(
            array_value=PB2ArrayValue(values=[_encode_value(v) for v in value])
        )
    # tracing specs currently does not support Mapping type attributes.
    # elif isinstance(value, abc.Mapping):
    #     pass
    else:
        raise Exception(f"Invalid type {type(value)} of value {value}")
    return any_value


def _encode_key_value(key: str, value: Any) -> PB2KeyValue:
    any_value = _encode_value(value)
    return PB2KeyValue(key=key, value=any_value)


def _encode_span_id(span_id: int) -> bytes:
    return span_id.to_bytes(length=8, byteorder="big", signed=False)


def _encode_trace_id(trace_id: int) -> bytes:
    return trace_id.to_bytes(length=16, byteorder="big", signed=False)
