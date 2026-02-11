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
import opentelemetry.proto_json.profiles.v1development.profiles


@typing.final
@_dataclass
class ExportProfilesServiceRequest:
    """
    Generated from protobuf message ExportProfilesServiceRequest
    """

    resource_profiles: builtins.list[opentelemetry.proto_json.profiles.v1development.profiles.ResourceProfiles] = dataclasses.field(default_factory=builtins.list)
    dictionary: typing.Optional[opentelemetry.proto_json.profiles.v1development.profiles.ProfilesDictionary] = None

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.resource_profiles:
            _result["resourceProfiles"] = _utils.encode_repeated(self.resource_profiles, lambda _v: _v.to_dict())
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
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "ExportProfilesServiceRequest":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            ExportProfilesServiceRequest instance
        """
        _utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("resourceProfiles")) is not None:
            _args["resource_profiles"] = _utils.decode_repeated(_value, lambda _v: opentelemetry.proto_json.profiles.v1development.profiles.ResourceProfiles.from_dict(_v), "resource_profiles")
        if (_value := data.get("dictionary")) is not None:
            _args["dictionary"] = opentelemetry.proto_json.profiles.v1development.profiles.ProfilesDictionary.from_dict(_value)

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "ExportProfilesServiceRequest":
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
class ExportProfilesServiceResponse:
    """
    Generated from protobuf message ExportProfilesServiceResponse
    """

    partial_success: typing.Optional[ExportProfilesPartialSuccess] = None

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.partial_success:
            _result["partialSuccess"] = self.partial_success.to_dict()
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "ExportProfilesServiceResponse":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            ExportProfilesServiceResponse instance
        """
        _utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("partialSuccess")) is not None:
            _args["partial_success"] = ExportProfilesPartialSuccess.from_dict(_value)

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "ExportProfilesServiceResponse":
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
class ExportProfilesPartialSuccess:
    """
    Generated from protobuf message ExportProfilesPartialSuccess
    """

    rejected_profiles: typing.Optional[builtins.int] = 0
    error_message: typing.Optional[builtins.str] = ""

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.rejected_profiles:
            _result["rejectedProfiles"] = _utils.encode_int64(self.rejected_profiles)
        if self.error_message:
            _result["errorMessage"] = self.error_message
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "ExportProfilesPartialSuccess":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            ExportProfilesPartialSuccess instance
        """
        _utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("rejectedProfiles")) is not None:
            _args["rejected_profiles"] = _utils.decode_int64(_value, "rejected_profiles")
        if (_value := data.get("errorMessage")) is not None:
            _utils.validate_type(_value, builtins.str, "error_message")
            _args["error_message"] = _value

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "ExportProfilesPartialSuccess":
        """
        Deserialize from a JSON string or bytes.

        Args:
            data: JSON string or bytes

        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))
