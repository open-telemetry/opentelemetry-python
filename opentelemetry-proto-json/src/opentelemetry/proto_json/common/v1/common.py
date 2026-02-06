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

    string_value: str = ''
    bool_value: bool = False
    int_value: int = 0
    double_value: float = 0.0
    array_value: ArrayValue = None
    kvlist_value: KeyValueList = None
    bytes_value: bytes = b''

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        res: dict[str, Any] = {}
        if self.string_value != '':
            res["stringValue"] = self.string_value
        if self.bool_value != False:
            res["boolValue"] = self.bool_value
        if self.int_value != 0:
            res["intValue"] = _utils.encode_int64(self.int_value)
        if self.double_value != 0.0:
            res["doubleValue"] = _utils.encode_float(self.double_value)
        if self.array_value is not None:
            res["arrayValue"] = self.array_value.to_dict()
        if self.kvlist_value is not None:
            res["kvlistValue"] = self.kvlist_value.to_dict()
        if self.bytes_value != b'':
            res["bytesValue"] = _utils.encode_base64(self.bytes_value)
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
            AnyValue instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("stringValue")) is not None:
            args["string_value"] = val
        if (val := data.get("boolValue")) is not None:
            args["bool_value"] = val
        if (val := data.get("intValue")) is not None:
            args["int_value"] = _utils.parse_int64(val)
        if (val := data.get("doubleValue")) is not None:
            args["double_value"] = _utils.parse_float(val)
        if (val := data.get("arrayValue")) is not None:
            args["array_value"] = ArrayValue.from_dict(val)
        if (val := data.get("kvlistValue")) is not None:
            args["kvlist_value"] = KeyValueList.from_dict(val)
        if (val := data.get("bytesValue")) is not None:
            args["bytes_value"] = _utils.decode_base64(val)
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
        res: dict[str, Any] = {}
        if self.values:
            res["values"] = _utils.serialize_repeated(self.values, lambda v: v.to_dict())
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
            ArrayValue instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("values")) is not None:
            args["values"] = _utils.deserialize_repeated(val, lambda v: AnyValue.from_dict(v))
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
        res: dict[str, Any] = {}
        if self.values:
            res["values"] = _utils.serialize_repeated(self.values, lambda v: v.to_dict())
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
            KeyValueList instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("values")) is not None:
            args["values"] = _utils.deserialize_repeated(val, lambda v: KeyValue.from_dict(v))
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
        res: dict[str, Any] = {}
        if self.key != '':
            res["key"] = self.key
        if self.value is not None:
            res["value"] = self.value.to_dict()
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
            KeyValue instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("key")) is not None:
            args["key"] = val
        if (val := data.get("value")) is not None:
            args["value"] = AnyValue.from_dict(val)
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
        res: dict[str, Any] = {}
        if self.name != '':
            res["name"] = self.name
        if self.version != '':
            res["version"] = self.version
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
            InstrumentationScope instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("name")) is not None:
            args["name"] = val
        if (val := data.get("version")) is not None:
            args["version"] = val
        if (val := data.get("attributes")) is not None:
            args["attributes"] = _utils.deserialize_repeated(val, lambda v: KeyValue.from_dict(v))
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
        res: dict[str, Any] = {}
        if self.schema_url != '':
            res["schemaUrl"] = self.schema_url
        if self.type != '':
            res["type"] = self.type
        if self.id_keys:
            res["idKeys"] = self.id_keys
        if self.description_keys:
            res["descriptionKeys"] = self.description_keys
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
            EntityRef instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("schemaUrl")) is not None:
            args["schema_url"] = val
        if (val := data.get("type")) is not None:
            args["type"] = val
        if (val := data.get("idKeys")) is not None:
            args["id_keys"] = val
        if (val := data.get("descriptionKeys")) is not None:
            args["description_keys"] = val
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