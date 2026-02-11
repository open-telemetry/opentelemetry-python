# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest
from google.protobuf import descriptor_pb2 as descriptor
from opentelemetry.codegen.json.types import (
    get_default_value,
    get_json_allowed_types,
    get_python_type,
    is_bytes_type,
    is_hex_encoded_field,
    is_int64_type,
    is_numeric_type,
    to_json_field_name,
)


@pytest.mark.parametrize(
    "proto_type, expected",
    [
        (descriptor.FieldDescriptorProto.TYPE_DOUBLE, "builtins.float"),
        (descriptor.FieldDescriptorProto.TYPE_INT64, "builtins.int"),
        (descriptor.FieldDescriptorProto.TYPE_BOOL, "builtins.bool"),
        (descriptor.FieldDescriptorProto.TYPE_STRING, "builtins.str"),
        (descriptor.FieldDescriptorProto.TYPE_BYTES, "builtins.bytes"),
        (999, "typing.Any"),
    ],
)
def test_get_python_type(proto_type: int, expected: str) -> None:
    assert get_python_type(proto_type) == expected


@pytest.mark.parametrize(
    "proto_type, expected",
    [
        (descriptor.FieldDescriptorProto.TYPE_DOUBLE, "0.0"),
        (descriptor.FieldDescriptorProto.TYPE_INT64, "0"),
        (descriptor.FieldDescriptorProto.TYPE_BOOL, "False"),
        (descriptor.FieldDescriptorProto.TYPE_STRING, '""'),
        (descriptor.FieldDescriptorProto.TYPE_BYTES, 'b""'),
        (999, "None"),
    ],
)
def test_get_default_value(proto_type: int, expected: str) -> None:
    assert get_default_value(proto_type) == expected


@pytest.mark.parametrize(
    "proto_type, expected",
    [
        (descriptor.FieldDescriptorProto.TYPE_INT64, True),
        (descriptor.FieldDescriptorProto.TYPE_UINT64, True),
        (descriptor.FieldDescriptorProto.TYPE_FIXED64, True),
        (descriptor.FieldDescriptorProto.TYPE_SFIXED64, True),
        (descriptor.FieldDescriptorProto.TYPE_SINT64, True),
        (descriptor.FieldDescriptorProto.TYPE_INT32, False),
        (descriptor.FieldDescriptorProto.TYPE_STRING, False),
    ],
)
def test_is_int64_type(proto_type: int, expected: bool) -> None:
    assert is_int64_type(proto_type) == expected


@pytest.mark.parametrize(
    "proto_type, expected",
    [
        (descriptor.FieldDescriptorProto.TYPE_BYTES, True),
        (descriptor.FieldDescriptorProto.TYPE_STRING, False),
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
        (descriptor.FieldDescriptorProto.TYPE_DOUBLE, True),
        (descriptor.FieldDescriptorProto.TYPE_INT64, True),
        (descriptor.FieldDescriptorProto.TYPE_INT32, True),
        (descriptor.FieldDescriptorProto.TYPE_BOOL, False),
        (descriptor.FieldDescriptorProto.TYPE_STRING, False),
    ],
)
def test_is_numeric_type(proto_type: int, expected: bool) -> None:
    assert is_numeric_type(proto_type) == expected


@pytest.mark.parametrize(
    "proto_type, field_name, expected",
    [
        (descriptor.FieldDescriptorProto.TYPE_BYTES, "data", "builtins.str"),
        (
            descriptor.FieldDescriptorProto.TYPE_STRING,
            "trace_id",
            "builtins.str",
        ),
        (
            descriptor.FieldDescriptorProto.TYPE_INT64,
            "count",
            "(builtins.int, builtins.str)",
        ),
        (
            descriptor.FieldDescriptorProto.TYPE_DOUBLE,
            "value",
            "(builtins.float, builtins.int, builtins.str)",
        ),
        (descriptor.FieldDescriptorProto.TYPE_BOOL, "flag", "builtins.bool"),
        (descriptor.FieldDescriptorProto.TYPE_INT32, "id", "builtins.int"),
    ],
)
def test_get_json_allowed_types(
    proto_type: int, field_name: str, expected: str
) -> None:
    assert get_json_allowed_types(proto_type, field_name) == expected
