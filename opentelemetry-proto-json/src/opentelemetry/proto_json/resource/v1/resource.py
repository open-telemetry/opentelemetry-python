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

import json
from typing import Any, Optional, Union, Self
from dataclasses import dataclass, field
from enum import IntEnum

import opentelemetry.proto_json._otlp_json_utils as _utils
import opentelemetry.proto_json.common.v1.common

@dataclass(slots=True)
class Resource:
    """
    Generated from protobuf message Resource
    """

    attributes: list[opentelemetry.proto_json.common.v1.common.KeyValue] = field(default_factory=list)
    dropped_attributes_count: int = 0
    entity_refs: list[opentelemetry.proto_json.common.v1.common.EntityRef] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        res: dict[str, Any] = {}
        if self.attributes:
            res["attributes"] = _utils.serialize_repeated(self.attributes, lambda v: v.to_dict())
        if self.dropped_attributes_count != 0:
            res["droppedAttributesCount"] = self.dropped_attributes_count
        if self.entity_refs:
            res["entityRefs"] = _utils.serialize_repeated(self.entity_refs, lambda v: v.to_dict())
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
            Resource instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("attributes")) is not None:
            args["attributes"] = _utils.deserialize_repeated(val, lambda v: opentelemetry.proto_json.common.v1.common.KeyValue.from_dict(v))
        if (val := data.get("droppedAttributesCount")) is not None:
            args["dropped_attributes_count"] = val
        if (val := data.get("entityRefs")) is not None:
            args["entity_refs"] = _utils.deserialize_repeated(val, lambda v: opentelemetry.proto_json.common.v1.common.EntityRef.from_dict(v))
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