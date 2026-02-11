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

# AUTO-GENERATED from "opentelemetry/proto/common/v1/common.proto"
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

import opentelemetry.proto_json._otlp_json_utils as _utils


@typing.final
@_dataclass
class AnyValue:
    """
    Generated from protobuf message AnyValue
    """

    string_value: typing.Optional[builtins.str] = None
    bool_value: typing.Optional[builtins.bool] = None
    int_value: typing.Optional[builtins.int] = None
    double_value: typing.Optional[builtins.float] = None
    array_value: typing.Optional[ArrayValue] = None
    kvlist_value: typing.Optional[KeyValueList] = None
    bytes_value: typing.Optional[builtins.bytes] = None

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.bytes_value is not None:
            _result["bytesValue"] = _utils.encode_base64(self.bytes_value)
        elif self.kvlist_value is not None:
            _result["kvlistValue"] = self.kvlist_value.to_dict()
        elif self.array_value is not None:
            _result["arrayValue"] = self.array_value.to_dict()
        elif self.double_value is not None:
            _result["doubleValue"] = _utils.encode_float(self.double_value)
        elif self.int_value is not None:
            _result["intValue"] = _utils.encode_int64(self.int_value)
        elif self.bool_value is not None:
            _result["boolValue"] = self.bool_value
        elif self.string_value is not None:
            _result["stringValue"] = self.string_value
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "AnyValue":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            AnyValue instance
        """
        _utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("bytesValue")) is not None:
            _args["bytes_value"] = _utils.decode_base64(_value, "bytes_value")
        elif (_value := data.get("kvlistValue")) is not None:
            _args["kvlist_value"] = KeyValueList.from_dict(_value)
        elif (_value := data.get("arrayValue")) is not None:
            _args["array_value"] = ArrayValue.from_dict(_value)
        elif (_value := data.get("doubleValue")) is not None:
            _args["double_value"] = _utils.decode_float(_value, "double_value")
        elif (_value := data.get("intValue")) is not None:
            _args["int_value"] = _utils.decode_int64(_value, "int_value")
        elif (_value := data.get("boolValue")) is not None:
            _utils.validate_type(_value, builtins.bool, "bool_value")
            _args["bool_value"] = _value
        elif (_value := data.get("stringValue")) is not None:
            _utils.validate_type(_value, builtins.str, "string_value")
            _args["string_value"] = _value

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "AnyValue":
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
class ArrayValue:
    """
    Generated from protobuf message ArrayValue
    """

    values: builtins.list[AnyValue] = dataclasses.field(default_factory=builtins.list)

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.values:
            _result["values"] = _utils.encode_repeated(self.values, lambda _v: _v.to_dict())
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "ArrayValue":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            ArrayValue instance
        """
        _utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("values")) is not None:
            _args["values"] = _utils.decode_repeated(_value, lambda _v: AnyValue.from_dict(_v), "values")

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "ArrayValue":
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
class KeyValueList:
    """
    Generated from protobuf message KeyValueList
    """

    values: builtins.list[KeyValue] = dataclasses.field(default_factory=builtins.list)

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.values:
            _result["values"] = _utils.encode_repeated(self.values, lambda _v: _v.to_dict())
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "KeyValueList":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            KeyValueList instance
        """
        _utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("values")) is not None:
            _args["values"] = _utils.decode_repeated(_value, lambda _v: KeyValue.from_dict(_v), "values")

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "KeyValueList":
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
class KeyValue:
    """
    Generated from protobuf message KeyValue
    """

    key: typing.Optional[builtins.str] = ""
    value: typing.Optional[AnyValue] = None

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.key:
            _result["key"] = self.key
        if self.value:
            _result["value"] = self.value.to_dict()
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "KeyValue":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            KeyValue instance
        """
        _utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("key")) is not None:
            _utils.validate_type(_value, builtins.str, "key")
            _args["key"] = _value
        if (_value := data.get("value")) is not None:
            _args["value"] = AnyValue.from_dict(_value)

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "KeyValue":
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
class InstrumentationScope:
    """
    Generated from protobuf message InstrumentationScope
    """

    name: typing.Optional[builtins.str] = ""
    version: typing.Optional[builtins.str] = ""
    attributes: builtins.list[KeyValue] = dataclasses.field(default_factory=builtins.list)
    dropped_attributes_count: typing.Optional[builtins.int] = 0

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.name:
            _result["name"] = self.name
        if self.version:
            _result["version"] = self.version
        if self.attributes:
            _result["attributes"] = _utils.encode_repeated(self.attributes, lambda _v: _v.to_dict())
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
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "InstrumentationScope":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            InstrumentationScope instance
        """
        _utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("name")) is not None:
            _utils.validate_type(_value, builtins.str, "name")
            _args["name"] = _value
        if (_value := data.get("version")) is not None:
            _utils.validate_type(_value, builtins.str, "version")
            _args["version"] = _value
        if (_value := data.get("attributes")) is not None:
            _args["attributes"] = _utils.decode_repeated(_value, lambda _v: KeyValue.from_dict(_v), "attributes")
        if (_value := data.get("droppedAttributesCount")) is not None:
            _utils.validate_type(_value, builtins.int, "dropped_attributes_count")
            _args["dropped_attributes_count"] = _value

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "InstrumentationScope":
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
class EntityRef:
    """
    Generated from protobuf message EntityRef
    """

    schema_url: typing.Optional[builtins.str] = ""
    type: typing.Optional[builtins.str] = ""
    id_keys: builtins.list[builtins.str] = dataclasses.field(default_factory=builtins.list)
    description_keys: builtins.list[builtins.str] = dataclasses.field(default_factory=builtins.list)

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.schema_url:
            _result["schemaUrl"] = self.schema_url
        if self.type:
            _result["type"] = self.type
        if self.id_keys:
            _result["idKeys"] = self.id_keys
        if self.description_keys:
            _result["descriptionKeys"] = self.description_keys
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "EntityRef":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            EntityRef instance
        """
        _utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("schemaUrl")) is not None:
            _utils.validate_type(_value, builtins.str, "schema_url")
            _args["schema_url"] = _value
        if (_value := data.get("type")) is not None:
            _utils.validate_type(_value, builtins.str, "type")
            _args["type"] = _value
        if (_value := data.get("idKeys")) is not None:
            _args["id_keys"] = _utils.decode_repeated(_value, lambda _v: _v, "id_keys")
        if (_value := data.get("descriptionKeys")) is not None:
            _args["description_keys"] = _utils.decode_repeated(_value, lambda _v: _v, "description_keys")

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "EntityRef":
        """
        Deserialize from a JSON string or bytes.

        Args:
            data: JSON string or bytes

        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))
