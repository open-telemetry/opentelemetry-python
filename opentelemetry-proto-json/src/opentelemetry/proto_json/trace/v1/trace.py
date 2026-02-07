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
        _result: dict[str, Any] = {}
        if self.resource_spans:
            _result["resourceSpans"] = _utils.serialize_repeated(self.resource_spans, lambda _v: _v.to_dict())
        return _result

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
        _args: dict[str, Any] = {}

        if (_value := data.get("resourceSpans")) is not None:
            _args["resource_spans"] = _utils.deserialize_repeated(_value, lambda _v: ResourceSpans.from_dict(_v))

        return cls(**_args)

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
        _result: dict[str, Any] = {}
        if self.resource is not None:
            _result["resource"] = self.resource.to_dict()
        if self.scope_spans:
            _result["scopeSpans"] = _utils.serialize_repeated(self.scope_spans, lambda _v: _v.to_dict())
        if self.schema_url != '':
            _result["schemaUrl"] = self.schema_url
        return _result

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
        _args: dict[str, Any] = {}

        if (_value := data.get("resource")) is not None:
            _args["resource"] = opentelemetry.proto_json.resource.v1.resource.Resource.from_dict(_value)
        if (_value := data.get("scopeSpans")) is not None:
            _args["scope_spans"] = _utils.deserialize_repeated(_value, lambda _v: ScopeSpans.from_dict(_v))
        if (_value := data.get("schemaUrl")) is not None:
            _args["schema_url"] = _value

        return cls(**_args)

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
        _result: dict[str, Any] = {}
        if self.scope is not None:
            _result["scope"] = self.scope.to_dict()
        if self.spans:
            _result["spans"] = _utils.serialize_repeated(self.spans, lambda _v: _v.to_dict())
        if self.schema_url != '':
            _result["schemaUrl"] = self.schema_url
        return _result

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
        _args: dict[str, Any] = {}

        if (_value := data.get("scope")) is not None:
            _args["scope"] = opentelemetry.proto_json.common.v1.common.InstrumentationScope.from_dict(_value)
        if (_value := data.get("spans")) is not None:
            _args["spans"] = _utils.deserialize_repeated(_value, lambda _v: Span.from_dict(_v))
        if (_value := data.get("schemaUrl")) is not None:
            _args["schema_url"] = _value

        return cls(**_args)

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
            _result: dict[str, Any] = {}
            if self.time_unix_nano != 0:
                _result["timeUnixNano"] = _utils.encode_int64(self.time_unix_nano)
            if self.name != '':
                _result["name"] = self.name
            if self.attributes:
                _result["attributes"] = _utils.serialize_repeated(self.attributes, lambda _v: _v.to_dict())
            if self.dropped_attributes_count != 0:
                _result["droppedAttributesCount"] = self.dropped_attributes_count
            return _result

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
            _args: dict[str, Any] = {}

            if (_value := data.get("timeUnixNano")) is not None:
                _args["time_unix_nano"] = _utils.parse_int64(_value)
            if (_value := data.get("name")) is not None:
                _args["name"] = _value
            if (_value := data.get("attributes")) is not None:
                _args["attributes"] = _utils.deserialize_repeated(_value, lambda _v: opentelemetry.proto_json.common.v1.common.KeyValue.from_dict(_v))
            if (_value := data.get("droppedAttributesCount")) is not None:
                _args["dropped_attributes_count"] = _value

            return cls(**_args)

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
            _result: dict[str, Any] = {}
            if self.trace_id != b'':
                _result["traceId"] = _utils.encode_hex(self.trace_id)
            if self.span_id != b'':
                _result["spanId"] = _utils.encode_hex(self.span_id)
            if self.trace_state != '':
                _result["traceState"] = self.trace_state
            if self.attributes:
                _result["attributes"] = _utils.serialize_repeated(self.attributes, lambda _v: _v.to_dict())
            if self.dropped_attributes_count != 0:
                _result["droppedAttributesCount"] = self.dropped_attributes_count
            if self.flags != 0:
                _result["flags"] = self.flags
            return _result

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
            _args: dict[str, Any] = {}

            if (_value := data.get("traceId")) is not None:
                _args["trace_id"] = _utils.decode_hex(_value)
            if (_value := data.get("spanId")) is not None:
                _args["span_id"] = _utils.decode_hex(_value)
            if (_value := data.get("traceState")) is not None:
                _args["trace_state"] = _value
            if (_value := data.get("attributes")) is not None:
                _args["attributes"] = _utils.deserialize_repeated(_value, lambda _v: opentelemetry.proto_json.common.v1.common.KeyValue.from_dict(_v))
            if (_value := data.get("droppedAttributesCount")) is not None:
                _args["dropped_attributes_count"] = _value
            if (_value := data.get("flags")) is not None:
                _args["flags"] = _value

            return cls(**_args)

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
        _result: dict[str, Any] = {}
        if self.trace_id != b'':
            _result["traceId"] = _utils.encode_hex(self.trace_id)
        if self.span_id != b'':
            _result["spanId"] = _utils.encode_hex(self.span_id)
        if self.trace_state != '':
            _result["traceState"] = self.trace_state
        if self.parent_span_id != b'':
            _result["parentSpanId"] = _utils.encode_hex(self.parent_span_id)
        if self.flags != 0:
            _result["flags"] = self.flags
        if self.name != '':
            _result["name"] = self.name
        if self.kind != None:
            _result["kind"] = int(self.kind)
        if self.start_time_unix_nano != 0:
            _result["startTimeUnixNano"] = _utils.encode_int64(self.start_time_unix_nano)
        if self.end_time_unix_nano != 0:
            _result["endTimeUnixNano"] = _utils.encode_int64(self.end_time_unix_nano)
        if self.attributes:
            _result["attributes"] = _utils.serialize_repeated(self.attributes, lambda _v: _v.to_dict())
        if self.dropped_attributes_count != 0:
            _result["droppedAttributesCount"] = self.dropped_attributes_count
        if self.events:
            _result["events"] = _utils.serialize_repeated(self.events, lambda _v: _v.to_dict())
        if self.dropped_events_count != 0:
            _result["droppedEventsCount"] = self.dropped_events_count
        if self.links:
            _result["links"] = _utils.serialize_repeated(self.links, lambda _v: _v.to_dict())
        if self.dropped_links_count != 0:
            _result["droppedLinksCount"] = self.dropped_links_count
        if self.status is not None:
            _result["status"] = self.status.to_dict()
        return _result

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
        _args: dict[str, Any] = {}

        if (_value := data.get("traceId")) is not None:
            _args["trace_id"] = _utils.decode_hex(_value)
        if (_value := data.get("spanId")) is not None:
            _args["span_id"] = _utils.decode_hex(_value)
        if (_value := data.get("traceState")) is not None:
            _args["trace_state"] = _value
        if (_value := data.get("parentSpanId")) is not None:
            _args["parent_span_id"] = _utils.decode_hex(_value)
        if (_value := data.get("flags")) is not None:
            _args["flags"] = _value
        if (_value := data.get("name")) is not None:
            _args["name"] = _value
        if (_value := data.get("kind")) is not None:
            _args["kind"] = Span.SpanKind(_value)
        if (_value := data.get("startTimeUnixNano")) is not None:
            _args["start_time_unix_nano"] = _utils.parse_int64(_value)
        if (_value := data.get("endTimeUnixNano")) is not None:
            _args["end_time_unix_nano"] = _utils.parse_int64(_value)
        if (_value := data.get("attributes")) is not None:
            _args["attributes"] = _utils.deserialize_repeated(_value, lambda _v: opentelemetry.proto_json.common.v1.common.KeyValue.from_dict(_v))
        if (_value := data.get("droppedAttributesCount")) is not None:
            _args["dropped_attributes_count"] = _value
        if (_value := data.get("events")) is not None:
            _args["events"] = _utils.deserialize_repeated(_value, lambda _v: Span.Event.from_dict(_v))
        if (_value := data.get("droppedEventsCount")) is not None:
            _args["dropped_events_count"] = _value
        if (_value := data.get("links")) is not None:
            _args["links"] = _utils.deserialize_repeated(_value, lambda _v: Span.Link.from_dict(_v))
        if (_value := data.get("droppedLinksCount")) is not None:
            _args["dropped_links_count"] = _value
        if (_value := data.get("status")) is not None:
            _args["status"] = Status.from_dict(_value)

        return cls(**_args)

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
        _result: dict[str, Any] = {}
        if self.message != '':
            _result["message"] = self.message
        if self.code != None:
            _result["code"] = int(self.code)
        return _result

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
        _args: dict[str, Any] = {}

        if (_value := data.get("message")) is not None:
            _args["message"] = _value
        if (_value := data.get("code")) is not None:
            _args["code"] = Status.StatusCode(_value)

        return cls(**_args)

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