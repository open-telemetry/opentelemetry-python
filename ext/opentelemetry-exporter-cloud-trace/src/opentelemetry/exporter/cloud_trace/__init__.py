# Copyright OpenTelemetry Authors
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

"""Cloud Trace Span Exporter for OpenTelemetry. Uses Cloud Trace Client's REST
API to export traces and spans for viewing in Cloud Trace.

Usage
-----

.. code-block:: python

    from opentelemetry import trace
    from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleExportSpanProcessor

    trace.set_tracer_provider(TracerProvider())

    cloud_trace_exporter = CloudTraceSpanExporter()
    trace.get_tracer_provider().add_span_processor(
        SimpleExportSpanProcessor(cloud_trace_exporter)
    )
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("foo"):
        print("Hello world!")


API
---
"""

import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple

import google.auth
from google.cloud.trace_v2 import TraceServiceClient
from google.cloud.trace_v2.proto.trace_pb2 import AttributeValue
from google.cloud.trace_v2.proto.trace_pb2 import Span as ProtoSpan
from google.cloud.trace_v2.proto.trace_pb2 import TruncatableString
from google.rpc.status_pb2 import Status

import opentelemetry.trace as trace_api
from opentelemetry.sdk.trace import Event
from opentelemetry.sdk.trace.export import Span, SpanExporter, SpanExportResult
from opentelemetry.sdk.util import BoundedDict
from opentelemetry.util import types

logger = logging.getLogger(__name__)

MAX_NUM_LINKS = 128
MAX_NUM_EVENTS = 32
MAX_EVENT_ATTRS = 4
MAX_LINK_ATTRS = 32
MAX_SPAN_ATTRS = 32


class CloudTraceSpanExporter(SpanExporter):
    """Cloud Trace span exporter for OpenTelemetry.

    Args:
        project_id: ID of the cloud project that will receive the traces.
        client: Cloud Trace client. If not given, will be taken from gcloud
            default credentials
    """

    def __init__(
        self, project_id=None, client=None,
    ):
        self.client = client or TraceServiceClient()
        if not project_id:
            _, self.project_id = google.auth.default()
        else:
            self.project_id = project_id

    def export(self, spans: Sequence[Span]) -> SpanExportResult:
        """Export the spans to Cloud Trace.

        See: https://cloud.google.com/trace/docs/reference/v2/rest/v2/projects.traces/batchWrite

        Args:
            spans: Tuple of spans to export
        """
        cloud_trace_spans = []
        for span in self._translate_to_cloud_trace(spans):
            try:
                cloud_trace_spans.append(self.client.create_span(**span))
            # pylint: disable=broad-except
            except Exception as ex:
                logger.error("Error when creating span %s", span, exc_info=ex)

        try:
            self.client.batch_write_spans(
                "projects/{}".format(self.project_id), cloud_trace_spans,
            )
        # pylint: disable=broad-except
        except Exception as ex:
            logger.error("Error while writing to Cloud Trace", exc_info=ex)
            return SpanExportResult.FAILURE

        return SpanExportResult.SUCCESS

    def _translate_to_cloud_trace(
        self, spans: Sequence[Span]
    ) -> List[Dict[str, Any]]:
        """Translate the spans to Cloud Trace format.

        Args:
            spans: Tuple of spans to convert
        """

        cloud_trace_spans = []

        for span in spans:
            ctx = span.get_context()
            trace_id = _get_hexadecimal_trace_id(ctx.trace_id)
            span_id = _get_hexadecimal_span_id(ctx.span_id)
            span_name = "projects/{}/traces/{}/spans/{}".format(
                self.project_id, trace_id, span_id
            )

            parent_id = None
            if span.parent:
                parent_id = _get_hexadecimal_span_id(span.parent.span_id)

            start_time = _get_time_from_ns(span.start_time)
            end_time = _get_time_from_ns(span.end_time)

            if len(span.attributes) > MAX_SPAN_ATTRS:
                logger.warning(
                    "Span has more then %s attributes, some will be truncated",
                    MAX_SPAN_ATTRS,
                )

            cloud_trace_spans.append(
                {
                    "name": span_name,
                    "span_id": span_id,
                    "display_name": _get_truncatable_str_object(
                        span.name, 128
                    ),
                    "start_time": start_time,
                    "end_time": end_time,
                    "parent_span_id": parent_id,
                    "attributes": _extract_attributes(
                        span.attributes, MAX_SPAN_ATTRS
                    ),
                    "links": _extract_links(span.links),
                    "status": _extract_status(span.status),
                    "time_events": _extract_events(span.events),
                }
            )
            # TODO: Leverage more of the Cloud Trace API, e.g.
            #  same_process_as_parent_span and child_span_count

        return cloud_trace_spans

    def shutdown(self):
        pass


def _get_hexadecimal_trace_id(trace_id: int) -> str:
    return "{:032x}".format(trace_id)


def _get_hexadecimal_span_id(span_id: int) -> str:
    return "{:016x}".format(span_id)


def _get_time_from_ns(nanoseconds: int) -> Dict:
    """Given epoch nanoseconds, split into epoch milliseconds and remaining
    nanoseconds"""
    if not nanoseconds:
        return None
    seconds, nanos = divmod(nanoseconds, 1e9)
    return {"seconds": int(seconds), "nanos": int(nanos)}


def _get_truncatable_str_object(str_to_convert: str, max_length: int):
    """Truncate the string if it exceeds the length limit and record the
    truncated bytes count."""
    truncated, truncated_byte_count = _truncate_str(str_to_convert, max_length)

    return TruncatableString(
        value=truncated, truncated_byte_count=truncated_byte_count
    )


def _truncate_str(str_to_check: str, limit: int) -> Tuple[str, int]:
    """Check the length of a string. If exceeds limit, then truncate it."""
    encoded = str_to_check.encode("utf-8")
    truncated_str = encoded[:limit].decode("utf-8", errors="ignore")
    return truncated_str, len(encoded) - len(truncated_str.encode("utf-8"))


def _extract_status(status: trace_api.Status) -> Optional[Status]:
    """Convert a Status object to protobuf object."""
    if not status:
        return None
    status_dict = {"details": None, "code": status.canonical_code.value}

    if status.description is not None:
        status_dict["message"] = status.description

    return Status(**status_dict)


def _extract_links(links: Sequence[trace_api.Link]) -> ProtoSpan.Links:
    """Convert span.links"""
    if not links:
        return None
    extracted_links = []
    dropped_links = 0
    if len(links) > MAX_NUM_LINKS:
        logger.warning(
            "Exporting more then %s links, some will be truncated",
            MAX_NUM_LINKS,
        )
        dropped_links = len(links) - MAX_NUM_LINKS
        links = links[:MAX_NUM_LINKS]
    for link in links:
        if len(link.attributes) > MAX_LINK_ATTRS:
            logger.warning(
                "Link has more then %s attributes, some will be truncated",
                MAX_LINK_ATTRS,
            )
        trace_id = _get_hexadecimal_trace_id(link.context.trace_id)
        span_id = _get_hexadecimal_span_id(link.context.span_id)
        extracted_links.append(
            {
                "trace_id": trace_id,
                "span_id": span_id,
                "type": "TYPE_UNSPECIFIED",
                "attributes": _extract_attributes(
                    link.attributes, MAX_LINK_ATTRS
                ),
            }
        )
    return ProtoSpan.Links(
        link=extracted_links, dropped_links_count=dropped_links
    )


def _extract_events(events: Sequence[Event]) -> ProtoSpan.TimeEvents:
    """Convert span.events to dict."""
    if not events:
        return None
    logs = []
    dropped_annontations = 0
    if len(events) > MAX_NUM_EVENTS:
        logger.warning(
            "Exporting more then %s annotations, some will be truncated",
            MAX_NUM_EVENTS,
        )
        dropped_annontations = len(events) - MAX_NUM_EVENTS
        events = events[:MAX_NUM_EVENTS]
    for event in events:
        if len(event.attributes) > MAX_EVENT_ATTRS:
            logger.warning(
                "Event %s has more then %s attributes, some will be truncated",
                event.name,
                MAX_EVENT_ATTRS,
            )
        logs.append(
            {
                "time": _get_time_from_ns(event.timestamp),
                "annotation": {
                    "description": _get_truncatable_str_object(
                        event.name, 256
                    ),
                    "attributes": _extract_attributes(
                        event.attributes, MAX_EVENT_ATTRS
                    ),
                },
            }
        )
    return ProtoSpan.TimeEvents(
        time_event=logs,
        dropped_annotations_count=dropped_annontations,
        dropped_message_events_count=0,
    )


def _extract_attributes(
    attrs: types.Attributes, num_attrs_limit: int
) -> ProtoSpan.Attributes:
    """Convert span.attributes to dict."""
    attributes_dict = BoundedDict(num_attrs_limit)

    for key, value in attrs.items():
        key = _truncate_str(key, 128)[0]
        value = _format_attribute_value(value)

        if value is not None:
            attributes_dict[key] = value
    return ProtoSpan.Attributes(
        attribute_map=attributes_dict,
        dropped_attributes_count=len(attrs) - len(attributes_dict),
    )


def _format_attribute_value(value: types.AttributeValue) -> AttributeValue:
    if isinstance(value, bool):
        value_type = "bool_value"
    elif isinstance(value, int):
        value_type = "int_value"
    elif isinstance(value, str):
        value_type = "string_value"
        value = _get_truncatable_str_object(value, 256)
    elif isinstance(value, float):
        value_type = "string_value"
        value = _get_truncatable_str_object("{:0.4f}".format(value), 256)
    else:
        logger.warning(
            "ignoring attribute value %s of type %s. Values type must be one "
            "of bool, int, string or float",
            value,
            type(value),
        )
        return None

    return AttributeValue(**{value_type: value})
