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

import builtins
import dataclasses
import enum
import functools
import json
import sys
import typing

if sys.version_info >= (3, 10):
    _dataclass = functools.partial(dataclasses.dataclass, slots=True)
else:
    _dataclass = dataclasses.dataclass

import opentelemetry.proto_json._otlp_json_utils as _utils
import opentelemetry.proto_json.common.v1.common
import opentelemetry.proto_json.resource.v1.resource


@typing.final
class SpanFlags(enum.IntEnum):
    """
    Generated from protobuf enum SpanFlags
    """

    SPAN_FLAGS_DO_NOT_USE = 0
    SPAN_FLAGS_TRACE_FLAGS_MASK = 255
    SPAN_FLAGS_CONTEXT_HAS_IS_REMOTE_MASK = 256
    SPAN_FLAGS_CONTEXT_IS_REMOTE_MASK = 512

@typing.final
@_dataclass
class TracesData:
    """
    Generated from protobuf message TracesData
    """

    resource_spans: builtins.list[ResourceSpans] = dataclasses.field(default_factory=builtins.list)

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.resource_spans:
            _result["resourceSpans"] = _utils.serialize_repeated(self.resource_spans, lambda _v: _v.to_dict())
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "TracesData":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            TracesData instance
        """
        _utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("resourceSpans")) is not None:
            _args["resource_spans"] = _utils.deserialize_repeated(_value, lambda _v: ResourceSpans.from_dict(_v), "resource_spans")

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "TracesData":
        """
        Deserialize from a JSON string or bytes.

        Args:
            data: JSON string or bytes

        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@typing.final
@_dataclass
class ResourceSpans:
    """
    Generated from protobuf message ResourceSpans
    """

    resource: typing.Optional[opentelemetry.proto_json.resource.v1.resource.Resource] = None
    scope_spans: builtins.list[ScopeSpans] = dataclasses.field(default_factory=builtins.list)
    schema_url: typing.Optional[builtins.str] = ""

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.resource:
            _result["resource"] = self.resource.to_dict()
        if self.scope_spans:
            _result["scopeSpans"] = _utils.serialize_repeated(self.scope_spans, lambda _v: _v.to_dict())
        if self.schema_url:
            _result["schemaUrl"] = self.schema_url
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "ResourceSpans":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            ResourceSpans instance
        """
        _utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("resource")) is not None:
            _args["resource"] = opentelemetry.proto_json.resource.v1.resource.Resource.from_dict(_value)
        if (_value := data.get("scopeSpans")) is not None:
            _args["scope_spans"] = _utils.deserialize_repeated(_value, lambda _v: ScopeSpans.from_dict(_v), "scope_spans")
        if (_value := data.get("schemaUrl")) is not None:
            _utils.validate_type(_value, builtins.str, "schema_url")
            _args["schema_url"] = _value

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "ResourceSpans":
        """
        Deserialize from a JSON string or bytes.

        Args:
            data: JSON string or bytes

        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@typing.final
@_dataclass
class ScopeSpans:
    """
    Generated from protobuf message ScopeSpans
    """

    scope: typing.Optional[opentelemetry.proto_json.common.v1.common.InstrumentationScope] = None
    spans: builtins.list[Span] = dataclasses.field(default_factory=builtins.list)
    schema_url: typing.Optional[builtins.str] = ""

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.scope:
            _result["scope"] = self.scope.to_dict()
        if self.spans:
            _result["spans"] = _utils.serialize_repeated(self.spans, lambda _v: _v.to_dict())
        if self.schema_url:
            _result["schemaUrl"] = self.schema_url
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "ScopeSpans":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            ScopeSpans instance
        """
        _utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("scope")) is not None:
            _args["scope"] = opentelemetry.proto_json.common.v1.common.InstrumentationScope.from_dict(_value)
        if (_value := data.get("spans")) is not None:
            _args["spans"] = _utils.deserialize_repeated(_value, lambda _v: Span.from_dict(_v), "spans")
        if (_value := data.get("schemaUrl")) is not None:
            _utils.validate_type(_value, builtins.str, "schema_url")
            _args["schema_url"] = _value

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "ScopeSpans":
        """
        Deserialize from a JSON string or bytes.

        Args:
            data: JSON string or bytes

        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@typing.final
@_dataclass
class Span:
    """
    Generated from protobuf message Span
    """

    @typing.final
    class SpanKind(enum.IntEnum):
        """
        Generated from protobuf enum SpanKind
        """

        SPAN_KIND_UNSPECIFIED = 0
        SPAN_KIND_INTERNAL = 1
        SPAN_KIND_SERVER = 2
        SPAN_KIND_CLIENT = 3
        SPAN_KIND_PRODUCER = 4
        SPAN_KIND_CONSUMER = 5

    @typing.final
    @_dataclass
    class Event:
        """
        Generated from protobuf message Event
        """

        time_unix_nano: typing.Optional[builtins.int] = 0
        name: typing.Optional[builtins.str] = ""
        attributes: builtins.list[opentelemetry.proto_json.common.v1.common.KeyValue] = dataclasses.field(default_factory=builtins.list)
        dropped_attributes_count: typing.Optional[builtins.int] = 0

        def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
            """
            Convert this message to a dictionary with lowerCamelCase keys.

            Returns:
                Dictionary representation following OTLP JSON encoding
            """
            _result = {}
            if self.time_unix_nano:
                _result["timeUnixNano"] = _utils.encode_int64(self.time_unix_nano)
            if self.name:
                _result["name"] = self.name
            if self.attributes:
                _result["attributes"] = _utils.serialize_repeated(self.attributes, lambda _v: _v.to_dict())
            if self.dropped_attributes_count:
                _result["droppedAttributesCount"] = self.dropped_attributes_count
            return _result

        def to_json(self) -> builtins.str:
            """
            Serialize this message to a JSON string.

            Returns:
                JSON string
            """
            return json.dumps(self.to_dict())

        @builtins.classmethod
        def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "Span.Event":
            """
            Create from a dictionary with lowerCamelCase keys.

            Args:
                data: Dictionary representation following OTLP JSON encoding

            Returns:
                Event instance
            """
            _utils.validate_type(data, builtins.dict, "data")
            _args = {}

            if (_value := data.get("timeUnixNano")) is not None:
                _args["time_unix_nano"] = _utils.parse_int64(_value, "time_unix_nano")
            if (_value := data.get("name")) is not None:
                _utils.validate_type(_value, builtins.str, "name")
                _args["name"] = _value
            if (_value := data.get("attributes")) is not None:
                _args["attributes"] = _utils.deserialize_repeated(_value, lambda _v: opentelemetry.proto_json.common.v1.common.KeyValue.from_dict(_v), "attributes")
            if (_value := data.get("droppedAttributesCount")) is not None:
                _utils.validate_type(_value, builtins.int, "dropped_attributes_count")
                _args["dropped_attributes_count"] = _value

            return cls(**_args)

        @builtins.classmethod
        def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "Span.Event":
            """
            Deserialize from a JSON string or bytes.

            Args:
                data: JSON string or bytes

            Returns:
                Instance of the class
            """
            return cls.from_dict(json.loads(data))

    @typing.final
    @_dataclass
    class Link:
        """
        Generated from protobuf message Link
        """

        trace_id: typing.Optional[builtins.bytes] = b""
        span_id: typing.Optional[builtins.bytes] = b""
        trace_state: typing.Optional[builtins.str] = ""
        attributes: builtins.list[opentelemetry.proto_json.common.v1.common.KeyValue] = dataclasses.field(default_factory=builtins.list)
        dropped_attributes_count: typing.Optional[builtins.int] = 0
        flags: typing.Optional[builtins.int] = 0

        def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
            """
            Convert this message to a dictionary with lowerCamelCase keys.

            Returns:
                Dictionary representation following OTLP JSON encoding
            """
            _result = {}
            if self.trace_id:
                _result["traceId"] = _utils.encode_hex(self.trace_id)
            if self.span_id:
                _result["spanId"] = _utils.encode_hex(self.span_id)
            if self.trace_state:
                _result["traceState"] = self.trace_state
            if self.attributes:
                _result["attributes"] = _utils.serialize_repeated(self.attributes, lambda _v: _v.to_dict())
            if self.dropped_attributes_count:
                _result["droppedAttributesCount"] = self.dropped_attributes_count
            if self.flags:
                _result["flags"] = self.flags
            return _result

        def to_json(self) -> builtins.str:
            """
            Serialize this message to a JSON string.

            Returns:
                JSON string
            """
            return json.dumps(self.to_dict())

        @builtins.classmethod
        def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "Span.Link":
            """
            Create from a dictionary with lowerCamelCase keys.

            Args:
                data: Dictionary representation following OTLP JSON encoding

            Returns:
                Link instance
            """
            _utils.validate_type(data, builtins.dict, "data")
            _args = {}

            if (_value := data.get("traceId")) is not None:
                _args["trace_id"] = _utils.decode_hex(_value, "trace_id")
            if (_value := data.get("spanId")) is not None:
                _args["span_id"] = _utils.decode_hex(_value, "span_id")
            if (_value := data.get("traceState")) is not None:
                _utils.validate_type(_value, builtins.str, "trace_state")
                _args["trace_state"] = _value
            if (_value := data.get("attributes")) is not None:
                _args["attributes"] = _utils.deserialize_repeated(_value, lambda _v: opentelemetry.proto_json.common.v1.common.KeyValue.from_dict(_v), "attributes")
            if (_value := data.get("droppedAttributesCount")) is not None:
                _utils.validate_type(_value, builtins.int, "dropped_attributes_count")
                _args["dropped_attributes_count"] = _value
            if (_value := data.get("flags")) is not None:
                _utils.validate_type(_value, builtins.int, "flags")
                _args["flags"] = _value

            return cls(**_args)

        @builtins.classmethod
        def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "Span.Link":
            """
            Deserialize from a JSON string or bytes.

            Args:
                data: JSON string or bytes

            Returns:
                Instance of the class
            """
            return cls.from_dict(json.loads(data))

    trace_id: typing.Optional[builtins.bytes] = b""
    span_id: typing.Optional[builtins.bytes] = b""
    trace_state: typing.Optional[builtins.str] = ""
    parent_span_id: typing.Optional[builtins.bytes] = b""
    flags: typing.Optional[builtins.int] = 0
    name: typing.Optional[builtins.str] = ""
    kind: typing.Union[Span.SpanKind, builtins.int, None] = 0
    start_time_unix_nano: typing.Optional[builtins.int] = 0
    end_time_unix_nano: typing.Optional[builtins.int] = 0
    attributes: builtins.list[opentelemetry.proto_json.common.v1.common.KeyValue] = dataclasses.field(default_factory=builtins.list)
    dropped_attributes_count: typing.Optional[builtins.int] = 0
    events: builtins.list[Span.Event] = dataclasses.field(default_factory=builtins.list)
    dropped_events_count: typing.Optional[builtins.int] = 0
    links: builtins.list[Span.Link] = dataclasses.field(default_factory=builtins.list)
    dropped_links_count: typing.Optional[builtins.int] = 0
    status: typing.Optional[Status] = None

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.trace_id:
            _result["traceId"] = _utils.encode_hex(self.trace_id)
        if self.span_id:
            _result["spanId"] = _utils.encode_hex(self.span_id)
        if self.trace_state:
            _result["traceState"] = self.trace_state
        if self.parent_span_id:
            _result["parentSpanId"] = _utils.encode_hex(self.parent_span_id)
        if self.flags:
            _result["flags"] = self.flags
        if self.name:
            _result["name"] = self.name
        if self.kind:
            _result["kind"] = builtins.int(self.kind)
        if self.start_time_unix_nano:
            _result["startTimeUnixNano"] = _utils.encode_int64(self.start_time_unix_nano)
        if self.end_time_unix_nano:
            _result["endTimeUnixNano"] = _utils.encode_int64(self.end_time_unix_nano)
        if self.attributes:
            _result["attributes"] = _utils.serialize_repeated(self.attributes, lambda _v: _v.to_dict())
        if self.dropped_attributes_count:
            _result["droppedAttributesCount"] = self.dropped_attributes_count
        if self.events:
            _result["events"] = _utils.serialize_repeated(self.events, lambda _v: _v.to_dict())
        if self.dropped_events_count:
            _result["droppedEventsCount"] = self.dropped_events_count
        if self.links:
            _result["links"] = _utils.serialize_repeated(self.links, lambda _v: _v.to_dict())
        if self.dropped_links_count:
            _result["droppedLinksCount"] = self.dropped_links_count
        if self.status:
            _result["status"] = self.status.to_dict()
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "Span":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            Span instance
        """
        _utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("traceId")) is not None:
            _args["trace_id"] = _utils.decode_hex(_value, "trace_id")
        if (_value := data.get("spanId")) is not None:
            _args["span_id"] = _utils.decode_hex(_value, "span_id")
        if (_value := data.get("traceState")) is not None:
            _utils.validate_type(_value, builtins.str, "trace_state")
            _args["trace_state"] = _value
        if (_value := data.get("parentSpanId")) is not None:
            _args["parent_span_id"] = _utils.decode_hex(_value, "parent_span_id")
        if (_value := data.get("flags")) is not None:
            _utils.validate_type(_value, builtins.int, "flags")
            _args["flags"] = _value
        if (_value := data.get("name")) is not None:
            _utils.validate_type(_value, builtins.str, "name")
            _args["name"] = _value
        if (_value := data.get("kind")) is not None:
            _utils.validate_type(_value, builtins.int, "kind")
            _args["kind"] = Span.SpanKind(_value)
        if (_value := data.get("startTimeUnixNano")) is not None:
            _args["start_time_unix_nano"] = _utils.parse_int64(_value, "start_time_unix_nano")
        if (_value := data.get("endTimeUnixNano")) is not None:
            _args["end_time_unix_nano"] = _utils.parse_int64(_value, "end_time_unix_nano")
        if (_value := data.get("attributes")) is not None:
            _args["attributes"] = _utils.deserialize_repeated(_value, lambda _v: opentelemetry.proto_json.common.v1.common.KeyValue.from_dict(_v), "attributes")
        if (_value := data.get("droppedAttributesCount")) is not None:
            _utils.validate_type(_value, builtins.int, "dropped_attributes_count")
            _args["dropped_attributes_count"] = _value
        if (_value := data.get("events")) is not None:
            _args["events"] = _utils.deserialize_repeated(_value, lambda _v: Span.Event.from_dict(_v), "events")
        if (_value := data.get("droppedEventsCount")) is not None:
            _utils.validate_type(_value, builtins.int, "dropped_events_count")
            _args["dropped_events_count"] = _value
        if (_value := data.get("links")) is not None:
            _args["links"] = _utils.deserialize_repeated(_value, lambda _v: Span.Link.from_dict(_v), "links")
        if (_value := data.get("droppedLinksCount")) is not None:
            _utils.validate_type(_value, builtins.int, "dropped_links_count")
            _args["dropped_links_count"] = _value
        if (_value := data.get("status")) is not None:
            _args["status"] = Status.from_dict(_value)

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "Span":
        """
        Deserialize from a JSON string or bytes.

        Args:
            data: JSON string or bytes

        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@typing.final
@_dataclass
class Status:
    """
    Generated from protobuf message Status
    """

    @typing.final
    class StatusCode(enum.IntEnum):
        """
        Generated from protobuf enum StatusCode
        """

        STATUS_CODE_UNSET = 0
        STATUS_CODE_OK = 1
        STATUS_CODE_ERROR = 2

    message: typing.Optional[builtins.str] = ""
    code: typing.Union[Status.StatusCode, builtins.int, None] = 0

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.message:
            _result["message"] = self.message
        if self.code:
            _result["code"] = builtins.int(self.code)
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "Status":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            Status instance
        """
        _utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("message")) is not None:
            _utils.validate_type(_value, builtins.str, "message")
            _args["message"] = _value
        if (_value := data.get("code")) is not None:
            _utils.validate_type(_value, builtins.int, "code")
            _args["code"] = Status.StatusCode(_value)

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "Status":
        """
        Deserialize from a JSON string or bytes.

        Args:
            data: JSON string or bytes

        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))
