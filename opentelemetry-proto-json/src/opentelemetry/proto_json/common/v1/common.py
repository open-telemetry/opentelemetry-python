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

import json
from typing import Any, Optional, Union, Self
from dataclasses import dataclass, field
from enum import IntEnum

import opentelemetry.proto_json._otlp_json_utils as _utils

@dataclass(slots=True)
class AnyValue:
    """
    Generated from protobuf message AnyValue
    """

    string_value: Optional[str] = None
    bool_value: Optional[bool] = None
    int_value: Optional[int] = None
    double_value: Optional[float] = None
    array_value: Optional[ArrayValue] = None
    kvlist_value: Optional[KeyValueList] = None
    bytes_value: Optional[bytes] = None

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result: dict[str, Any] = {}
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
            AnyValue instance
        """
        _args: dict[str, Any] = {}

        if (_value := data.get("bytesValue")) is not None:
            _args["bytes_value"] = _utils.decode_base64(_value)
        elif (_value := data.get("kvlistValue")) is not None:
            _args["kvlist_value"] = KeyValueList.from_dict(_value)
        elif (_value := data.get("arrayValue")) is not None:
            _args["array_value"] = ArrayValue.from_dict(_value)
        elif (_value := data.get("doubleValue")) is not None:
            _args["double_value"] = _utils.parse_float(_value)
        elif (_value := data.get("intValue")) is not None:
            _args["int_value"] = _utils.parse_int64(_value)
        elif (_value := data.get("boolValue")) is not None:
            _args["bool_value"] = _value
        elif (_value := data.get("stringValue")) is not None:
            _args["string_value"] = _value

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
class ArrayValue:
    """
    Generated from protobuf message ArrayValue
    """

    values: list[AnyValue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result: dict[str, Any] = {}
        if self.values:
            _result["values"] = _utils.serialize_repeated(self.values, lambda _v: _v.to_dict())
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
            ArrayValue instance
        """
        _args: dict[str, Any] = {}

        if (_value := data.get("values")) is not None:
            _args["values"] = _utils.deserialize_repeated(_value, lambda _v: AnyValue.from_dict(_v))

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
class KeyValueList:
    """
    Generated from protobuf message KeyValueList
    """

    values: list[KeyValue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result: dict[str, Any] = {}
        if self.values:
            _result["values"] = _utils.serialize_repeated(self.values, lambda _v: _v.to_dict())
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
            KeyValueList instance
        """
        _args: dict[str, Any] = {}

        if (_value := data.get("values")) is not None:
            _args["values"] = _utils.deserialize_repeated(_value, lambda _v: KeyValue.from_dict(_v))

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
class KeyValue:
    """
    Generated from protobuf message KeyValue
    """

    key: str = ''
    value: AnyValue = None

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result: dict[str, Any] = {}
        if self.key != '':
            _result["key"] = self.key
        if self.value is not None:
            _result["value"] = self.value.to_dict()
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
            KeyValue instance
        """
        _args: dict[str, Any] = {}

        if (_value := data.get("key")) is not None:
            _args["key"] = _value
        if (_value := data.get("value")) is not None:
            _args["value"] = AnyValue.from_dict(_value)

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
class InstrumentationScope:
    """
    Generated from protobuf message InstrumentationScope
    """

    name: str = ''
    version: str = ''
    attributes: list[KeyValue] = field(default_factory=list)
    dropped_attributes_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result: dict[str, Any] = {}
        if self.name != '':
            _result["name"] = self.name
        if self.version != '':
            _result["version"] = self.version
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
            InstrumentationScope instance
        """
        _args: dict[str, Any] = {}

        if (_value := data.get("name")) is not None:
            _args["name"] = _value
        if (_value := data.get("version")) is not None:
            _args["version"] = _value
        if (_value := data.get("attributes")) is not None:
            _args["attributes"] = _utils.deserialize_repeated(_value, lambda _v: KeyValue.from_dict(_v))
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
class EntityRef:
    """
    Generated from protobuf message EntityRef
    """

    schema_url: str = ''
    type: str = ''
    id_keys: list[str] = field(default_factory=list)
    description_keys: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result: dict[str, Any] = {}
        if self.schema_url != '':
            _result["schemaUrl"] = self.schema_url
        if self.type != '':
            _result["type"] = self.type
        if self.id_keys:
            _result["idKeys"] = self.id_keys
        if self.description_keys:
            _result["descriptionKeys"] = self.description_keys
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
            EntityRef instance
        """
        _args: dict[str, Any] = {}

        if (_value := data.get("schemaUrl")) is not None:
            _args["schema_url"] = _value
        if (_value := data.get("type")) is not None:
            _args["type"] = _value
        if (_value := data.get("idKeys")) is not None:
            _args["id_keys"] = _value
        if (_value := data.get("descriptionKeys")) is not None:
            _args["description_keys"] = _value

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