# tests/test__enum.py
#
# encode_enum encodes an integer enum value using the same wire format as
# int32: non-negative values as a plain varint, negative values as a 64-bit
# two's-complement varint. These tests verify that contract using hand-computed
# expected byte literals.

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory
from pytest import mark

from opentelemetry._proto._pyprotobuf import encode_enum, encode_int, encode_tag


def test_zero() -> None:
    # The proto3 default enum value is always 0.
    assert encode_enum(0) == b"\x00"


def test_one() -> None:
    # Typical enum constant fits in a single varint byte.
    assert encode_enum(1) == b"\x01"


def test_two() -> None:
    assert encode_enum(2) == b"\x02"


def test_two_byte_value() -> None:
    # A large enum constant that requires two varint bytes (same as encode_int(300)).
    assert encode_enum(300) == b"\xac\x02"


def test_negative_value() -> None:
    # Negative enum values use 64-bit two's-complement encoding.
    # -1 → 10-byte varint for 2^64-1.
    assert encode_enum(-1) == b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\x01"


def test_matches_encode_int_for_positive_values() -> None:
    # encode_enum and encode_int must produce identical bytes for non-negative inputs.
    for value in [0, 1, 2, 127, 128, 255, 300, 2**16]:
        assert encode_enum(value) == encode_int(value)


def test_matches_encode_int_for_negative_values() -> None:
    for value in [-1, -2, -(2**31)]:
        assert encode_enum(value) == encode_int(value)


# ── oracle — byte-for-byte comparison with google.protobuf ────────────────────
#
# A proto2 message with a Color enum field is used as the oracle.  proto2 is
# chosen so the field is serialised even when its value is the default (0).
#
# The Color enum defines RED=0, GREEN=1, BLUE=2.  Only those three values are
# used because proto2 rejects assignments of undefined enum constants.
#
# The serialised message is exactly encode_tag(field, 0) + encode_enum(value).

_FIELD = 1
_WT = 0  # wire type 0 — varint


def _build_enum_message_class():
    file_proto = descriptor_pb2.FileDescriptorProto()
    file_proto.name = "opentelemetry_pyproto_test_enum.proto"
    file_proto.syntax = "proto2"

    color = file_proto.enum_type.add()
    color.name = "Color"
    for name, number in [("RED", 0), ("GREEN", 1), ("BLUE", 2)]:
        ev = color.value.add()
        ev.name = name
        ev.number = number

    msg_proto = file_proto.message_type.add()
    msg_proto.name = "EnumMessage"
    f = msg_proto.field.add()
    f.name = "color_field"
    f.number = _FIELD
    f.type = descriptor_pb2.FieldDescriptorProto.TYPE_ENUM
    f.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    f.type_name = ".Color"

    pool = descriptor_pool.DescriptorPool()
    pool.Add(file_proto)
    return message_factory.GetMessageClass(pool.FindMessageTypeByName("EnumMessage"))


_EnumMessage = _build_enum_message_class()


@mark.parametrize("value", [0, 1, 2])
def test_encode_enum_matches_protobuf(value: int) -> None:
    expected = encode_tag(_FIELD, _WT) + encode_enum(value)
    assert _EnumMessage(color_field=value).SerializeToString() == expected
