from opentelemetry.proto._test.common.v1 import common_pb2 as _common_pb2
from opentelemetry.proto._test.resource.v1 import resource_pb2 as _resource_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class SeverityNumber(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SEVERITY_NUMBER_UNSPECIFIED: _ClassVar[SeverityNumber]
    SEVERITY_NUMBER_TRACE: _ClassVar[SeverityNumber]
    SEVERITY_NUMBER_TRACE2: _ClassVar[SeverityNumber]
    SEVERITY_NUMBER_TRACE3: _ClassVar[SeverityNumber]
    SEVERITY_NUMBER_TRACE4: _ClassVar[SeverityNumber]
    SEVERITY_NUMBER_DEBUG: _ClassVar[SeverityNumber]
    SEVERITY_NUMBER_DEBUG2: _ClassVar[SeverityNumber]
    SEVERITY_NUMBER_DEBUG3: _ClassVar[SeverityNumber]
    SEVERITY_NUMBER_DEBUG4: _ClassVar[SeverityNumber]
    SEVERITY_NUMBER_INFO: _ClassVar[SeverityNumber]
    SEVERITY_NUMBER_INFO2: _ClassVar[SeverityNumber]
    SEVERITY_NUMBER_INFO3: _ClassVar[SeverityNumber]
    SEVERITY_NUMBER_INFO4: _ClassVar[SeverityNumber]
    SEVERITY_NUMBER_WARN: _ClassVar[SeverityNumber]
    SEVERITY_NUMBER_WARN2: _ClassVar[SeverityNumber]
    SEVERITY_NUMBER_WARN3: _ClassVar[SeverityNumber]
    SEVERITY_NUMBER_WARN4: _ClassVar[SeverityNumber]
    SEVERITY_NUMBER_ERROR: _ClassVar[SeverityNumber]
    SEVERITY_NUMBER_ERROR2: _ClassVar[SeverityNumber]
    SEVERITY_NUMBER_ERROR3: _ClassVar[SeverityNumber]
    SEVERITY_NUMBER_ERROR4: _ClassVar[SeverityNumber]
    SEVERITY_NUMBER_FATAL: _ClassVar[SeverityNumber]
    SEVERITY_NUMBER_FATAL2: _ClassVar[SeverityNumber]
    SEVERITY_NUMBER_FATAL3: _ClassVar[SeverityNumber]
    SEVERITY_NUMBER_FATAL4: _ClassVar[SeverityNumber]

class LogRecordFlags(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    LOG_RECORD_FLAGS_DO_NOT_USE: _ClassVar[LogRecordFlags]
    LOG_RECORD_FLAGS_TRACE_FLAGS_MASK: _ClassVar[LogRecordFlags]
SEVERITY_NUMBER_UNSPECIFIED: SeverityNumber
SEVERITY_NUMBER_TRACE: SeverityNumber
SEVERITY_NUMBER_TRACE2: SeverityNumber
SEVERITY_NUMBER_TRACE3: SeverityNumber
SEVERITY_NUMBER_TRACE4: SeverityNumber
SEVERITY_NUMBER_DEBUG: SeverityNumber
SEVERITY_NUMBER_DEBUG2: SeverityNumber
SEVERITY_NUMBER_DEBUG3: SeverityNumber
SEVERITY_NUMBER_DEBUG4: SeverityNumber
SEVERITY_NUMBER_INFO: SeverityNumber
SEVERITY_NUMBER_INFO2: SeverityNumber
SEVERITY_NUMBER_INFO3: SeverityNumber
SEVERITY_NUMBER_INFO4: SeverityNumber
SEVERITY_NUMBER_WARN: SeverityNumber
SEVERITY_NUMBER_WARN2: SeverityNumber
SEVERITY_NUMBER_WARN3: SeverityNumber
SEVERITY_NUMBER_WARN4: SeverityNumber
SEVERITY_NUMBER_ERROR: SeverityNumber
SEVERITY_NUMBER_ERROR2: SeverityNumber
SEVERITY_NUMBER_ERROR3: SeverityNumber
SEVERITY_NUMBER_ERROR4: SeverityNumber
SEVERITY_NUMBER_FATAL: SeverityNumber
SEVERITY_NUMBER_FATAL2: SeverityNumber
SEVERITY_NUMBER_FATAL3: SeverityNumber
SEVERITY_NUMBER_FATAL4: SeverityNumber
LOG_RECORD_FLAGS_DO_NOT_USE: LogRecordFlags
LOG_RECORD_FLAGS_TRACE_FLAGS_MASK: LogRecordFlags

class LogsData(_message.Message):
    __slots__ = ("resource_logs",)
    RESOURCE_LOGS_FIELD_NUMBER: _ClassVar[int]
    resource_logs: _containers.RepeatedCompositeFieldContainer[ResourceLogs]
    def __init__(self, resource_logs: _Optional[_Iterable[_Union[ResourceLogs, _Mapping]]] = ...) -> None: ...

class ResourceLogs(_message.Message):
    __slots__ = ("resource", "scope_logs", "schema_url")
    RESOURCE_FIELD_NUMBER: _ClassVar[int]
    SCOPE_LOGS_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_URL_FIELD_NUMBER: _ClassVar[int]
    resource: _resource_pb2.Resource
    scope_logs: _containers.RepeatedCompositeFieldContainer[ScopeLogs]
    schema_url: str
    def __init__(self, resource: _Optional[_Union[_resource_pb2.Resource, _Mapping]] = ..., scope_logs: _Optional[_Iterable[_Union[ScopeLogs, _Mapping]]] = ..., schema_url: _Optional[str] = ...) -> None: ...

class ScopeLogs(_message.Message):
    __slots__ = ("scope", "log_records", "schema_url")
    SCOPE_FIELD_NUMBER: _ClassVar[int]
    LOG_RECORDS_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_URL_FIELD_NUMBER: _ClassVar[int]
    scope: _common_pb2.InstrumentationScope
    log_records: _containers.RepeatedCompositeFieldContainer[LogRecord]
    schema_url: str
    def __init__(self, scope: _Optional[_Union[_common_pb2.InstrumentationScope, _Mapping]] = ..., log_records: _Optional[_Iterable[_Union[LogRecord, _Mapping]]] = ..., schema_url: _Optional[str] = ...) -> None: ...

class LogRecord(_message.Message):
    __slots__ = ("time_unix_nano", "observed_time_unix_nano", "severity_number", "severity_text", "body", "attributes", "dropped_attributes_count", "flags", "trace_id", "span_id", "event_name")
    TIME_UNIX_NANO_FIELD_NUMBER: _ClassVar[int]
    OBSERVED_TIME_UNIX_NANO_FIELD_NUMBER: _ClassVar[int]
    SEVERITY_NUMBER_FIELD_NUMBER: _ClassVar[int]
    SEVERITY_TEXT_FIELD_NUMBER: _ClassVar[int]
    BODY_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    DROPPED_ATTRIBUTES_COUNT_FIELD_NUMBER: _ClassVar[int]
    FLAGS_FIELD_NUMBER: _ClassVar[int]
    TRACE_ID_FIELD_NUMBER: _ClassVar[int]
    SPAN_ID_FIELD_NUMBER: _ClassVar[int]
    EVENT_NAME_FIELD_NUMBER: _ClassVar[int]
    time_unix_nano: int
    observed_time_unix_nano: int
    severity_number: SeverityNumber
    severity_text: str
    body: _common_pb2.AnyValue
    attributes: _containers.RepeatedCompositeFieldContainer[_common_pb2.KeyValue]
    dropped_attributes_count: int
    flags: int
    trace_id: bytes
    span_id: bytes
    event_name: str
    def __init__(self, time_unix_nano: _Optional[int] = ..., observed_time_unix_nano: _Optional[int] = ..., severity_number: _Optional[_Union[SeverityNumber, str]] = ..., severity_text: _Optional[str] = ..., body: _Optional[_Union[_common_pb2.AnyValue, _Mapping]] = ..., attributes: _Optional[_Iterable[_Union[_common_pb2.KeyValue, _Mapping]]] = ..., dropped_attributes_count: _Optional[int] = ..., flags: _Optional[int] = ..., trace_id: _Optional[bytes] = ..., span_id: _Optional[bytes] = ..., event_name: _Optional[str] = ...) -> None: ...
