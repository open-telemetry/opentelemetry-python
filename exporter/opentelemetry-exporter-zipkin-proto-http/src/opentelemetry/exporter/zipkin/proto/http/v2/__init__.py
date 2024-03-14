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

"""Zipkin Export Encoder for Protobuf

API spec: https://github.com/openzipkin/zipkin-api/blob/master/zipkin.proto
"""
from typing import List, Optional, Sequence

from opentelemetry.exporter.zipkin.encoder import Encoder
from opentelemetry.exporter.zipkin.proto.http.v2.gen import zipkin_pb2
from opentelemetry.exporter.zipkin.node_endpoint import NodeEndpoint
from opentelemetry.sdk.trace import Event
from opentelemetry.trace import Span, SpanKind


class ProtobufEncoder(Encoder):
    """Zipkin Export Encoder for Protobuf

    API spec: https://github.com/openzipkin/zipkin-api/blob/master/zipkin.proto
    """

    SPAN_KIND_MAP = {
        SpanKind.INTERNAL: zipkin_pb2.Span.Kind.SPAN_KIND_UNSPECIFIED,
        SpanKind.SERVER: zipkin_pb2.Span.Kind.SERVER,
        SpanKind.CLIENT: zipkin_pb2.Span.Kind.CLIENT,
        SpanKind.PRODUCER: zipkin_pb2.Span.Kind.PRODUCER,
        SpanKind.CONSUMER: zipkin_pb2.Span.Kind.CONSUMER,
    }

    @staticmethod
    def content_type():
        return "application/x-protobuf"

    def serialize(
        self, spans: Sequence[Span], local_endpoint: NodeEndpoint
    ) -> bytes:
        encoded_local_endpoint = self._encode_local_endpoint(local_endpoint)
        # pylint: disable=no-member
        encoded_spans = zipkin_pb2.ListOfSpans()
        for span in spans:
            encoded_spans.spans.append(
                self._encode_span(span, encoded_local_endpoint)
            )
        return encoded_spans.SerializeToString()

    def _encode_span(
        self, span: Span, encoded_local_endpoint: zipkin_pb2.Endpoint
    ) -> zipkin_pb2.Span:
        context = span.get_span_context()
        # pylint: disable=no-member
        encoded_span = zipkin_pb2.Span(
            trace_id=self._encode_trace_id(context.trace_id),
            id=self._encode_span_id(context.span_id),
            name=span.name,
            timestamp=self._nsec_to_usec_round(span.start_time),
            duration=self._nsec_to_usec_round(span.end_time - span.start_time),
            local_endpoint=encoded_local_endpoint,
            kind=self.SPAN_KIND_MAP[span.kind],
        )

        tags = self._extract_tags_from_span(span)
        if tags:
            encoded_span.tags.update(tags)

        annotations = self._encode_annotations(span.events)
        if annotations:
            encoded_span.annotations.extend(annotations)

        debug = self._encode_debug(context)
        if debug:
            encoded_span.debug = debug

        parent_id = self._get_parent_id(span.parent)
        if parent_id is not None:
            encoded_span.parent_id = self._encode_span_id(parent_id)

        return encoded_span

    def _encode_annotations(
        self, span_events: Optional[List[Event]]
    ) -> Optional[List]:
        annotations = self._extract_annotations_from_events(span_events)
        if annotations is None:
            encoded_annotations = None
        else:
            encoded_annotations = []
            for annotation in annotations:
                encoded_annotations.append(
                    zipkin_pb2.Annotation(
                        timestamp=annotation["timestamp"],
                        value=annotation["value"],
                    )
                )
        return encoded_annotations

    @staticmethod
    def _encode_local_endpoint(
        local_endpoint: NodeEndpoint,
    ) -> zipkin_pb2.Endpoint:
        encoded_local_endpoint = zipkin_pb2.Endpoint(
            service_name=local_endpoint.service_name,
        )
        if local_endpoint.ipv4 is not None:
            encoded_local_endpoint.ipv4 = local_endpoint.ipv4.packed
        if local_endpoint.ipv6 is not None:
            encoded_local_endpoint.ipv6 = local_endpoint.ipv6.packed
        if local_endpoint.port is not None:
            encoded_local_endpoint.port = local_endpoint.port
        return encoded_local_endpoint

    @staticmethod
    def _encode_span_id(span_id: int) -> bytes:
        return span_id.to_bytes(length=8, byteorder="big", signed=False)

    @staticmethod
    def _encode_trace_id(trace_id: int) -> bytes:
        return trace_id.to_bytes(length=16, byteorder="big", signed=False)
