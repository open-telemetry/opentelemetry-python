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
import json
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, TypeVar

from opentelemetry.exporter.zipkin.node_endpoint import NodeEndpoint
from opentelemetry.sdk.trace import Event
from opentelemetry.trace import (
    Span,
    SpanContext,
    StatusCode,
    format_span_id,
    format_trace_id,
)

EncodedLocalEndpointT = TypeVar("EncodedLocalEndpointT")

DEFAULT_MAX_TAG_VALUE_LENGTH = 128
NAME_KEY = "otel.library.name"
VERSION_KEY = "otel.library.version"
_SCOPE_NAME_KEY = "otel.scope.name"
_SCOPE_VERSION_KEY = "otel.scope.version"

logger = logging.getLogger(__name__)


class Protocol(Enum):
    """Enum of supported protocol formats.

    Values are human-readable strings so that they can be easily used by the
    OS environ var OTEL_EXPORTER_ZIPKIN_PROTOCOL (reserved for future usage).
    """

    V1 = "v1"
    V2 = "v2"


# pylint: disable=W0223
class Encoder(abc.ABC):
    """Base class for encoders that are used by the exporter.

    Args:
        max_tag_value_length: maximum length of an exported tag value. Values
          will be truncated to conform. Since values are serialized to a JSON
          list string, max_tag_value_length is honored at the element boundary.
    """

    def __init__(
        self, max_tag_value_length: int = DEFAULT_MAX_TAG_VALUE_LENGTH
    ):
        self.max_tag_value_length = max_tag_value_length

    @staticmethod
    @abc.abstractmethod
    def content_type() -> str:
        pass

    @abc.abstractmethod
    def serialize(
        self, spans: Sequence[Span], local_endpoint: NodeEndpoint
    ) -> str:
        pass

    @abc.abstractmethod
    def _encode_span(
        self, span: Span, encoded_local_endpoint: EncodedLocalEndpointT
    ) -> Any:
        """
        Per spec Zipkin fields that can be absent SHOULD be omitted from the
        payload when they are empty in the OpenTelemetry Span.

        https://github.com/open-telemetry/opentelemetry-specification/blob/master/specification/trace/sdk_exporters/zipkin.md#request-payload
        """

    @staticmethod
    @abc.abstractmethod
    def _encode_local_endpoint(
        local_endpoint: NodeEndpoint,
    ) -> EncodedLocalEndpointT:
        pass

    @staticmethod
    def _encode_debug(span_context) -> Any:
        return span_context.trace_flags.sampled

    @staticmethod
    @abc.abstractmethod
    def _encode_span_id(span_id: int) -> Any:
        pass

    @staticmethod
    @abc.abstractmethod
    def _encode_trace_id(trace_id: int) -> Any:
        pass

    @staticmethod
    def _get_parent_id(span_context) -> Optional[int]:
        if isinstance(span_context, Span):
            parent_id = span_context.parent.span_id
        elif isinstance(span_context, SpanContext):
            parent_id = span_context.span_id
        else:
            parent_id = None
        return parent_id

    def _extract_tags_from_dict(
        self, tags_dict: Optional[Dict]
    ) -> Dict[str, str]:
        tags = {}
        if not tags_dict:
            return tags
        for attribute_key, attribute_value in tags_dict.items():
            if isinstance(attribute_value, bool):
                value = str(attribute_value).lower()
            elif isinstance(attribute_value, (int, float, str)):
                value = str(attribute_value)
            elif isinstance(attribute_value, Sequence):
                value = self._extract_tag_value_string_from_sequence(
                    attribute_value
                )
                if not value:
                    logger.warning("Could not serialize tag %s", attribute_key)
                    continue
            else:
                logger.warning("Could not serialize tag %s", attribute_key)
                continue

            if (
                self.max_tag_value_length is not None
                and self.max_tag_value_length > 0
            ):
                value = value[: self.max_tag_value_length]
            tags[attribute_key] = value
        return tags

    def _extract_tag_value_string_from_sequence(self, sequence: Sequence):
        if self.max_tag_value_length and self.max_tag_value_length == 1:
            return None

        tag_value_elements = []
        running_string_length = (
            2  # accounts for array brackets in output string
        )
        defined_max_tag_value_length = (
            self.max_tag_value_length is not None
            and self.max_tag_value_length > 0
        )

        for element in sequence:
            if isinstance(element, bool):
                tag_value_element = str(element).lower()
            elif isinstance(element, (int, float, str)):
                tag_value_element = str(element)
            elif element is None:
                tag_value_element = None
            else:
                continue

            if defined_max_tag_value_length:
                if tag_value_element is None:
                    running_string_length += 4  # null with no quotes
                else:
                    # + 2 accounts for string quotation marks
                    running_string_length += len(tag_value_element) + 2

                if tag_value_elements:
                    # accounts for ',' item separator
                    running_string_length += 1

                if running_string_length > self.max_tag_value_length:
                    break

            tag_value_elements.append(tag_value_element)

        return json.dumps(tag_value_elements, separators=(",", ":"))

    def _extract_tags_from_span(self, span: Span) -> Dict[str, str]:
        tags = self._extract_tags_from_dict(span.attributes)
        if span.resource:
            tags.update(self._extract_tags_from_dict(span.resource.attributes))
        if span.instrumentation_scope is not None:
            tags.update(
                {
                    NAME_KEY: span.instrumentation_scope.name,
                    VERSION_KEY: span.instrumentation_scope.version,
                    _SCOPE_NAME_KEY: span.instrumentation_scope.name,
                    _SCOPE_VERSION_KEY: span.instrumentation_scope.version,
                }
            )
        if span.status.status_code is not StatusCode.UNSET:
            tags.update({"otel.status_code": span.status.status_code.name})
            if span.status.status_code is StatusCode.ERROR:
                tags.update({"error": span.status.description or ""})

        if span.dropped_attributes:
            tags.update(
                {"otel.dropped_attributes_count": str(span.dropped_attributes)}
            )

        if span.dropped_events:
            tags.update(
                {"otel.dropped_events_count": str(span.dropped_events)}
            )

        if span.dropped_links:
            tags.update({"otel.dropped_links_count": str(span.dropped_links)})

        return tags

    def _extract_annotations_from_events(
        self, events: Optional[List[Event]]
    ) -> Optional[List[Dict]]:
        if not events:
            return None

        annotations = []
        for event in events:
            attrs = {}
            for key, value in event.attributes.items():
                if (
                    isinstance(value, str)
                    and self.max_tag_value_length is not None
                    and self.max_tag_value_length > 0
                ):
                    value = value[: self.max_tag_value_length]
                attrs[key] = value

            annotations.append(
                {
                    "timestamp": self._nsec_to_usec_round(event.timestamp),
                    "value": json.dumps({event.name: attrs}, sort_keys=True),
                }
            )
        return annotations

    @staticmethod
    def _nsec_to_usec_round(nsec: int) -> int:
        """Round nanoseconds to microseconds

        Timestamp in zipkin spans is int of microseconds.
        See: https://zipkin.io/pages/instrumenting.html
        """
        return (nsec + 500) // 10**3


class JsonEncoder(Encoder):
    @staticmethod
    def content_type():
        return "application/json"

    def serialize(
        self, spans: Sequence[Span], local_endpoint: NodeEndpoint
    ) -> str:
        encoded_local_endpoint = self._encode_local_endpoint(local_endpoint)
        encoded_spans = []
        for span in spans:
            encoded_spans.append(
                self._encode_span(span, encoded_local_endpoint)
            )
        return json.dumps(encoded_spans)

    @staticmethod
    def _encode_local_endpoint(local_endpoint: NodeEndpoint) -> Dict:
        encoded_local_endpoint = {"serviceName": local_endpoint.service_name}
        if local_endpoint.ipv4 is not None:
            encoded_local_endpoint["ipv4"] = str(local_endpoint.ipv4)
        if local_endpoint.ipv6 is not None:
            encoded_local_endpoint["ipv6"] = str(local_endpoint.ipv6)
        if local_endpoint.port is not None:
            encoded_local_endpoint["port"] = local_endpoint.port
        return encoded_local_endpoint

    @staticmethod
    def _encode_span_id(span_id: int) -> str:
        return format_span_id(span_id)

    @staticmethod
    def _encode_trace_id(trace_id: int) -> str:
        return format_trace_id(trace_id)
