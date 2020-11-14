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

import abc

from opentelemetry.exporter.zipkin.encoder import Encoder
from opentelemetry.trace import Span, SpanContext, SpanKind


# pylint: disable=W0223
class V1Encoder(Encoder, abc.ABC):
    def _extract_binary_annotations(self, span: Span, encoded_local_endpoint):
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
