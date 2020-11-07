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

"""Zipkin Exporter Transport Formatter

Base module and abstract class for specific transport formatters to extend.
"""

import abc
import json
from typing import Optional, Sequence

from opentelemetry.exporter.zipkin.endpoint import LocalEndpoint
from opentelemetry.trace import Span

DEFAULT_MAX_TAG_VALUE_LENGTH = 128


class TransportFormatter(abc.ABC):
    """Base class for transport formatters that are used by the exporter.

    Args:
        local_endpoint: Zipkin endpoint where exports will be sent
        max_tag_value_length: Length limit for exported tag values
    """

    def __init__(
        self,
        local_endpoint: LocalEndpoint,
        max_tag_value_length: Optional[int] = None,
    ):
        self.local_endpoint = local_endpoint

        if max_tag_value_length is None:
            self.max_tag_value_length = DEFAULT_MAX_TAG_VALUE_LENGTH
        else:
            self.max_tag_value_length = max_tag_value_length

    def format(self, spans: Sequence[Span]) -> str:
        return self._format(spans)

    @abc.abstractmethod
    def _format(self, spans: Sequence[Span]) -> str:
        pass

    @staticmethod
    @abc.abstractmethod
    def http_content_type() -> str:
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
                if isinstance(value, str):
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
        """Round nanoseconds to microseconds"""
        return (nsec + 500) // 10 ** 3
