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
from opentelemetry.exporter.zipkin.encoder.protobuf.gen import zipkin_pb2
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

    def _encode(self, spans: Sequence[Span]) -> str:

        pbuf_local_endpoint = self._encode_local_endpoint()
        pbuf_spans = zipkin_pb2.ListOfSpans()

        for span in spans:
            context = span.get_span_context()
            trace_id = context.trace_id.to_bytes(
                length=16, byteorder="big", signed=False,
            )
            span_id = self.encode_pbuf_span_id(context.span_id)

            # Timestamp in zipkin spans is int of microseconds.
            # see: https://zipkin.io/pages/instrumenting.html
            start_timestamp_mus = self.nsec_to_usec_round(span.start_time)
            duration_mus = self.nsec_to_usec_round(
                span.end_time - span.start_time
            )

            # pylint: disable=no-member
            pbuf_span = zipkin_pb2.Span(
                trace_id=trace_id,
                id=span_id,
                name=span.name,
                timestamp=start_timestamp_mus,
                duration=duration_mus,
                local_endpoint=pbuf_local_endpoint,
                kind=self.SPAN_KIND_MAP[span.kind],
                tags=self._extract_tags_from_span(span),
            )

            annotations = self._extract_annotations_from_events(span.events)

            if annotations is not None:
                for annotation in annotations:
                    pbuf_span.annotations.append(
                        zipkin_pb2.Annotation(
                            timestamp=annotation["timestamp"],
                            value=annotation["value"],
                        )
                    )

            if span.instrumentation_info is not None:
                pbuf_span.tags.update(
                    {
                        "otel.instrumentation_library.name": span.instrumentation_info.name,
                        "otel.instrumentation_library.version": span.instrumentation_info.version,
                    }
                )

            if span.status is not None:
                pbuf_span.tags.update(
                    {"otel.status_code": str(span.status.status_code.value)}
                )
                if span.status.description is not None:
                    pbuf_span.tags.update(
                        {"otel.status_description": span.status.description}
                    )

            if context.trace_flags.sampled:
                pbuf_span.debug = True

            if isinstance(span.parent, Span):
                pbuf_span.parent_id = self.encode_pbuf_span_id(
                    span.parent.get_span_context().span_id
                )
            elif isinstance(span.parent, SpanContext):
                pbuf_span.parent_id = self.encode_pbuf_span_id(
                    span.parent.span_id
                )

            pbuf_spans.spans.append(pbuf_span)

        return pbuf_spans.SerializeToString()

    def _encode_local_endpoint(self) -> zipkin_pb2.Endpoint:
        pbuf_local_endpoint = zipkin_pb2.Endpoint(
            service_name=self.local_endpoint.service_name,
        )

        if self.local_endpoint.ipv4 is not None:
            pbuf_local_endpoint.ipv4 = self.local_endpoint.ipv4

        if self.local_endpoint.ipv6 is not None:
            pbuf_local_endpoint.ipv6 = self.local_endpoint.ipv6

        if self.local_endpoint.port is not None:
            pbuf_local_endpoint.port = self.local_endpoint.port

        return pbuf_local_endpoint

    @staticmethod
    def encode_pbuf_span_id(span_id: int):
        return span_id.to_bytes(length=8, byteorder="big", signed=False)
