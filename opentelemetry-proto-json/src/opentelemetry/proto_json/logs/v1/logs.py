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

# AUTO-GENERATED from "opentelemetry/proto/logs/v1/logs.proto"
# DO NOT EDIT MANUALLY

from __future__ import annotations

import builtins
import dataclasses
import enum
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
import opentelemetry.proto_json.resource.v1.resource


@typing.final
class SeverityNumber(enum.IntEnum):
    """
    Generated from protobuf enum SeverityNumber
    """

    SEVERITY_NUMBER_UNSPECIFIED = 0
    SEVERITY_NUMBER_TRACE = 1
    SEVERITY_NUMBER_TRACE2 = 2
    SEVERITY_NUMBER_TRACE3 = 3
    SEVERITY_NUMBER_TRACE4 = 4
    SEVERITY_NUMBER_DEBUG = 5
    SEVERITY_NUMBER_DEBUG2 = 6
    SEVERITY_NUMBER_DEBUG3 = 7
    SEVERITY_NUMBER_DEBUG4 = 8
    SEVERITY_NUMBER_INFO = 9
    SEVERITY_NUMBER_INFO2 = 10
    SEVERITY_NUMBER_INFO3 = 11
    SEVERITY_NUMBER_INFO4 = 12
    SEVERITY_NUMBER_WARN = 13
    SEVERITY_NUMBER_WARN2 = 14
    SEVERITY_NUMBER_WARN3 = 15
    SEVERITY_NUMBER_WARN4 = 16
    SEVERITY_NUMBER_ERROR = 17
    SEVERITY_NUMBER_ERROR2 = 18
    SEVERITY_NUMBER_ERROR3 = 19
    SEVERITY_NUMBER_ERROR4 = 20
    SEVERITY_NUMBER_FATAL = 21
    SEVERITY_NUMBER_FATAL2 = 22
    SEVERITY_NUMBER_FATAL3 = 23
    SEVERITY_NUMBER_FATAL4 = 24

@typing.final
class LogRecordFlags(enum.IntEnum):
    """
    Generated from protobuf enum LogRecordFlags
    """

    LOG_RECORD_FLAGS_DO_NOT_USE = 0
    LOG_RECORD_FLAGS_TRACE_FLAGS_MASK = 255

@typing.final
@_dataclass
class LogsData:
    """
    Generated from protobuf message LogsData
    """

    resource_logs: builtins.list[ResourceLogs] = dataclasses.field(default_factory=builtins.list)

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.resource_logs:
            _result["resourceLogs"] = _utils.serialize_repeated(self.resource_logs, lambda _v: _v.to_dict())
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "LogsData":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            LogsData instance
        """
        _utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("resourceLogs")) is not None:
            _args["resource_logs"] = _utils.deserialize_repeated(_value, lambda _v: ResourceLogs.from_dict(_v), "resource_logs")

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "LogsData":
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
class ResourceLogs:
    """
    Generated from protobuf message ResourceLogs
    """

    resource: typing.Optional[opentelemetry.proto_json.resource.v1.resource.Resource] = None
    scope_logs: builtins.list[ScopeLogs] = dataclasses.field(default_factory=builtins.list)
    schema_url: typing.Optional[builtins.str] = ""

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.resource:
            _result["resource"] = self.resource.to_dict()
        if self.scope_logs:
            _result["scopeLogs"] = _utils.serialize_repeated(self.scope_logs, lambda _v: _v.to_dict())
        if self.schema_url:
            _result["schemaUrl"] = self.schema_url
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "ResourceLogs":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            ResourceLogs instance
        """
        _utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("resource")) is not None:
            _args["resource"] = opentelemetry.proto_json.resource.v1.resource.Resource.from_dict(_value)
        if (_value := data.get("scopeLogs")) is not None:
            _args["scope_logs"] = _utils.deserialize_repeated(_value, lambda _v: ScopeLogs.from_dict(_v), "scope_logs")
        if (_value := data.get("schemaUrl")) is not None:
            _utils.validate_type(_value, builtins.str, "schema_url")
            _args["schema_url"] = _value

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "ResourceLogs":
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
class ScopeLogs:
    """
    Generated from protobuf message ScopeLogs
    """

    scope: typing.Optional[opentelemetry.proto_json.common.v1.common.InstrumentationScope] = None
    log_records: builtins.list[LogRecord] = dataclasses.field(default_factory=builtins.list)
    schema_url: typing.Optional[builtins.str] = ""

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.scope:
            _result["scope"] = self.scope.to_dict()
        if self.log_records:
            _result["logRecords"] = _utils.serialize_repeated(self.log_records, lambda _v: _v.to_dict())
        if self.schema_url:
            _result["schemaUrl"] = self.schema_url
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "ScopeLogs":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            ScopeLogs instance
        """
        _utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("scope")) is not None:
            _args["scope"] = opentelemetry.proto_json.common.v1.common.InstrumentationScope.from_dict(_value)
        if (_value := data.get("logRecords")) is not None:
            _args["log_records"] = _utils.deserialize_repeated(_value, lambda _v: LogRecord.from_dict(_v), "log_records")
        if (_value := data.get("schemaUrl")) is not None:
            _utils.validate_type(_value, builtins.str, "schema_url")
            _args["schema_url"] = _value

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "ScopeLogs":
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
class LogRecord:
    """
    Generated from protobuf message LogRecord
    """

    time_unix_nano: typing.Optional[builtins.int] = 0
    observed_time_unix_nano: typing.Optional[builtins.int] = 0
    severity_number: typing.Union[SeverityNumber, builtins.int, None] = 0
    severity_text: typing.Optional[builtins.str] = ""
    body: typing.Optional[opentelemetry.proto_json.common.v1.common.AnyValue] = None
    attributes: builtins.list[opentelemetry.proto_json.common.v1.common.KeyValue] = dataclasses.field(default_factory=builtins.list)
    dropped_attributes_count: typing.Optional[builtins.int] = 0
    flags: typing.Optional[builtins.int] = 0
    trace_id: typing.Optional[builtins.bytes] = b""
    span_id: typing.Optional[builtins.bytes] = b""
    event_name: typing.Optional[builtins.str] = ""

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.time_unix_nano:
            _result["timeUnixNano"] = _utils.encode_int64(self.time_unix_nano)
        if self.observed_time_unix_nano:
            _result["observedTimeUnixNano"] = _utils.encode_int64(self.observed_time_unix_nano)
        if self.severity_number:
            _result["severityNumber"] = builtins.int(self.severity_number)
        if self.severity_text:
            _result["severityText"] = self.severity_text
        if self.body:
            _result["body"] = self.body.to_dict()
        if self.attributes:
            _result["attributes"] = _utils.serialize_repeated(self.attributes, lambda _v: _v.to_dict())
        if self.dropped_attributes_count:
            _result["droppedAttributesCount"] = self.dropped_attributes_count
        if self.flags:
            _result["flags"] = self.flags
        if self.trace_id:
            _result["traceId"] = _utils.encode_hex(self.trace_id)
        if self.span_id:
            _result["spanId"] = _utils.encode_hex(self.span_id)
        if self.event_name:
            _result["eventName"] = self.event_name
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "LogRecord":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            LogRecord instance
        """
        _utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("timeUnixNano")) is not None:
            _args["time_unix_nano"] = _utils.parse_int64(_value, "time_unix_nano")
        if (_value := data.get("observedTimeUnixNano")) is not None:
            _args["observed_time_unix_nano"] = _utils.parse_int64(_value, "observed_time_unix_nano")
        if (_value := data.get("severityNumber")) is not None:
            _utils.validate_type(_value, builtins.int, "severity_number")
            _args["severity_number"] = SeverityNumber(_value)
        if (_value := data.get("severityText")) is not None:
            _utils.validate_type(_value, builtins.str, "severity_text")
            _args["severity_text"] = _value
        if (_value := data.get("body")) is not None:
            _args["body"] = opentelemetry.proto_json.common.v1.common.AnyValue.from_dict(_value)
        if (_value := data.get("attributes")) is not None:
            _args["attributes"] = _utils.deserialize_repeated(_value, lambda _v: opentelemetry.proto_json.common.v1.common.KeyValue.from_dict(_v), "attributes")
        if (_value := data.get("droppedAttributesCount")) is not None:
            _utils.validate_type(_value, builtins.int, "dropped_attributes_count")
            _args["dropped_attributes_count"] = _value
        if (_value := data.get("flags")) is not None:
            _utils.validate_type(_value, builtins.int, "flags")
            _args["flags"] = _value
        if (_value := data.get("traceId")) is not None:
            _args["trace_id"] = _utils.decode_hex(_value, "trace_id")
        if (_value := data.get("spanId")) is not None:
            _args["span_id"] = _utils.decode_hex(_value, "span_id")
        if (_value := data.get("eventName")) is not None:
            _utils.validate_type(_value, builtins.str, "event_name")
            _args["event_name"] = _value

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "LogRecord":
        """
        Deserialize from a JSON string or bytes.

        Args:
            data: JSON string or bytes

        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))
