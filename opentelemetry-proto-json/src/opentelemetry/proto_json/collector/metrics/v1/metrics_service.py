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

# AUTO-GENERATED from "opentelemetry/proto/collector/metrics/v1/metrics_service.proto"
# DO NOT EDIT MANUALLY

from __future__ import annotations

import json
from typing import Any, Optional, Union, Self
from dataclasses import dataclass, field
from enum import IntEnum

import opentelemetry.proto_json._otlp_json_utils as _utils
import opentelemetry.proto_json.metrics.v1.metrics

@dataclass(slots=True)
class ExportMetricsServiceRequest:
    """
    Generated from protobuf message ExportMetricsServiceRequest
    """

    resource_metrics: list[opentelemetry.proto_json.metrics.v1.metrics.ResourceMetrics] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result: dict[str, Any] = {}
        if self.resource_metrics:
            _result["resourceMetrics"] = _utils.serialize_repeated(self.resource_metrics, lambda _v: _v.to_dict())
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
            ExportMetricsServiceRequest instance
        """
        _args: dict[str, Any] = {}
        if (_value := data.get("resourceMetrics")) is not None:
            _args["resource_metrics"] = _utils.deserialize_repeated(_value, lambda _v: opentelemetry.proto_json.metrics.v1.metrics.ResourceMetrics.from_dict(_v))
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
class ExportMetricsServiceResponse:
    """
    Generated from protobuf message ExportMetricsServiceResponse
    """

    partial_success: ExportMetricsPartialSuccess = None

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
            ExportMetricsServiceResponse instance
        """
        _args: dict[str, Any] = {}
        if (_value := data.get("partialSuccess")) is not None:
            _args["partial_success"] = ExportMetricsPartialSuccess.from_dict(_value)
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
class ExportMetricsPartialSuccess:
    """
    Generated from protobuf message ExportMetricsPartialSuccess
    """

    rejected_data_points: int = 0
    error_message: str = ''

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result: dict[str, Any] = {}
        if self.rejected_data_points != 0:
            _result["rejectedDataPoints"] = _utils.encode_int64(self.rejected_data_points)
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
            ExportMetricsPartialSuccess instance
        """
        _args: dict[str, Any] = {}
        if (_value := data.get("rejectedDataPoints")) is not None:
            _args["rejected_data_points"] = _utils.parse_int64(_value)
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