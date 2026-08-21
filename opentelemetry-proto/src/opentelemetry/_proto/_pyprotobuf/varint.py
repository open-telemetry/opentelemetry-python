"""Varint encoding for the protobuf wire format.

Reference:
    https://protobuf.dev/programming-guides/encoding/

The protobuf encoding guide explains the wire format mostly from the point of
view of inspecting or decoding bytes that already exist. For example, it shows
how a varint byte sequence can be read by removing each byte's continuation bit,
then combining the remaining 7-bit payload groups.

This module implements the encoder side of the same algorithm. Instead of
starting with bytes and recovering the integer, we start with the integer and
produce the bytes. That means the operations appear in the opposite direction:

    documented explanation / decoding view:
        bytes -> remove continuation bits -> collect 7-bit groups -> integer

    implementation / encoding view:
        integer -> extract 7-bit groups -> add continuation bits -> bytes

The bit layout is the same in both directions.
"""


def encode_varint(value: int) -> bytes:
    """Encode a non-negative integer as a protobuf varint.

    A protobuf varint stores an integer as one or more bytes.

    Each byte has two parts:

        bit 7:      continuation bit
        bits 0-6:   seven payload bits

    The continuation bit is the most significant bit of the byte:

        0b1000_0000 == 0x80

    The payload bits are the lower seven bits of the byte:

        0b0111_1111 == 0x7F

    The official protobuf encoding guide describes this format here:

        https://protobuf.dev/programming-guides/encoding/

    The guide explains that the payload is split into 7-bit groups and that the
    groups are stored in little-endian order. In this context, little-endian
    means the least significant 7-bit group is written first.

    This implementation directly performs that encoder-side operation:

        1. Take the least significant 7 bits of the integer.
        2. Write those 7 bits into the next output byte.
        3. If more integer bits remain, set the byte's continuation bit.
        4. Shift the integer right by 7 bits so the next group becomes the new
           least significant group.
        5. Repeat until the remaining integer fits in one final 7-bit payload.

    This is different from the document's presentation because the document is
    mostly showing how to interpret already-encoded bytes. Here we are producing
    those bytes. The two views are inverse operations of the same wire-format
    rule.
    """
    # Protobuf varints, as implemented by this function, encode unsigned integer
    # payloads. Signed integer fields need additional field-specific handling
    # before varint encoding. For example, sint32/sint64 use ZigZag encoding
    # before the resulting non-negative integer is encoded as a varint.
    if value < 0:
        raise ValueError("varint values must be non-negative")

    # bytearray is used because we build the encoded byte sequence one byte at a
    # time. A bytearray is mutable, so appending to it is clearer and cheaper
    # than repeatedly concatenating immutable bytes objects.
    output = bytearray()

    # 0x7F is binary 0111_1111.
    #
    # If value is greater than 0x7F, it cannot fit in one protobuf varint byte,
    # because one varint byte has only seven payload bits. In that case, we must
    # emit one byte containing the current least significant 7-bit group and then
    # continue encoding the remaining higher bits.
    while value > 0x7F:
        # value & 0x7F keeps only the lower seven bits of value.
        #
        # This extracts exactly one protobuf varint payload group.
        #
        # Example:
        #
        #     value        = 0b1001_0110   # decimal 150
        #     0x7F         = 0b0111_1111
        #     value & 0x7F = 0b0001_0110   # decimal 22
        #
        # This corresponds to the guide's 7-bit payload group, but from the
        # encoder direction. The guide often starts from encoded bytes and strips
        # the continuation bit. Here we start from the integer and extract the
        # payload bits before adding the continuation bit.
        payload_bits = value & 0x7F

        # 0x80 is binary 1000_0000.
        #
        # payload_bits | 0x80 sets the most significant bit of the output byte.
        # That most significant bit is the protobuf varint continuation bit.
        #
        # Setting it to 1 means:
        #
        #     "this is not the final varint byte; another byte follows"
        #
        # This byte needs the continuation bit because the while condition has
        # already proven that value has more than seven bits left to encode.
        output.append(payload_bits | 0x80)

        # Shift value right by seven bits.
        #
        # This discards the payload group we just emitted and moves the next
        # higher 7-bit group into the lowest seven bits, ready for the next loop
        # iteration.
        #
        # This is why protobuf varints are little-endian at the 7-bit-group
        # level: we emit the least significant group first, then move toward more
        # significant groups.
        value >>= 7

    # When the loop ends, value is between 0 and 0x7F inclusive, so it fits in a
    # single 7-bit payload group.
    #
    # This is the final varint byte, so we do NOT set the continuation bit.
    # A most significant bit of 0 means:
    #
    #     "this is the final byte of the varint"
    output.append(value)

    # Convert the mutable bytearray into immutable bytes, which is the natural
    # representation for encoded wire-format data in Python.
    return bytes(output)
