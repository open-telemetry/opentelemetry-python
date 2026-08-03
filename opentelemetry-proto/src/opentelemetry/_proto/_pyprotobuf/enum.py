"""Encoder for protobuf enum field values.

Protobuf enum fields use wire type 0 (varint) and share the exact same wire
encoding as int32. This module exists as its own file — separate from
_scalars.py — because an enum is not a scalar type. Enum fields carry named
constants, not raw numeric values. The distinction matters at the .proto
language level even though the wire encoding is identical to int32.

Reference:
    https://protobuf.dev/programming-guides/encoding/
"""

from .scalars import encode_int


def encode_enum(value: int) -> bytes:
    """Encode a protobuf enum value.

    Protobuf enum fields use wire type 0 (varint) and share the exact same
    wire encoding as int32. The encoding guide states:

        Enum values are always 32-bit integers and the encoding follows the
        same rules as int32.

    Reference:
        https://protobuf.dev/programming-guides/encoding/

    Enum values in practice
    -----------------------
    In proto3, enum values defined in a .proto file are non-negative named
    constants (0, 1, 2, …). The first value of any proto3 enum must be 0.

    In proto2, negative enum values are legal. Negative enum values can also
    appear in proto3 messages received from a proto2 sender: the decoder
    preserves them as their raw integer value. In both cases the int32 wire
    encoding applies, meaning negative enum values produce a 10-byte varint
    (via 64-bit sign extension, exactly as encode_int does for negative ints).

    This function is a thin wrapper around encode_int. Its purpose is
    readability at call sites: code that encodes an enum field can call
    encode_enum to make the intent explicit, rather than encode_int, which
    suggests an arbitrary integer.
    """
    # Delegate entirely to encode_int, which implements the int32 wire rule:
    #
    #   - Non-negative values → encode_varint directly (compact, 1–5 bytes).
    #   - Negative values → mask to 64-bit unsigned two's complement, then
    #     encode_varint (always 10 bytes).
    #
    # No additional logic is needed: the spec defines enum encoding as
    # identical to int32, so encode_int is the correct and complete
    # implementation of both.
    return encode_int(value)
