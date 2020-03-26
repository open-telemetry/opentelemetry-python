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

"""OpenTelemetry Collector Exporter."""

import logging
from typing import Optional, Sequence

import grpc
from opencensus.proto.agent.trace.v1 import (
    trace_service_pb2,
    trace_service_pb2_grpc,
)
from opencensus.proto.trace.v1 import trace_pb2

import opentelemetry.ext.otcollector.util as utils
import opentelemetry.trace as trace_api
from opentelemetry.sdk.trace import Span, SpanContext
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import SpanKind, TraceState

DEFAULT_ENDPOINT = "localhost:55678"

logger = logging.getLogger(__name__)


# pylint: disable=no-member
class CollectorSpanExporter(SpanExporter):
    """OpenTelemetry Collector span exporter.

    Args:
        endpoint: OpenTelemetry Collector OpenCensus receiver endpoint.
        service_name: Name of Collector service.
        host_name: Host name.
        client: TraceService client stub.
    """

    def __init__(
        self,
        endpoint=DEFAULT_ENDPOINT,
        service_name=None,
        host_name=None,
        client=None,
    ):
        self.endpoint = endpoint
        if client is None:
            self.channel = grpc.insecure_channel(self.endpoint)
            self.client = trace_service_pb2_grpc.TraceServiceStub(
                channel=self.channel
            )
        else:
            self.client = client

        self.node = utils.get_node(service_name, host_name)

    def export(self, spans: Sequence[Span]) -> SpanExportResult:
        try:
            responses = self.client.Export(self.generate_span_requests(spans))

            # Read response
            for _ in responses:
                pass

        except grpc.RpcError:
            return SpanExportResult.FAILED_NOT_RETRYABLE

        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass

    def generate_span_requests(self, spans):
        collector_spans = translate_to_collector(spans)
        service_request = trace_service_pb2.ExportTraceServiceRequest(
            node=self.node, spans=collector_spans
        )
        yield service_request


# pylint: disable=too-many-branches
def translate_to_collector(spans: Sequence[Span]):
    collector_spans = []
    for span in spans:
        status = None
        if span.status is not None:
            status = trace_pb2.Status(
                code=span.status.canonical_code.value,
                message=span.status.description,
            )
        collector_span = trace_pb2.Span(
            name=trace_pb2.TruncatableString(value=span.name),
            kind=utils.get_collector_span_kind(span.kind),
            trace_id=span.context.trace_id.to_bytes(16, "big"),
            span_id=span.context.span_id.to_bytes(8, "big"),
            start_time=utils.proto_timestamp_from_time_ns(span.start_time),
            end_time=utils.proto_timestamp_from_time_ns(span.end_time),
            status=status,
        )

        parent_id = 0
        if isinstance(span.parent, trace_api.Span):
            parent_id = span.parent.get_context().span_id
        elif isinstance(span.parent, trace_api.SpanContext):
            parent_id = span.parent.span_id

        collector_span.parent_span_id = parent_id.to_bytes(8, "big")

        if span.context.trace_state is not None:
            for (key, value) in span.context.trace_state.items():
                collector_span.tracestate.entries.add(key=key, value=value)

        if span.attributes:
            for (key, value) in span.attributes.items():
                utils.add_proto_attribute_value(
                    collector_span.attributes, key, value
                )

        if span.events:
            for event in span.events:

                collector_annotation = trace_pb2.Span.TimeEvent.Annotation(
                    description=trace_pb2.TruncatableString(value=event.name)
                )

                if event.attributes:
                    for (key, value) in event.attributes.items():
                        utils.add_proto_attribute_value(
                            collector_annotation.attributes, key, value
                        )

                collector_span.time_events.time_event.add(
                    time=utils.proto_timestamp_from_time_ns(event.timestamp),
                    annotation=collector_annotation,
                )

        if span.links:
            for link in span.links:
                collector_span_link = collector_span.links.link.add()
                collector_span_link.trace_id = link.context.trace_id.to_bytes(
                    16, "big"
                )
                collector_span_link.span_id = link.context.span_id.to_bytes(
                    8, "big"
                )

                collector_span_link.type = (
                    trace_pb2.Span.Link.Type.TYPE_UNSPECIFIED
                )

                if isinstance(span.parent, trace_api.Span):
                    if (
                        link.context.span_id
                        == span.parent.get_context().span_id
                        and link.context.trace_id
                        == span.parent.get_context().trace_id
                    ):
                        collector_span_link.type = (
                            trace_pb2.Span.Link.Type.PARENT_LINKED_SPAN
                        )
                elif isinstance(span.parent, trace_api.SpanContext):
                    if (
                        link.context.span_id == span.parent.span_id
                        and link.context.trace_id == span.parent.trace_id
                    ):
                        collector_span_link.type = (
                            trace_pb2.Span.Link.Type.PARENT_LINKED_SPAN
                        )

                if link.attributes:
                    for (key, value) in link.attributes.items():
                        utils.add_proto_attribute_value(
                            collector_span_link.attributes, key, value
                        )

        collector_spans.append(collector_span)
    return collector_spans
