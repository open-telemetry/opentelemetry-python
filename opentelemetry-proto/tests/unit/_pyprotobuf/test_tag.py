# tests/test__tag.py
#
# encode_tag(field_number, wire_type) encodes (field_number << 3) | wire_type
# as a varint. These tests verify the formula and the varint encoding of the
# resulting tag integer, using hand-computed expected bytes.
#
# Wire type constants:
#   0  VARINT    — int32, int64, uint32, uint64, bool, enum
#   1  64BIT     — fixed64, sfixed64, double
#   2  LEN       — string, bytes, embedded messages, packed repeated
#   5  32BIT     — fixed32, sfixed32, float

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory
from pytest import mark

from opentelemetry._proto._pyprotobuf import encode_tag, encode_varint


@mark.parametrize(
    ("field_number", "wire_type"),
    [
        (1,  0),   # tag = 8    → 1-byte varint
        (1,  1),   # tag = 9    → 1-byte varint
        (1,  2),   # tag = 10   → 1-byte varint
        (1,  5),   # tag = 13   → 1-byte varint
        (15, 0),   # tag = 120  → last 1-byte tag for wire type 0
        (16, 0),   # tag = 128  → first 2-byte tag for wire type 0
        (150,       0),   # tag = 1200  → 2-byte varint
        (1024,      0),   # tag = 8192  → 2-byte varint
        (1048576,   2),   # tag = 8388610  → 4-byte varint
    ],
)
def test_encode_tag_matches_formula(field_number: int, wire_type: int) -> None:
    # encode_tag must produce the same bytes as encoding the tag integer directly.
    tag_int = (field_number << 3) | wire_type
    assert encode_tag(field_number, wire_type) == encode_varint(tag_int)


def test_field_1_wire_type_0() -> None:
    # (1 << 3) | 0 = 8 → single byte 0x08
    assert encode_tag(1, 0) == b"\x08"


def test_field_1_wire_type_2() -> None:
    # (1 << 3) | 2 = 10 → single byte 0x0A
    assert encode_tag(1, 2) == b"\x0a"


def test_field_15_wire_type_0() -> None:
    # (15 << 3) | 0 = 120 → single byte 0x78 (last 1-byte wt-0 tag)
    assert encode_tag(15, 0) == b"\x78"


def test_field_16_wire_type_0() -> None:
    # (16 << 3) | 0 = 128 → two bytes 0x80 0x01 (first 2-byte wt-0 tag)
    assert encode_tag(16, 0) == b"\x80\x01"


def test_field_2_wire_type_1() -> None:
    # (2 << 3) | 1 = 17 → single byte 0x11
    assert encode_tag(2, 1) == b"\x11"


def test_field_3_wire_type_5() -> None:
    # (3 << 3) | 5 = 29 → single byte 0x1D
    assert encode_tag(3, 5) == b"\x1d"


# ── oracle — byte-for-byte comparison with google.protobuf ────────────────────
#
# A proto2 message with fields at distinct positions and wire types is used as
# the oracle.  For each (field_number, wire_type) pair we serialise a message
# with only that field set and verify that encode_tag(field_number, wire_type)
# matches the first len(tag) bytes of the serialised output.
#
# Field number / tag varint length:
#   field   1, wt 0: tag =   8  → 1-byte   (last before multi-byte for wt 0)
#   field  10, wt 1: tag =  81  → 1-byte   (wire type 1)
#   field  11, wt 2: tag =  90  → 1-byte   (wire type 2)
#   field  12, wt 5: tag = 101  → 1-byte   (wire type 5)
#   field  15, wt 0: tag = 120  → 1-byte   (last 1-byte wt-0 tag)
#   field  16, wt 0: tag = 128  → 2-byte   (first 2-byte wt-0 tag)
#   field 150, wt 0: tag = 1200 → 2-byte
#  field 1048576, wt 2: tag = 8388610 → 4-byte

_WT_VARINT = 0
_WT_64BIT  = 1
_WT_LEN    = 2
_WT_32BIT  = 5

_F_UINT64     = 1
_F_FIXED64    = 10
_F_STRING     = 11
_F_FIXED32    = 12
_F_UINT64_15  = 15
_F_UINT64_16  = 16
_F_UINT64_150 = 150
_F_STRING_BIG = 1048576


def _build_tag_message_class():
    file_proto = descriptor_pb2.FileDescriptorProto()
    file_proto.name = "opentelemetry_pyproto_test_tag.proto"
    file_proto.syntax = "proto2"
    msg_proto = file_proto.message_type.add()
    msg_proto.name = "TagMessage"

    T = descriptor_pb2.FieldDescriptorProto

    def _add(name, number, type_id):
        f = msg_proto.field.add()
        f.name = name
        f.number = number
        f.type = type_id
        f.label = T.LABEL_OPTIONAL

    _add("uint64_field",     _F_UINT64,     T.TYPE_UINT64)
    _add("fixed64_field",    _F_FIXED64,    T.TYPE_FIXED64)
    _add("string_field",     _F_STRING,     T.TYPE_STRING)
    _add("fixed32_field",    _F_FIXED32,    T.TYPE_FIXED32)
    _add("uint64_field_15",  _F_UINT64_15,  T.TYPE_UINT64)
    _add("uint64_field_16",  _F_UINT64_16,  T.TYPE_UINT64)
    _add("uint64_field_150", _F_UINT64_150, T.TYPE_UINT64)
    _add("string_field_big", _F_STRING_BIG, T.TYPE_STRING)

    pool = descriptor_pool.DescriptorPool()
    pool.Add(file_proto)
    return message_factory.GetMessageClass(pool.FindMessageTypeByName("TagMessage"))


_TagMessage = _build_tag_message_class()


@mark.parametrize(
    ("field_name", "field_number", "wire_type", "field_value"),
    [
        ("uint64_field",     _F_UINT64,     _WT_VARINT, 1  ),
        ("fixed64_field",    _F_FIXED64,    _WT_64BIT,  1  ),
        ("string_field",     _F_STRING,     _WT_LEN,    "x"),
        ("fixed32_field",    _F_FIXED32,    _WT_32BIT,  1  ),
        ("uint64_field_15",  _F_UINT64_15,  _WT_VARINT, 1  ),
        ("uint64_field_16",  _F_UINT64_16,  _WT_VARINT, 1  ),
        ("uint64_field_150", _F_UINT64_150, _WT_VARINT, 1  ),
        ("string_field_big", _F_STRING_BIG, _WT_LEN,    "x"),
    ],
)
def test_encode_tag_matches_protobuf(
    field_name: str, field_number: int, wire_type: int, field_value
) -> None:
    serialized = _TagMessage(**{field_name: field_value}).SerializeToString()
    tag = encode_tag(field_number, wire_type)
    assert serialized[: len(tag)] == tag
