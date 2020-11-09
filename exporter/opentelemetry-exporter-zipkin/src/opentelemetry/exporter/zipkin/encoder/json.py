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

"""Zipkin Export Encoder for v2 JSON API

API spec: https://github.com/openzipkin/zipkin-api/blob/master/zipkin2-api.yaml
"""

import abc
from json import dumps
from typing import Sequence

from opentelemetry.exporter.zipkin.encoder import Encoder
from opentelemetry.trace import Span, SpanContext, SpanKind


class JsonEncoder(Encoder):

    def _encode(self, spans: Sequence[Span]) -> str:

        encoded_local_endpoint = self._encode_local_endpoint()
        zipkin_spans = []

        for span in spans:
            zipkin_spans.append(self._encode_span(
                span, encoded_local_endpoint
            ))

        return dumps(zipkin_spans)

    def _encode_local_endpoint(self):
        encoded_local_endpoint = {
            "serviceName": self.local_endpoint.service_name
        }

        if self.local_endpoint.ipv4 is not None:
            encoded_local_endpoint["ipv4"] = self.local_endpoint.ipv4

        if self.local_endpoint.ipv6 is not None:
            encoded_local_endpoint["ipv6"] = self.local_endpoint.ipv6

        if self.local_endpoint.port is not None:
            encoded_local_endpoint["port"] = self.local_endpoint.port

        return encoded_local_endpoint

    @abc.abstractmethod
    def _encode_span(self, span: Span, encoded_local_endpoint):
        pass

    @staticmethod
    def encode_span_id(span_id):
        return format(span_id, "016x")

    @staticmethod
    def encode_trace_id(trace_id):
        return format(trace_id, "032x")


class JsonV2Encoder(JsonEncoder):
    """Zipkin Export Encoder for v2 JSON API

    API spec: https://github.com/openzipkin/zipkin-api/blob/master/zipkin2-api.yaml
    """

    SPAN_KIND_MAP = {
        SpanKind.INTERNAL: None,
        SpanKind.SERVER: "SERVER",
        SpanKind.CLIENT: "CLIENT",
        SpanKind.PRODUCER: "PRODUCER",
        SpanKind.CONSUMER: "CONSUMER",
    }

    def _encode_span(self, span: Span, encoded_local_endpoint):
        context = span.get_span_context()
        trace_id = context.trace_id
        span_id = context.span_id

        start_timestamp_mus = self.nsec_to_usec_round(span.start_time)
        duration_mus = self.nsec_to_usec_round(
            span.end_time - span.start_time
        )

        zipkin_span = {
            "traceId": self.encode_trace_id(trace_id),
            "id": self.encode_span_id(span_id),
            "name": span.name,
            "timestamp": start_timestamp_mus,
            "duration": duration_mus,
            "localEndpoint": encoded_local_endpoint,
            "kind": self.SPAN_KIND_MAP[span.kind],
            "tags": self._extract_tags_from_span(span),
            "annotations": self._extract_annotations_from_events(
                span.events
            ),
        }

        if span.instrumentation_info is not None:
            zipkin_span["tags"][
                "otel.instrumentation_library.name"
            ] = span.instrumentation_info.name
            zipkin_span["tags"][
                "otel.instrumentation_library.version"
            ] = span.instrumentation_info.version

        if span.status is not None:
            zipkin_span["tags"]["otel.status_code"] = str(
                span.status.status_code.value
            )
            if span.status.description is not None:
                zipkin_span["tags"][
                    "otel.status_description"
                ] = span.status.description

        if context.trace_flags.sampled:
            zipkin_span["debug"] = True

        if isinstance(span.parent, Span):
            zipkin_span["parentId"] = self.encode_span_id(
                span.parent.get_span_context().span_id
            )
        elif isinstance(span.parent, SpanContext):
            zipkin_span["parentId"] = self.encode_span_id(span.parent.span_id)

        return zipkin_span


class JsonV1Encoder(JsonEncoder):
    """Zipkin Export Encoder for JSON v1 API

    API spec: https://github.com/openzipkin/zipkin-api/blob/master/zipkin-api.yaml
    """

    def _encode_span(self, span: Span, encoded_local_endpoint):
        context = span.get_span_context()
        trace_id = context.trace_id
        span_id = context.span_id

        start_timestamp_mus = self.nsec_to_usec_round(span.start_time)
        duration_mus = self.nsec_to_usec_round(
            span.end_time - span.start_time
        )

        annotations = self._extract_annotations_from_events(span.events)

        if annotations is not None:
            for annotation in annotations:
                annotation["endpoint"] = encoded_local_endpoint

        binary_annotations = self._extract_binary_annotations(
            span, encoded_local_endpoint
        )

        zipkin_span = {
            "traceId": self.encode_trace_id(trace_id),
            "id": self.encode_span_id(span_id),
            "name": span.name,
            "timestamp": start_timestamp_mus,
            "duration": duration_mus,
            "annotations": annotations,
            "binaryAnnotations": binary_annotations,
        }

        if context.trace_flags.sampled:
            zipkin_span["debug"] = True

        if isinstance(span.parent, Span):
            zipkin_span["parentId"] = self.encode_span_id(
                span.parent.get_span_context().span_id
            )
        elif isinstance(span.parent, SpanContext):
            zipkin_span["parentId"] = self.encode_span_id(span.parent.span_id)

        return zipkin_span

    def _extract_binary_annotations(
        self, span: Span, encoded_local_endpoint
    ):
        binary_annotations = []

        for k, v in self._extract_tags_from_span(span).items():
            if isinstance(v, str) and self.max_tag_value_length > 0:
                v = v[: self.max_tag_value_length]
            binary_annotations.append(
                {"key": k, "value": v, "endpoint": encoded_local_endpoint}
            )

        if span.instrumentation_info is not None:
            binary_annotations.extend(
                [
                    {
                        "key": "otel.instrumentation_library.name",
                        "value": span.instrumentation_info.name,
                        "endpoint": encoded_local_endpoint,
                    },
                    {
                        "key": "otel.instrumentation_library.version",
                        "value": span.instrumentation_info.version,
                        "endpoint": encoded_local_endpoint,
                    },
                ]
            )

        if span.status is not None:
            binary_annotations.append(
                {
                    "key": "otel.status_code",
                    "value": str(span.status.status_code.value),
                    "endpoint": encoded_local_endpoint,
                }
            )

            if span.status.description is not None:
                binary_annotations.append(
                    {
                        "key": "otel.status_description",
                        "value": span.status.description,
                        "endpoint": encoded_local_endpoint,
                    }
                )

        return binary_annotations
