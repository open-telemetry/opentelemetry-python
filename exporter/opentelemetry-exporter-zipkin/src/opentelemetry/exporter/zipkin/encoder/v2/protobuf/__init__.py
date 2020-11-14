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
from typing import Sequence

from opentelemetry.exporter.zipkin.encoder import Encoder
from opentelemetry.exporter.zipkin.encoder.v2.protobuf.gen import zipkin_pb2
from opentelemetry.trace import Span, SpanContext, SpanKind


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

    def _encode_spans(self, spans: Sequence[Span]) -> str:
        encoded_local_endpoint = self._encode_local_endpoint()
        # pylint: disable=no-member
        encoded_spans = zipkin_pb2.ListOfSpans()
        for span in spans:
            encoded_spans.spans.append(
                self._encode_span(span, encoded_local_endpoint)
            )
        return encoded_spans.SerializeToString()

    def _encode_span(self, span: Span, encoded_local_endpoint):
        context = span.get_span_context()
        # pylint: disable=no-member
        encoded_span = zipkin_pb2.Span(
            trace_id=self.encode_trace_id(context.trace_id),
            id=self.encode_span_id(context.span_id),
            name=span.name,
            timestamp=self.nsec_to_usec_round(span.start_time),
            duration=self.nsec_to_usec_round(span.end_time - span.start_time),
            local_endpoint=encoded_local_endpoint,
            kind=self.SPAN_KIND_MAP[span.kind],
            tags=self._extract_tags_from_span(span),
            annotations=self._encode_annotations(span.events),
            debug=self._encode_debug(context),
        )

        parent_id = self._get_parent_id(span.parent)
        if parent_id is not None:
            encoded_span.parent_id = self.encode_span_id(parent_id)

        return encoded_span

    def _encode_annotations(self, span_events):
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

    def _encode_local_endpoint(self) -> zipkin_pb2.Endpoint:
        encoded_local_endpoint = zipkin_pb2.Endpoint(
            service_name=self.local_endpoint.service_name,
        )

        if self.local_endpoint.ipv4 is not None:
            encoded_local_endpoint.ipv4 = self.local_endpoint.ipv4

        if self.local_endpoint.ipv6 is not None:
            encoded_local_endpoint.ipv6 = self.local_endpoint.ipv6

        if self.local_endpoint.port is not None:
            encoded_local_endpoint.port = self.local_endpoint.port

        return encoded_local_endpoint

    @staticmethod
    def encode_span_id(span_id: int):
        return span_id.to_bytes(length=8, byteorder="big", signed=False)

    @staticmethod
    def encode_trace_id(trace_id: int):
        return trace_id.to_bytes(length=16, byteorder="big", signed=False)
