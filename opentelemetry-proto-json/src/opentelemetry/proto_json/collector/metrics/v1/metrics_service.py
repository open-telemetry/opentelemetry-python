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

import builtins
import dataclasses
import functools
import sys
import typing

if sys.version_info >= (3, 10):
    _dataclass = functools.partial(dataclasses.dataclass, slots=True)
else:
    _dataclass = dataclasses.dataclass

import opentelemetry.proto_json._json_codec
import opentelemetry.proto_json.metrics.v1.metrics


@typing.final
@_dataclass
class ExportMetricsServiceRequest(opentelemetry.proto_json._json_codec.JsonMessage):
    """
    Generated from protobuf message ExportMetricsServiceRequest
    """

    resource_metrics: builtins.list[opentelemetry.proto_json.metrics.v1.metrics.ResourceMetrics] = dataclasses.field(default_factory=builtins.list)

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.resource_metrics:
            _result["resourceMetrics"] = opentelemetry.proto_json._json_codec.encode_repeated(self.resource_metrics, lambda _v: _v.to_dict())
        return _result

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "ExportMetricsServiceRequest":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            ExportMetricsServiceRequest instance
        """
        opentelemetry.proto_json._json_codec.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("resourceMetrics")) is not None:
            _args["resource_metrics"] = opentelemetry.proto_json._json_codec.decode_repeated(_value, lambda _v: opentelemetry.proto_json.metrics.v1.metrics.ResourceMetrics.from_dict(_v), "resource_metrics")

        return cls(**_args)


@typing.final
@_dataclass
class ExportMetricsServiceResponse(opentelemetry.proto_json._json_codec.JsonMessage):
    """
    Generated from protobuf message ExportMetricsServiceResponse
    """

    partial_success: typing.Optional[ExportMetricsPartialSuccess] = None

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

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "ExportMetricsServiceResponse":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            ExportMetricsServiceResponse instance
        """
        opentelemetry.proto_json._json_codec.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("partialSuccess")) is not None:
            _args["partial_success"] = ExportMetricsPartialSuccess.from_dict(_value)

        return cls(**_args)


@typing.final
@_dataclass
class ExportMetricsPartialSuccess(opentelemetry.proto_json._json_codec.JsonMessage):
    """
    Generated from protobuf message ExportMetricsPartialSuccess
    """

    rejected_data_points: typing.Optional[builtins.int] = 0
    error_message: typing.Optional[builtins.str] = ""

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.rejected_data_points:
            _result["rejectedDataPoints"] = opentelemetry.proto_json._json_codec.encode_int64(self.rejected_data_points)
        if self.error_message:
            _result["errorMessage"] = self.error_message
        return _result

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "ExportMetricsPartialSuccess":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            ExportMetricsPartialSuccess instance
        """
        opentelemetry.proto_json._json_codec.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("rejectedDataPoints")) is not None:
            _args["rejected_data_points"] = opentelemetry.proto_json._json_codec.decode_int64(_value, "rejected_data_points")
        if (_value := data.get("errorMessage")) is not None:
            opentelemetry.proto_json._json_codec.validate_type(_value, builtins.str, "error_message")
            _args["error_message"] = _value

        return cls(**_args)
