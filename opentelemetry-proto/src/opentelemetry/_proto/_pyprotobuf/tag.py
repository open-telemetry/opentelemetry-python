"""Tag encoding for the protobuf wire format.

Every protobuf message on the wire is a flat sequence of records. Each record
has exactly two parts:

    1. A tag  — a varint that encodes the field number and wire type.
    2. A value — the encoded field value, whose byte layout depends on the wire
                 type stored in the preceding tag.

The tag is the reader's only guide to what follows. Without it, the decoder
would not know where one field ends and the next begins.

Wire types
----------
The protobuf spec defines six wire types. The wire type tells the decoder how
many bytes to consume for the value — not what the logical type is, just how
to delimit it on the wire:

    0  Varint        — one or more bytes, continuation bit in MSB of each byte.
    1  64-bit        — exactly 8 bytes (used for fixed64, sfixed64, double).
    2  Length-delimited — a varint length prefix followed by that many bytes
                       (used for string, bytes, embedded messages, packed
                       repeated fields).
    3  Start group   — deprecated; marks the start of a group (proto2 only).
    4  End group     — deprecated; marks the end of a group (proto2 only).
    5  32-bit        — exactly 4 bytes (used for fixed32, sfixed32, float).

Wire types 3 and 4 are not used in proto3 and should not appear in new code.

Tag bit layout
--------------
The tag integer packs the field number and wire type into a single value:

    bits [2:0]  — wire type  (3 bits, enough for values 0–7)
    bits [N:3]  — field number (all remaining higher bits)

The formula is:

    tag = (field_number << 3) | wire_type

Three bits are reserved for the wire type because there are only six defined
wire type values (0–5), which fit comfortably in 3 bits (range 0–7).

Example — field 1, wire type 0 (varint):

    field_number = 1     ->  binary 0000_0001
    field_number << 3    ->  binary 0000_1000  (decimal 8)
    wire_type    = 0     ->  binary 0000_0000
    tag          = 8 | 0 ->  binary 0000_1000  (decimal 8)

    Varint-encoded: 0x08  (fits in one byte, no continuation bit needed)

Example — field 2, wire type 2 (length-delimited):

    field_number = 2     ->  binary 0000_0010
    field_number << 3    ->  binary 0001_0000  (decimal 16)
    wire_type    = 2     ->  binary 0000_0010
    tag          = 16|2  ->  binary 0001_0010  (decimal 18)

    Varint-encoded: 0x12  (one byte)

Example — field 16, wire type 0 (varint):

    field_number = 16    ->  binary 0001_0000
    field_number << 3    ->  binary 1000_0000  (decimal 128)
    wire_type    = 0     ->  binary 0000_0000
    tag          = 128   ->  varint requires two bytes: 0x80 0x01

    The first byte 0x80 has its continuation bit set, meaning another byte
    follows. The second byte 0x01 carries the remaining bits with no
    continuation bit. This is the standard varint encoding for 128.

Reference:
    https://protobuf.dev/programming-guides/encoding/
"""

from .varint import encode_varint


def encode_tag(field_number: int, wire_type: int) -> bytes:
    """Encode a protobuf record tag.

    The tag is the varint-encoded integer produced by:

        tag = (field_number << 3) | wire_type

    It is written before every field value in a serialised protobuf message.
    The decoder reads this tag first to learn the field number (which .proto
    field this value belongs to) and the wire type (how many bytes to read for
    the value).

    Parameters
    ----------
    field_number:
        The field number as declared in the .proto schema. Must be a positive
        integer. Field numbers 1–15 produce a one-byte tag for wire types 0–5;
        field numbers 16–2047 produce a two-byte tag.
    wire_type:
        One of the six protobuf wire type constants (0–5). See the module
        docstring for the full list and their meanings.

    Reference:
        https://protobuf.dev/programming-guides/encoding/
    """
    # field_number << 3 shifts the field number left by three bit positions.
    #
    # This makes room in the three lowest bits of the tag integer for the wire
    # type. The three-bit reservation comes directly from the protobuf spec:
    # wire types 0–5 fit in 3 bits, so the spec dedicates exactly 3 bits to
    # the wire type in every tag.
    #
    # Example:
    #
    #     field_number = 1
    #     field_number in binary  = 0000_0001
    #     field_number << 3       = 0000_1000  (decimal 8)
    #
    # After the shift, bits [2:0] are always zero, leaving space for
    # the wire type to be OR'd in below.
    field_number_bits = field_number << 3

    # The bitwise OR writes the wire type into the lowest three bits.
    #
    # Because field_number_bits always has its lowest three bits set to zero
    # (from the shift above), and wire_type is always in the range 0–5 (which
    # fits in three bits), the OR simply places the wire type value into those
    # three vacated bit positions without disturbing the field number bits.
    #
    # Example (field 1, wire type 2):
    #
    #     field_number_bits = 0b0000_1000   (8)
    #     wire_type         = 0b0000_0010   (2)
    #     tag               = 0b0000_1010   (10)
    #
    # Example (field 15, wire type 0):
    #
    #     field_number_bits = 0b0111_1000   (120)
    #     wire_type         = 0b0000_0000   (0)
    #     tag               = 0b0111_1000   (120)
    #
    # Field numbers 1–15 combined with any wire type 0–5 always produce a tag
    # integer of at most 127, which encodes as a single varint byte. This is
    # why the protobuf style guide recommends reserving field numbers 1–15 for
    # the most frequently used fields: their tags are one byte instead of two.
    tag = field_number_bits | wire_type

    # The tag integer is itself encoded as a varint before being written to the
    # wire. For field numbers 1–15 the tag integer is at most 127, fitting in
    # one varint byte. For field number 16 and above the tag integer exceeds
    # 127 and requires two or more varint bytes.
    return encode_varint(tag)
