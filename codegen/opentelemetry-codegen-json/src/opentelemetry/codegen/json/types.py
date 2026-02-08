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

from typing import Final

from google.protobuf import descriptor_pb2 as descriptor

PROTO_TO_PYTHON: Final[dict[int, str]] = {
    descriptor.FieldDescriptorProto.TYPE_DOUBLE: "float",
    descriptor.FieldDescriptorProto.TYPE_FLOAT: "float",
    descriptor.FieldDescriptorProto.TYPE_INT64: "int",
    descriptor.FieldDescriptorProto.TYPE_UINT64: "int",
    descriptor.FieldDescriptorProto.TYPE_INT32: "int",
    descriptor.FieldDescriptorProto.TYPE_FIXED64: "int",
    descriptor.FieldDescriptorProto.TYPE_FIXED32: "int",
    descriptor.FieldDescriptorProto.TYPE_BOOL: "bool",
    descriptor.FieldDescriptorProto.TYPE_STRING: "str",
    descriptor.FieldDescriptorProto.TYPE_BYTES: "bytes",
    descriptor.FieldDescriptorProto.TYPE_UINT32: "int",
    descriptor.FieldDescriptorProto.TYPE_SFIXED32: "int",
    descriptor.FieldDescriptorProto.TYPE_SFIXED64: "int",
    descriptor.FieldDescriptorProto.TYPE_SINT32: "int",
    descriptor.FieldDescriptorProto.TYPE_SINT64: "int",
}

PROTO_DEFAULTS: Final[dict[int, str]] = {
    descriptor.FieldDescriptorProto.TYPE_DOUBLE: "0.0",
    descriptor.FieldDescriptorProto.TYPE_FLOAT: "0.0",
    descriptor.FieldDescriptorProto.TYPE_INT64: "0",
    descriptor.FieldDescriptorProto.TYPE_UINT64: "0",
    descriptor.FieldDescriptorProto.TYPE_INT32: "0",
    descriptor.FieldDescriptorProto.TYPE_FIXED64: "0",
    descriptor.FieldDescriptorProto.TYPE_FIXED32: "0",
    descriptor.FieldDescriptorProto.TYPE_BOOL: "False",
    descriptor.FieldDescriptorProto.TYPE_STRING: "''",
    descriptor.FieldDescriptorProto.TYPE_BYTES: "b''",
    descriptor.FieldDescriptorProto.TYPE_UINT32: "0",
    descriptor.FieldDescriptorProto.TYPE_SFIXED32: "0",
    descriptor.FieldDescriptorProto.TYPE_SFIXED64: "0",
    descriptor.FieldDescriptorProto.TYPE_SINT32: "0",
    descriptor.FieldDescriptorProto.TYPE_SINT64: "0",
}

INT64_TYPES: Final[set[int]] = {
    descriptor.FieldDescriptorProto.TYPE_INT64,
    descriptor.FieldDescriptorProto.TYPE_UINT64,
    descriptor.FieldDescriptorProto.TYPE_FIXED64,
    descriptor.FieldDescriptorProto.TYPE_SFIXED64,
    descriptor.FieldDescriptorProto.TYPE_SINT64,
}

HEX_ENCODED_FIELDS: Final[set[str]] = {
    "trace_id",
    "span_id",
    "parent_span_id",
}


def get_python_type(proto_type: int) -> str:
    """Get Python type for a protobuf field type."""
    return PROTO_TO_PYTHON.get(proto_type, "Any")


def get_default_value(proto_type: int) -> str:
    """Get default value for a protobuf field type."""
    return PROTO_DEFAULTS.get(proto_type, "None")


def is_int64_type(proto_type: int) -> bool:
    """Check if type is a 64-bit integer requiring string serialization."""
    return proto_type in INT64_TYPES


def is_bytes_type(proto_type: int) -> bool:
    """Check if type is bytes."""
    return proto_type == descriptor.FieldDescriptorProto.TYPE_BYTES


def is_hex_encoded_field(field_name: str) -> bool:
    """Check if this is a trace/span ID field requiring hex encoding."""
    return field_name in HEX_ENCODED_FIELDS


def to_json_field_name(snake_name: str) -> str:
    """Convert snake_case field name to lowerCamelCase JSON name."""
    components = snake_name.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def is_numeric_type(proto_type: int) -> bool:
    """Check if type is numeric (int or float)."""
    if proto_type in INT64_TYPES:
        return True
    return proto_type in {
        descriptor.FieldDescriptorProto.TYPE_DOUBLE,
        descriptor.FieldDescriptorProto.TYPE_FLOAT,
        descriptor.FieldDescriptorProto.TYPE_INT32,
        descriptor.FieldDescriptorProto.TYPE_FIXED32,
        descriptor.FieldDescriptorProto.TYPE_UINT32,
        descriptor.FieldDescriptorProto.TYPE_SFIXED32,
        descriptor.FieldDescriptorProto.TYPE_SINT32,
    }


def get_json_allowed_types(proto_type: int, field_name: str = "") -> str:
    """
    Get the Python type(s) allowed for the JSON representation of a field.
    Returns a string representation of the type or tuple of types.
    """
    if is_hex_encoded_field(field_name):
        return "str"
    if is_int64_type(proto_type):
        return "(int, str)"
    if is_bytes_type(proto_type):
        return "str"
    if proto_type in (
        descriptor.FieldDescriptorProto.TYPE_FLOAT,
        descriptor.FieldDescriptorProto.TYPE_DOUBLE,
    ):
        return "(float, int, str)"

    py_type = get_python_type(proto_type)
    return py_type
