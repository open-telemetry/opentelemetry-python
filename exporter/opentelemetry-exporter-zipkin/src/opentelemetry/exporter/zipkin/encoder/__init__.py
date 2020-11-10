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

"""Zipkin Exporter Transport Encoder

Base module and abstract class for concrete transport encoders to extend.
"""

import abc
from enum import Enum
import json
import logging
from typing import Optional, Sequence

from opentelemetry.exporter.zipkin.endpoint import Endpoint
from opentelemetry.trace import Span

DEFAULT_MAX_TAG_VALUE_LENGTH = 128

logger = logging.getLogger(__name__)


class Encoding(Enum):
    """Enum of supported encoding formats.

    Values are human-readable strings so that they can be easily used by the
    OS environ var OTEL_EXPORTER_ZIPKIN_ENCODING.
    """

    JSON_V1 = "json_v1"
    JSON_V2 = "json_v2"
    PROTOBUF = "protobuf"


class Encoder(abc.ABC):
    """Base class for encoders that are used by the exporter.

    Args:
        TODO
    """

    def __init__(
        self,
        local_endpoint: Endpoint,
        max_tag_value_length: Optional[int] = None,
    ):
        self.local_endpoint = local_endpoint

        if max_tag_value_length is None:
            self.max_tag_value_length = DEFAULT_MAX_TAG_VALUE_LENGTH
        else:
            self.max_tag_value_length = max_tag_value_length

    def encode(self, spans: Sequence[Span]) -> str:
        return self._encode(spans)

    @abc.abstractmethod
    def _encode(self, spans: Sequence[Span]) -> str:
        pass

    @staticmethod
    @abc.abstractmethod
    def encode_span_id(span_id):
        pass

    @staticmethod
    @abc.abstractmethod
    def encode_trace_id(trace_id):
        pass

    def _extract_tags_from_dict(self, tags_dict):
        tags = {}
        if not tags_dict:
            return tags
        for attribute_key, attribute_value in tags_dict.items():
            if isinstance(attribute_value, (int, bool, float)):
                value = str(attribute_value)
            elif isinstance(attribute_value, str):
                value = attribute_value
            else:
                logger.warning("Could not serialize tag %s", attribute_key)
                continue

            if self.max_tag_value_length > 0:
                value = value[: self.max_tag_value_length]
            tags[attribute_key] = value
        return tags

    def _extract_tags_from_span(self, span: Span):
        tags = self._extract_tags_from_dict(getattr(span, "attributes", None))
        if span.resource:
            tags.update(self._extract_tags_from_dict(span.resource.attributes))
        return tags

    def _extract_annotations_from_events(self, events):
        if not events:
            return None

        annotations = []
        for event in events:
            attrs = {}
            for key, value in event.attributes.items():
                if isinstance(value, str) and self.max_tag_value_length > 0:
                    value = value[: self.max_tag_value_length]
                attrs[key] = value

            annotations.append(
                {
                    "timestamp": self.nsec_to_usec_round(event.timestamp),
                    "value": json.dumps({event.name: attrs}),
                }
            )
        return annotations

    @staticmethod
    def nsec_to_usec_round(nsec):
        """Round nanoseconds to microseconds

        Timestamp in zipkin spans is int of microseconds.
        See: https://zipkin.io/pages/instrumenting.html
        """
        return (nsec + 500) // 10 ** 3
