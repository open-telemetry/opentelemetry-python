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

# AUTO-GENERATED from "opentelemetry/proto/resource/v1/resource.proto"
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
import opentelemetry.proto_json.common.v1.common


@typing.final
@_dataclass
class Resource:
    """
    Generated from protobuf message Resource
    """

    attributes: builtins.list[opentelemetry.proto_json.common.v1.common.KeyValue] = dataclasses.field(default_factory=builtins.list)
    dropped_attributes_count: typing.Optional[builtins.int] = 0
    entity_refs: builtins.list[opentelemetry.proto_json.common.v1.common.EntityRef] = dataclasses.field(default_factory=builtins.list)

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.attributes:
            _result["attributes"] = _utils.encode_repeated(self.attributes, lambda _v: _v.to_dict())
        if self.dropped_attributes_count:
            _result["droppedAttributesCount"] = self.dropped_attributes_count
        if self.entity_refs:
            _result["entityRefs"] = _utils.encode_repeated(self.entity_refs, lambda _v: _v.to_dict())
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "Resource":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            Resource instance
        """
        _utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("attributes")) is not None:
            _args["attributes"] = _utils.decode_repeated(_value, lambda _v: opentelemetry.proto_json.common.v1.common.KeyValue.from_dict(_v), "attributes")
        if (_value := data.get("droppedAttributesCount")) is not None:
            _utils.validate_type(_value, builtins.int, "dropped_attributes_count")
            _args["dropped_attributes_count"] = _value
        if (_value := data.get("entityRefs")) is not None:
            _args["entity_refs"] = _utils.decode_repeated(_value, lambda _v: opentelemetry.proto_json.common.v1.common.EntityRef.from_dict(_v), "entity_refs")

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "Resource":
        """
        Deserialize from a JSON string or bytes.

        Args:
            data: JSON string or bytes

        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))
