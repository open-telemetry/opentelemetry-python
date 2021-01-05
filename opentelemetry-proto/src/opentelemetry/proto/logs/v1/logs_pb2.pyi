# @generated by generate_proto_mypy_stubs.py.  Do not edit!
import sys
from google.protobuf.descriptor import (
    Descriptor as google___protobuf___descriptor___Descriptor,
    EnumDescriptor as google___protobuf___descriptor___EnumDescriptor,
    FileDescriptor as google___protobuf___descriptor___FileDescriptor,
)

from google.protobuf.internal.containers import (
    RepeatedCompositeFieldContainer as google___protobuf___internal___containers___RepeatedCompositeFieldContainer,
)

from google.protobuf.internal.enum_type_wrapper import (
    _EnumTypeWrapper as google___protobuf___internal___enum_type_wrapper____EnumTypeWrapper,
)

from google.protobuf.message import (
    Message as google___protobuf___message___Message,
)

from opentelemetry.proto.common.v1.common_pb2 import (
    AnyValue as opentelemetry___proto___common___v1___common_pb2___AnyValue,
    InstrumentationLibrary as opentelemetry___proto___common___v1___common_pb2___InstrumentationLibrary,
    KeyValue as opentelemetry___proto___common___v1___common_pb2___KeyValue,
)

from opentelemetry.proto.resource.v1.resource_pb2 import (
    Resource as opentelemetry___proto___resource___v1___resource_pb2___Resource,
)

from typing import (
    Iterable as typing___Iterable,
    NewType as typing___NewType,
    Optional as typing___Optional,
    Text as typing___Text,
    cast as typing___cast,
)

from typing_extensions import Literal as typing_extensions___Literal

builtin___bool = bool
builtin___bytes = bytes
builtin___float = float
builtin___int = int

DESCRIPTOR: google___protobuf___descriptor___FileDescriptor = ...

SeverityNumberValue = typing___NewType("SeverityNumberValue", builtin___int)
type___SeverityNumberValue = SeverityNumberValue
SeverityNumber: _SeverityNumber

class _SeverityNumber(
    google___protobuf___internal___enum_type_wrapper____EnumTypeWrapper[
        SeverityNumberValue
    ]
):
    DESCRIPTOR: google___protobuf___descriptor___EnumDescriptor = ...
    SEVERITY_NUMBER_UNSPECIFIED = typing___cast(SeverityNumberValue, 0)
    SEVERITY_NUMBER_TRACE = typing___cast(SeverityNumberValue, 1)
    SEVERITY_NUMBER_TRACE2 = typing___cast(SeverityNumberValue, 2)
    SEVERITY_NUMBER_TRACE3 = typing___cast(SeverityNumberValue, 3)
    SEVERITY_NUMBER_TRACE4 = typing___cast(SeverityNumberValue, 4)
    SEVERITY_NUMBER_DEBUG = typing___cast(SeverityNumberValue, 5)
    SEVERITY_NUMBER_DEBUG2 = typing___cast(SeverityNumberValue, 6)
    SEVERITY_NUMBER_DEBUG3 = typing___cast(SeverityNumberValue, 7)
    SEVERITY_NUMBER_DEBUG4 = typing___cast(SeverityNumberValue, 8)
    SEVERITY_NUMBER_INFO = typing___cast(SeverityNumberValue, 9)
    SEVERITY_NUMBER_INFO2 = typing___cast(SeverityNumberValue, 10)
    SEVERITY_NUMBER_INFO3 = typing___cast(SeverityNumberValue, 11)
    SEVERITY_NUMBER_INFO4 = typing___cast(SeverityNumberValue, 12)
    SEVERITY_NUMBER_WARN = typing___cast(SeverityNumberValue, 13)
    SEVERITY_NUMBER_WARN2 = typing___cast(SeverityNumberValue, 14)
    SEVERITY_NUMBER_WARN3 = typing___cast(SeverityNumberValue, 15)
    SEVERITY_NUMBER_WARN4 = typing___cast(SeverityNumberValue, 16)
    SEVERITY_NUMBER_ERROR = typing___cast(SeverityNumberValue, 17)
    SEVERITY_NUMBER_ERROR2 = typing___cast(SeverityNumberValue, 18)
    SEVERITY_NUMBER_ERROR3 = typing___cast(SeverityNumberValue, 19)
    SEVERITY_NUMBER_ERROR4 = typing___cast(SeverityNumberValue, 20)
    SEVERITY_NUMBER_FATAL = typing___cast(SeverityNumberValue, 21)
    SEVERITY_NUMBER_FATAL2 = typing___cast(SeverityNumberValue, 22)
    SEVERITY_NUMBER_FATAL3 = typing___cast(SeverityNumberValue, 23)
    SEVERITY_NUMBER_FATAL4 = typing___cast(SeverityNumberValue, 24)

SEVERITY_NUMBER_UNSPECIFIED = typing___cast(SeverityNumberValue, 0)
SEVERITY_NUMBER_TRACE = typing___cast(SeverityNumberValue, 1)
SEVERITY_NUMBER_TRACE2 = typing___cast(SeverityNumberValue, 2)
SEVERITY_NUMBER_TRACE3 = typing___cast(SeverityNumberValue, 3)
SEVERITY_NUMBER_TRACE4 = typing___cast(SeverityNumberValue, 4)
SEVERITY_NUMBER_DEBUG = typing___cast(SeverityNumberValue, 5)
SEVERITY_NUMBER_DEBUG2 = typing___cast(SeverityNumberValue, 6)
SEVERITY_NUMBER_DEBUG3 = typing___cast(SeverityNumberValue, 7)
SEVERITY_NUMBER_DEBUG4 = typing___cast(SeverityNumberValue, 8)
SEVERITY_NUMBER_INFO = typing___cast(SeverityNumberValue, 9)
SEVERITY_NUMBER_INFO2 = typing___cast(SeverityNumberValue, 10)
SEVERITY_NUMBER_INFO3 = typing___cast(SeverityNumberValue, 11)
SEVERITY_NUMBER_INFO4 = typing___cast(SeverityNumberValue, 12)
SEVERITY_NUMBER_WARN = typing___cast(SeverityNumberValue, 13)
SEVERITY_NUMBER_WARN2 = typing___cast(SeverityNumberValue, 14)
SEVERITY_NUMBER_WARN3 = typing___cast(SeverityNumberValue, 15)
SEVERITY_NUMBER_WARN4 = typing___cast(SeverityNumberValue, 16)
SEVERITY_NUMBER_ERROR = typing___cast(SeverityNumberValue, 17)
SEVERITY_NUMBER_ERROR2 = typing___cast(SeverityNumberValue, 18)
SEVERITY_NUMBER_ERROR3 = typing___cast(SeverityNumberValue, 19)
SEVERITY_NUMBER_ERROR4 = typing___cast(SeverityNumberValue, 20)
SEVERITY_NUMBER_FATAL = typing___cast(SeverityNumberValue, 21)
SEVERITY_NUMBER_FATAL2 = typing___cast(SeverityNumberValue, 22)
SEVERITY_NUMBER_FATAL3 = typing___cast(SeverityNumberValue, 23)
SEVERITY_NUMBER_FATAL4 = typing___cast(SeverityNumberValue, 24)
type___SeverityNumber = SeverityNumber

LogRecordFlagsValue = typing___NewType("LogRecordFlagsValue", builtin___int)
type___LogRecordFlagsValue = LogRecordFlagsValue
LogRecordFlags: _LogRecordFlags

class _LogRecordFlags(
    google___protobuf___internal___enum_type_wrapper____EnumTypeWrapper[
        LogRecordFlagsValue
    ]
):
    DESCRIPTOR: google___protobuf___descriptor___EnumDescriptor = ...
    LOG_RECORD_FLAG_UNSPECIFIED = typing___cast(LogRecordFlagsValue, 0)
    LOG_RECORD_FLAG_TRACE_FLAGS_MASK = typing___cast(LogRecordFlagsValue, 255)

LOG_RECORD_FLAG_UNSPECIFIED = typing___cast(LogRecordFlagsValue, 0)
LOG_RECORD_FLAG_TRACE_FLAGS_MASK = typing___cast(LogRecordFlagsValue, 255)
type___LogRecordFlags = LogRecordFlags

class ResourceLogs(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    @property
    def resource(
        self,
    ) -> opentelemetry___proto___resource___v1___resource_pb2___Resource: ...
    @property
    def instrumentation_library_logs(
        self,
    ) -> google___protobuf___internal___containers___RepeatedCompositeFieldContainer[
        type___InstrumentationLibraryLogs
    ]: ...
    def __init__(
        self,
        *,
        resource: typing___Optional[
            opentelemetry___proto___resource___v1___resource_pb2___Resource
        ] = None,
        instrumentation_library_logs: typing___Optional[
            typing___Iterable[type___InstrumentationLibraryLogs]
        ] = None,
    ) -> None: ...
    def HasField(
        self, field_name: typing_extensions___Literal["resource", b"resource"]
    ) -> builtin___bool: ...
    def ClearField(
        self,
        field_name: typing_extensions___Literal[
            "instrumentation_library_logs",
            b"instrumentation_library_logs",
            "resource",
            b"resource",
        ],
    ) -> None: ...

type___ResourceLogs = ResourceLogs

class InstrumentationLibraryLogs(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    @property
    def instrumentation_library(
        self,
    ) -> opentelemetry___proto___common___v1___common_pb2___InstrumentationLibrary: ...
    @property
    def logs(
        self,
    ) -> google___protobuf___internal___containers___RepeatedCompositeFieldContainer[
        type___LogRecord
    ]: ...
    def __init__(
        self,
        *,
        instrumentation_library: typing___Optional[
            opentelemetry___proto___common___v1___common_pb2___InstrumentationLibrary
        ] = None,
        logs: typing___Optional[typing___Iterable[type___LogRecord]] = None,
    ) -> None: ...
    def HasField(
        self,
        field_name: typing_extensions___Literal[
            "instrumentation_library", b"instrumentation_library"
        ],
    ) -> builtin___bool: ...
    def ClearField(
        self,
        field_name: typing_extensions___Literal[
            "instrumentation_library",
            b"instrumentation_library",
            "logs",
            b"logs",
        ],
    ) -> None: ...

type___InstrumentationLibraryLogs = InstrumentationLibraryLogs

class LogRecord(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    time_unix_nano: builtin___int = ...
    severity_number: type___SeverityNumberValue = ...
    severity_text: typing___Text = ...
    name: typing___Text = ...
    dropped_attributes_count: builtin___int = ...
    flags: builtin___int = ...
    trace_id: builtin___bytes = ...
    span_id: builtin___bytes = ...
    @property
    def body(
        self,
    ) -> opentelemetry___proto___common___v1___common_pb2___AnyValue: ...
    @property
    def attributes(
        self,
    ) -> google___protobuf___internal___containers___RepeatedCompositeFieldContainer[
        opentelemetry___proto___common___v1___common_pb2___KeyValue
    ]: ...
    def __init__(
        self,
        *,
        time_unix_nano: typing___Optional[builtin___int] = None,
        severity_number: typing___Optional[type___SeverityNumberValue] = None,
        severity_text: typing___Optional[typing___Text] = None,
        name: typing___Optional[typing___Text] = None,
        body: typing___Optional[
            opentelemetry___proto___common___v1___common_pb2___AnyValue
        ] = None,
        attributes: typing___Optional[
            typing___Iterable[
                opentelemetry___proto___common___v1___common_pb2___KeyValue
            ]
        ] = None,
        dropped_attributes_count: typing___Optional[builtin___int] = None,
        flags: typing___Optional[builtin___int] = None,
        trace_id: typing___Optional[builtin___bytes] = None,
        span_id: typing___Optional[builtin___bytes] = None,
    ) -> None: ...
    def HasField(
        self, field_name: typing_extensions___Literal["body", b"body"]
    ) -> builtin___bool: ...
    def ClearField(
        self,
        field_name: typing_extensions___Literal[
            "attributes",
            b"attributes",
            "body",
            b"body",
            "dropped_attributes_count",
            b"dropped_attributes_count",
            "flags",
            b"flags",
            "name",
            b"name",
            "severity_number",
            b"severity_number",
            "severity_text",
            b"severity_text",
            "span_id",
            b"span_id",
            "time_unix_nano",
            b"time_unix_nano",
            "trace_id",
            b"trace_id",
        ],
    ) -> None: ...

type___LogRecord = LogRecord
