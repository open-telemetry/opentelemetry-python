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

"""JSON encoder for OpenTelemetry spans to match the ProtoJSON format."""

import base64
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import Event, ReadableSpan, Status, StatusCode
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.exporter.otlp.json.common._internal.encoder_utils import encode_id
from opentelemetry.exporter.otlp.json.common.encoding import IdEncoding

def encode_spans(
        spans: Sequence[ReadableSpan],
        id_encoding: Optional[IdEncoding] = None) -> Dict[str, Any]:
    """Encodes spans in the OTLP JSON format.

    Returns:
        A dict representing the spans in OTLP JSON format as specified in the
        OpenTelemetry Protocol and ProtoJSON format.
    """
    id_encoding = id_encoding or IdEncoding.BASE64

    resource_spans = {}  # Key is resource hashcode
    for span in spans:
        if span.resource.attributes or not resource_spans:
            resource_key = _compute_resource_hashcode(span.resource)
            if resource_key not in resource_spans:
                resource_spans[resource_key] = {
                    "resource": _encode_resource(span.resource),
                    "scopeSpans": {},  # Key is instrumentation scope hashcode
                    "schemaUrl": span.resource.schema_url or "",
                }
        else:
            # Handle empty resource
            resource_key = ""
            if resource_key not in resource_spans:
                resource_spans[resource_key] = {
                    "resource": _encode_resource(span.resource),
                    "scopeSpans": {},
                    "schemaUrl": "",
                }

        instrumentation_scope_hashcode = (
            _compute_instrumentation_scope_hashcode(span.instrumentation_scope)
        )
        scope_spans = resource_spans[resource_key]["scopeSpans"]

        if instrumentation_scope_hashcode not in scope_spans:
            scope_spans[instrumentation_scope_hashcode] = {
                "scope": _encode_instrumentation_scope(
                    span.instrumentation_scope
                ),
                "spans": [],
                "schemaUrl": (
                    span.instrumentation_scope.schema_url
                    if hasattr(span.instrumentation_scope, "schema_url")
                    else ""
                ),
            }

        scope_spans[instrumentation_scope_hashcode]["spans"].append(
            _encode_span(span, id_encoding)
        )

    # Transform resource_spans dict to list for proper JSON output
    resource_spans_list = []
    for resource_span_data in resource_spans.values():
        scope_spans_list = []
        for scope_span_data in resource_span_data["scopeSpans"].values():
            scope_spans_list.append(scope_span_data)

        resource_span_data["scopeSpans"] = scope_spans_list
        resource_spans_list.append(resource_span_data)

    return {"resourceSpans": resource_spans_list}


def _compute_resource_hashcode(resource: Resource) -> str:
    """Computes a hashcode for the resource based on its attributes."""
    if not resource.attributes:
        return ""
    # Simple implementation: use string representation of sorted attributes
    return str(sorted(resource.attributes.items()))


def _compute_instrumentation_scope_hashcode(
    scope: InstrumentationScope,
) -> str:
    """Computes a hashcode for the instrumentation scope."""
    if scope is None:
        return ""
    return f"{scope.name}|{scope.version}"


def _encode_resource(resource: Resource) -> Dict[str, Any]:
    """Encodes a resource into OTLP JSON format."""
    if not resource:
        return {"attributes": []}

    return {
        "attributes": _encode_attributes(resource.attributes),
        "droppedAttributesCount": 0,  # Not tracking dropped attributes yet
    }


def _encode_instrumentation_scope(
    scope: Optional[InstrumentationScope],
) -> Dict[str, Any]:
    """Encodes an instrumentation scope into OTLP JSON format."""
    if scope is None:
        return {"name": "", "version": ""}

    return {
        "name": scope.name or "",
        "version": scope.version or "",
        "attributes": [],  # Not using attributes for scope yet
        "droppedAttributesCount": 0,
    }


def _encode_span(span: ReadableSpan, id_encoding: IdEncoding) -> Dict[str, Any]:
    """Encodes a span into OTLP JSON format."""

    # Convert trace_id and span_id to base64
    trace_id = encode_id(id_encoding, span.context.trace_id, 16)
    span_id = encode_id(id_encoding, span.context.span_id, 8)

    parent_id = ""
    # Handle different span implementations that might not have parent_span_id
    if hasattr(span, "parent_span_id") and span.parent_span_id:
        parent_id = encode_id(id_encoding, span.parent_span_id, 8)
    elif (
        hasattr(span, "parent")
        and span.parent
        and hasattr(span.parent, "span_id")
    ):
        parent_id = encode_id(id_encoding, span.parent.span_id, 8)

    # Convert timestamps to nanoseconds
    start_time_ns = _timestamp_to_ns(span.start_time)
    end_time_ns = _timestamp_to_ns(span.end_time) if span.end_time else 0

    # Format span according to ProtoJSON
    result = {
        "traceId": trace_id,
        "spanId": span_id,
        "parentSpanId": parent_id,
        "name": span.name,
        "kind": _get_span_kind_value(span.kind),
        "startTimeUnixNano": str(start_time_ns),
        "endTimeUnixNano": str(end_time_ns),
        "attributes": _encode_attributes(span.attributes),
        "droppedAttributesCount": span.dropped_attributes,
        "events": _encode_events(span.events),
        "droppedEventsCount": span.dropped_events,
        "links": _encode_links(span.links, id_encoding),
        "droppedLinksCount": span.dropped_links,
        "status": _encode_status(span.status),
    }

    # Add traceState if it exists
    if span.context.trace_state:
        result["traceState"] = str(span.context.trace_state)

    return result


def _encode_attributes(attributes: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Encodes attributes into OTLP JSON format."""
    if not attributes:
        return []

    attribute_list = []
    for key, value in attributes.items():
        if value is None:
            continue

        attribute = {"key": key}
        attribute.update(_encode_attribute_value(value))
        attribute_list.append(attribute)

    return attribute_list


# pylint: disable=too-many-return-statements
def _encode_attribute_value(value: Any) -> Dict[str, Any]:
    """Encodes a single attribute value into OTLP JSON format."""
    if isinstance(value, bool):
        return {"value": {"boolValue": value}}
    if isinstance(value, int):
        return {"value": {"intValue": str(value)}}
    if isinstance(value, float):
        return {"value": {"doubleValue": value}}
    if isinstance(value, str):
        return {"value": {"stringValue": value}}
    if isinstance(value, (list, tuple)):
        if not value:
            return {"value": {"arrayValue": {"values": []}}}

        array_value = {"values": []}
        for element in value:
            element_value = _encode_attribute_value(element)["value"]
            array_value["values"].append(element_value)

        return {"value": {"arrayValue": array_value}}
    if isinstance(value, bytes):
        return {
            "value": {"bytesValue": base64.b64encode(value).decode("ascii")}
        }
    # Convert anything else to string
    return {"value": {"stringValue": str(value)}}


def _encode_events(
    events: Sequence[Union[Event, Tuple[int, str, Dict[str, Any]]]],
) -> List[Dict[str, Any]]:
    """Encodes span events into OTLP JSON format."""
    if not events:
        return []

    event_list = []

    # Handle both Event objects and tuples
    for event in events:
        if (
            hasattr(event, "timestamp")
            and hasattr(event, "name")
            and hasattr(event, "attributes")
        ):
            # It's an Event object
            timestamp_ns = _timestamp_to_ns(event.timestamp)
            event_list.append(
                {
                    "timeUnixNano": str(timestamp_ns),
                    "name": event.name,
                    "attributes": _encode_attributes(event.attributes),
                    "droppedAttributesCount": getattr(
                        event, "dropped_attributes_count", 0
                    ),
                }
            )
        elif isinstance(event, tuple) and len(event) == 3:
            # It's a tuple of (timestamp, name, attributes)
            timestamp, name, attributes = event
            timestamp_ns = _timestamp_to_ns(timestamp)
            event_list.append(
                {
                    "timeUnixNano": str(timestamp_ns),
                    "name": name,
                    "attributes": _encode_attributes(attributes),
                    "droppedAttributesCount": 0,  # Not tracking dropped event attributes yet
                }
            )

    return event_list


def _encode_links(links: Sequence[trace.Link], id_encoding: IdEncoding) -> List[Dict[str, Any]]:
    """Encodes span links into OTLP JSON format."""
    if not links:
        return []

    link_list = []
    for link in links:
        trace_id = encode_id(id_encoding, link.context.trace_id, 16)
        span_id = encode_id(id_encoding, link.context.span_id, 8)

        link_data = {
            "traceId": trace_id,
            "spanId": span_id,
            "attributes": _encode_attributes(link.attributes),
            "droppedAttributesCount": 0,  # Not tracking dropped link attributes yet
        }

        if link.context.trace_state:
            link_data["traceState"] = str(link.context.trace_state)

        link_list.append(link_data)

    return link_list


def _encode_status(status: Union[Status, StatusCode, None]) -> Dict[str, Any]:
    """Encodes span status into OTLP JSON format."""
    if status is None:
        return {"code": "STATUS_CODE_UNSET"}

    # Handle Status objects with status_code attribute
    if hasattr(status, "status_code"):
        status_code = status.status_code
        if status_code == StatusCode.OK:
            result = {"code": "STATUS_CODE_OK"}
        elif status_code == StatusCode.ERROR:
            result = {"code": "STATUS_CODE_ERROR"}
        else:
            result = {"code": "STATUS_CODE_UNSET"}

        # Add description if available
        if hasattr(status, "description") and status.description:
            result["message"] = status.description

        return result

    # Handle direct StatusCode values
    if status == StatusCode.OK:
        return {"code": "STATUS_CODE_OK"}
    if status == StatusCode.ERROR:
        return {"code": "STATUS_CODE_ERROR"}
    return {"code": "STATUS_CODE_UNSET"}


def _get_span_kind_value(kind: trace.SpanKind) -> str:
    """Maps the OpenTelemetry SpanKind to OTLP JSON values."""
    if kind == trace.SpanKind.SERVER:
        return "SPAN_KIND_SERVER"
    if kind == trace.SpanKind.CLIENT:
        return "SPAN_KIND_CLIENT"
    if kind == trace.SpanKind.PRODUCER:
        return "SPAN_KIND_PRODUCER"
    if kind == trace.SpanKind.CONSUMER:
        return "SPAN_KIND_CONSUMER"
    if kind == trace.SpanKind.INTERNAL:
        return "SPAN_KIND_INTERNAL"
    return "SPAN_KIND_UNSPECIFIED"


def _timestamp_to_ns(timestamp: Optional[int]) -> int:
    """Converts a timestamp to nanoseconds."""
    if timestamp is None:
        return 0

    if timestamp > 1e10:  # Already in nanoseconds
        return timestamp

    return int(timestamp * 1e9)  # Convert seconds to nanoseconds
