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

# AUTO-GENERATED from "opentelemetry/proto/collector/logs/v1/logs_service.proto"
# DO NOT EDIT MANUALLY

from __future__ import annotations

import json
from typing import Any, Optional, Union, Self
from dataclasses import dataclass, field
from enum import IntEnum

import opentelemetry.proto_json._otlp_json_utils as _utils
import opentelemetry.proto_json.logs.v1.logs

@dataclass(slots=True)
class ExportLogsServiceRequest:
    """
    Generated from protobuf message ExportLogsServiceRequest
    """

    resource_logs: list[opentelemetry.proto_json.logs.v1.logs.ResourceLogs] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result: dict[str, Any] = {}
        if self.resource_logs:
            _result["resourceLogs"] = _utils.serialize_repeated(self.resource_logs, lambda _v: _v.to_dict())
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
            ExportLogsServiceRequest instance
        """
        _utils.validate_type(data, dict, "data")
        _args: dict[str, Any] = {}

        if (_value := data.get("resourceLogs")) is not None:
            _args["resource_logs"] = _utils.deserialize_repeated(_value, lambda _v: opentelemetry.proto_json.logs.v1.logs.ResourceLogs.from_dict(_v), "resource_logs")

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
class ExportLogsServiceResponse:
    """
    Generated from protobuf message ExportLogsServiceResponse
    """

    partial_success: ExportLogsPartialSuccess = None

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result: dict[str, Any] = {}
        if self.partial_success is not None:
            _result["partialSuccess"] = self.partial_success.to_dict()
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
            ExportLogsServiceResponse instance
        """
        _utils.validate_type(data, dict, "data")
        _args: dict[str, Any] = {}

        if (_value := data.get("partialSuccess")) is not None:
            _args["partial_success"] = ExportLogsPartialSuccess.from_dict(_value)

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
class ExportLogsPartialSuccess:
    """
    Generated from protobuf message ExportLogsPartialSuccess
    """

    rejected_log_records: int = 0
    error_message: str = ''

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result: dict[str, Any] = {}
        if self.rejected_log_records != 0:
            _result["rejectedLogRecords"] = _utils.encode_int64(self.rejected_log_records)
        if self.error_message != '':
            _result["errorMessage"] = self.error_message
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
            ExportLogsPartialSuccess instance
        """
        _utils.validate_type(data, dict, "data")
        _args: dict[str, Any] = {}

        if (_value := data.get("rejectedLogRecords")) is not None:
            _args["rejected_log_records"] = _utils.parse_int64(_value, "rejected_log_records")
        if (_value := data.get("errorMessage")) is not None:
            _utils.validate_type(_value, str, "error_message")
            _args["error_message"] = _value

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