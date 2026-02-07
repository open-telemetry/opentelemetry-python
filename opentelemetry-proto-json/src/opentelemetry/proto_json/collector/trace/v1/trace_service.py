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

# AUTO-GENERATED from "opentelemetry/proto/collector/trace/v1/trace_service.proto"
# DO NOT EDIT MANUALLY

from __future__ import annotations

import json
from typing import Any, Optional, Union, Self
from dataclasses import dataclass, field
from enum import IntEnum

import opentelemetry.proto_json._otlp_json_utils as _utils
import opentelemetry.proto_json.trace.v1.trace

@dataclass(slots=True)
class ExportTraceServiceRequest:
    """
    Generated from protobuf message ExportTraceServiceRequest
    """

    resource_spans: list[opentelemetry.proto_json.trace.v1.trace.ResourceSpans] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result: dict[str, Any] = {}
        if self.resource_spans:
            _result["resourceSpans"] = _utils.serialize_repeated(self.resource_spans, lambda _v: _v.to_dict())
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
            ExportTraceServiceRequest instance
        """
        _args: dict[str, Any] = {}

        if (_value := data.get("resourceSpans")) is not None:
            _args["resource_spans"] = _utils.deserialize_repeated(_value, lambda _v: opentelemetry.proto_json.trace.v1.trace.ResourceSpans.from_dict(_v))

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
class ExportTraceServiceResponse:
    """
    Generated from protobuf message ExportTraceServiceResponse
    """

    partial_success: ExportTracePartialSuccess = None

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
            ExportTraceServiceResponse instance
        """
        _args: dict[str, Any] = {}

        if (_value := data.get("partialSuccess")) is not None:
            _args["partial_success"] = ExportTracePartialSuccess.from_dict(_value)

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
class ExportTracePartialSuccess:
    """
    Generated from protobuf message ExportTracePartialSuccess
    """

    rejected_spans: int = 0
    error_message: str = ''

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result: dict[str, Any] = {}
        if self.rejected_spans != 0:
            _result["rejectedSpans"] = _utils.encode_int64(self.rejected_spans)
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
            ExportTracePartialSuccess instance
        """
        _args: dict[str, Any] = {}

        if (_value := data.get("rejectedSpans")) is not None:
            _args["rejected_spans"] = _utils.parse_int64(_value)
        if (_value := data.get("errorMessage")) is not None:
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