# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=no-member

"""Proto-type to Python-type and proto-type to wire-helper mappings.

This is the wire-serialization counterpart of the JSON plugin's types module.
Instead of mapping proto types to JSON encoders, it maps proto types to the
field helpers in ``opentelemetry._proto._pyprotobuf.fields`` that produce the
protobuf wire-format bytes for a single field.
"""

from typing import Final

from google.protobuf import descriptor_pb2 as descriptor

_FD = descriptor.FieldDescriptorProto

PROTO_TO_PYTHON: Final[dict[int, str]] = {
    _FD.TYPE_DOUBLE: "float",
    _FD.TYPE_FLOAT: "float",
    _FD.TYPE_INT64: "int",
    _FD.TYPE_UINT64: "int",
    _FD.TYPE_INT32: "int",
    _FD.TYPE_FIXED64: "int",
    _FD.TYPE_FIXED32: "int",
    _FD.TYPE_BOOL: "bool",
    _FD.TYPE_STRING: "str",
    _FD.TYPE_BYTES: "bytes",
    _FD.TYPE_UINT32: "int",
    _FD.TYPE_SFIXED32: "int",
    _FD.TYPE_SFIXED64: "int",
    _FD.TYPE_SINT32: "int",
    _FD.TYPE_SINT64: "int",
}

# Signed/unsigned integer bounds for oneof scalar setters. protobuf raises
# ValueError when an assigned value does not fit the field's declared width, so
# the generated setters reproduce that check.
INT_BOUNDS: Final[dict[int, tuple[int, int]]] = {
    _FD.TYPE_INT64: (-(2**63), 2**63),
    _FD.TYPE_SINT64: (-(2**63), 2**63),
    _FD.TYPE_SFIXED64: (-(2**63), 2**63),
    _FD.TYPE_UINT64: (0, 2**64),
    _FD.TYPE_FIXED64: (0, 2**64),
    _FD.TYPE_INT32: (-(2**31), 2**31),
    _FD.TYPE_SINT32: (-(2**31), 2**31),
    _FD.TYPE_SFIXED32: (-(2**31), 2**31),
    _FD.TYPE_UINT32: (0, 2**32),
    _FD.TYPE_FIXED32: (0, 2**32),
}

PROTO_DEFAULTS: Final[dict[int, str]] = {
    _FD.TYPE_DOUBLE: "0.0",
    _FD.TYPE_FLOAT: "0.0",
    _FD.TYPE_INT64: "0",
    _FD.TYPE_UINT64: "0",
    _FD.TYPE_INT32: "0",
    _FD.TYPE_FIXED64: "0",
    _FD.TYPE_FIXED32: "0",
    _FD.TYPE_BOOL: "False",
    _FD.TYPE_STRING: '""',
    _FD.TYPE_BYTES: 'b""',
    _FD.TYPE_UINT32: "0",
    _FD.TYPE_SFIXED32: "0",
    _FD.TYPE_SFIXED64: "0",
    _FD.TYPE_SINT32: "0",
    _FD.TYPE_SINT64: "0",
}

# Field helper (from _pyprotobuf.fields) for a singular, non-oneof scalar field.
# Each helper applies the proto3 default-omission rule, encodes the tag, and
# encodes the value.
SINGULAR_WIRE_HELPER: Final[dict[int, str]] = {
    _FD.TYPE_DOUBLE: "dbl",
    _FD.TYPE_FLOAT: "flt",
    _FD.TYPE_INT64: "u64",
    _FD.TYPE_UINT64: "u64",
    _FD.TYPE_INT32: "u64",
    _FD.TYPE_UINT32: "u64",
    _FD.TYPE_BOOL: "bool_field",
    _FD.TYPE_STRING: "string",
    _FD.TYPE_BYTES: "byt",
    _FD.TYPE_FIXED64: "fix64",
    _FD.TYPE_SFIXED64: "fix64",
    _FD.TYPE_FIXED32: "fix32",
    _FD.TYPE_SFIXED32: "fix32",
    _FD.TYPE_SINT32: "sint32",
    _FD.TYPE_SINT64: "sint64",
}

# Field helper for a packed repeated scalar field.
PACKED_WIRE_HELPER: Final[dict[int, str]] = {
    _FD.TYPE_DOUBLE: "packed_double",
    _FD.TYPE_INT64: "packed_uint64",
    _FD.TYPE_UINT64: "packed_uint64",
    _FD.TYPE_INT32: "packed_uint64",
    _FD.TYPE_UINT32: "packed_uint64",
    _FD.TYPE_BOOL: "packed_uint64",
    _FD.TYPE_FIXED64: "packed_fix64",
    _FD.TYPE_SFIXED64: "packed_fix64",
    _FD.TYPE_FIXED32: "packed_fix32",
    _FD.TYPE_SFIXED32: "packed_fix32",
}

# Inline oneof member encoding. A oneof member is always written even when its
# value equals the proto3 default, so the field helpers (which omit defaults)
# cannot be used. Each entry maps a proto scalar type to
# (wire_type_constant, value_expression_template). The template's ``{v}``
# placeholder is replaced with the attribute access expression.
ONEOF_SCALAR_INLINE: Final[dict[int, tuple[str, str]]] = {
    _FD.TYPE_STRING: ("WT_LEN", "_STRING"),  # handled specially (length prefix)
    _FD.TYPE_BYTES: ("WT_LEN", "_BYTES"),  # handled specially (length prefix)
    _FD.TYPE_BOOL: ("WT_VARINT", "encode_varint(1 if {v} else 0)"),
    _FD.TYPE_INT32: ("WT_VARINT", "encode_int({v})"),
    _FD.TYPE_INT64: ("WT_VARINT", "encode_int({v})"),
    _FD.TYPE_UINT32: ("WT_VARINT", "encode_varint({v})"),
    _FD.TYPE_UINT64: ("WT_VARINT", "encode_varint({v})"),
    _FD.TYPE_SINT32: ("WT_VARINT", "encode_sint32({v})"),
    _FD.TYPE_SINT64: ("WT_VARINT", "encode_sint64({v})"),
    _FD.TYPE_DOUBLE: ("WT_64BIT", 'pack("<d", {v})'),
    _FD.TYPE_FLOAT: ("WT_32BIT", 'pack("<f", {v})'),
    _FD.TYPE_FIXED64: ("WT_64BIT", "encode_fixed64({v})"),
    _FD.TYPE_SFIXED64: ("WT_64BIT", "encode_sfixed64({v})"),
    _FD.TYPE_FIXED32: ("WT_32BIT", "encode_fixed32({v})"),
    _FD.TYPE_SFIXED32: ("WT_32BIT", "encode_sfixed32({v})"),
}


def get_python_type(proto_type: int) -> str:
    """Return the Python type name corresponding to a protobuf scalar type."""
    if proto_type not in PROTO_TO_PYTHON:
        raise ValueError(f"Unknown protobuf type: {proto_type}")
    return PROTO_TO_PYTHON[proto_type]


def get_default_value(proto_type: int) -> str:
    """Return the proto3 default value literal for a scalar type as a string."""
    return PROTO_DEFAULTS.get(proto_type, "None")
