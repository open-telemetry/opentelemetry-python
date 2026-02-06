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

import json
from typing import Any, Optional, Union, Self
from dataclasses import dataclass, field
from enum import IntEnum

import opentelemetry.proto_json._otlp_json_utils as _utils
import opentelemetry.proto_json.common.v1.common
import opentelemetry.proto_json.resource.v1.resource

class SeverityNumber(IntEnum):
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

class LogRecordFlags(IntEnum):
    """
    Generated from protobuf enum LogRecordFlags
    """

    LOG_RECORD_FLAGS_DO_NOT_USE = 0
    LOG_RECORD_FLAGS_TRACE_FLAGS_MASK = 255

@dataclass(slots=True)
class LogsData:
    """
    Generated from protobuf message LogsData
    """

    resource_logs: list[ResourceLogs] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        res: dict[str, Any] = {}
        if self.resource_logs:
            res["resourceLogs"] = _utils.serialize_repeated(self.resource_logs, lambda v: v.to_dict())
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
            LogsData instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("resourceLogs")) is not None:
            args["resource_logs"] = _utils.deserialize_repeated(val, lambda v: ResourceLogs.from_dict(v))
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
class ResourceLogs:
    """
    Generated from protobuf message ResourceLogs
    """

    resource: opentelemetry.proto_json.resource.v1.resource.Resource = None
    scope_logs: list[ScopeLogs] = field(default_factory=list)
    schema_url: str = ''

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        res: dict[str, Any] = {}
        if self.resource is not None:
            res["resource"] = self.resource.to_dict()
        if self.scope_logs:
            res["scopeLogs"] = _utils.serialize_repeated(self.scope_logs, lambda v: v.to_dict())
        if self.schema_url != '':
            res["schemaUrl"] = self.schema_url
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
            ResourceLogs instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("resource")) is not None:
            args["resource"] = opentelemetry.proto_json.resource.v1.resource.Resource.from_dict(val)
        if (val := data.get("scopeLogs")) is not None:
            args["scope_logs"] = _utils.deserialize_repeated(val, lambda v: ScopeLogs.from_dict(v))
        if (val := data.get("schemaUrl")) is not None:
            args["schema_url"] = val
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
class ScopeLogs:
    """
    Generated from protobuf message ScopeLogs
    """

    scope: opentelemetry.proto_json.common.v1.common.InstrumentationScope = None
    log_records: list[LogRecord] = field(default_factory=list)
    schema_url: str = ''

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        res: dict[str, Any] = {}
        if self.scope is not None:
            res["scope"] = self.scope.to_dict()
        if self.log_records:
            res["logRecords"] = _utils.serialize_repeated(self.log_records, lambda v: v.to_dict())
        if self.schema_url != '':
            res["schemaUrl"] = self.schema_url
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
            ScopeLogs instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("scope")) is not None:
            args["scope"] = opentelemetry.proto_json.common.v1.common.InstrumentationScope.from_dict(val)
        if (val := data.get("logRecords")) is not None:
            args["log_records"] = _utils.deserialize_repeated(val, lambda v: LogRecord.from_dict(v))
        if (val := data.get("schemaUrl")) is not None:
            args["schema_url"] = val
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
class LogRecord:
    """
    Generated from protobuf message LogRecord
    """

    time_unix_nano: int = 0
    observed_time_unix_nano: int = 0
    severity_number: SeverityNumber = 0
    severity_text: str = ''
    body: opentelemetry.proto_json.common.v1.common.AnyValue = None
    attributes: list[opentelemetry.proto_json.common.v1.common.KeyValue] = field(default_factory=list)
    dropped_attributes_count: int = 0
    flags: int = 0
    trace_id: bytes = b''
    span_id: bytes = b''
    event_name: str = ''

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        res: dict[str, Any] = {}
        if self.time_unix_nano != 0:
            res["timeUnixNano"] = _utils.encode_int64(self.time_unix_nano)
        if self.observed_time_unix_nano != 0:
            res["observedTimeUnixNano"] = _utils.encode_int64(self.observed_time_unix_nano)
        if self.severity_number != None:
            res["severityNumber"] = int(self.severity_number)
        if self.severity_text != '':
            res["severityText"] = self.severity_text
        if self.body is not None:
            res["body"] = self.body.to_dict()
        if self.attributes:
            res["attributes"] = _utils.serialize_repeated(self.attributes, lambda v: v.to_dict())
        if self.dropped_attributes_count != 0:
            res["droppedAttributesCount"] = self.dropped_attributes_count
        if self.flags != 0:
            res["flags"] = self.flags
        if self.trace_id != b'':
            res["traceId"] = _utils.encode_hex(self.trace_id)
        if self.span_id != b'':
            res["spanId"] = _utils.encode_hex(self.span_id)
        if self.event_name != '':
            res["eventName"] = self.event_name
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
            LogRecord instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("timeUnixNano")) is not None:
            args["time_unix_nano"] = _utils.parse_int64(val)
        if (val := data.get("observedTimeUnixNano")) is not None:
            args["observed_time_unix_nano"] = _utils.parse_int64(val)
        if (val := data.get("severityNumber")) is not None:
            args["severity_number"] = SeverityNumber(val)
        if (val := data.get("severityText")) is not None:
            args["severity_text"] = val
        if (val := data.get("body")) is not None:
            args["body"] = opentelemetry.proto_json.common.v1.common.AnyValue.from_dict(val)
        if (val := data.get("attributes")) is not None:
            args["attributes"] = _utils.deserialize_repeated(val, lambda v: opentelemetry.proto_json.common.v1.common.KeyValue.from_dict(v))
        if (val := data.get("droppedAttributesCount")) is not None:
            args["dropped_attributes_count"] = val
        if (val := data.get("flags")) is not None:
            args["flags"] = val
        if (val := data.get("traceId")) is not None:
            args["trace_id"] = _utils.decode_hex(val)
        if (val := data.get("spanId")) is not None:
            args["span_id"] = _utils.decode_hex(val)
        if (val := data.get("eventName")) is not None:
            args["event_name"] = val
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