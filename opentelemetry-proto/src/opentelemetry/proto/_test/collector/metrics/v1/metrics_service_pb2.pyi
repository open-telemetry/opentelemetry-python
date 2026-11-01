from opentelemetry.proto._test.metrics.v1 import metrics_pb2 as _metrics_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ExportMetricsServiceRequest(_message.Message):
    __slots__ = ("resource_metrics",)
    RESOURCE_METRICS_FIELD_NUMBER: _ClassVar[int]
    resource_metrics: _containers.RepeatedCompositeFieldContainer[_metrics_pb2.ResourceMetrics]
    def __init__(self, resource_metrics: _Optional[_Iterable[_Union[_metrics_pb2.ResourceMetrics, _Mapping]]] = ...) -> None: ...

class ExportMetricsServiceResponse(_message.Message):
    __slots__ = ("partial_success",)
    PARTIAL_SUCCESS_FIELD_NUMBER: _ClassVar[int]
    partial_success: ExportMetricsPartialSuccess
    def __init__(self, partial_success: _Optional[_Union[ExportMetricsPartialSuccess, _Mapping]] = ...) -> None: ...

class ExportMetricsPartialSuccess(_message.Message):
    __slots__ = ("rejected_data_points", "error_message")
    REJECTED_DATA_POINTS_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    rejected_data_points: int
    error_message: str
    def __init__(self, rejected_data_points: _Optional[int] = ..., error_message: _Optional[str] = ...) -> None: ...
