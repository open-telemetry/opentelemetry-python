# tests/test__scalars.py
#
# Tests for all scalar encoders in _scalars.py. The oracle for fixed-width
# types is Python's struct module (independent standard-library implementation).
# Variable-width types (varint-backed) are verified against hand-computed
# expected byte literals derived from the protobuf wire-format spec.

from math import e, inf, nan, pi, tau
from struct import pack, unpack

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory
from pytest import mark

from opentelemetry._proto._pyprotobuf import (
    encode_bool,
    encode_bytes,
    encode_double,
    encode_fixed32,
    encode_fixed64,
    encode_float,
    encode_int,
    encode_sfixed32,
    encode_sfixed64,
    encode_sint32,
    encode_sint64,
    encode_string,
    encode_tag,
    encode_uint32,
    encode_uint64,
    encode_varint,
)


# ── encode_uint32 ──────────────────────────────────────────────────────────────


def test_uint32_zero() -> None:
    assert encode_uint32(0) == b"\x00"


def test_uint32_one() -> None:
    assert encode_uint32(1) == b"\x01"


def test_uint32_max() -> None:
    # 2^32-1 encodes as five varint bytes: all low bits set.
    assert encode_uint32(2**32 - 1) == b"\xff\xff\xff\xff\x0f"


@mark.parametrize("value", [0, 1, 127, 128, 255, 300, 2**16 - 1, 2**16, 2**32 - 1])
def test_uint32_matches_uint64_encoding(value: int) -> None:
    # uint32 and uint64 share the same varint encoding for values in [0, 2^32-1].
    assert encode_uint32(value) == encode_uint64(value)


# ── encode_uint64 ──────────────────────────────────────────────────────────────


def test_uint64_zero() -> None:
    assert encode_uint64(0) == b"\x00"


def test_uint64_max() -> None:
    assert encode_uint64(2**64 - 1) == b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\x01"


@mark.parametrize(
    "value",
    [0, 1, 127, 128, 2**32 - 1, 2**32, 2**56, 2**63 - 1, 2**63, 2**64 - 1],
)
def test_uint64_is_varint(value: int) -> None:
    assert encode_uint64(value) == encode_varint(value)


# ── encode_bool ────────────────────────────────────────────────────────────────


def test_bool_false() -> None:
    assert encode_bool(False) == b"\x00"


def test_bool_true() -> None:
    assert encode_bool(True) == b"\x01"


def test_bool_truthy_int() -> None:
    # Any truthy value must encode as 1, not as the integer itself.
    assert encode_bool(42) == b"\x01"


def test_bool_falsy_int() -> None:
    assert encode_bool(0) == b"\x00"


# ── encode_int ─────────────────────────────────────────────────────────────────
#
# int32 / int64: non-negative values encode like varint; negative values are
# sign-extended to 64 bits (two's complement) then encoded as a varint.


def test_int_zero() -> None:
    assert encode_int(0) == b"\x00"


def test_int_positive_small() -> None:
    assert encode_int(1) == b"\x01"


def test_int_positive_300() -> None:
    assert encode_int(300) == b"\xac\x02"


def test_int_negative_one() -> None:
    # -1 in 64-bit two's complement is 2^64-1, which requires 10 varint bytes.
    assert encode_int(-1) == b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\x01"


def test_int_negative_two() -> None:
    assert encode_int(-2) == b"\xfe\xff\xff\xff\xff\xff\xff\xff\xff\x01"


def test_int_int32_min() -> None:
    # -2^31 in 64-bit two's complement: bits 31-63 all set, bits 0-30 clear.
    assert encode_int(-(2**31)) == b"\x80\x80\x80\x80\xf8\xff\xff\xff\xff\x01"


def test_int_int64_min() -> None:
    # -2^63: only bit 63 set. Nine groups of 0x80, then final byte 0x01.
    assert encode_int(-(2**63)) == b"\x80\x80\x80\x80\x80\x80\x80\x80\x80\x01"


# ── encode_sint32 ──────────────────────────────────────────────────────────────
#
# ZigZag32: n>=0 → 2n, n<0 → -2n-1. Result fits in 32 bits; encoded as varint.


def test_sint32_zero() -> None:
    # ZigZag(0) = 0
    assert encode_sint32(0) == b"\x00"


def test_sint32_negative_one() -> None:
    # ZigZag(-1) = 1
    assert encode_sint32(-1) == b"\x01"


def test_sint32_positive_one() -> None:
    # ZigZag(1) = 2
    assert encode_sint32(1) == b"\x02"


def test_sint32_negative_two() -> None:
    # ZigZag(-2) = 3
    assert encode_sint32(-2) == b"\x03"


def test_sint32_positive_two() -> None:
    # ZigZag(2) = 4
    assert encode_sint32(2) == b"\x04"


def test_sint32_max() -> None:
    # ZigZag(2^31-1) = 2^32-2 = 0xFFFFFFFE → 5-byte varint
    assert encode_sint32(2**31 - 1) == b"\xfe\xff\xff\xff\x0f"


def test_sint32_min() -> None:
    # ZigZag(-2^31) = 2^32-1 = 0xFFFFFFFF → 5-byte varint
    assert encode_sint32(-(2**31)) == b"\xff\xff\xff\xff\x0f"


@mark.parametrize("value", [0, 1, -1, 2, -2, 150, -150, 2**31 - 1, -(2**31)])
def test_sint32_zigzag(value: int) -> None:
    # Verify ZigZag correctness using the arithmetic definition as oracle.
    zigzag = 2 * value if value >= 0 else -2 * value - 1
    assert encode_sint32(value) == encode_varint(zigzag)


# ── encode_sint64 ──────────────────────────────────────────────────────────────
#
# ZigZag64: same interleaving as sint32 but over the 64-bit domain.


def test_sint64_zero() -> None:
    assert encode_sint64(0) == b"\x00"


def test_sint64_negative_one() -> None:
    assert encode_sint64(-1) == b"\x01"


def test_sint64_positive_one() -> None:
    assert encode_sint64(1) == b"\x02"


def test_sint64_max() -> None:
    # ZigZag64(2^63-1) = 2^64-2 = 0xFFFFFFFFFFFFFFFE → 10-byte varint
    assert encode_sint64(2**63 - 1) == b"\xfe\xff\xff\xff\xff\xff\xff\xff\xff\x01"


def test_sint64_min() -> None:
    # ZigZag64(-2^63) = 2^64-1 = 0xFFFFFFFFFFFFFFFF → 10-byte varint
    assert encode_sint64(-(2**63)) == b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\x01"


@mark.parametrize(
    "value",
    [0, 1, -1, 2, -2, 150, -150, 2**31 - 1, -(2**31), 2**32, -(2**32), 2**63 - 1, -(2**63)],
)
def test_sint64_zigzag(value: int) -> None:
    zigzag = 2 * value if value >= 0 else -2 * value - 1
    assert encode_sint64(value) == encode_varint(zigzag)


# ── encode_float ───────────────────────────────────────────────────────────────


def test_float_zero() -> None:
    assert encode_float(0.0) == b"\x00\x00\x00\x00"


def test_float_one() -> None:
    # IEEE 754 single 1.0 = 0x3F800000; little-endian: 00 00 80 3F
    assert encode_float(1.0) == b"\x00\x00\x80\x3f"


def test_float_negative_one() -> None:
    # IEEE 754 single -1.0 = 0xBF800000; little-endian: 00 00 80 BF
    assert encode_float(-1.0) == b"\x00\x00\x80\xbf"


def test_float_always_four_bytes() -> None:
    assert len(encode_float(0.0)) == 4
    assert len(encode_float(1.0)) == 4
    assert len(encode_float(inf)) == 4


@mark.parametrize(
    "value",
    [
        0.0, 1.0, -1.0, 0.5, -0.5, 0.25, 2.0, -2.0,
        unpack("<f", b"\xff\x7f\x7f\x7f")[0],
        inf, -inf,
    ],
)
def test_float_matches_struct(value: float) -> None:
    assert encode_float(value) == pack("<f", value)


def test_float_nan_matches_struct() -> None:
    assert encode_float(nan) == pack("<f", nan)


# ── encode_double ──────────────────────────────────────────────────────────────


def test_double_zero() -> None:
    assert encode_double(0.0) == b"\x00\x00\x00\x00\x00\x00\x00\x00"


def test_double_one() -> None:
    # IEEE 754 double 1.0 = 0x3FF0000000000000; little-endian: 00 00 00 00 00 00 F0 3F
    assert encode_double(1.0) == b"\x00\x00\x00\x00\x00\x00\xf0\x3f"


def test_double_negative_one() -> None:
    assert encode_double(-1.0) == b"\x00\x00\x00\x00\x00\x00\xf0\xbf"


def test_double_always_eight_bytes() -> None:
    assert len(encode_double(0.0)) == 8
    assert len(encode_double(1.0)) == 8
    assert len(encode_double(inf)) == 8


@mark.parametrize(
    "value",
    [
        0.0, 1.0, -1.0, 0.5, -0.5, pi, e, tau,
        1e100, -1e100, 5e-324, 1.7976931348623157e308, inf, -inf,
    ],
)
def test_double_matches_struct(value: float) -> None:
    assert encode_double(value) == pack("<d", value)


def test_double_nan_matches_struct() -> None:
    assert encode_double(nan) == pack("<d", nan)


# ── encode_fixed32 ─────────────────────────────────────────────────────────────


def test_fixed32_zero() -> None:
    assert encode_fixed32(0) == b"\x00\x00\x00\x00"


def test_fixed32_one() -> None:
    assert encode_fixed32(1) == b"\x01\x00\x00\x00"


def test_fixed32_max() -> None:
    assert encode_fixed32(2**32 - 1) == b"\xff\xff\xff\xff"


def test_fixed32_always_four_bytes() -> None:
    assert len(encode_fixed32(0)) == 4
    assert len(encode_fixed32(2**32 - 1)) == 4


@mark.parametrize("value", [0, 1, 127, 128, 255, 256, 2**16 - 1, 2**16, 2**24, 2**32 - 1])
def test_fixed32_matches_struct(value: int) -> None:
    assert encode_fixed32(value) == pack("<I", value)


# ── encode_sfixed32 ────────────────────────────────────────────────────────────


def test_sfixed32_zero() -> None:
    assert encode_sfixed32(0) == b"\x00\x00\x00\x00"


def test_sfixed32_negative_one() -> None:
    # -1 in 32-bit two's complement is 0xFFFFFFFF; all bytes 0xFF.
    assert encode_sfixed32(-1) == b"\xff\xff\xff\xff"


def test_sfixed32_min() -> None:
    # -2^31 = 0x80000000 little-endian: 00 00 00 80
    assert encode_sfixed32(-(2**31)) == b"\x00\x00\x00\x80"


def test_sfixed32_max() -> None:
    # 2^31-1 = 0x7FFFFFFF little-endian: FF FF FF 7F
    assert encode_sfixed32(2**31 - 1) == b"\xff\xff\xff\x7f"


def test_sfixed32_always_four_bytes() -> None:
    assert len(encode_sfixed32(0)) == 4
    assert len(encode_sfixed32(-1)) == 4


@mark.parametrize("value", [0, 1, -1, 127, -128, 2**15 - 1, -(2**15), 2**31 - 1, -(2**31)])
def test_sfixed32_matches_struct(value: int) -> None:
    assert encode_sfixed32(value) == pack("<i", value)


# ── encode_fixed64 ─────────────────────────────────────────────────────────────


def test_fixed64_zero() -> None:
    assert encode_fixed64(0) == b"\x00\x00\x00\x00\x00\x00\x00\x00"


def test_fixed64_one() -> None:
    assert encode_fixed64(1) == b"\x01\x00\x00\x00\x00\x00\x00\x00"


def test_fixed64_max() -> None:
    assert encode_fixed64(2**64 - 1) == b"\xff\xff\xff\xff\xff\xff\xff\xff"


def test_fixed64_always_eight_bytes() -> None:
    assert len(encode_fixed64(0)) == 8
    assert len(encode_fixed64(2**64 - 1)) == 8


@mark.parametrize(
    "value", [0, 1, 255, 2**16 - 1, 2**32 - 1, 2**32, 2**48, 2**63, 2**64 - 1]
)
def test_fixed64_matches_struct(value: int) -> None:
    assert encode_fixed64(value) == pack("<Q", value)


# ── encode_sfixed64 ────────────────────────────────────────────────────────────


def test_sfixed64_zero() -> None:
    assert encode_sfixed64(0) == b"\x00\x00\x00\x00\x00\x00\x00\x00"


def test_sfixed64_negative_one() -> None:
    # -1 in 64-bit two's complement: all bytes 0xFF.
    assert encode_sfixed64(-1) == b"\xff\xff\xff\xff\xff\xff\xff\xff"


def test_sfixed64_min() -> None:
    # -2^63 = 0x8000000000000000 little-endian: 00 00 00 00 00 00 00 80
    assert encode_sfixed64(-(2**63)) == b"\x00\x00\x00\x00\x00\x00\x00\x80"


def test_sfixed64_max() -> None:
    # 2^63-1 = 0x7FFFFFFFFFFFFFFF little-endian: FF FF FF FF FF FF FF 7F
    assert encode_sfixed64(2**63 - 1) == b"\xff\xff\xff\xff\xff\xff\xff\x7f"


def test_sfixed64_always_eight_bytes() -> None:
    assert len(encode_sfixed64(0)) == 8
    assert len(encode_sfixed64(-1)) == 8


@mark.parametrize(
    "value",
    [0, 1, -1, 127, -128, 2**31 - 1, -(2**31), 2**32, -(2**32), 2**63 - 1, -(2**63)],
)
def test_sfixed64_matches_struct(value: int) -> None:
    assert encode_sfixed64(value) == pack("<q", value)


# ── encode_string ──────────────────────────────────────────────────────────────
#
# Wire type 2: varint(len(utf8_bytes)) + utf8_bytes


def test_string_empty() -> None:
    assert encode_string("") == b"\x00"


def test_string_ascii_single_char() -> None:
    assert encode_string("A") == b"\x01A"


def test_string_ascii_word() -> None:
    assert encode_string("hi") == b"\x02hi"


def test_string_two_byte_utf8() -> None:
    # "é" = U+00E9, UTF-8: 0xC3 0xA9 (2 bytes, not 1 character)
    assert encode_string("é") == b"\x02\xc3\xa9"


def test_string_three_byte_utf8() -> None:
    # "中" = U+4E2D, UTF-8: 0xE4 0xB8 0xAD (3 bytes)
    assert encode_string("中") == b"\x03\xe4\xb8\xad"


def test_string_length_counts_bytes_not_chars() -> None:
    # "日本語" is 3 characters but 9 UTF-8 bytes.
    value = "日本語"
    result = encode_string(value)
    assert result[0] == 9      # byte count, not char count
    assert result[1:] == value.encode("utf-8")


def test_string_two_byte_length_prefix() -> None:
    # A string of 128 ASCII characters needs a 2-byte varint length prefix.
    result = encode_string("a" * 128)
    assert result[:2] == b"\x80\x01"
    assert result[2:] == b"a" * 128


@mark.parametrize(
    "value",
    ["", "a", "hello", "café", "Ünïcödé", "日本語", "中文", "\U0001F600", "hello 世界"],
)
def test_string_length_prefix_matches_utf8_bytecount(value: str) -> None:
    utf8 = value.encode("utf-8")
    result = encode_string(value)
    assert result == encode_varint(len(utf8)) + utf8


# ── encode_bytes ───────────────────────────────────────────────────────────────


def test_bytes_empty() -> None:
    assert encode_bytes(b"") == b"\x00"


def test_bytes_single_byte() -> None:
    assert encode_bytes(b"\x42") == b"\x01\x42"


def test_bytes_high_bytes() -> None:
    # Values >= 0x80 must pass through verbatim.
    assert encode_bytes(b"\xff\x80") == b"\x02\xff\x80"


def test_bytes_null_bytes() -> None:
    assert encode_bytes(b"\x00\x00\x00") == b"\x03\x00\x00\x00"


def test_bytes_all_byte_values() -> None:
    # 256-byte payload; length prefix is encode_varint(256) = b'\x80\x02'
    payload = bytes(range(256))
    result = encode_bytes(payload)
    assert result[:2] == b"\x80\x02"
    assert result[2:] == payload


def test_bytes_two_byte_length_prefix() -> None:
    value = b"\xab" * 128
    result = encode_bytes(value)
    assert result[:2] == b"\x80\x01"
    assert result[2:] == value


@mark.parametrize(
    "value",
    [b"", b"\x00", b"\xff", b"hello", b"\x00\x01\x02\x03", b"\x80\x81\x82", b"\xfe\xff"],
)
def test_bytes_length_prefix_matches_payload_length(value: bytes) -> None:
    result = encode_bytes(value)
    assert result == encode_varint(len(value)) + value


# ── oracle — byte-for-byte comparison with google.protobuf ────────────────────
#
# A proto2 message with one optional field per scalar type is used as the
# oracle.  proto2 is chosen because it serialises every field that has been
# explicitly set, including fields whose value equals the type default (0,
# False, b"", ""), which proto3 would silently omit.
#
# For each function under test the pattern is:
#   expected = encode_tag(field_number, wire_type) + encode_X(value)
#   assert _ScalarMessage(**{field_name: value}).SerializeToString() == expected
#
# Field number assignments:
_F_UINT32   = 1   # wt 0
_F_UINT64   = 2   # wt 0
_F_BOOL     = 3   # wt 0
_F_INT32    = 4   # wt 0
_F_INT64    = 5   # wt 0
_F_SINT32   = 6   # wt 0
_F_SINT64   = 7   # wt 0
_F_FLOAT    = 8   # wt 5
_F_DOUBLE   = 9   # wt 1
_F_FIXED32  = 10  # wt 5
_F_SFIXED32 = 11  # wt 5
_F_FIXED64  = 12  # wt 1
_F_SFIXED64 = 13  # wt 1
_F_STRING   = 14  # wt 2
_F_BYTES    = 15  # wt 2

_WT_VARINT = 0
_WT_64BIT  = 1
_WT_LEN    = 2
_WT_32BIT  = 5


def _build_scalar_message_class():
    file_proto = descriptor_pb2.FileDescriptorProto()
    file_proto.name = "opentelemetry_pyproto_test_scalars.proto"
    file_proto.syntax = "proto2"
    msg_proto = file_proto.message_type.add()
    msg_proto.name = "ScalarMessage"

    T = descriptor_pb2.FieldDescriptorProto

    def _add(name, number, type_id):
        f = msg_proto.field.add()
        f.name = name
        f.number = number
        f.type = type_id
        f.label = T.LABEL_OPTIONAL

    _add("uint32_field",   _F_UINT32,   T.TYPE_UINT32)
    _add("uint64_field",   _F_UINT64,   T.TYPE_UINT64)
    _add("bool_field",     _F_BOOL,     T.TYPE_BOOL)
    _add("int32_field",    _F_INT32,    T.TYPE_INT32)
    _add("int64_field",    _F_INT64,    T.TYPE_INT64)
    _add("sint32_field",   _F_SINT32,   T.TYPE_SINT32)
    _add("sint64_field",   _F_SINT64,   T.TYPE_SINT64)
    _add("float_field",    _F_FLOAT,    T.TYPE_FLOAT)
    _add("double_field",   _F_DOUBLE,   T.TYPE_DOUBLE)
    _add("fixed32_field",  _F_FIXED32,  T.TYPE_FIXED32)
    _add("sfixed32_field", _F_SFIXED32, T.TYPE_SFIXED32)
    _add("fixed64_field",  _F_FIXED64,  T.TYPE_FIXED64)
    _add("sfixed64_field", _F_SFIXED64, T.TYPE_SFIXED64)
    _add("string_field",   _F_STRING,   T.TYPE_STRING)
    _add("bytes_field",    _F_BYTES,    T.TYPE_BYTES)

    pool = descriptor_pool.DescriptorPool()
    pool.Add(file_proto)
    return message_factory.GetMessageClass(pool.FindMessageTypeByName("ScalarMessage"))


_ScalarMessage = _build_scalar_message_class()


def _s(field_name: str, value) -> bytes:
    return _ScalarMessage(**{field_name: value}).SerializeToString()


# ── encode_uint32 oracle ───────────────────────────────────────────────────────

@mark.parametrize("value", [0, 1, 127, 128, 255, 300, 2**16, 2**32 - 1])
def test_encode_uint32_matches_protobuf(value: int) -> None:
    assert _s("uint32_field", value) == encode_tag(_F_UINT32, _WT_VARINT) + encode_uint32(value)


# ── encode_uint64 oracle ───────────────────────────────────────────────────────

@mark.parametrize("value", [0, 1, 127, 128, 2**32 - 1, 2**32, 2**63, 2**64 - 1])
def test_encode_uint64_matches_protobuf(value: int) -> None:
    assert _s("uint64_field", value) == encode_tag(_F_UINT64, _WT_VARINT) + encode_uint64(value)


# ── encode_bool oracle ─────────────────────────────────────────────────────────

@mark.parametrize("value", [False, True])
def test_encode_bool_matches_protobuf(value: bool) -> None:
    assert _s("bool_field", value) == encode_tag(_F_BOOL, _WT_VARINT) + encode_bool(value)


# ── encode_int oracle (int32 / int64) ─────────────────────────────────────────

@mark.parametrize("value", [0, 1, 127, 128, 2**31 - 1, -1, -2, -128, -(2**31)])
def test_encode_int_int32_matches_protobuf(value: int) -> None:
    assert _s("int32_field", value) == encode_tag(_F_INT32, _WT_VARINT) + encode_int(value)


@mark.parametrize("value", [0, 1, 2**63 - 1, -1, -(2**63)])
def test_encode_int_int64_matches_protobuf(value: int) -> None:
    assert _s("int64_field", value) == encode_tag(_F_INT64, _WT_VARINT) + encode_int(value)


# ── encode_sint32 oracle ───────────────────────────────────────────────────────

@mark.parametrize("value", [0, 1, -1, 2, -2, 150, -150, 2**31 - 1, -(2**31)])
def test_encode_sint32_matches_protobuf(value: int) -> None:
    assert _s("sint32_field", value) == encode_tag(_F_SINT32, _WT_VARINT) + encode_sint32(value)


# ── encode_sint64 oracle ───────────────────────────────────────────────────────

@mark.parametrize("value", [0, 1, -1, 150, -150, 2**63 - 1, -(2**63)])
def test_encode_sint64_matches_protobuf(value: int) -> None:
    assert _s("sint64_field", value) == encode_tag(_F_SINT64, _WT_VARINT) + encode_sint64(value)


# ── encode_float oracle ────────────────────────────────────────────────────────

@mark.parametrize("value", [0.0, 1.0, -1.0, 0.5, inf, -inf])
def test_encode_float_matches_protobuf(value: float) -> None:
    assert _s("float_field", value) == encode_tag(_F_FLOAT, _WT_32BIT) + encode_float(value)


# ── encode_double oracle ───────────────────────────────────────────────────────

@mark.parametrize("value", [0.0, 1.0, -1.0, pi, 1e100, inf, -inf])
def test_encode_double_matches_protobuf(value: float) -> None:
    assert _s("double_field", value) == encode_tag(_F_DOUBLE, _WT_64BIT) + encode_double(value)


# ── encode_fixed32 oracle ──────────────────────────────────────────────────────

@mark.parametrize("value", [0, 1, 255, 2**16, 2**32 - 1])
def test_encode_fixed32_matches_protobuf(value: int) -> None:
    assert _s("fixed32_field", value) == encode_tag(_F_FIXED32, _WT_32BIT) + encode_fixed32(value)


# ── encode_sfixed32 oracle ─────────────────────────────────────────────────────

@mark.parametrize("value", [0, 1, -1, 2**31 - 1, -(2**31)])
def test_encode_sfixed32_matches_protobuf(value: int) -> None:
    assert _s("sfixed32_field", value) == encode_tag(_F_SFIXED32, _WT_32BIT) + encode_sfixed32(value)


# ── encode_fixed64 oracle ──────────────────────────────────────────────────────

@mark.parametrize("value", [0, 1, 2**32, 2**64 - 1])
def test_encode_fixed64_matches_protobuf(value: int) -> None:
    assert _s("fixed64_field", value) == encode_tag(_F_FIXED64, _WT_64BIT) + encode_fixed64(value)


# ── encode_sfixed64 oracle ─────────────────────────────────────────────────────

@mark.parametrize("value", [0, 1, -1, 2**63 - 1, -(2**63)])
def test_encode_sfixed64_matches_protobuf(value: int) -> None:
    assert _s("sfixed64_field", value) == encode_tag(_F_SFIXED64, _WT_64BIT) + encode_sfixed64(value)


# ── encode_string oracle ───────────────────────────────────────────────────────

@mark.parametrize("value", ["", "a", "hello", "café", "日本語", "\U0001F600", "x" * 128])
def test_encode_string_matches_protobuf(value: str) -> None:
    assert _s("string_field", value) == encode_tag(_F_STRING, _WT_LEN) + encode_string(value)


# ── encode_bytes oracle ────────────────────────────────────────────────────────

@mark.parametrize("value", [b"", b"\x00", b"\xff", b"hello", b"\x80\x81\x82", b"\xab" * 128])
def test_encode_bytes_matches_protobuf(value: bytes) -> None:
    assert _s("bytes_field", value) == encode_tag(_F_BYTES, _WT_LEN) + encode_bytes(value)
