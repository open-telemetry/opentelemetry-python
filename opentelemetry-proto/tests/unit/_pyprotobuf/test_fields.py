# tests/_pyprotobuf/test_fields.py
#
# Tests for the proto3 field-level encoding helpers in fields.py.
#
# Every test follows the same pattern:
#   1. Verify default-omission: proto3 defaults (zero, empty, None) produce b"".
#   2. Verify tag: the first byte(s) of the output encode the correct field
#      number and wire type using the formula (field_number << 3) | wire_type.
#   3. Verify value: the bytes after the tag match the correct wire encoding.
#
# All expected byte literals are derived by hand from the protobuf wire-format
# specification and cross-checked against encode_tag + the primitive encoders.

from math import inf, nan
from struct import pack

from pytest import mark

from opentelemetry._proto._pyprotobuf import encode_tag, encode_varint
from opentelemetry._proto._pyprotobuf.fields import (
    WT_32BIT,
    WT_64BIT,
    WT_LEN,
    WT_VARINT,
    bool_field,
    byt,
    dbl,
    fix32,
    fix64,
    msg,
    opt_dbl,
    packed_double,
    packed_fix64,
    packed_uint64,
    sint32,
    string,
    u64,
)


# ── Wire-type constants ────────────────────────────────────────────────────────


def test_wt_varint_is_zero() -> None:
    assert WT_VARINT == 0


def test_wt_64bit_is_one() -> None:
    assert WT_64BIT == 1


def test_wt_len_is_two() -> None:
    assert WT_LEN == 2


def test_wt_32bit_is_five() -> None:
    assert WT_32BIT == 5


# ── msg ────────────────────────────────────────────────────────────────────────
#
# msg always writes (no omission for empty content). The caller decides whether
# to guard on None. Wire layout: tag | varint(len(content)) | content.


def test_msg_empty_content() -> None:
    # An empty sub-message produces tag + varint(0), not b"".
    # tag(1, 2) = (1<<3)|2 = 10 = 0x0A; varint(0) = 0x00
    assert msg(1, b"") == b"\x0a\x00"


def test_msg_single_byte_content() -> None:
    # tag(1, 2) = 0x0A; varint(1) = 0x01; content = 0xAB
    assert msg(1, b"\xab") == b"\x0a\x01\xab"


def test_msg_two_byte_content() -> None:
    # tag(1, 2) = 0x0A; varint(2) = 0x02; content = 0xDE 0xAD
    assert msg(1, b"\xde\xad") == b"\x0a\x02\xde\xad"


def test_msg_field_number_2() -> None:
    # tag(2, 2) = (2<<3)|2 = 18 = 0x12
    assert msg(2, b"\x01") == b"\x12\x01\x01"


def test_msg_tag_uses_wt_len() -> None:
    result = msg(3, b"\xff")
    assert result[0] == (3 << 3) | WT_LEN


def test_msg_length_prefix_correct_for_long_content() -> None:
    # 128 bytes of content — length prefix needs two varint bytes (0x80 0x01)
    content = b"\x00" * 128
    result = msg(1, content)
    assert result[0:1] == b"\x0a"
    assert result[1:3] == b"\x80\x01"
    assert result[3:] == content


def test_msg_matches_formula() -> None:
    content = b"\x42" * 5
    field = 4
    expected = encode_tag(field, WT_LEN) + encode_varint(len(content)) + content
    assert msg(field, content) == expected


# ── string ─────────────────────────────────────────────────────────────────────
#
# Omit when empty. Wire layout: tag (wt=2) | varint(len(utf8)) | utf8 bytes.


def test_string_empty_is_omitted() -> None:
    assert string(1, "") == b""


def test_string_ascii() -> None:
    # tag(1, 2) = 0x0A; varint(2) = 0x02; "hi" = 0x68 0x69
    assert string(1, "hi") == b"\x0a\x02hi"


def test_string_single_char() -> None:
    assert string(1, "A") == b"\x0a\x01A"


def test_string_two_byte_utf8() -> None:
    # "é" = U+00E9, UTF-8: C3 A9 (2 bytes)
    assert string(1, "é") == b"\x0a\x02\xc3\xa9"


def test_string_three_byte_utf8() -> None:
    # "中" = U+4E2D, UTF-8: E4 B8 AD (3 bytes)
    assert string(1, "中") == b"\x0a\x03\xe4\xb8\xad"


def test_string_field_number_affects_tag() -> None:
    # tag(3, 2) = (3<<3)|2 = 26 = 0x1A
    assert string(3, "x") == b"\x1a\x01x"


def test_string_tag_uses_wt_len() -> None:
    result = string(2, "hello")
    assert result[0] == (2 << 3) | WT_LEN


def test_string_length_is_byte_count_not_char_count() -> None:
    # "日" = 3 UTF-8 bytes; length prefix must be 3, not 1
    result = string(1, "日")
    assert result[1] == 3


@mark.parametrize("value", ["a", "hello", "café", "Ünïcödé", "日本語", "\U0001F600"])
def test_string_matches_formula(value: str) -> None:
    utf8 = value.encode("utf-8")
    expected = encode_tag(1, WT_LEN) + encode_varint(len(utf8)) + utf8
    assert string(1, value) == expected


# ── byt ────────────────────────────────────────────────────────────────────────
#
# Omit when empty. Wire layout: tag (wt=2) | varint(len) | raw bytes.
# Identical layout to string but no UTF-8 encoding step.


def test_byt_empty_is_omitted() -> None:
    assert byt(1, b"") == b""


def test_byt_single_byte() -> None:
    # tag(1, 2) = 0x0A; varint(1) = 0x01; payload = 0x42
    assert byt(1, b"\x42") == b"\x0a\x01\x42"


def test_byt_two_bytes() -> None:
    assert byt(1, b"\xde\xad") == b"\x0a\x02\xde\xad"


def test_byt_null_bytes_preserved() -> None:
    assert byt(1, b"\x00\x00") == b"\x0a\x02\x00\x00"


def test_byt_high_bytes_preserved() -> None:
    assert byt(1, b"\xff\x80") == b"\x0a\x02\xff\x80"


def test_byt_field_number_affects_tag() -> None:
    # tag(7, 2) = (7<<3)|2 = 58 = 0x3A
    assert byt(7, b"\x01") == b"\x3a\x01\x01"


def test_byt_tag_uses_wt_len() -> None:
    result = byt(2, b"\x99")
    assert result[0] == (2 << 3) | WT_LEN


@mark.parametrize("value", [b"\x00", b"\xff", b"hello", b"\x00\x01\x02", b"\x80\x81\x82"])
def test_byt_matches_formula(value: bytes) -> None:
    expected = encode_tag(1, WT_LEN) + encode_varint(len(value)) + value
    assert byt(1, value) == expected


# ── u64 ────────────────────────────────────────────────────────────────────────
#
# Omit when zero. Wire layout: tag (wt=0) | varint(value).


def test_u64_zero_is_omitted() -> None:
    assert u64(1, 0) == b""


def test_u64_one() -> None:
    # tag(1, 0) = 0x08; varint(1) = 0x01
    assert u64(1, 1) == b"\x08\x01"


def test_u64_127() -> None:
    assert u64(1, 127) == b"\x08\x7f"


def test_u64_128() -> None:
    # varint(128) = 0x80 0x01
    assert u64(1, 128) == b"\x08\x80\x01"


def test_u64_field_number_affects_tag() -> None:
    # tag(4, 0) = (4<<3)|0 = 32 = 0x20
    assert u64(4, 1) == b"\x20\x01"


def test_u64_tag_uses_wt_varint() -> None:
    result = u64(5, 99)
    assert result[0] == (5 << 3) | WT_VARINT


@mark.parametrize("value", [1, 127, 128, 255, 300, 2**32 - 1, 2**32, 2**64 - 1])
def test_u64_matches_formula(value: int) -> None:
    expected = encode_tag(1, WT_VARINT) + encode_varint(value)
    assert u64(1, value) == expected


# ── bool_field ─────────────────────────────────────────────────────────────────
#
# Omit when False. True encodes as varint 1. Wire type is WT_VARINT.


def test_bool_false_is_omitted() -> None:
    assert bool_field(1, False) == b""


def test_bool_true() -> None:
    # tag(1, 0) = 0x08; varint(1) = 0x01
    assert bool_field(1, True) == b"\x08\x01"


def test_bool_field_number_affects_tag() -> None:
    # tag(6, 0) = (6<<3)|0 = 48 = 0x30
    assert bool_field(6, True) == b"\x30\x01"


def test_bool_tag_uses_wt_varint() -> None:
    result = bool_field(2, True)
    assert result[0] == (2 << 3) | WT_VARINT


def test_bool_true_always_encodes_as_one() -> None:
    # bool True always produces a varint 1 regardless of the Python truthiness integer
    assert bool_field(1, True) == encode_tag(1, WT_VARINT) + b"\x01"


# ── fix32 ──────────────────────────────────────────────────────────────────────
#
# Omit when zero. Wire layout: tag (wt=5) | 4-byte little-endian uint32.


def test_fix32_zero_is_omitted() -> None:
    assert fix32(1, 0) == b""


def test_fix32_one() -> None:
    # tag(1, 5) = (1<<3)|5 = 13 = 0x0D; pack("<I", 1) = 01 00 00 00
    assert fix32(1, 1) == b"\x0d\x01\x00\x00\x00"


def test_fix32_max() -> None:
    # 2^32-1 → all bytes 0xFF
    assert fix32(1, 2**32 - 1) == b"\x0d\xff\xff\xff\xff"


def test_fix32_field_number_affects_tag() -> None:
    # tag(3, 5) = (3<<3)|5 = 29 = 0x1D
    assert fix32(3, 1) == b"\x1d\x01\x00\x00\x00"


def test_fix32_tag_uses_wt_32bit() -> None:
    result = fix32(2, 7)
    assert result[0] == (2 << 3) | WT_32BIT


def test_fix32_always_four_value_bytes() -> None:
    result = fix32(1, 42)
    # 1 tag byte + 4 value bytes
    assert len(result) == 5


@mark.parametrize("value", [1, 255, 256, 2**16, 2**24, 2**32 - 1])
def test_fix32_matches_formula(value: int) -> None:
    expected = encode_tag(1, WT_32BIT) + pack("<I", value)
    assert fix32(1, value) == expected


# ── fix64 ──────────────────────────────────────────────────────────────────────
#
# Omit when zero. Wire layout: tag (wt=1) | 8-byte little-endian uint64.


def test_fix64_zero_is_omitted() -> None:
    assert fix64(1, 0) == b""


def test_fix64_one() -> None:
    # tag(1, 1) = (1<<3)|1 = 9 = 0x09; pack("<Q", 1) = 01 00 00 00 00 00 00 00
    assert fix64(1, 1) == b"\x09\x01\x00\x00\x00\x00\x00\x00\x00"


def test_fix64_max() -> None:
    assert fix64(1, 2**64 - 1) == b"\x09\xff\xff\xff\xff\xff\xff\xff\xff"


def test_fix64_field_number_affects_tag() -> None:
    # tag(2, 1) = (2<<3)|1 = 17 = 0x11
    assert fix64(2, 1) == b"\x11\x01\x00\x00\x00\x00\x00\x00\x00"


def test_fix64_tag_uses_wt_64bit() -> None:
    result = fix64(3, 99)
    assert result[0] == (3 << 3) | WT_64BIT


def test_fix64_always_eight_value_bytes() -> None:
    result = fix64(1, 42)
    # 1 tag byte + 8 value bytes
    assert len(result) == 9


@mark.parametrize("value", [1, 255, 2**32 - 1, 2**32, 2**63, 2**64 - 1])
def test_fix64_matches_formula(value: int) -> None:
    expected = encode_tag(1, WT_64BIT) + pack("<Q", value)
    assert fix64(1, value) == expected


# ── dbl ────────────────────────────────────────────────────────────────────────
#
# Omit when 0.0. Wire layout: tag (wt=1) | 8-byte little-endian double.


def test_dbl_zero_is_omitted() -> None:
    assert dbl(1, 0.0) == b""


def test_dbl_negative_zero_is_omitted() -> None:
    # -0.0 == 0.0 in Python, so it is treated as the proto3 default and omitted.
    assert dbl(1, -0.0) == b""


def test_dbl_one() -> None:
    # tag(1, 1) = 0x09; pack("<d", 1.0) = 00 00 00 00 00 00 F0 3F
    assert dbl(1, 1.0) == b"\x09\x00\x00\x00\x00\x00\x00\xf0\x3f"


def test_dbl_negative_one() -> None:
    assert dbl(1, -1.0) == b"\x09\x00\x00\x00\x00\x00\x00\xf0\xbf"


def test_dbl_infinity_is_encoded() -> None:
    result = dbl(1, inf)
    assert result == encode_tag(1, WT_64BIT) + pack("<d", inf)


def test_dbl_nan_is_encoded() -> None:
    result = dbl(1, nan)
    assert result == encode_tag(1, WT_64BIT) + pack("<d", nan)


def test_dbl_field_number_affects_tag() -> None:
    # tag(4, 1) = (4<<3)|1 = 33 = 0x21
    result = dbl(4, 1.0)
    assert result[0] == (4 << 3) | WT_64BIT


def test_dbl_always_eight_value_bytes() -> None:
    result = dbl(1, 3.14)
    assert len(result) == 9


@mark.parametrize("value", [1.0, -1.0, 0.5, 3.14, 1e100, -1e100, inf, -inf])
def test_dbl_matches_formula(value: float) -> None:
    expected = encode_tag(1, WT_64BIT) + pack("<d", value)
    assert dbl(1, value) == expected


# ── opt_dbl ────────────────────────────────────────────────────────────────────
#
# Omit only when None. 0.0 IS encoded (field is present but zero).
# Used for optional double fields where presence is meaningful (histogram sum/min/max).


def test_opt_dbl_none_is_omitted() -> None:
    assert opt_dbl(1, None) == b""


def test_opt_dbl_zero_is_NOT_omitted() -> None:
    # This is the key difference from dbl: 0.0 is a valid measurement.
    result = opt_dbl(1, 0.0)
    assert result != b""
    assert result == encode_tag(1, WT_64BIT) + pack("<d", 0.0)


def test_opt_dbl_negative_zero_is_encoded() -> None:
    result = opt_dbl(1, -0.0)
    assert result != b""


def test_opt_dbl_one() -> None:
    assert opt_dbl(1, 1.0) == b"\x09\x00\x00\x00\x00\x00\x00\xf0\x3f"


def test_opt_dbl_negative_one() -> None:
    assert opt_dbl(1, -1.0) == b"\x09\x00\x00\x00\x00\x00\x00\xf0\xbf"


def test_opt_dbl_infinity_is_encoded() -> None:
    result = opt_dbl(1, inf)
    assert result == encode_tag(1, WT_64BIT) + pack("<d", inf)


def test_opt_dbl_nan_is_encoded() -> None:
    result = opt_dbl(1, nan)
    assert result == encode_tag(1, WT_64BIT) + pack("<d", nan)


def test_opt_dbl_field_number_affects_tag() -> None:
    result = opt_dbl(5, 1.0)
    assert result[0] == (5 << 3) | WT_64BIT


@mark.parametrize("value", [0.0, -0.0, 1.0, -1.0, 0.5, 3.14, 1e100, inf, -inf])
def test_opt_dbl_matches_formula(value: float) -> None:
    expected = encode_tag(1, WT_64BIT) + pack("<d", value)
    assert opt_dbl(1, value) == expected


def test_opt_dbl_versus_dbl_differ_at_zero() -> None:
    # dbl omits 0.0; opt_dbl does not.
    assert dbl(1, 0.0) == b""
    assert opt_dbl(1, 0.0) != b""


# ── sint32 ─────────────────────────────────────────────────────────────────────
#
# Omit when zero. ZigZag encoding: n>=0 → 2n, n<0 → -2n-1. Wire type WT_VARINT.


def test_sint32_zero_is_omitted() -> None:
    assert sint32(1, 0) == b""


def test_sint32_positive_one() -> None:
    # ZigZag(1) = 2; tag(1,0)=0x08; varint(2)=0x02
    assert sint32(1, 1) == b"\x08\x02"


def test_sint32_negative_one() -> None:
    # ZigZag(-1) = 1; tag(1,0)=0x08; varint(1)=0x01
    assert sint32(1, -1) == b"\x08\x01"


def test_sint32_positive_two() -> None:
    # ZigZag(2) = 4
    assert sint32(1, 2) == b"\x08\x04"


def test_sint32_negative_two() -> None:
    # ZigZag(-2) = 3
    assert sint32(1, -2) == b"\x08\x03"


def test_sint32_field_number_affects_tag() -> None:
    # tag(7, 0) = (7<<3)|0 = 56 = 0x38
    result = sint32(7, 1)
    assert result[0] == (7 << 3) | WT_VARINT


def test_sint32_tag_uses_wt_varint() -> None:
    result = sint32(3, -5)
    assert result[0] == (3 << 3) | WT_VARINT


@mark.parametrize("value", [1, -1, 2, -2, 127, -128, 150, -150, 2**31 - 1, -(2**31)])
def test_sint32_zigzag_formula(value: int) -> None:
    zigzag = 2 * value if value >= 0 else -2 * value - 1
    expected = encode_tag(1, WT_VARINT) + encode_varint(zigzag)
    assert sint32(1, value) == expected


# ── packed_uint64 ──────────────────────────────────────────────────────────────
#
# Omit when empty. Wire layout: tag (wt=2) | varint(payload_len) | varint*...


def test_packed_uint64_empty_is_omitted() -> None:
    assert packed_uint64(1, []) == b""


def test_packed_uint64_single_element() -> None:
    # payload = varint(1) = 0x01; len=1
    # tag(1,2)=0x0A; varint(1)=0x01; payload=0x01
    assert packed_uint64(1, [1]) == b"\x0a\x01\x01"


def test_packed_uint64_three_elements() -> None:
    # payload = varint(1)+varint(2)+varint(3) = 0x01 0x02 0x03; len=3
    assert packed_uint64(1, [1, 2, 3]) == b"\x0a\x03\x01\x02\x03"


def test_packed_uint64_element_zero() -> None:
    # Zero element encodes as varint(0) = 0x00 — still written (not omitted within payload)
    assert packed_uint64(1, [0]) == b"\x0a\x01\x00"


def test_packed_uint64_field_number_affects_tag() -> None:
    result = packed_uint64(3, [1])
    assert result[0] == (3 << 3) | WT_LEN


def test_packed_uint64_tag_uses_wt_len() -> None:
    result = packed_uint64(2, [42])
    assert result[0] == (2 << 3) | WT_LEN


def test_packed_uint64_length_prefix_covers_payload() -> None:
    values = [1, 128, 300]
    payload = b"".join(encode_varint(v) for v in values)
    result = packed_uint64(1, values)
    # byte at index 1 is varint(len(payload)); for short payloads this is 1 byte
    assert result == encode_tag(1, WT_LEN) + encode_varint(len(payload)) + payload


@mark.parametrize("values", [[1], [0, 1, 2], [127, 128, 255], [2**32 - 1, 2**64 - 1]])
def test_packed_uint64_matches_formula(values: list) -> None:
    payload = b"".join(encode_varint(v) for v in values)
    expected = encode_tag(1, WT_LEN) + encode_varint(len(payload)) + payload
    assert packed_uint64(1, values) == expected


# ── packed_fix64 ───────────────────────────────────────────────────────────────
#
# Omit when empty. Wire layout: tag (wt=2) | varint(payload_len) | fixed64*...
# Each element is 8 bytes little-endian regardless of value.


def test_packed_fix64_empty_is_omitted() -> None:
    assert packed_fix64(1, []) == b""


def test_packed_fix64_single_element() -> None:
    # payload = pack("<Q", 1) = 8 bytes; len=8 → varint(8)=0x08
    # tag(1,2)=0x0A; varint(8)=0x08; payload
    result = packed_fix64(1, [1])
    assert result == b"\x0a\x08" + pack("<Q", 1)


def test_packed_fix64_two_elements() -> None:
    # payload = 16 bytes; varint(16)=0x10
    result = packed_fix64(1, [1, 2])
    expected = b"\x0a\x10" + pack("<Q", 1) + pack("<Q", 2)
    assert result == expected


def test_packed_fix64_element_zero_is_written() -> None:
    result = packed_fix64(1, [0])
    assert result == b"\x0a\x08" + b"\x00" * 8


def test_packed_fix64_field_number_affects_tag() -> None:
    result = packed_fix64(5, [1])
    assert result[0] == (5 << 3) | WT_LEN


def test_packed_fix64_payload_length_always_multiple_of_8() -> None:
    for n in [1, 2, 3, 5]:
        result = packed_fix64(1, list(range(n)))
        # payload length is n*8; varint(n*8) occupies 1 byte for n<=15
        payload_len = result[1]
        assert payload_len == n * 8


@mark.parametrize("values", [[0], [1, 2], [2**32 - 1, 2**64 - 1], [0, 0, 0]])
def test_packed_fix64_matches_formula(values: list) -> None:
    payload = b"".join(pack("<Q", v) for v in values)
    expected = encode_tag(1, WT_LEN) + encode_varint(len(payload)) + payload
    assert packed_fix64(1, values) == expected


# ── packed_double ──────────────────────────────────────────────────────────────
#
# Omit when empty. Wire layout: tag (wt=2) | varint(payload_len) | double*...
# Each element is 8 bytes (IEEE 754, little-endian).


def test_packed_double_empty_is_omitted() -> None:
    assert packed_double(1, []) == b""


def test_packed_double_single_element() -> None:
    # payload = pack("<d", 1.0) = 8 bytes; varint(8) = 0x08
    result = packed_double(1, [1.0])
    assert result == b"\x0a\x08" + pack("<d", 1.0)


def test_packed_double_two_elements() -> None:
    result = packed_double(1, [1.0, 2.0])
    expected = b"\x0a\x10" + pack("<2d", 1.0, 2.0)
    assert result == expected


def test_packed_double_zero_element_is_written() -> None:
    # 0.0 is valid inside a packed repeated field (only the field itself is omitted when empty)
    result = packed_double(1, [0.0])
    assert result == b"\x0a\x08" + pack("<d", 0.0)


def test_packed_double_field_number_affects_tag() -> None:
    result = packed_double(7, [1.0])
    assert result[0] == (7 << 3) | WT_LEN


def test_packed_double_payload_length_always_multiple_of_8() -> None:
    for n in [1, 2, 3]:
        result = packed_double(1, [float(i) for i in range(n)])
        payload_len = result[1]
        assert payload_len == n * 8


@mark.parametrize(
    "values",
    [[0.0], [1.0, -1.0], [0.5, 3.14, 2.71], [inf, -inf]],
)
def test_packed_double_matches_formula(values: list) -> None:
    payload = pack(f"<{len(values)}d", *values)
    expected = encode_tag(1, WT_LEN) + encode_varint(len(payload)) + payload
    assert packed_double(1, values) == expected
