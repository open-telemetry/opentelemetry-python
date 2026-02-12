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

import builtins
import dataclasses
import functools
import json
import sys
import typing

if sys.version_info >= (3, 10):
    _dataclass = functools.partial(dataclasses.dataclass, slots=True)
else:
    _dataclass = dataclasses.dataclass

import opentelemetry.proto_json._otlp_json_utils
import opentelemetry.proto_json.common.v1.common
import opentelemetry.proto_json.resource.v1.resource


@typing.final
@_dataclass
class ProfilesDictionary:
    """
    Generated from protobuf message ProfilesDictionary
    """

    mapping_table: builtins.list[Mapping] = dataclasses.field(default_factory=builtins.list)
    location_table: builtins.list[Location] = dataclasses.field(default_factory=builtins.list)
    function_table: builtins.list[Function] = dataclasses.field(default_factory=builtins.list)
    link_table: builtins.list[Link] = dataclasses.field(default_factory=builtins.list)
    string_table: builtins.list[builtins.str] = dataclasses.field(default_factory=builtins.list)
    attribute_table: builtins.list[KeyValueAndUnit] = dataclasses.field(default_factory=builtins.list)
    stack_table: builtins.list[Stack] = dataclasses.field(default_factory=builtins.list)

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.mapping_table:
            _result["mappingTable"] = opentelemetry.proto_json._otlp_json_utils.encode_repeated(self.mapping_table, lambda _v: _v.to_dict())
        if self.location_table:
            _result["locationTable"] = opentelemetry.proto_json._otlp_json_utils.encode_repeated(self.location_table, lambda _v: _v.to_dict())
        if self.function_table:
            _result["functionTable"] = opentelemetry.proto_json._otlp_json_utils.encode_repeated(self.function_table, lambda _v: _v.to_dict())
        if self.link_table:
            _result["linkTable"] = opentelemetry.proto_json._otlp_json_utils.encode_repeated(self.link_table, lambda _v: _v.to_dict())
        if self.string_table:
            _result["stringTable"] = self.string_table
        if self.attribute_table:
            _result["attributeTable"] = opentelemetry.proto_json._otlp_json_utils.encode_repeated(self.attribute_table, lambda _v: _v.to_dict())
        if self.stack_table:
            _result["stackTable"] = opentelemetry.proto_json._otlp_json_utils.encode_repeated(self.stack_table, lambda _v: _v.to_dict())
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "ProfilesDictionary":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            ProfilesDictionary instance
        """
        opentelemetry.proto_json._otlp_json_utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("mappingTable")) is not None:
            _args["mapping_table"] = opentelemetry.proto_json._otlp_json_utils.decode_repeated(_value, lambda _v: Mapping.from_dict(_v), "mapping_table")
        if (_value := data.get("locationTable")) is not None:
            _args["location_table"] = opentelemetry.proto_json._otlp_json_utils.decode_repeated(_value, lambda _v: Location.from_dict(_v), "location_table")
        if (_value := data.get("functionTable")) is not None:
            _args["function_table"] = opentelemetry.proto_json._otlp_json_utils.decode_repeated(_value, lambda _v: Function.from_dict(_v), "function_table")
        if (_value := data.get("linkTable")) is not None:
            _args["link_table"] = opentelemetry.proto_json._otlp_json_utils.decode_repeated(_value, lambda _v: Link.from_dict(_v), "link_table")
        if (_value := data.get("stringTable")) is not None:
            _args["string_table"] = opentelemetry.proto_json._otlp_json_utils.decode_repeated(_value, lambda _v: _v, "string_table")
        if (_value := data.get("attributeTable")) is not None:
            _args["attribute_table"] = opentelemetry.proto_json._otlp_json_utils.decode_repeated(_value, lambda _v: KeyValueAndUnit.from_dict(_v), "attribute_table")
        if (_value := data.get("stackTable")) is not None:
            _args["stack_table"] = opentelemetry.proto_json._otlp_json_utils.decode_repeated(_value, lambda _v: Stack.from_dict(_v), "stack_table")

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "ProfilesDictionary":
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
class ProfilesData:
    """
    Generated from protobuf message ProfilesData
    """

    resource_profiles: builtins.list[ResourceProfiles] = dataclasses.field(default_factory=builtins.list)
    dictionary: typing.Optional[ProfilesDictionary] = None

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.resource_profiles:
            _result["resourceProfiles"] = opentelemetry.proto_json._otlp_json_utils.encode_repeated(self.resource_profiles, lambda _v: _v.to_dict())
        if self.dictionary:
            _result["dictionary"] = self.dictionary.to_dict()
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "ProfilesData":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            ProfilesData instance
        """
        opentelemetry.proto_json._otlp_json_utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("resourceProfiles")) is not None:
            _args["resource_profiles"] = opentelemetry.proto_json._otlp_json_utils.decode_repeated(_value, lambda _v: ResourceProfiles.from_dict(_v), "resource_profiles")
        if (_value := data.get("dictionary")) is not None:
            _args["dictionary"] = ProfilesDictionary.from_dict(_value)

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "ProfilesData":
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
class ResourceProfiles:
    """
    Generated from protobuf message ResourceProfiles
    """

    resource: typing.Optional[opentelemetry.proto_json.resource.v1.resource.Resource] = None
    scope_profiles: builtins.list[ScopeProfiles] = dataclasses.field(default_factory=builtins.list)
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
        if self.scope_profiles:
            _result["scopeProfiles"] = opentelemetry.proto_json._otlp_json_utils.encode_repeated(self.scope_profiles, lambda _v: _v.to_dict())
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
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "ResourceProfiles":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            ResourceProfiles instance
        """
        opentelemetry.proto_json._otlp_json_utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("resource")) is not None:
            _args["resource"] = opentelemetry.proto_json.resource.v1.resource.Resource.from_dict(_value)
        if (_value := data.get("scopeProfiles")) is not None:
            _args["scope_profiles"] = opentelemetry.proto_json._otlp_json_utils.decode_repeated(_value, lambda _v: ScopeProfiles.from_dict(_v), "scope_profiles")
        if (_value := data.get("schemaUrl")) is not None:
            opentelemetry.proto_json._otlp_json_utils.validate_type(_value, builtins.str, "schema_url")
            _args["schema_url"] = _value

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "ResourceProfiles":
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
class ScopeProfiles:
    """
    Generated from protobuf message ScopeProfiles
    """

    scope: typing.Optional[opentelemetry.proto_json.common.v1.common.InstrumentationScope] = None
    profiles: builtins.list[Profile] = dataclasses.field(default_factory=builtins.list)
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
        if self.profiles:
            _result["profiles"] = opentelemetry.proto_json._otlp_json_utils.encode_repeated(self.profiles, lambda _v: _v.to_dict())
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
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "ScopeProfiles":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            ScopeProfiles instance
        """
        opentelemetry.proto_json._otlp_json_utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("scope")) is not None:
            _args["scope"] = opentelemetry.proto_json.common.v1.common.InstrumentationScope.from_dict(_value)
        if (_value := data.get("profiles")) is not None:
            _args["profiles"] = opentelemetry.proto_json._otlp_json_utils.decode_repeated(_value, lambda _v: Profile.from_dict(_v), "profiles")
        if (_value := data.get("schemaUrl")) is not None:
            opentelemetry.proto_json._otlp_json_utils.validate_type(_value, builtins.str, "schema_url")
            _args["schema_url"] = _value

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "ScopeProfiles":
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
class Profile:
    """
    Generated from protobuf message Profile
    """

    sample_type: typing.Optional[ValueType] = None
    samples: builtins.list[Sample] = dataclasses.field(default_factory=builtins.list)
    time_unix_nano: typing.Optional[builtins.int] = 0
    duration_nano: typing.Optional[builtins.int] = 0
    period_type: typing.Optional[ValueType] = None
    period: typing.Optional[builtins.int] = 0
    profile_id: typing.Optional[builtins.bytes] = b""
    dropped_attributes_count: typing.Optional[builtins.int] = 0
    original_payload_format: typing.Optional[builtins.str] = ""
    original_payload: typing.Optional[builtins.bytes] = b""
    attribute_indices: builtins.list[builtins.int] = dataclasses.field(default_factory=builtins.list)

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.sample_type:
            _result["sampleType"] = self.sample_type.to_dict()
        if self.samples:
            _result["samples"] = opentelemetry.proto_json._otlp_json_utils.encode_repeated(self.samples, lambda _v: _v.to_dict())
        if self.time_unix_nano:
            _result["timeUnixNano"] = opentelemetry.proto_json._otlp_json_utils.encode_int64(self.time_unix_nano)
        if self.duration_nano:
            _result["durationNano"] = opentelemetry.proto_json._otlp_json_utils.encode_int64(self.duration_nano)
        if self.period_type:
            _result["periodType"] = self.period_type.to_dict()
        if self.period:
            _result["period"] = opentelemetry.proto_json._otlp_json_utils.encode_int64(self.period)
        if self.profile_id:
            _result["profileId"] = opentelemetry.proto_json._otlp_json_utils.encode_base64(self.profile_id)
        if self.dropped_attributes_count:
            _result["droppedAttributesCount"] = self.dropped_attributes_count
        if self.original_payload_format:
            _result["originalPayloadFormat"] = self.original_payload_format
        if self.original_payload:
            _result["originalPayload"] = opentelemetry.proto_json._otlp_json_utils.encode_base64(self.original_payload)
        if self.attribute_indices:
            _result["attributeIndices"] = self.attribute_indices
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "Profile":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            Profile instance
        """
        opentelemetry.proto_json._otlp_json_utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("sampleType")) is not None:
            _args["sample_type"] = ValueType.from_dict(_value)
        if (_value := data.get("samples")) is not None:
            _args["samples"] = opentelemetry.proto_json._otlp_json_utils.decode_repeated(_value, lambda _v: Sample.from_dict(_v), "samples")
        if (_value := data.get("timeUnixNano")) is not None:
            _args["time_unix_nano"] = opentelemetry.proto_json._otlp_json_utils.decode_int64(_value, "time_unix_nano")
        if (_value := data.get("durationNano")) is not None:
            _args["duration_nano"] = opentelemetry.proto_json._otlp_json_utils.decode_int64(_value, "duration_nano")
        if (_value := data.get("periodType")) is not None:
            _args["period_type"] = ValueType.from_dict(_value)
        if (_value := data.get("period")) is not None:
            _args["period"] = opentelemetry.proto_json._otlp_json_utils.decode_int64(_value, "period")
        if (_value := data.get("profileId")) is not None:
            _args["profile_id"] = opentelemetry.proto_json._otlp_json_utils.decode_base64(_value, "profile_id")
        if (_value := data.get("droppedAttributesCount")) is not None:
            opentelemetry.proto_json._otlp_json_utils.validate_type(_value, builtins.int, "dropped_attributes_count")
            _args["dropped_attributes_count"] = _value
        if (_value := data.get("originalPayloadFormat")) is not None:
            opentelemetry.proto_json._otlp_json_utils.validate_type(_value, builtins.str, "original_payload_format")
            _args["original_payload_format"] = _value
        if (_value := data.get("originalPayload")) is not None:
            _args["original_payload"] = opentelemetry.proto_json._otlp_json_utils.decode_base64(_value, "original_payload")
        if (_value := data.get("attributeIndices")) is not None:
            _args["attribute_indices"] = opentelemetry.proto_json._otlp_json_utils.decode_repeated(_value, lambda _v: _v, "attribute_indices")

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "Profile":
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

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.trace_id:
            _result["traceId"] = opentelemetry.proto_json._otlp_json_utils.encode_hex(self.trace_id)
        if self.span_id:
            _result["spanId"] = opentelemetry.proto_json._otlp_json_utils.encode_hex(self.span_id)
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "Link":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            Link instance
        """
        opentelemetry.proto_json._otlp_json_utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("traceId")) is not None:
            _args["trace_id"] = opentelemetry.proto_json._otlp_json_utils.decode_hex(_value, "trace_id")
        if (_value := data.get("spanId")) is not None:
            _args["span_id"] = opentelemetry.proto_json._otlp_json_utils.decode_hex(_value, "span_id")

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "Link":
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
class ValueType:
    """
    Generated from protobuf message ValueType
    """

    type_strindex: typing.Optional[builtins.int] = 0
    unit_strindex: typing.Optional[builtins.int] = 0

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.type_strindex:
            _result["typeStrindex"] = self.type_strindex
        if self.unit_strindex:
            _result["unitStrindex"] = self.unit_strindex
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "ValueType":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            ValueType instance
        """
        opentelemetry.proto_json._otlp_json_utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("typeStrindex")) is not None:
            opentelemetry.proto_json._otlp_json_utils.validate_type(_value, builtins.int, "type_strindex")
            _args["type_strindex"] = _value
        if (_value := data.get("unitStrindex")) is not None:
            opentelemetry.proto_json._otlp_json_utils.validate_type(_value, builtins.int, "unit_strindex")
            _args["unit_strindex"] = _value

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "ValueType":
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
class Sample:
    """
    Generated from protobuf message Sample
    """

    stack_index: typing.Optional[builtins.int] = 0
    values: builtins.list[builtins.int] = dataclasses.field(default_factory=builtins.list)
    attribute_indices: builtins.list[builtins.int] = dataclasses.field(default_factory=builtins.list)
    link_index: typing.Optional[builtins.int] = 0
    timestamps_unix_nano: builtins.list[builtins.int] = dataclasses.field(default_factory=builtins.list)

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.stack_index:
            _result["stackIndex"] = self.stack_index
        if self.values:
            _result["values"] = opentelemetry.proto_json._otlp_json_utils.encode_repeated(self.values, lambda _v: opentelemetry.proto_json._otlp_json_utils.encode_int64(_v))
        if self.attribute_indices:
            _result["attributeIndices"] = self.attribute_indices
        if self.link_index:
            _result["linkIndex"] = self.link_index
        if self.timestamps_unix_nano:
            _result["timestampsUnixNano"] = opentelemetry.proto_json._otlp_json_utils.encode_repeated(self.timestamps_unix_nano, lambda _v: opentelemetry.proto_json._otlp_json_utils.encode_int64(_v))
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "Sample":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            Sample instance
        """
        opentelemetry.proto_json._otlp_json_utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("stackIndex")) is not None:
            opentelemetry.proto_json._otlp_json_utils.validate_type(_value, builtins.int, "stack_index")
            _args["stack_index"] = _value
        if (_value := data.get("values")) is not None:
            _args["values"] = opentelemetry.proto_json._otlp_json_utils.decode_repeated(_value, lambda _v: opentelemetry.proto_json._otlp_json_utils.decode_int64(_v, "values"), "values")
        if (_value := data.get("attributeIndices")) is not None:
            _args["attribute_indices"] = opentelemetry.proto_json._otlp_json_utils.decode_repeated(_value, lambda _v: _v, "attribute_indices")
        if (_value := data.get("linkIndex")) is not None:
            opentelemetry.proto_json._otlp_json_utils.validate_type(_value, builtins.int, "link_index")
            _args["link_index"] = _value
        if (_value := data.get("timestampsUnixNano")) is not None:
            _args["timestamps_unix_nano"] = opentelemetry.proto_json._otlp_json_utils.decode_repeated(_value, lambda _v: opentelemetry.proto_json._otlp_json_utils.decode_int64(_v, "timestamps_unix_nano"), "timestamps_unix_nano")

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "Sample":
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
class Mapping:
    """
    Generated from protobuf message Mapping
    """

    memory_start: typing.Optional[builtins.int] = 0
    memory_limit: typing.Optional[builtins.int] = 0
    file_offset: typing.Optional[builtins.int] = 0
    filename_strindex: typing.Optional[builtins.int] = 0
    attribute_indices: builtins.list[builtins.int] = dataclasses.field(default_factory=builtins.list)

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.memory_start:
            _result["memoryStart"] = opentelemetry.proto_json._otlp_json_utils.encode_int64(self.memory_start)
        if self.memory_limit:
            _result["memoryLimit"] = opentelemetry.proto_json._otlp_json_utils.encode_int64(self.memory_limit)
        if self.file_offset:
            _result["fileOffset"] = opentelemetry.proto_json._otlp_json_utils.encode_int64(self.file_offset)
        if self.filename_strindex:
            _result["filenameStrindex"] = self.filename_strindex
        if self.attribute_indices:
            _result["attributeIndices"] = self.attribute_indices
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "Mapping":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            Mapping instance
        """
        opentelemetry.proto_json._otlp_json_utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("memoryStart")) is not None:
            _args["memory_start"] = opentelemetry.proto_json._otlp_json_utils.decode_int64(_value, "memory_start")
        if (_value := data.get("memoryLimit")) is not None:
            _args["memory_limit"] = opentelemetry.proto_json._otlp_json_utils.decode_int64(_value, "memory_limit")
        if (_value := data.get("fileOffset")) is not None:
            _args["file_offset"] = opentelemetry.proto_json._otlp_json_utils.decode_int64(_value, "file_offset")
        if (_value := data.get("filenameStrindex")) is not None:
            opentelemetry.proto_json._otlp_json_utils.validate_type(_value, builtins.int, "filename_strindex")
            _args["filename_strindex"] = _value
        if (_value := data.get("attributeIndices")) is not None:
            _args["attribute_indices"] = opentelemetry.proto_json._otlp_json_utils.decode_repeated(_value, lambda _v: _v, "attribute_indices")

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "Mapping":
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
class Stack:
    """
    Generated from protobuf message Stack
    """

    location_indices: builtins.list[builtins.int] = dataclasses.field(default_factory=builtins.list)

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.location_indices:
            _result["locationIndices"] = self.location_indices
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "Stack":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            Stack instance
        """
        opentelemetry.proto_json._otlp_json_utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("locationIndices")) is not None:
            _args["location_indices"] = opentelemetry.proto_json._otlp_json_utils.decode_repeated(_value, lambda _v: _v, "location_indices")

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "Stack":
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
class Location:
    """
    Generated from protobuf message Location
    """

    mapping_index: typing.Optional[builtins.int] = 0
    address: typing.Optional[builtins.int] = 0
    lines: builtins.list[Line] = dataclasses.field(default_factory=builtins.list)
    attribute_indices: builtins.list[builtins.int] = dataclasses.field(default_factory=builtins.list)

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.mapping_index:
            _result["mappingIndex"] = self.mapping_index
        if self.address:
            _result["address"] = opentelemetry.proto_json._otlp_json_utils.encode_int64(self.address)
        if self.lines:
            _result["lines"] = opentelemetry.proto_json._otlp_json_utils.encode_repeated(self.lines, lambda _v: _v.to_dict())
        if self.attribute_indices:
            _result["attributeIndices"] = self.attribute_indices
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "Location":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            Location instance
        """
        opentelemetry.proto_json._otlp_json_utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("mappingIndex")) is not None:
            opentelemetry.proto_json._otlp_json_utils.validate_type(_value, builtins.int, "mapping_index")
            _args["mapping_index"] = _value
        if (_value := data.get("address")) is not None:
            _args["address"] = opentelemetry.proto_json._otlp_json_utils.decode_int64(_value, "address")
        if (_value := data.get("lines")) is not None:
            _args["lines"] = opentelemetry.proto_json._otlp_json_utils.decode_repeated(_value, lambda _v: Line.from_dict(_v), "lines")
        if (_value := data.get("attributeIndices")) is not None:
            _args["attribute_indices"] = opentelemetry.proto_json._otlp_json_utils.decode_repeated(_value, lambda _v: _v, "attribute_indices")

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "Location":
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
class Line:
    """
    Generated from protobuf message Line
    """

    function_index: typing.Optional[builtins.int] = 0
    line: typing.Optional[builtins.int] = 0
    column: typing.Optional[builtins.int] = 0

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.function_index:
            _result["functionIndex"] = self.function_index
        if self.line:
            _result["line"] = opentelemetry.proto_json._otlp_json_utils.encode_int64(self.line)
        if self.column:
            _result["column"] = opentelemetry.proto_json._otlp_json_utils.encode_int64(self.column)
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "Line":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            Line instance
        """
        opentelemetry.proto_json._otlp_json_utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("functionIndex")) is not None:
            opentelemetry.proto_json._otlp_json_utils.validate_type(_value, builtins.int, "function_index")
            _args["function_index"] = _value
        if (_value := data.get("line")) is not None:
            _args["line"] = opentelemetry.proto_json._otlp_json_utils.decode_int64(_value, "line")
        if (_value := data.get("column")) is not None:
            _args["column"] = opentelemetry.proto_json._otlp_json_utils.decode_int64(_value, "column")

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "Line":
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
class Function:
    """
    Generated from protobuf message Function
    """

    name_strindex: typing.Optional[builtins.int] = 0
    system_name_strindex: typing.Optional[builtins.int] = 0
    filename_strindex: typing.Optional[builtins.int] = 0
    start_line: typing.Optional[builtins.int] = 0

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.name_strindex:
            _result["nameStrindex"] = self.name_strindex
        if self.system_name_strindex:
            _result["systemNameStrindex"] = self.system_name_strindex
        if self.filename_strindex:
            _result["filenameStrindex"] = self.filename_strindex
        if self.start_line:
            _result["startLine"] = opentelemetry.proto_json._otlp_json_utils.encode_int64(self.start_line)
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "Function":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            Function instance
        """
        opentelemetry.proto_json._otlp_json_utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("nameStrindex")) is not None:
            opentelemetry.proto_json._otlp_json_utils.validate_type(_value, builtins.int, "name_strindex")
            _args["name_strindex"] = _value
        if (_value := data.get("systemNameStrindex")) is not None:
            opentelemetry.proto_json._otlp_json_utils.validate_type(_value, builtins.int, "system_name_strindex")
            _args["system_name_strindex"] = _value
        if (_value := data.get("filenameStrindex")) is not None:
            opentelemetry.proto_json._otlp_json_utils.validate_type(_value, builtins.int, "filename_strindex")
            _args["filename_strindex"] = _value
        if (_value := data.get("startLine")) is not None:
            _args["start_line"] = opentelemetry.proto_json._otlp_json_utils.decode_int64(_value, "start_line")

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "Function":
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
class KeyValueAndUnit:
    """
    Generated from protobuf message KeyValueAndUnit
    """

    key_strindex: typing.Optional[builtins.int] = 0
    value: typing.Optional[opentelemetry.proto_json.common.v1.common.AnyValue] = None
    unit_strindex: typing.Optional[builtins.int] = 0

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.key_strindex:
            _result["keyStrindex"] = self.key_strindex
        if self.value:
            _result["value"] = self.value.to_dict()
        if self.unit_strindex:
            _result["unitStrindex"] = self.unit_strindex
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "KeyValueAndUnit":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            KeyValueAndUnit instance
        """
        opentelemetry.proto_json._otlp_json_utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("keyStrindex")) is not None:
            opentelemetry.proto_json._otlp_json_utils.validate_type(_value, builtins.int, "key_strindex")
            _args["key_strindex"] = _value
        if (_value := data.get("value")) is not None:
            _args["value"] = opentelemetry.proto_json.common.v1.common.AnyValue.from_dict(_value)
        if (_value := data.get("unitStrindex")) is not None:
            opentelemetry.proto_json._otlp_json_utils.validate_type(_value, builtins.int, "unit_strindex")
            _args["unit_strindex"] = _value

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "KeyValueAndUnit":
        """
        Deserialize from a JSON string or bytes.

        Args:
            data: JSON string or bytes

        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))
