from opentelemetry.proto.common.v1.common_pb2 import (
    AnyValue as ProtoAnyValue,
    ArrayValue as ProtoArrayValue,
    InstrumentationScope as ProtoInstrumentationScope,
    KeyValue as ProtoKeyValue,
    KeyValueList as ProtoKeyValueList,
)

from opentelemetry._proto.common.v1.common_pb2 import (
    AnyValue,
    ArrayValue,
    InstrumentationScope,
    KeyValue,
    KeyValueList,
)


# ── AnyValue ──────────────────────────────────────────────────────────────────

def test_any_value_empty() -> None:
    assert AnyValue().SerializeToString() == b""


def test_any_value_empty_matches_proto() -> None:
    assert AnyValue().SerializeToString() == ProtoAnyValue().SerializeToString()


def test_any_value_string() -> None:
    our = AnyValue(string_value="hello")
    proto = ProtoAnyValue(string_value="hello")
    assert our.SerializeToString() == proto.SerializeToString()


def test_any_value_bool_true() -> None:
    our = AnyValue(bool_value=True)
    proto = ProtoAnyValue(bool_value=True)
    assert our.SerializeToString() == proto.SerializeToString()


def test_any_value_bool_false() -> None:
    our = AnyValue(bool_value=False)
    proto = ProtoAnyValue(bool_value=False)
    assert our.SerializeToString() == proto.SerializeToString()


def test_any_value_int() -> None:
    our = AnyValue(int_value=42)
    proto = ProtoAnyValue(int_value=42)
    assert our.SerializeToString() == proto.SerializeToString()


def test_any_value_int_negative() -> None:
    our = AnyValue(int_value=-1)
    proto = ProtoAnyValue(int_value=-1)
    assert our.SerializeToString() == proto.SerializeToString()


def test_any_value_double() -> None:
    our = AnyValue(double_value=3.14)
    proto = ProtoAnyValue(double_value=3.14)
    assert our.SerializeToString() == proto.SerializeToString()


def test_any_value_bytes() -> None:
    our = AnyValue(bytes_value=b"\x01\x02\x03")
    proto = ProtoAnyValue(bytes_value=b"\x01\x02\x03")
    assert our.SerializeToString() == proto.SerializeToString()


def test_any_value_array_empty() -> None:
    our = AnyValue(array_value=ArrayValue())
    proto = ProtoAnyValue(array_value=ProtoArrayValue())
    assert our.SerializeToString() == proto.SerializeToString()


def test_any_value_kvlist_empty() -> None:
    our = AnyValue(kvlist_value=KeyValueList())
    proto = ProtoAnyValue(kvlist_value=ProtoKeyValueList())
    assert our.SerializeToString() == proto.SerializeToString()


# ── ArrayValue ────────────────────────────────────────────────────────────────

def test_array_value_empty() -> None:
    assert ArrayValue().SerializeToString() == b""


def test_array_value_empty_matches_proto() -> None:
    assert ArrayValue().SerializeToString() == ProtoArrayValue().SerializeToString()


def test_array_value_with_elements() -> None:
    our = ArrayValue(values=[AnyValue(string_value="a"), AnyValue(int_value=1)])
    proto = ProtoArrayValue(values=[ProtoAnyValue(string_value="a"), ProtoAnyValue(int_value=1)])
    assert our.SerializeToString() == proto.SerializeToString()


# ── KeyValueList ──────────────────────────────────────────────────────────────

def test_kvlist_empty() -> None:
    assert KeyValueList().SerializeToString() == b""


def test_kvlist_empty_matches_proto() -> None:
    assert KeyValueList().SerializeToString() == ProtoKeyValueList().SerializeToString()


def test_kvlist_with_values() -> None:
    our = KeyValueList(values=[KeyValue(key="k", value=AnyValue(string_value="v"))])
    proto = ProtoKeyValueList(values=[ProtoKeyValue(key="k", value=ProtoAnyValue(string_value="v"))])
    assert our.SerializeToString() == proto.SerializeToString()


# ── KeyValue ──────────────────────────────────────────────────────────────────

def test_key_value_empty() -> None:
    assert KeyValue().SerializeToString() == b""


def test_key_value_empty_matches_proto() -> None:
    assert KeyValue().SerializeToString() == ProtoKeyValue().SerializeToString()


def test_key_value_key_only() -> None:
    our = KeyValue(key="mykey")
    proto = ProtoKeyValue(key="mykey")
    assert our.SerializeToString() == proto.SerializeToString()


def test_key_value_string() -> None:
    our = KeyValue(key="k", value=AnyValue(string_value="v"))
    proto = ProtoKeyValue(key="k", value=ProtoAnyValue(string_value="v"))
    assert our.SerializeToString() == proto.SerializeToString()


def test_key_value_int() -> None:
    our = KeyValue(key="count", value=AnyValue(int_value=42))
    proto = ProtoKeyValue(key="count", value=ProtoAnyValue(int_value=42))
    assert our.SerializeToString() == proto.SerializeToString()


def test_key_value_double() -> None:
    our = KeyValue(key="ratio", value=AnyValue(double_value=0.5))
    proto = ProtoKeyValue(key="ratio", value=ProtoAnyValue(double_value=0.5))
    assert our.SerializeToString() == proto.SerializeToString()


# ── InstrumentationScope ──────────────────────────────────────────────────────

def test_instrumentation_scope_empty() -> None:
    assert InstrumentationScope().SerializeToString() == b""


def test_instrumentation_scope_empty_matches_proto() -> None:
    assert (
        InstrumentationScope().SerializeToString()
        == ProtoInstrumentationScope().SerializeToString()
    )


def test_instrumentation_scope_name() -> None:
    our = InstrumentationScope(name="mylib")
    proto = ProtoInstrumentationScope(name="mylib")
    assert our.SerializeToString() == proto.SerializeToString()


def test_instrumentation_scope_name_version() -> None:
    our = InstrumentationScope(name="mylib", version="1.2.3")
    proto = ProtoInstrumentationScope(name="mylib", version="1.2.3")
    assert our.SerializeToString() == proto.SerializeToString()


def test_instrumentation_scope_with_attributes() -> None:
    attr = KeyValue(key="env", value=AnyValue(string_value="prod"))
    proto_attr = ProtoKeyValue(key="env", value=ProtoAnyValue(string_value="prod"))
    our = InstrumentationScope(
        name="mylib",
        version="1.0",
        attributes=[attr],
        dropped_attributes_count=3,
    )
    proto = ProtoInstrumentationScope(
        name="mylib",
        version="1.0",
        attributes=[proto_attr],
        dropped_attributes_count=3,
    )
    assert our.SerializeToString() == proto.SerializeToString()
