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

# AUTO-GENERATED from "opentelemetry/proto/collector/profiles/v1development/profiles_service.proto"
# DO NOT EDIT MANUALLY

from __future__ import annotations

import json
from typing import Any, Optional, Union, Self
from dataclasses import dataclass, field
from enum import IntEnum

import opentelemetry.proto_json._otlp_json_utils as _utils
import opentelemetry.proto_json.profiles.v1development.profiles

@dataclass(slots=True)
class ExportProfilesServiceRequest:
    """
    Generated from protobuf message ExportProfilesServiceRequest
    """

    resource_profiles: list[opentelemetry.proto_json.profiles.v1development.profiles.ResourceProfiles] = field(default_factory=list)
    dictionary: opentelemetry.proto_json.profiles.v1development.profiles.ProfilesDictionary = None

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
            ExportProfilesServiceRequest instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("resourceProfiles")) is not None:
            args["resource_profiles"] = _utils.deserialize_repeated(val, lambda v: opentelemetry.proto_json.profiles.v1development.profiles.ResourceProfiles.from_dict(v))
        if (val := data.get("dictionary")) is not None:
            args["dictionary"] = opentelemetry.proto_json.profiles.v1development.profiles.ProfilesDictionary.from_dict(val)
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
class ExportProfilesServiceResponse:
    """
    Generated from protobuf message ExportProfilesServiceResponse
    """

    partial_success: ExportProfilesPartialSuccess = None

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        res: dict[str, Any] = {}
        if self.partial_success is not None:
            res["partialSuccess"] = self.partial_success.to_dict()
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
            ExportProfilesServiceResponse instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("partialSuccess")) is not None:
            args["partial_success"] = ExportProfilesPartialSuccess.from_dict(val)
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
class ExportProfilesPartialSuccess:
    """
    Generated from protobuf message ExportProfilesPartialSuccess
    """

    rejected_profiles: int = 0
    error_message: str = ''

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        res: dict[str, Any] = {}
        if self.rejected_profiles != 0:
            res["rejectedProfiles"] = _utils.encode_int64(self.rejected_profiles)
        if self.error_message != '':
            res["errorMessage"] = self.error_message
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
            ExportProfilesPartialSuccess instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("rejectedProfiles")) is not None:
            args["rejected_profiles"] = _utils.parse_int64(val)
        if (val := data.get("errorMessage")) is not None:
            args["error_message"] = val
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