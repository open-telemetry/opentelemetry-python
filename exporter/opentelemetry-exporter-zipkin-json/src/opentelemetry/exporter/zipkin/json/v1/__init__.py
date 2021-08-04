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

from typing import Dict, List

from opentelemetry.exporter.zipkin.encoder import Encoder, JsonEncoder
from opentelemetry.trace import Span


# pylint: disable=W0223
class V1Encoder(Encoder):
    def _extract_binary_annotations(
        self, span: Span, encoded_local_endpoint: Dict
    ) -> List[Dict]:
        binary_annotations = []
        for tag_key, tag_value in self._extract_tags_from_span(span).items():
            if isinstance(tag_value, str) and self.max_tag_value_length > 0:
                tag_value = tag_value[: self.max_tag_value_length]
            binary_annotations.append(
                {
                    "key": tag_key,
                    "value": tag_value,
                    "endpoint": encoded_local_endpoint,
                }
            )
        return binary_annotations


class JsonV1Encoder(JsonEncoder, V1Encoder):
    """Zipkin Export Encoder for JSON v1 API

    API spec: https://github.com/openzipkin/zipkin-api/blob/master/zipkin-api.yaml
    """

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
        }

        encoded_annotations = self._extract_annotations_from_events(
            span.events
        )
        if encoded_annotations is not None:
            for annotation in encoded_annotations:
                annotation["endpoint"] = encoded_local_endpoint
            encoded_span["annotations"] = encoded_annotations

        binary_annotations = self._extract_binary_annotations(
            span, encoded_local_endpoint
        )
        if binary_annotations:
            encoded_span["binaryAnnotations"] = binary_annotations

        debug = self._encode_debug(context)
        if debug:
            encoded_span["debug"] = debug

        parent_id = self._get_parent_id(span.parent)
        if parent_id is not None:
            encoded_span["parentId"] = self._encode_span_id(parent_id)

        return encoded_span
