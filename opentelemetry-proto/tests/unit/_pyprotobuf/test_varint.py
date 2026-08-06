# tests/test__varint.py

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory
from pytest import mark, raises

from opentelemetry._proto._pyprotobuf import encode_tag, encode_varint


def test_zero() -> None:
    assert encode_varint(0) == b"\x00"


def test_single_byte_max() -> None:
    assert encode_varint(127) == b"\x7f"


def test_first_two_byte_value() -> None:
    assert encode_varint(128) == b"\x80\x01"


def test_150() -> None:
    assert encode_varint(150) == b"\x96\x01"


def test_300() -> None:
    assert encode_varint(300) == b"\xac\x02"


def test_uint32_max() -> None:
    assert encode_varint(2**32 - 1) == b"\xff\xff\xff\xff\x0f"


def test_uint64_max() -> None:
    assert encode_varint(2**64 - 1) == b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\x01"


def test_rejects_negative_values() -> None:
    with raises(ValueError, match="varint values must be non-negative"):
        encode_varint(-1)


def test_two_byte_boundary_low() -> None:
    # 16383 = 0x3FFF — the largest value that fits in two varint bytes.
    # 7-bit groups: 0x7F (lower), 0x7F (upper, no continuation bit).
    assert encode_varint(16_383) == b"\xff\x7f"


def test_three_byte_boundary_low() -> None:
    # 16384 = 0x4000 — the first value that requires three varint bytes.
    assert encode_varint(16_384) == b"\x80\x80\x01"


def test_one() -> None:
    # 1 fits in a single byte; no continuation bit needed.
    assert encode_varint(1) == b"\x01"


# ── oracle — byte-for-byte comparison with google.protobuf ────────────────────
#
# A proto2 message with a single uint64 field is used as the oracle.  proto2
# is chosen because it serialises the field even when its value is the type
# default (0).  uint64 covers the full [0, 2^64-1] varint range.
#
# The serialised message for a single field is exactly:
#   tag (varint) + value (varint)
#
# Asserting that encode_tag(field, wt) + encode_varint(value) equals the
# serialised message verifies that our varint encoder produces the exact same
# bytes as google.protobuf for every tested value.

_FIELD = 1
_WT = 0  # wire type 0 — varint


def _build_varint_message_class():
    file_proto = descriptor_pb2.FileDescriptorProto()
    file_proto.name = "opentelemetry_pyproto_test_varint.proto"
    file_proto.syntax = "proto2"
    msg_proto = file_proto.message_type.add()
    msg_proto.name = "VarintMessage"
    f = msg_proto.field.add()
    f.name = "uint64_field"
    f.number = _FIELD
    f.type = descriptor_pb2.FieldDescriptorProto.TYPE_UINT64
    f.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    pool = descriptor_pool.DescriptorPool()
    pool.Add(file_proto)
    return message_factory.GetMessageClass(pool.FindMessageTypeByName("VarintMessage"))


_VarintMessage = _build_varint_message_class()


@mark.parametrize(
    "value",
    [
        0,
        1,
        127,
        128,
        150,
        300,
        16_383,
        16_384,
        2**16,
        2**28,
        2**32 - 1,
        2**32,
        2**63 - 1,
        2**64 - 1,
    ],
)
def test_encode_varint_matches_protobuf(value: int) -> None:
    expected = encode_tag(_FIELD, _WT) + encode_varint(value)
    assert _VarintMessage(uint64_field=value).SerializeToString() == expected
