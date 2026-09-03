from opentelemetry.proto._test.common.v1 import common_pb2 as _common_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Resource(_message.Message):
    __slots__ = ("attributes", "dropped_attributes_count", "entity_refs")
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    DROPPED_ATTRIBUTES_COUNT_FIELD_NUMBER: _ClassVar[int]
    ENTITY_REFS_FIELD_NUMBER: _ClassVar[int]
    attributes: _containers.RepeatedCompositeFieldContainer[_common_pb2.KeyValue]
    dropped_attributes_count: int
    entity_refs: _containers.RepeatedCompositeFieldContainer[_common_pb2.EntityRef]
    def __init__(self, attributes: _Optional[_Iterable[_Union[_common_pb2.KeyValue, _Mapping]]] = ..., dropped_attributes_count: _Optional[int] = ..., entity_refs: _Optional[_Iterable[_Union[_common_pb2.EntityRef, _Mapping]]] = ...) -> None: ...
