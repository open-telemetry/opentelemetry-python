# @generated by generate_proto_mypy_stubs.py.  Do not edit!
import sys
from google.protobuf.descriptor import (
    Descriptor as google___protobuf___descriptor___Descriptor,
    FileDescriptor as google___protobuf___descriptor___FileDescriptor,
)

from google.protobuf.internal.containers import (
    RepeatedCompositeFieldContainer as google___protobuf___internal___containers___RepeatedCompositeFieldContainer,
)

from google.protobuf.message import (
    Message as google___protobuf___message___Message,
)

from opentelemetry.proto.metrics.v1.metrics_pb2 import (
    ResourceMetrics as opentelemetry___proto___metrics___v1___metrics_pb2___ResourceMetrics,
)

from typing import (
    Iterable as typing___Iterable,
    Optional as typing___Optional,
    Union as typing___Union,
)

from typing_extensions import (
    Literal as typing_extensions___Literal,
)


builtin___bool = bool
builtin___bytes = bytes
builtin___float = float
builtin___int = int
if sys.version_info < (3,):
    builtin___buffer = buffer
    builtin___unicode = unicode


DESCRIPTOR: google___protobuf___descriptor___FileDescriptor = ...

class ExportMetricsServiceRequest(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...

    @property
    def resource_metrics(self) -> google___protobuf___internal___containers___RepeatedCompositeFieldContainer[opentelemetry___proto___metrics___v1___metrics_pb2___ResourceMetrics]: ...

    def __init__(self,
        *,
        resource_metrics : typing___Optional[typing___Iterable[opentelemetry___proto___metrics___v1___metrics_pb2___ResourceMetrics]] = None,
        ) -> None: ...
    if sys.version_info >= (3,):
        @classmethod
        def FromString(cls, s: builtin___bytes) -> ExportMetricsServiceRequest: ...
    else:
        @classmethod
        def FromString(cls, s: typing___Union[builtin___bytes, builtin___buffer, builtin___unicode]) -> ExportMetricsServiceRequest: ...
    def ClearField(self, field_name: typing_extensions___Literal[u"resource_metrics",b"resource_metrics"]) -> None: ...
type___ExportMetricsServiceRequest = ExportMetricsServiceRequest

class ExportMetricsServiceResponse(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...

    def __init__(self,
        ) -> None: ...
    if sys.version_info >= (3,):
        @classmethod
        def FromString(cls, s: builtin___bytes) -> ExportMetricsServiceResponse: ...
    else:
        @classmethod
        def FromString(cls, s: typing___Union[builtin___bytes, builtin___buffer, builtin___unicode]) -> ExportMetricsServiceResponse: ...
type___ExportMetricsServiceResponse = ExportMetricsServiceResponse
