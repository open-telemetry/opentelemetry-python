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

"""Zipkin Export Encoders for JSON formats
"""
from typing import Dict

from opentelemetry.exporter.zipkin.encoder import JsonEncoder
from opentelemetry.trace import Span, SpanKind


class JsonV2Encoder(JsonEncoder):
    """Zipkin Export Encoder for JSON v2 API

    API spec: https://github.com/openzipkin/zipkin-api/blob/master/zipkin2-api.yaml
    """

    SPAN_KIND_MAP = {
        SpanKind.INTERNAL: None,
        SpanKind.SERVER: "SERVER",
        SpanKind.CLIENT: "CLIENT",
        SpanKind.PRODUCER: "PRODUCER",
        SpanKind.CONSUMER: "CONSUMER",
    }

    def _encode_span(self, span: Span, encoded_local_endpoint: Dict) -> Dict:
        context = span.get_span_context()
        encoded_span = {
            "traceId": self._encode_trace_id(context.trace_id),
            "id": self._encode_span_id(context.span_id),
            "name": span.name,
            "timestamp": self._nsec_to_usec_round(span.start_time),
            "duration": self._nsec_to_usec_round(
                span.end_time - span.start_time
            ),
            "localEndpoint": encoded_local_endpoint,
            "kind": self.SPAN_KIND_MAP[span.kind],
        }

        tags = self._extract_tags_from_span(span)
        if tags:
            encoded_span["tags"] = tags

        annotations = self._extract_annotations_from_events(span.events)
        if annotations:
            encoded_span["annotations"] = annotations

        debug = self._encode_debug(context)
        if debug:
            encoded_span["debug"] = debug

        parent_id = self._get_parent_id(span.parent)
        if parent_id is not None:
            encoded_span["parentId"] = self._encode_span_id(parent_id)

        return encoded_span
