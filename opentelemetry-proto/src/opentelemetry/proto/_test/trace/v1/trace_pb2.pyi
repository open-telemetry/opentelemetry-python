from opentelemetry.proto._test.common.v1 import common_pb2 as _common_pb2
from opentelemetry.proto._test.resource.v1 import resource_pb2 as _resource_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class SpanFlags(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SPAN_FLAGS_DO_NOT_USE: _ClassVar[SpanFlags]
    SPAN_FLAGS_TRACE_FLAGS_MASK: _ClassVar[SpanFlags]
    SPAN_FLAGS_CONTEXT_HAS_IS_REMOTE_MASK: _ClassVar[SpanFlags]
    SPAN_FLAGS_CONTEXT_IS_REMOTE_MASK: _ClassVar[SpanFlags]
SPAN_FLAGS_DO_NOT_USE: SpanFlags
SPAN_FLAGS_TRACE_FLAGS_MASK: SpanFlags
SPAN_FLAGS_CONTEXT_HAS_IS_REMOTE_MASK: SpanFlags
SPAN_FLAGS_CONTEXT_IS_REMOTE_MASK: SpanFlags

class TracesData(_message.Message):
    __slots__ = ("resource_spans",)
    RESOURCE_SPANS_FIELD_NUMBER: _ClassVar[int]
    resource_spans: _containers.RepeatedCompositeFieldContainer[ResourceSpans]
    def __init__(self, resource_spans: _Optional[_Iterable[_Union[ResourceSpans, _Mapping]]] = ...) -> None: ...

class ResourceSpans(_message.Message):
    __slots__ = ("resource", "scope_spans", "schema_url")
    RESOURCE_FIELD_NUMBER: _ClassVar[int]
    SCOPE_SPANS_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_URL_FIELD_NUMBER: _ClassVar[int]
    resource: _resource_pb2.Resource
    scope_spans: _containers.RepeatedCompositeFieldContainer[ScopeSpans]
    schema_url: str
    def __init__(self, resource: _Optional[_Union[_resource_pb2.Resource, _Mapping]] = ..., scope_spans: _Optional[_Iterable[_Union[ScopeSpans, _Mapping]]] = ..., schema_url: _Optional[str] = ...) -> None: ...

class ScopeSpans(_message.Message):
    __slots__ = ("scope", "spans", "schema_url")
    SCOPE_FIELD_NUMBER: _ClassVar[int]
    SPANS_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_URL_FIELD_NUMBER: _ClassVar[int]
    scope: _common_pb2.InstrumentationScope
    spans: _containers.RepeatedCompositeFieldContainer[Span]
    schema_url: str
    def __init__(self, scope: _Optional[_Union[_common_pb2.InstrumentationScope, _Mapping]] = ..., spans: _Optional[_Iterable[_Union[Span, _Mapping]]] = ..., schema_url: _Optional[str] = ...) -> None: ...

class Span(_message.Message):
    __slots__ = ("trace_id", "span_id", "trace_state", "parent_span_id", "flags", "name", "kind", "start_time_unix_nano", "end_time_unix_nano", "attributes", "dropped_attributes_count", "events", "dropped_events_count", "links", "dropped_links_count", "status")
    class SpanKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        SPAN_KIND_UNSPECIFIED: _ClassVar[Span.SpanKind]
        SPAN_KIND_INTERNAL: _ClassVar[Span.SpanKind]
        SPAN_KIND_SERVER: _ClassVar[Span.SpanKind]
        SPAN_KIND_CLIENT: _ClassVar[Span.SpanKind]
        SPAN_KIND_PRODUCER: _ClassVar[Span.SpanKind]
        SPAN_KIND_CONSUMER: _ClassVar[Span.SpanKind]
    SPAN_KIND_UNSPECIFIED: Span.SpanKind
    SPAN_KIND_INTERNAL: Span.SpanKind
    SPAN_KIND_SERVER: Span.SpanKind
    SPAN_KIND_CLIENT: Span.SpanKind
    SPAN_KIND_PRODUCER: Span.SpanKind
    SPAN_KIND_CONSUMER: Span.SpanKind
    class Event(_message.Message):
        __slots__ = ("time_unix_nano", "name", "attributes", "dropped_attributes_count")
        TIME_UNIX_NANO_FIELD_NUMBER: _ClassVar[int]
        NAME_FIELD_NUMBER: _ClassVar[int]
        ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
        DROPPED_ATTRIBUTES_COUNT_FIELD_NUMBER: _ClassVar[int]
        time_unix_nano: int
        name: str
        attributes: _containers.RepeatedCompositeFieldContainer[_common_pb2.KeyValue]
        dropped_attributes_count: int
        def __init__(self, time_unix_nano: _Optional[int] = ..., name: _Optional[str] = ..., attributes: _Optional[_Iterable[_Union[_common_pb2.KeyValue, _Mapping]]] = ..., dropped_attributes_count: _Optional[int] = ...) -> None: ...
    class Link(_message.Message):
        __slots__ = ("trace_id", "span_id", "trace_state", "attributes", "dropped_attributes_count", "flags")
        TRACE_ID_FIELD_NUMBER: _ClassVar[int]
        SPAN_ID_FIELD_NUMBER: _ClassVar[int]
        TRACE_STATE_FIELD_NUMBER: _ClassVar[int]
        ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
        DROPPED_ATTRIBUTES_COUNT_FIELD_NUMBER: _ClassVar[int]
        FLAGS_FIELD_NUMBER: _ClassVar[int]
        trace_id: bytes
        span_id: bytes
        trace_state: str
        attributes: _containers.RepeatedCompositeFieldContainer[_common_pb2.KeyValue]
        dropped_attributes_count: int
        flags: int
        def __init__(self, trace_id: _Optional[bytes] = ..., span_id: _Optional[bytes] = ..., trace_state: _Optional[str] = ..., attributes: _Optional[_Iterable[_Union[_common_pb2.KeyValue, _Mapping]]] = ..., dropped_attributes_count: _Optional[int] = ..., flags: _Optional[int] = ...) -> None: ...
    TRACE_ID_FIELD_NUMBER: _ClassVar[int]
    SPAN_ID_FIELD_NUMBER: _ClassVar[int]
    TRACE_STATE_FIELD_NUMBER: _ClassVar[int]
    PARENT_SPAN_ID_FIELD_NUMBER: _ClassVar[int]
    FLAGS_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    START_TIME_UNIX_NANO_FIELD_NUMBER: _ClassVar[int]
    END_TIME_UNIX_NANO_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    DROPPED_ATTRIBUTES_COUNT_FIELD_NUMBER: _ClassVar[int]
    EVENTS_FIELD_NUMBER: _ClassVar[int]
    DROPPED_EVENTS_COUNT_FIELD_NUMBER: _ClassVar[int]
    LINKS_FIELD_NUMBER: _ClassVar[int]
    DROPPED_LINKS_COUNT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    trace_id: bytes
    span_id: bytes
    trace_state: str
    parent_span_id: bytes
    flags: int
    name: str
    kind: Span.SpanKind
    start_time_unix_nano: int
    end_time_unix_nano: int
    attributes: _containers.RepeatedCompositeFieldContainer[_common_pb2.KeyValue]
    dropped_attributes_count: int
    events: _containers.RepeatedCompositeFieldContainer[Span.Event]
    dropped_events_count: int
    links: _containers.RepeatedCompositeFieldContainer[Span.Link]
    dropped_links_count: int
    status: Status
    def __init__(self, trace_id: _Optional[bytes] = ..., span_id: _Optional[bytes] = ..., trace_state: _Optional[str] = ..., parent_span_id: _Optional[bytes] = ..., flags: _Optional[int] = ..., name: _Optional[str] = ..., kind: _Optional[_Union[Span.SpanKind, str]] = ..., start_time_unix_nano: _Optional[int] = ..., end_time_unix_nano: _Optional[int] = ..., attributes: _Optional[_Iterable[_Union[_common_pb2.KeyValue, _Mapping]]] = ..., dropped_attributes_count: _Optional[int] = ..., events: _Optional[_Iterable[_Union[Span.Event, _Mapping]]] = ..., dropped_events_count: _Optional[int] = ..., links: _Optional[_Iterable[_Union[Span.Link, _Mapping]]] = ..., dropped_links_count: _Optional[int] = ..., status: _Optional[_Union[Status, _Mapping]] = ...) -> None: ...

class Status(_message.Message):
    __slots__ = ("message", "code")
    class StatusCode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        STATUS_CODE_UNSET: _ClassVar[Status.StatusCode]
        STATUS_CODE_OK: _ClassVar[Status.StatusCode]
        STATUS_CODE_ERROR: _ClassVar[Status.StatusCode]
    STATUS_CODE_UNSET: Status.StatusCode
    STATUS_CODE_OK: Status.StatusCode
    STATUS_CODE_ERROR: Status.StatusCode
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    message: str
    code: Status.StatusCode
    def __init__(self, message: _Optional[str] = ..., code: _Optional[_Union[Status.StatusCode, str]] = ...) -> None: ...
