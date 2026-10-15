# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=no-member

import ast
import builtins

import pytest  # type: ignore
from google.protobuf import descriptor_pb2 as descriptor

from opentelemetry.codegen.json.types import (
    PROTO_DEFAULTS,
    PROTO_TO_PYTHON,
    get_default_value,
    get_json_allowed_types,
    get_python_type,
    is_bytes_type,
    is_hex_encoded_field,
    is_int64_type,
    is_numeric_type,
    to_json_field_name,
)

FDP = descriptor.FieldDescriptorProto


@pytest.mark.parametrize(
    "proto_type, expected",
    [
        (FDP.TYPE_DOUBLE, "builtins.float"),
        (FDP.TYPE_INT64, "builtins.int"),
        (FDP.TYPE_BOOL, "builtins.bool"),
        (FDP.TYPE_STRING, "builtins.str"),
        (FDP.TYPE_BYTES, "builtins.bytes"),
    ],
)
def test_get_python_type(proto_type: int, expected: str) -> None:
    assert get_python_type(proto_type) == expected


@pytest.mark.parametrize(
    "proto_type, expected",
    [
        (FDP.TYPE_DOUBLE, "0.0"),
        (FDP.TYPE_FLOAT, "0.0"),
        (FDP.TYPE_INT64, "0"),
        (FDP.TYPE_UINT32, "0"),
        (FDP.TYPE_SINT64, "0"),
        (FDP.TYPE_BOOL, "False"),
        (FDP.TYPE_STRING, '""'),
        (FDP.TYPE_BYTES, 'b""'),
    ],
)
def test_get_default_value(proto_type: int, expected: str) -> None:
    assert get_default_value(proto_type) == expected


@pytest.mark.parametrize(
    "proto_type",
    [FDP.TYPE_GROUP, FDP.TYPE_MESSAGE, FDP.TYPE_ENUM],
)
def test_get_default_value_types_without_default(proto_type: int) -> None:
    assert get_default_value(proto_type) == "None"


@pytest.mark.parametrize("proto_type", [0, -1, 999, 2**31])
def test_get_default_value_out_of_range(proto_type: int) -> None:
    assert get_default_value(proto_type) == "None"


def test_every_mapped_type_has_a_default() -> None:
    # keeps PROTO_TO_PYTHON and PROTO_DEFAULTS from drifting apart
    assert set(PROTO_TO_PYTHON) == set(PROTO_DEFAULTS)


@pytest.mark.parametrize("proto_type", PROTO_DEFAULTS)
def test_default_is_valid_python_literal(proto_type: int) -> None:
    # the default is emitted into generated code, so it must parse cleanly
    value = ast.literal_eval(get_default_value(proto_type))
    type_name = get_python_type(proto_type).removeprefix("builtins.")
    assert isinstance(value, getattr(builtins, type_name))


@pytest.mark.parametrize(
    "proto_type, expected",
    [
        (FDP.TYPE_INT64, True),
        (FDP.TYPE_UINT64, True),
        (FDP.TYPE_FIXED64, True),
        (FDP.TYPE_SFIXED64, True),
        (FDP.TYPE_SINT64, True),
        (FDP.TYPE_INT32, False),
        (FDP.TYPE_STRING, False),
    ],
)
def test_is_int64_type(proto_type: int, expected: bool) -> None:
    assert is_int64_type(proto_type) == expected


@pytest.mark.parametrize(
    "proto_type, expected",
    [
        (FDP.TYPE_BYTES, True),
        (FDP.TYPE_STRING, False),
    ],
)
def test_is_bytes_type(proto_type: int, expected: bool) -> None:
    assert is_bytes_type(proto_type) == expected


@pytest.mark.parametrize(
    "field_name, expected",
    [
        ("trace_id", True),
        ("span_id", True),
        ("parent_span_id", True),
        ("name", False),
        ("time_unix_nano", False),
    ],
)
def test_is_hex_encoded_field(field_name: str, expected: bool) -> None:
    assert is_hex_encoded_field(field_name) == expected


@pytest.mark.parametrize(
    "snake_name, expected",
    [
        ("name", "name"),
        ("start_time_unix_nano", "startTimeUnixNano"),
        ("trace_id", "traceId"),
        ("multiple___underscores", "multipleUnderscores"),
    ],
)
def test_to_json_field_name(snake_name: str, expected: str) -> None:
    assert to_json_field_name(snake_name) == expected


@pytest.mark.parametrize(
    "proto_type, expected",
    [
        (FDP.TYPE_DOUBLE, True),
        (FDP.TYPE_INT64, True),
        (FDP.TYPE_INT32, True),
        (FDP.TYPE_BOOL, False),
        (FDP.TYPE_STRING, False),
    ],
)
def test_is_numeric_type(proto_type: int, expected: bool) -> None:
    assert is_numeric_type(proto_type) == expected


@pytest.mark.parametrize(
    "proto_type, field_name, expected",
    [
        (FDP.TYPE_BYTES, "data", "builtins.str"),
        (FDP.TYPE_STRING, "trace_id", "builtins.str"),
        (FDP.TYPE_INT64, "count", "(builtins.int, builtins.str)"),
        (
            FDP.TYPE_DOUBLE,
            "value",
            "(builtins.float, builtins.int, builtins.str)",
        ),
        (FDP.TYPE_BOOL, "flag", "builtins.bool"),
        (FDP.TYPE_INT32, "id", "builtins.int"),
    ],
)
def test_get_json_allowed_types(
    proto_type: int, field_name: str, expected: str
) -> None:
    assert get_json_allowed_types(proto_type, field_name) == expected