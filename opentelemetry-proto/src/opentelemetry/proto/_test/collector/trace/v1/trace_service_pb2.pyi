from opentelemetry.proto._test.trace.v1 import trace_pb2 as _trace_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ExportTraceServiceRequest(_message.Message):
    __slots__ = ("resource_spans",)
    RESOURCE_SPANS_FIELD_NUMBER: _ClassVar[int]
    resource_spans: _containers.RepeatedCompositeFieldContainer[_trace_pb2.ResourceSpans]
    def __init__(self, resource_spans: _Optional[_Iterable[_Union[_trace_pb2.ResourceSpans, _Mapping]]] = ...) -> None: ...

class ExportTraceServiceResponse(_message.Message):
    __slots__ = ("partial_success",)
    PARTIAL_SUCCESS_FIELD_NUMBER: _ClassVar[int]
    partial_success: ExportTracePartialSuccess
    def __init__(self, partial_success: _Optional[_Union[ExportTracePartialSuccess, _Mapping]] = ...) -> None: ...

class ExportTracePartialSuccess(_message.Message):
    __slots__ = ("rejected_spans", "error_message")
    REJECTED_SPANS_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    rejected_spans: int
    error_message: str
    def __init__(self, rejected_spans: _Optional[int] = ..., error_message: _Optional[str] = ...) -> None: ...
