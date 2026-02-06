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

# AUTO-GENERATED from "opentelemetry/proto/trace/v1/trace.proto"
# DO NOT EDIT MANUALLY

from __future__ import annotations

import json
from typing import Any, Optional, Union, Self
from dataclasses import dataclass, field
from enum import IntEnum

import opentelemetry.proto_json._otlp_json_utils as _utils
import opentelemetry.proto_json.common.v1.common
import opentelemetry.proto_json.resource.v1.resource

class SpanFlags(IntEnum):
    """
    Generated from protobuf enum SpanFlags
    """

    SPAN_FLAGS_DO_NOT_USE = 0
    SPAN_FLAGS_TRACE_FLAGS_MASK = 255
    SPAN_FLAGS_CONTEXT_HAS_IS_REMOTE_MASK = 256
    SPAN_FLAGS_CONTEXT_IS_REMOTE_MASK = 512

@dataclass(slots=True)
class TracesData:
    """
    Generated from protobuf message TracesData
    """

    resource_spans: list[ResourceSpans] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        res: dict[str, Any] = {}
        if self.resource_spans:
            res["resourceSpans"] = _utils.serialize_repeated(self.resource_spans, lambda v: v.to_dict())
        return res

    def to_json(self) -> str:
        """
        Serialize this message to a JSON string.
        
        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """
        Create from a dictionary with lowerCamelCase keys.
        
        Args:
            data: Dictionary representation following OTLP JSON encoding
        
        Returns:
            TracesData instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("resourceSpans")) is not None:
            args["resource_spans"] = _utils.deserialize_repeated(val, lambda v: ResourceSpans.from_dict(v))
        return cls(**args)

    @classmethod
    def from_json(cls, data: Union[str, bytes]) -> Self:
        """
        Deserialize from a JSON string or bytes.
        
        Args:
            data: JSON string or bytes
        
        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@dataclass(slots=True)
class ResourceSpans:
    """
    Generated from protobuf message ResourceSpans
    """

    resource: opentelemetry.proto_json.resource.v1.resource.Resource = None
    scope_spans: list[ScopeSpans] = field(default_factory=list)
    schema_url: str = ''

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        res: dict[str, Any] = {}
        if self.resource is not None:
            res["resource"] = self.resource.to_dict()
        if self.scope_spans:
            res["scopeSpans"] = _utils.serialize_repeated(self.scope_spans, lambda v: v.to_dict())
        if self.schema_url != '':
            res["schemaUrl"] = self.schema_url
        return res

    def to_json(self) -> str:
        """
        Serialize this message to a JSON string.
        
        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """
        Create from a dictionary with lowerCamelCase keys.
        
        Args:
            data: Dictionary representation following OTLP JSON encoding
        
        Returns:
            ResourceSpans instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("resource")) is not None:
            args["resource"] = opentelemetry.proto_json.resource.v1.resource.Resource.from_dict(val)
        if (val := data.get("scopeSpans")) is not None:
            args["scope_spans"] = _utils.deserialize_repeated(val, lambda v: ScopeSpans.from_dict(v))
        if (val := data.get("schemaUrl")) is not None:
            args["schema_url"] = val
        return cls(**args)

    @classmethod
    def from_json(cls, data: Union[str, bytes]) -> Self:
        """
        Deserialize from a JSON string or bytes.
        
        Args:
            data: JSON string or bytes
        
        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@dataclass(slots=True)
class ScopeSpans:
    """
    Generated from protobuf message ScopeSpans
    """

    scope: opentelemetry.proto_json.common.v1.common.InstrumentationScope = None
    spans: list[Span] = field(default_factory=list)
    schema_url: str = ''

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        res: dict[str, Any] = {}
        if self.scope is not None:
            res["scope"] = self.scope.to_dict()
        if self.spans:
            res["spans"] = _utils.serialize_repeated(self.spans, lambda v: v.to_dict())
        if self.schema_url != '':
            res["schemaUrl"] = self.schema_url
        return res

    def to_json(self) -> str:
        """
        Serialize this message to a JSON string.
        
        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """
        Create from a dictionary with lowerCamelCase keys.
        
        Args:
            data: Dictionary representation following OTLP JSON encoding
        
        Returns:
            ScopeSpans instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("scope")) is not None:
            args["scope"] = opentelemetry.proto_json.common.v1.common.InstrumentationScope.from_dict(val)
        if (val := data.get("spans")) is not None:
            args["spans"] = _utils.deserialize_repeated(val, lambda v: Span.from_dict(v))
        if (val := data.get("schemaUrl")) is not None:
            args["schema_url"] = val
        return cls(**args)

    @classmethod
    def from_json(cls, data: Union[str, bytes]) -> Self:
        """
        Deserialize from a JSON string or bytes.
        
        Args:
            data: JSON string or bytes
        
        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@dataclass(slots=True)
class Span:
    """
    Generated from protobuf message Span
    """

    class SpanKind(IntEnum):
        """
        Generated from protobuf enum SpanKind
        """

        SPAN_KIND_UNSPECIFIED = 0
        SPAN_KIND_INTERNAL = 1
        SPAN_KIND_SERVER = 2
        SPAN_KIND_CLIENT = 3
        SPAN_KIND_PRODUCER = 4
        SPAN_KIND_CONSUMER = 5

    @dataclass(slots=True)
    class Event:
        """
        Generated from protobuf message Event
        """

        time_unix_nano: int = 0
        name: str = ''
        attributes: list[opentelemetry.proto_json.common.v1.common.KeyValue] = field(default_factory=list)
        dropped_attributes_count: int = 0

        def to_dict(self) -> dict[str, Any]:
            """
            Convert this message to a dictionary with lowerCamelCase keys.
            
            Returns:
                Dictionary representation following OTLP JSON encoding
            """
            res: dict[str, Any] = {}
            if self.time_unix_nano != 0:
                res["timeUnixNano"] = _utils.encode_int64(self.time_unix_nano)
            if self.name != '':
                res["name"] = self.name
            if self.attributes:
                res["attributes"] = _utils.serialize_repeated(self.attributes, lambda v: v.to_dict())
            if self.dropped_attributes_count != 0:
                res["droppedAttributesCount"] = self.dropped_attributes_count
            return res

        def to_json(self) -> str:
            """
            Serialize this message to a JSON string.
            
            Returns:
                JSON string
            """
            return json.dumps(self.to_dict())

        @classmethod
        def from_dict(cls, data: dict[str, Any]) -> Self:
            """
            Create from a dictionary with lowerCamelCase keys.
            
            Args:
                data: Dictionary representation following OTLP JSON encoding
            
            Returns:
                Event instance
            """
            args: dict[str, Any] = {}
            if (val := data.get("timeUnixNano")) is not None:
                args["time_unix_nano"] = _utils.parse_int64(val)
            if (val := data.get("name")) is not None:
                args["name"] = val
            if (val := data.get("attributes")) is not None:
                args["attributes"] = _utils.deserialize_repeated(val, lambda v: opentelemetry.proto_json.common.v1.common.KeyValue.from_dict(v))
            if (val := data.get("droppedAttributesCount")) is not None:
                args["dropped_attributes_count"] = val
            return cls(**args)

        @classmethod
        def from_json(cls, data: Union[str, bytes]) -> Self:
            """
            Deserialize from a JSON string or bytes.
            
            Args:
                data: JSON string or bytes
            
            Returns:
                Instance of the class
            """
            return cls.from_dict(json.loads(data))

    @dataclass(slots=True)
    class Link:
        """
        Generated from protobuf message Link
        """

        trace_id: bytes = b''
        span_id: bytes = b''
        trace_state: str = ''
        attributes: list[opentelemetry.proto_json.common.v1.common.KeyValue] = field(default_factory=list)
        dropped_attributes_count: int = 0
        flags: int = 0

        def to_dict(self) -> dict[str, Any]:
            """
            Convert this message to a dictionary with lowerCamelCase keys.
            
            Returns:
                Dictionary representation following OTLP JSON encoding
            """
            res: dict[str, Any] = {}
            if self.trace_id != b'':
                res["traceId"] = _utils.encode_hex(self.trace_id)
            if self.span_id != b'':
                res["spanId"] = _utils.encode_hex(self.span_id)
            if self.trace_state != '':
                res["traceState"] = self.trace_state
            if self.attributes:
                res["attributes"] = _utils.serialize_repeated(self.attributes, lambda v: v.to_dict())
            if self.dropped_attributes_count != 0:
                res["droppedAttributesCount"] = self.dropped_attributes_count
            if self.flags != 0:
                res["flags"] = self.flags
            return res

        def to_json(self) -> str:
            """
            Serialize this message to a JSON string.
            
            Returns:
                JSON string
            """
            return json.dumps(self.to_dict())

        @classmethod
        def from_dict(cls, data: dict[str, Any]) -> Self:
            """
            Create from a dictionary with lowerCamelCase keys.
            
            Args:
                data: Dictionary representation following OTLP JSON encoding
            
            Returns:
                Link instance
            """
            args: dict[str, Any] = {}
            if (val := data.get("traceId")) is not None:
                args["trace_id"] = _utils.decode_hex(val)
            if (val := data.get("spanId")) is not None:
                args["span_id"] = _utils.decode_hex(val)
            if (val := data.get("traceState")) is not None:
                args["trace_state"] = val
            if (val := data.get("attributes")) is not None:
                args["attributes"] = _utils.deserialize_repeated(val, lambda v: opentelemetry.proto_json.common.v1.common.KeyValue.from_dict(v))
            if (val := data.get("droppedAttributesCount")) is not None:
                args["dropped_attributes_count"] = val
            if (val := data.get("flags")) is not None:
                args["flags"] = val
            return cls(**args)

        @classmethod
        def from_json(cls, data: Union[str, bytes]) -> Self:
            """
            Deserialize from a JSON string or bytes.
            
            Args:
                data: JSON string or bytes
            
            Returns:
                Instance of the class
            """
            return cls.from_dict(json.loads(data))

    trace_id: bytes = b''
    span_id: bytes = b''
    trace_state: str = ''
    parent_span_id: bytes = b''
    flags: int = 0
    name: str = ''
    kind: Span.SpanKind = 0
    start_time_unix_nano: int = 0
    end_time_unix_nano: int = 0
    attributes: list[opentelemetry.proto_json.common.v1.common.KeyValue] = field(default_factory=list)
    dropped_attributes_count: int = 0
    events: list[Span.Event] = field(default_factory=list)
    dropped_events_count: int = 0
    links: list[Span.Link] = field(default_factory=list)
    dropped_links_count: int = 0
    status: Status = None

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        res: dict[str, Any] = {}
        if self.trace_id != b'':
            res["traceId"] = _utils.encode_hex(self.trace_id)
        if self.span_id != b'':
            res["spanId"] = _utils.encode_hex(self.span_id)
        if self.trace_state != '':
            res["traceState"] = self.trace_state
        if self.parent_span_id != b'':
            res["parentSpanId"] = _utils.encode_hex(self.parent_span_id)
        if self.flags != 0:
            res["flags"] = self.flags
        if self.name != '':
            res["name"] = self.name
        if self.kind != None:
            res["kind"] = int(self.kind)
        if self.start_time_unix_nano != 0:
            res["startTimeUnixNano"] = _utils.encode_int64(self.start_time_unix_nano)
        if self.end_time_unix_nano != 0:
            res["endTimeUnixNano"] = _utils.encode_int64(self.end_time_unix_nano)
        if self.attributes:
            res["attributes"] = _utils.serialize_repeated(self.attributes, lambda v: v.to_dict())
        if self.dropped_attributes_count != 0:
            res["droppedAttributesCount"] = self.dropped_attributes_count
        if self.events:
            res["events"] = _utils.serialize_repeated(self.events, lambda v: v.to_dict())
        if self.dropped_events_count != 0:
            res["droppedEventsCount"] = self.dropped_events_count
        if self.links:
            res["links"] = _utils.serialize_repeated(self.links, lambda v: v.to_dict())
        if self.dropped_links_count != 0:
            res["droppedLinksCount"] = self.dropped_links_count
        if self.status is not None:
            res["status"] = self.status.to_dict()
        return res

    def to_json(self) -> str:
        """
        Serialize this message to a JSON string.
        
        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """
        Create from a dictionary with lowerCamelCase keys.
        
        Args:
            data: Dictionary representation following OTLP JSON encoding
        
        Returns:
            Span instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("traceId")) is not None:
            args["trace_id"] = _utils.decode_hex(val)
        if (val := data.get("spanId")) is not None:
            args["span_id"] = _utils.decode_hex(val)
        if (val := data.get("traceState")) is not None:
            args["trace_state"] = val
        if (val := data.get("parentSpanId")) is not None:
            args["parent_span_id"] = _utils.decode_hex(val)
        if (val := data.get("flags")) is not None:
            args["flags"] = val
        if (val := data.get("name")) is not None:
            args["name"] = val
        if (val := data.get("kind")) is not None:
            args["kind"] = Span.SpanKind(val)
        if (val := data.get("startTimeUnixNano")) is not None:
            args["start_time_unix_nano"] = _utils.parse_int64(val)
        if (val := data.get("endTimeUnixNano")) is not None:
            args["end_time_unix_nano"] = _utils.parse_int64(val)
        if (val := data.get("attributes")) is not None:
            args["attributes"] = _utils.deserialize_repeated(val, lambda v: opentelemetry.proto_json.common.v1.common.KeyValue.from_dict(v))
        if (val := data.get("droppedAttributesCount")) is not None:
            args["dropped_attributes_count"] = val
        if (val := data.get("events")) is not None:
            args["events"] = _utils.deserialize_repeated(val, lambda v: Span.Event.from_dict(v))
        if (val := data.get("droppedEventsCount")) is not None:
            args["dropped_events_count"] = val
        if (val := data.get("links")) is not None:
            args["links"] = _utils.deserialize_repeated(val, lambda v: Span.Link.from_dict(v))
        if (val := data.get("droppedLinksCount")) is not None:
            args["dropped_links_count"] = val
        if (val := data.get("status")) is not None:
            args["status"] = Status.from_dict(val)
        return cls(**args)

    @classmethod
    def from_json(cls, data: Union[str, bytes]) -> Self:
        """
        Deserialize from a JSON string or bytes.
        
        Args:
            data: JSON string or bytes
        
        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@dataclass(slots=True)
class Status:
    """
    Generated from protobuf message Status
    """

    class StatusCode(IntEnum):
        """
        Generated from protobuf enum StatusCode
        """

        STATUS_CODE_UNSET = 0
        STATUS_CODE_OK = 1
        STATUS_CODE_ERROR = 2

    message: str = ''
    code: Status.StatusCode = 0

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        res: dict[str, Any] = {}
        if self.message != '':
            res["message"] = self.message
        if self.code != None:
            res["code"] = int(self.code)
        return res

    def to_json(self) -> str:
        """
        Serialize this message to a JSON string.
        
        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """
        Create from a dictionary with lowerCamelCase keys.
        
        Args:
            data: Dictionary representation following OTLP JSON encoding
        
        Returns:
            Status instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("message")) is not None:
            args["message"] = val
        if (val := data.get("code")) is not None:
            args["code"] = Status.StatusCode(val)
        return cls(**args)

    @classmethod
    def from_json(cls, data: Union[str, bytes]) -> Self:
        """
        Deserialize from a JSON string or bytes.
        
        Args:
            data: JSON string or bytes
        
        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))