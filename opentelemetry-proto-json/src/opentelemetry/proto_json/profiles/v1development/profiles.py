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
        res: dict[str, Any] = {}
        if self.mapping_table:
            res["mappingTable"] = _utils.serialize_repeated(self.mapping_table, lambda v: v.to_dict())
        if self.location_table:
            res["locationTable"] = _utils.serialize_repeated(self.location_table, lambda v: v.to_dict())
        if self.function_table:
            res["functionTable"] = _utils.serialize_repeated(self.function_table, lambda v: v.to_dict())
        if self.link_table:
            res["linkTable"] = _utils.serialize_repeated(self.link_table, lambda v: v.to_dict())
        if self.string_table:
            res["stringTable"] = self.string_table
        if self.attribute_table:
            res["attributeTable"] = _utils.serialize_repeated(self.attribute_table, lambda v: v.to_dict())
        if self.stack_table:
            res["stackTable"] = _utils.serialize_repeated(self.stack_table, lambda v: v.to_dict())
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
            ProfilesDictionary instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("mappingTable")) is not None:
            args["mapping_table"] = _utils.deserialize_repeated(val, lambda v: Mapping.from_dict(v))
        if (val := data.get("locationTable")) is not None:
            args["location_table"] = _utils.deserialize_repeated(val, lambda v: Location.from_dict(v))
        if (val := data.get("functionTable")) is not None:
            args["function_table"] = _utils.deserialize_repeated(val, lambda v: Function.from_dict(v))
        if (val := data.get("linkTable")) is not None:
            args["link_table"] = _utils.deserialize_repeated(val, lambda v: Link.from_dict(v))
        if (val := data.get("stringTable")) is not None:
            args["string_table"] = val
        if (val := data.get("attributeTable")) is not None:
            args["attribute_table"] = _utils.deserialize_repeated(val, lambda v: KeyValueAndUnit.from_dict(v))
        if (val := data.get("stackTable")) is not None:
            args["stack_table"] = _utils.deserialize_repeated(val, lambda v: Stack.from_dict(v))
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
        res: dict[str, Any] = {}
        if self.resource_profiles:
            res["resourceProfiles"] = _utils.serialize_repeated(self.resource_profiles, lambda v: v.to_dict())
        if self.dictionary is not None:
            res["dictionary"] = self.dictionary.to_dict()
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
            ProfilesData instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("resourceProfiles")) is not None:
            args["resource_profiles"] = _utils.deserialize_repeated(val, lambda v: ResourceProfiles.from_dict(v))
        if (val := data.get("dictionary")) is not None:
            args["dictionary"] = ProfilesDictionary.from_dict(val)
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
        res: dict[str, Any] = {}
        if self.resource is not None:
            res["resource"] = self.resource.to_dict()
        if self.scope_profiles:
            res["scopeProfiles"] = _utils.serialize_repeated(self.scope_profiles, lambda v: v.to_dict())
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
            ResourceProfiles instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("resource")) is not None:
            args["resource"] = opentelemetry.proto_json.resource.v1.resource.Resource.from_dict(val)
        if (val := data.get("scopeProfiles")) is not None:
            args["scope_profiles"] = _utils.deserialize_repeated(val, lambda v: ScopeProfiles.from_dict(v))
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
        res: dict[str, Any] = {}
        if self.scope is not None:
            res["scope"] = self.scope.to_dict()
        if self.profiles:
            res["profiles"] = _utils.serialize_repeated(self.profiles, lambda v: v.to_dict())
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
            ScopeProfiles instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("scope")) is not None:
            args["scope"] = opentelemetry.proto_json.common.v1.common.InstrumentationScope.from_dict(val)
        if (val := data.get("profiles")) is not None:
            args["profiles"] = _utils.deserialize_repeated(val, lambda v: Profile.from_dict(v))
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
        res: dict[str, Any] = {}
        if self.sample_type is not None:
            res["sampleType"] = self.sample_type.to_dict()
        if self.samples:
            res["samples"] = _utils.serialize_repeated(self.samples, lambda v: v.to_dict())
        if self.time_unix_nano != 0:
            res["timeUnixNano"] = _utils.encode_int64(self.time_unix_nano)
        if self.duration_nano != 0:
            res["durationNano"] = _utils.encode_int64(self.duration_nano)
        if self.period_type is not None:
            res["periodType"] = self.period_type.to_dict()
        if self.period != 0:
            res["period"] = _utils.encode_int64(self.period)
        if self.profile_id != b'':
            res["profileId"] = _utils.encode_base64(self.profile_id)
        if self.dropped_attributes_count != 0:
            res["droppedAttributesCount"] = self.dropped_attributes_count
        if self.original_payload_format != '':
            res["originalPayloadFormat"] = self.original_payload_format
        if self.original_payload != b'':
            res["originalPayload"] = _utils.encode_base64(self.original_payload)
        if self.attribute_indices:
            res["attributeIndices"] = self.attribute_indices
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
            Profile instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("sampleType")) is not None:
            args["sample_type"] = ValueType.from_dict(val)
        if (val := data.get("samples")) is not None:
            args["samples"] = _utils.deserialize_repeated(val, lambda v: Sample.from_dict(v))
        if (val := data.get("timeUnixNano")) is not None:
            args["time_unix_nano"] = _utils.parse_int64(val)
        if (val := data.get("durationNano")) is not None:
            args["duration_nano"] = _utils.parse_int64(val)
        if (val := data.get("periodType")) is not None:
            args["period_type"] = ValueType.from_dict(val)
        if (val := data.get("period")) is not None:
            args["period"] = _utils.parse_int64(val)
        if (val := data.get("profileId")) is not None:
            args["profile_id"] = _utils.decode_base64(val)
        if (val := data.get("droppedAttributesCount")) is not None:
            args["dropped_attributes_count"] = val
        if (val := data.get("originalPayloadFormat")) is not None:
            args["original_payload_format"] = val
        if (val := data.get("originalPayload")) is not None:
            args["original_payload"] = _utils.decode_base64(val)
        if (val := data.get("attributeIndices")) is not None:
            args["attribute_indices"] = val
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
        res: dict[str, Any] = {}
        if self.type_strindex != 0:
            res["typeStrindex"] = self.type_strindex
        if self.unit_strindex != 0:
            res["unitStrindex"] = self.unit_strindex
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
            ValueType instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("typeStrindex")) is not None:
            args["type_strindex"] = val
        if (val := data.get("unitStrindex")) is not None:
            args["unit_strindex"] = val
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
        res: dict[str, Any] = {}
        if self.stack_index != 0:
            res["stackIndex"] = self.stack_index
        if self.values:
            res["values"] = _utils.serialize_repeated(self.values, lambda v: _utils.encode_int64(v))
        if self.attribute_indices:
            res["attributeIndices"] = self.attribute_indices
        if self.link_index != 0:
            res["linkIndex"] = self.link_index
        if self.timestamps_unix_nano:
            res["timestampsUnixNano"] = _utils.serialize_repeated(self.timestamps_unix_nano, lambda v: _utils.encode_int64(v))
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
            Sample instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("stackIndex")) is not None:
            args["stack_index"] = val
        if (val := data.get("values")) is not None:
            args["values"] = _utils.deserialize_repeated(val, lambda v: _utils.parse_int64(v))
        if (val := data.get("attributeIndices")) is not None:
            args["attribute_indices"] = val
        if (val := data.get("linkIndex")) is not None:
            args["link_index"] = val
        if (val := data.get("timestampsUnixNano")) is not None:
            args["timestamps_unix_nano"] = _utils.deserialize_repeated(val, lambda v: _utils.parse_int64(v))
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
        res: dict[str, Any] = {}
        if self.memory_start != 0:
            res["memoryStart"] = _utils.encode_int64(self.memory_start)
        if self.memory_limit != 0:
            res["memoryLimit"] = _utils.encode_int64(self.memory_limit)
        if self.file_offset != 0:
            res["fileOffset"] = _utils.encode_int64(self.file_offset)
        if self.filename_strindex != 0:
            res["filenameStrindex"] = self.filename_strindex
        if self.attribute_indices:
            res["attributeIndices"] = self.attribute_indices
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
            Mapping instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("memoryStart")) is not None:
            args["memory_start"] = _utils.parse_int64(val)
        if (val := data.get("memoryLimit")) is not None:
            args["memory_limit"] = _utils.parse_int64(val)
        if (val := data.get("fileOffset")) is not None:
            args["file_offset"] = _utils.parse_int64(val)
        if (val := data.get("filenameStrindex")) is not None:
            args["filename_strindex"] = val
        if (val := data.get("attributeIndices")) is not None:
            args["attribute_indices"] = val
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
        res: dict[str, Any] = {}
        if self.location_indices:
            res["locationIndices"] = self.location_indices
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
            Stack instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("locationIndices")) is not None:
            args["location_indices"] = val
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
        res: dict[str, Any] = {}
        if self.mapping_index != 0:
            res["mappingIndex"] = self.mapping_index
        if self.address != 0:
            res["address"] = _utils.encode_int64(self.address)
        if self.lines:
            res["lines"] = _utils.serialize_repeated(self.lines, lambda v: v.to_dict())
        if self.attribute_indices:
            res["attributeIndices"] = self.attribute_indices
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
            Location instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("mappingIndex")) is not None:
            args["mapping_index"] = val
        if (val := data.get("address")) is not None:
            args["address"] = _utils.parse_int64(val)
        if (val := data.get("lines")) is not None:
            args["lines"] = _utils.deserialize_repeated(val, lambda v: Line.from_dict(v))
        if (val := data.get("attributeIndices")) is not None:
            args["attribute_indices"] = val
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
        res: dict[str, Any] = {}
        if self.function_index != 0:
            res["functionIndex"] = self.function_index
        if self.line != 0:
            res["line"] = _utils.encode_int64(self.line)
        if self.column != 0:
            res["column"] = _utils.encode_int64(self.column)
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
            Line instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("functionIndex")) is not None:
            args["function_index"] = val
        if (val := data.get("line")) is not None:
            args["line"] = _utils.parse_int64(val)
        if (val := data.get("column")) is not None:
            args["column"] = _utils.parse_int64(val)
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
        res: dict[str, Any] = {}
        if self.name_strindex != 0:
            res["nameStrindex"] = self.name_strindex
        if self.system_name_strindex != 0:
            res["systemNameStrindex"] = self.system_name_strindex
        if self.filename_strindex != 0:
            res["filenameStrindex"] = self.filename_strindex
        if self.start_line != 0:
            res["startLine"] = _utils.encode_int64(self.start_line)
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
            Function instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("nameStrindex")) is not None:
            args["name_strindex"] = val
        if (val := data.get("systemNameStrindex")) is not None:
            args["system_name_strindex"] = val
        if (val := data.get("filenameStrindex")) is not None:
            args["filename_strindex"] = val
        if (val := data.get("startLine")) is not None:
            args["start_line"] = _utils.parse_int64(val)
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
        res: dict[str, Any] = {}
        if self.key_strindex != 0:
            res["keyStrindex"] = self.key_strindex
        if self.value is not None:
            res["value"] = self.value.to_dict()
        if self.unit_strindex != 0:
            res["unitStrindex"] = self.unit_strindex
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
            KeyValueAndUnit instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("keyStrindex")) is not None:
            args["key_strindex"] = val
        if (val := data.get("value")) is not None:
            args["value"] = opentelemetry.proto_json.common.v1.common.AnyValue.from_dict(val)
        if (val := data.get("unitStrindex")) is not None:
            args["unit_strindex"] = val
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