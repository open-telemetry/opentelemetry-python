from opentelemetry.proto.common.v1.common_pb2 import (
    AnyValue as ProtoAnyValue,
    KeyValue as ProtoKeyValue,
)
from opentelemetry.proto.resource.v1.resource_pb2 import Resource as ProtoResource

from opentelemetry._proto.common.v1.common_pb2 import AnyValue, KeyValue
from opentelemetry._proto.resource.v1.resource_pb2 import Resource


def test_resource_empty() -> None:
    assert Resource().SerializeToString() == b""


def test_resource_empty_matches_proto() -> None:
    assert Resource().SerializeToString() == ProtoResource().SerializeToString()


def test_resource_dropped_attributes_count() -> None:
    our = Resource(dropped_attributes_count=5)
    proto = ProtoResource(dropped_attributes_count=5)
    assert our.SerializeToString() == proto.SerializeToString()


def test_resource_with_one_attribute() -> None:
    attr = KeyValue(key="service.name", value=AnyValue(string_value="my-service"))
    proto_attr = ProtoKeyValue(key="service.name", value=ProtoAnyValue(string_value="my-service"))
    our = Resource(attributes=[attr])
    proto = ProtoResource(attributes=[proto_attr])
    assert our.SerializeToString() == proto.SerializeToString()


def test_resource_with_multiple_attributes() -> None:
    attrs = [
        KeyValue(key="service.name", value=AnyValue(string_value="my-service")),
        KeyValue(key="service.version", value=AnyValue(string_value="1.0.0")),
        KeyValue(key="deployment.environment", value=AnyValue(string_value="prod")),
    ]
    proto_attrs = [
        ProtoKeyValue(key="service.name", value=ProtoAnyValue(string_value="my-service")),
        ProtoKeyValue(key="service.version", value=ProtoAnyValue(string_value="1.0.0")),
        ProtoKeyValue(key="deployment.environment", value=ProtoAnyValue(string_value="prod")),
    ]
    our = Resource(attributes=attrs)
    proto = ProtoResource(attributes=proto_attrs)
    assert our.SerializeToString() == proto.SerializeToString()


def test_resource_full() -> None:
    attrs = [
        KeyValue(key="k", value=AnyValue(string_value="v")),
    ]
    proto_attrs = [
        ProtoKeyValue(key="k", value=ProtoAnyValue(string_value="v")),
    ]
    our = Resource(attributes=attrs, dropped_attributes_count=2)
    proto = ProtoResource(attributes=proto_attrs, dropped_attributes_count=2)
    assert our.SerializeToString() == proto.SerializeToString()


def test_resource_with_int_attribute() -> None:
    our = Resource(attributes=[KeyValue(key="pid", value=AnyValue(int_value=1234))])
    proto = ProtoResource(attributes=[ProtoKeyValue(key="pid", value=ProtoAnyValue(int_value=1234))])
    assert our.SerializeToString() == proto.SerializeToString()
