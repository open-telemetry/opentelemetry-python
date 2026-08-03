# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry.exporter.otlp.proto.common._internal import (
    _encode_attributes as proto_encode_attributes,
    _encode_instrumentation_scope as proto_encode_instrumentation_scope,
    _encode_resource as proto_encode_resource,
    _encode_span_id as proto_encode_span_id,
    _encode_trace_id as proto_encode_trace_id,
    _encode_value as proto_encode_value,
)
from opentelemetry.exporter.otlp._proto.common._internal import (
    _encode_attributes,
    _encode_instrumentation_scope,
    _encode_resource,
    _encode_span_id,
    _encode_trace_id,
    _encode_value,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope


# ── _encode_span_id / _encode_trace_id ───────────────────────────────────────

def test_encode_span_id_matches_proto() -> None:
    span_id = 0x1234567890ABCDEF
    assert _encode_span_id(span_id) == proto_encode_span_id(span_id)


def test_encode_trace_id_matches_proto() -> None:
    trace_id = 0x3E0C63257DE34C926F9EFCD03927272E
    assert _encode_trace_id(trace_id) == proto_encode_trace_id(trace_id)


def test_encode_span_id_zero() -> None:
    assert _encode_span_id(0) == proto_encode_span_id(0)


# ── _encode_value ─────────────────────────────────────────────────────────────

def test_encode_value_none_matches_proto() -> None:
    assert _encode_value(None).SerializeToString() == proto_encode_value(None).SerializeToString()


def test_encode_value_string_matches_proto() -> None:
    assert _encode_value("hello").SerializeToString() == proto_encode_value("hello").SerializeToString()


def test_encode_value_bool_true_matches_proto() -> None:
    assert _encode_value(True).SerializeToString() == proto_encode_value(True).SerializeToString()


def test_encode_value_bool_false_matches_proto() -> None:
    assert _encode_value(False).SerializeToString() == proto_encode_value(False).SerializeToString()


def test_encode_value_int_matches_proto() -> None:
    assert _encode_value(42).SerializeToString() == proto_encode_value(42).SerializeToString()


def test_encode_value_negative_int_matches_proto() -> None:
    assert _encode_value(-7).SerializeToString() == proto_encode_value(-7).SerializeToString()


def test_encode_value_float_matches_proto() -> None:
    assert _encode_value(3.14).SerializeToString() == proto_encode_value(3.14).SerializeToString()


def test_encode_value_bytes_matches_proto() -> None:
    assert _encode_value(b"\x01\x02\x03").SerializeToString() == proto_encode_value(b"\x01\x02\x03").SerializeToString()


def test_encode_value_list_matches_proto() -> None:
    assert _encode_value([1, "a", True]).SerializeToString() == proto_encode_value([1, "a", True]).SerializeToString()


def test_encode_value_dict_matches_proto() -> None:
    assert _encode_value({"k": "v", "n": 1}).SerializeToString() == proto_encode_value({"k": "v", "n": 1}).SerializeToString()


def test_encode_value_nested_matches_proto() -> None:
    value = {"error": None, "tags": ["a", "b"], "count": 5}
    assert _encode_value(value).SerializeToString() == proto_encode_value(value).SerializeToString()


# ── _encode_attributes ────────────────────────────────────────────────────────

def test_encode_attributes_empty_matches_proto() -> None:
    our = _encode_attributes({})
    proto = proto_encode_attributes({})
    our_bytes = b"".join(kv.SerializeToString() for kv in our)
    proto_bytes = b"".join(kv.SerializeToString() for kv in proto)
    assert our_bytes == proto_bytes


def test_encode_attributes_with_values_matches_proto() -> None:
    attrs = {"service.name": "my-service", "count": 5, "enabled": True, "ratio": 0.5}
    our = _encode_attributes(attrs)
    proto = proto_encode_attributes(attrs)
    our_bytes = b"".join(kv.SerializeToString() for kv in our)
    proto_bytes = b"".join(kv.SerializeToString() for kv in proto)
    assert our_bytes == proto_bytes


def test_encode_attributes_none_matches_proto() -> None:
    our = _encode_attributes(None)
    proto = proto_encode_attributes(None)
    assert our == proto == []


# ── _encode_instrumentation_scope ─────────────────────────────────────────────

def test_encode_instrumentation_scope_empty_matches_proto() -> None:
    scope = InstrumentationScope(name="")
    our = _encode_instrumentation_scope(scope)
    proto = proto_encode_instrumentation_scope(scope)
    assert our.SerializeToString() == proto.SerializeToString()


def test_encode_instrumentation_scope_name_version_matches_proto() -> None:
    scope = InstrumentationScope(name="mylib", version="1.2.3")
    our = _encode_instrumentation_scope(scope)
    proto = proto_encode_instrumentation_scope(scope)
    assert our.SerializeToString() == proto.SerializeToString()


def test_encode_instrumentation_scope_with_attributes_matches_proto() -> None:
    scope = InstrumentationScope(
        name="mylib",
        version="2.0",
        schema_url="https://example.com",
        attributes={"env": "prod", "version": 2},
    )
    our = _encode_instrumentation_scope(scope)
    proto = proto_encode_instrumentation_scope(scope)
    assert our.SerializeToString() == proto.SerializeToString()


def test_encode_instrumentation_scope_none_matches_proto() -> None:
    our = _encode_instrumentation_scope(None)
    proto = proto_encode_instrumentation_scope(None)
    assert our.SerializeToString() == proto.SerializeToString()


# ── _encode_resource ──────────────────────────────────────────────────────────

def test_encode_resource_empty_matches_proto() -> None:
    resource = Resource({})
    our = _encode_resource(resource)
    proto = proto_encode_resource(resource)
    assert our.SerializeToString() == proto.SerializeToString()


def test_encode_resource_with_attributes_matches_proto() -> None:
    resource = Resource({"service.name": "my-service", "host.name": "localhost", "pid": 1234})
    our = _encode_resource(resource)
    proto = proto_encode_resource(resource)
    assert our.SerializeToString() == proto.SerializeToString()
