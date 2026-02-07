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

# AUTO-GENERATED from "opentelemetry/proto/profiles/v1development/profiles.proto"
# DO NOT EDIT MANUALLY

from __future__ import annotations

import json
from typing import Any, Optional, Union, Self
from dataclasses import dataclass, field
from enum import IntEnum

import opentelemetry.proto_json._otlp_json_utils as _utils
import opentelemetry.proto_json.common.v1.common
import opentelemetry.proto_json.resource.v1.resource

@dataclass(slots=True)
class ProfilesDictionary:
    """
    Generated from protobuf message ProfilesDictionary
    """

    mapping_table: list[Mapping] = field(default_factory=list)
    location_table: list[Location] = field(default_factory=list)
    function_table: list[Function] = field(default_factory=list)
    link_table: list[Link] = field(default_factory=list)
    string_table: list[str] = field(default_factory=list)
    attribute_table: list[KeyValueAndUnit] = field(default_factory=list)
    stack_table: list[Stack] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result: dict[str, Any] = {}
        if self.mapping_table:
            _result["mappingTable"] = _utils.serialize_repeated(self.mapping_table, lambda _v: _v.to_dict())
        if self.location_table:
            _result["locationTable"] = _utils.serialize_repeated(self.location_table, lambda _v: _v.to_dict())
        if self.function_table:
            _result["functionTable"] = _utils.serialize_repeated(self.function_table, lambda _v: _v.to_dict())
        if self.link_table:
            _result["linkTable"] = _utils.serialize_repeated(self.link_table, lambda _v: _v.to_dict())
        if self.string_table:
            _result["stringTable"] = self.string_table
        if self.attribute_table:
            _result["attributeTable"] = _utils.serialize_repeated(self.attribute_table, lambda _v: _v.to_dict())
        if self.stack_table:
            _result["stackTable"] = _utils.serialize_repeated(self.stack_table, lambda _v: _v.to_dict())
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
            ProfilesDictionary instance
        """
        _args: dict[str, Any] = {}
        if (_value := data.get("mappingTable")) is not None:
            _args["mapping_table"] = _utils.deserialize_repeated(_value, lambda _v: Mapping.from_dict(_v))
        if (_value := data.get("locationTable")) is not None:
            _args["location_table"] = _utils.deserialize_repeated(_value, lambda _v: Location.from_dict(_v))
        if (_value := data.get("functionTable")) is not None:
            _args["function_table"] = _utils.deserialize_repeated(_value, lambda _v: Function.from_dict(_v))
        if (_value := data.get("linkTable")) is not None:
            _args["link_table"] = _utils.deserialize_repeated(_value, lambda _v: Link.from_dict(_v))
        if (_value := data.get("stringTable")) is not None:
            _args["string_table"] = _value
        if (_value := data.get("attributeTable")) is not None:
            _args["attribute_table"] = _utils.deserialize_repeated(_value, lambda _v: KeyValueAndUnit.from_dict(_v))
        if (_value := data.get("stackTable")) is not None:
            _args["stack_table"] = _utils.deserialize_repeated(_value, lambda _v: Stack.from_dict(_v))
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
class ProfilesData:
    """
    Generated from protobuf message ProfilesData
    """

    resource_profiles: list[ResourceProfiles] = field(default_factory=list)
    dictionary: ProfilesDictionary = None

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result: dict[str, Any] = {}
        if self.resource_profiles:
            _result["resourceProfiles"] = _utils.serialize_repeated(self.resource_profiles, lambda _v: _v.to_dict())
        if self.dictionary is not None:
            _result["dictionary"] = self.dictionary.to_dict()
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
            ProfilesData instance
        """
        _args: dict[str, Any] = {}
        if (_value := data.get("resourceProfiles")) is not None:
            _args["resource_profiles"] = _utils.deserialize_repeated(_value, lambda _v: ResourceProfiles.from_dict(_v))
        if (_value := data.get("dictionary")) is not None:
            _args["dictionary"] = ProfilesDictionary.from_dict(_value)
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
class ResourceProfiles:
    """
    Generated from protobuf message ResourceProfiles
    """

    resource: opentelemetry.proto_json.resource.v1.resource.Resource = None
    scope_profiles: list[ScopeProfiles] = field(default_factory=list)
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
        if self.scope_profiles:
            _result["scopeProfiles"] = _utils.serialize_repeated(self.scope_profiles, lambda _v: _v.to_dict())
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
            ResourceProfiles instance
        """
        _args: dict[str, Any] = {}
        if (_value := data.get("resource")) is not None:
            _args["resource"] = opentelemetry.proto_json.resource.v1.resource.Resource.from_dict(_value)
        if (_value := data.get("scopeProfiles")) is not None:
            _args["scope_profiles"] = _utils.deserialize_repeated(_value, lambda _v: ScopeProfiles.from_dict(_v))
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
class ScopeProfiles:
    """
    Generated from protobuf message ScopeProfiles
    """

    scope: opentelemetry.proto_json.common.v1.common.InstrumentationScope = None
    profiles: list[Profile] = field(default_factory=list)
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
        if self.profiles:
            _result["profiles"] = _utils.serialize_repeated(self.profiles, lambda _v: _v.to_dict())
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
            ScopeProfiles instance
        """
        _args: dict[str, Any] = {}
        if (_value := data.get("scope")) is not None:
            _args["scope"] = opentelemetry.proto_json.common.v1.common.InstrumentationScope.from_dict(_value)
        if (_value := data.get("profiles")) is not None:
            _args["profiles"] = _utils.deserialize_repeated(_value, lambda _v: Profile.from_dict(_v))
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
class Profile:
    """
    Generated from protobuf message Profile
    """

    sample_type: ValueType = None
    samples: list[Sample] = field(default_factory=list)
    time_unix_nano: int = 0
    duration_nano: int = 0
    period_type: ValueType = None
    period: int = 0
    profile_id: bytes = b''
    dropped_attributes_count: int = 0
    original_payload_format: str = ''
    original_payload: bytes = b''
    attribute_indices: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result: dict[str, Any] = {}
        if self.sample_type is not None:
            _result["sampleType"] = self.sample_type.to_dict()
        if self.samples:
            _result["samples"] = _utils.serialize_repeated(self.samples, lambda _v: _v.to_dict())
        if self.time_unix_nano != 0:
            _result["timeUnixNano"] = _utils.encode_int64(self.time_unix_nano)
        if self.duration_nano != 0:
            _result["durationNano"] = _utils.encode_int64(self.duration_nano)
        if self.period_type is not None:
            _result["periodType"] = self.period_type.to_dict()
        if self.period != 0:
            _result["period"] = _utils.encode_int64(self.period)
        if self.profile_id != b'':
            _result["profileId"] = _utils.encode_base64(self.profile_id)
        if self.dropped_attributes_count != 0:
            _result["droppedAttributesCount"] = self.dropped_attributes_count
        if self.original_payload_format != '':
            _result["originalPayloadFormat"] = self.original_payload_format
        if self.original_payload != b'':
            _result["originalPayload"] = _utils.encode_base64(self.original_payload)
        if self.attribute_indices:
            _result["attributeIndices"] = self.attribute_indices
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
            Profile instance
        """
        _args: dict[str, Any] = {}
        if (_value := data.get("sampleType")) is not None:
            _args["sample_type"] = ValueType.from_dict(_value)
        if (_value := data.get("samples")) is not None:
            _args["samples"] = _utils.deserialize_repeated(_value, lambda _v: Sample.from_dict(_v))
        if (_value := data.get("timeUnixNano")) is not None:
            _args["time_unix_nano"] = _utils.parse_int64(_value)
        if (_value := data.get("durationNano")) is not None:
            _args["duration_nano"] = _utils.parse_int64(_value)
        if (_value := data.get("periodType")) is not None:
            _args["period_type"] = ValueType.from_dict(_value)
        if (_value := data.get("period")) is not None:
            _args["period"] = _utils.parse_int64(_value)
        if (_value := data.get("profileId")) is not None:
            _args["profile_id"] = _utils.decode_base64(_value)
        if (_value := data.get("droppedAttributesCount")) is not None:
            _args["dropped_attributes_count"] = _value
        if (_value := data.get("originalPayloadFormat")) is not None:
            _args["original_payload_format"] = _value
        if (_value := data.get("originalPayload")) is not None:
            _args["original_payload"] = _utils.decode_base64(_value)
        if (_value := data.get("attributeIndices")) is not None:
            _args["attribute_indices"] = _value
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
class ValueType:
    """
    Generated from protobuf message ValueType
    """

    type_strindex: int = 0
    unit_strindex: int = 0

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result: dict[str, Any] = {}
        if self.type_strindex != 0:
            _result["typeStrindex"] = self.type_strindex
        if self.unit_strindex != 0:
            _result["unitStrindex"] = self.unit_strindex
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
            ValueType instance
        """
        _args: dict[str, Any] = {}
        if (_value := data.get("typeStrindex")) is not None:
            _args["type_strindex"] = _value
        if (_value := data.get("unitStrindex")) is not None:
            _args["unit_strindex"] = _value
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
class Sample:
    """
    Generated from protobuf message Sample
    """

    stack_index: int = 0
    values: list[int] = field(default_factory=list)
    attribute_indices: list[int] = field(default_factory=list)
    link_index: int = 0
    timestamps_unix_nano: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result: dict[str, Any] = {}
        if self.stack_index != 0:
            _result["stackIndex"] = self.stack_index
        if self.values:
            _result["values"] = _utils.serialize_repeated(self.values, lambda _v: _utils.encode_int64(_v))
        if self.attribute_indices:
            _result["attributeIndices"] = self.attribute_indices
        if self.link_index != 0:
            _result["linkIndex"] = self.link_index
        if self.timestamps_unix_nano:
            _result["timestampsUnixNano"] = _utils.serialize_repeated(self.timestamps_unix_nano, lambda _v: _utils.encode_int64(_v))
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
            Sample instance
        """
        _args: dict[str, Any] = {}
        if (_value := data.get("stackIndex")) is not None:
            _args["stack_index"] = _value
        if (_value := data.get("values")) is not None:
            _args["values"] = _utils.deserialize_repeated(_value, lambda _v: _utils.parse_int64(_v))
        if (_value := data.get("attributeIndices")) is not None:
            _args["attribute_indices"] = _value
        if (_value := data.get("linkIndex")) is not None:
            _args["link_index"] = _value
        if (_value := data.get("timestampsUnixNano")) is not None:
            _args["timestamps_unix_nano"] = _utils.deserialize_repeated(_value, lambda _v: _utils.parse_int64(_v))
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
class Mapping:
    """
    Generated from protobuf message Mapping
    """

    memory_start: int = 0
    memory_limit: int = 0
    file_offset: int = 0
    filename_strindex: int = 0
    attribute_indices: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result: dict[str, Any] = {}
        if self.memory_start != 0:
            _result["memoryStart"] = _utils.encode_int64(self.memory_start)
        if self.memory_limit != 0:
            _result["memoryLimit"] = _utils.encode_int64(self.memory_limit)
        if self.file_offset != 0:
            _result["fileOffset"] = _utils.encode_int64(self.file_offset)
        if self.filename_strindex != 0:
            _result["filenameStrindex"] = self.filename_strindex
        if self.attribute_indices:
            _result["attributeIndices"] = self.attribute_indices
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
            Mapping instance
        """
        _args: dict[str, Any] = {}
        if (_value := data.get("memoryStart")) is not None:
            _args["memory_start"] = _utils.parse_int64(_value)
        if (_value := data.get("memoryLimit")) is not None:
            _args["memory_limit"] = _utils.parse_int64(_value)
        if (_value := data.get("fileOffset")) is not None:
            _args["file_offset"] = _utils.parse_int64(_value)
        if (_value := data.get("filenameStrindex")) is not None:
            _args["filename_strindex"] = _value
        if (_value := data.get("attributeIndices")) is not None:
            _args["attribute_indices"] = _value
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
class Stack:
    """
    Generated from protobuf message Stack
    """

    location_indices: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result: dict[str, Any] = {}
        if self.location_indices:
            _result["locationIndices"] = self.location_indices
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
            Stack instance
        """
        _args: dict[str, Any] = {}
        if (_value := data.get("locationIndices")) is not None:
            _args["location_indices"] = _value
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
class Location:
    """
    Generated from protobuf message Location
    """

    mapping_index: int = 0
    address: int = 0
    lines: list[Line] = field(default_factory=list)
    attribute_indices: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result: dict[str, Any] = {}
        if self.mapping_index != 0:
            _result["mappingIndex"] = self.mapping_index
        if self.address != 0:
            _result["address"] = _utils.encode_int64(self.address)
        if self.lines:
            _result["lines"] = _utils.serialize_repeated(self.lines, lambda _v: _v.to_dict())
        if self.attribute_indices:
            _result["attributeIndices"] = self.attribute_indices
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
            Location instance
        """
        _args: dict[str, Any] = {}
        if (_value := data.get("mappingIndex")) is not None:
            _args["mapping_index"] = _value
        if (_value := data.get("address")) is not None:
            _args["address"] = _utils.parse_int64(_value)
        if (_value := data.get("lines")) is not None:
            _args["lines"] = _utils.deserialize_repeated(_value, lambda _v: Line.from_dict(_v))
        if (_value := data.get("attributeIndices")) is not None:
            _args["attribute_indices"] = _value
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
class Line:
    """
    Generated from protobuf message Line
    """

    function_index: int = 0
    line: int = 0
    column: int = 0

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result: dict[str, Any] = {}
        if self.function_index != 0:
            _result["functionIndex"] = self.function_index
        if self.line != 0:
            _result["line"] = _utils.encode_int64(self.line)
        if self.column != 0:
            _result["column"] = _utils.encode_int64(self.column)
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
            Line instance
        """
        _args: dict[str, Any] = {}
        if (_value := data.get("functionIndex")) is not None:
            _args["function_index"] = _value
        if (_value := data.get("line")) is not None:
            _args["line"] = _utils.parse_int64(_value)
        if (_value := data.get("column")) is not None:
            _args["column"] = _utils.parse_int64(_value)
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
class Function:
    """
    Generated from protobuf message Function
    """

    name_strindex: int = 0
    system_name_strindex: int = 0
    filename_strindex: int = 0
    start_line: int = 0

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result: dict[str, Any] = {}
        if self.name_strindex != 0:
            _result["nameStrindex"] = self.name_strindex
        if self.system_name_strindex != 0:
            _result["systemNameStrindex"] = self.system_name_strindex
        if self.filename_strindex != 0:
            _result["filenameStrindex"] = self.filename_strindex
        if self.start_line != 0:
            _result["startLine"] = _utils.encode_int64(self.start_line)
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
            Function instance
        """
        _args: dict[str, Any] = {}
        if (_value := data.get("nameStrindex")) is not None:
            _args["name_strindex"] = _value
        if (_value := data.get("systemNameStrindex")) is not None:
            _args["system_name_strindex"] = _value
        if (_value := data.get("filenameStrindex")) is not None:
            _args["filename_strindex"] = _value
        if (_value := data.get("startLine")) is not None:
            _args["start_line"] = _utils.parse_int64(_value)
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
class KeyValueAndUnit:
    """
    Generated from protobuf message KeyValueAndUnit
    """

    key_strindex: int = 0
    value: opentelemetry.proto_json.common.v1.common.AnyValue = None
    unit_strindex: int = 0

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result: dict[str, Any] = {}
        if self.key_strindex != 0:
            _result["keyStrindex"] = self.key_strindex
        if self.value is not None:
            _result["value"] = self.value.to_dict()
        if self.unit_strindex != 0:
            _result["unitStrindex"] = self.unit_strindex
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
            KeyValueAndUnit instance
        """
        _args: dict[str, Any] = {}
        if (_value := data.get("keyStrindex")) is not None:
            _args["key_strindex"] = _value
        if (_value := data.get("value")) is not None:
            _args["value"] = opentelemetry.proto_json.common.v1.common.AnyValue.from_dict(_value)
        if (_value := data.get("unitStrindex")) is not None:
            _args["unit_strindex"] = _value
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