"""Encoders for protobuf scalar field types.

This module contains one encoding function for each protobuf scalar type.
The functions are grouped by wire type, because the wire type determines the
byte layout on the wire — not the logical .proto type name.

Wire type 0 — Varint
    Encodes as one or more bytes with a continuation bit in the MSB of each
    byte. The number of output bytes grows with the magnitude of the value.

        bool    — varint 0 or 1 only.
        int32   — varint; negative values always cost 10 bytes.
        int64   — identical wire encoding to int32.
        sint32  — varint with ZigZag pre-encoding; negative values stay small.
        sint64  — varint with ZigZag pre-encoding; 64-bit domain.
        uint32  — plain varint; valid range [0, 2^32 - 1].
        uint64  — plain varint; valid range [0, 2^64 - 1].

Wire type 5 — 32-bit fixed-width
    Always exactly 4 bytes, stored in little-endian byte order. The fixed size
    makes these types attractive when values are large enough that a varint
    would also be 4–5 bytes.

        float   — IEEE 754 single-precision (32-bit).
        fixed32 — unsigned 32-bit integer.
        sfixed32 — signed 32-bit integer (two's complement).

Wire type 1 — 64-bit fixed-width
    Always exactly 8 bytes, stored in little-endian byte order.

        double   — IEEE 754 double-precision (64-bit).
        fixed64  — unsigned 64-bit integer.
        sfixed64 — signed 64-bit integer (two's complement).

Wire type 2 — Length-delimited
    A varint giving the byte length of the payload, followed immediately by
    that many payload bytes. The decoder reads the varint first, then reads
    exactly that many bytes.

        string — UTF-8 encoded text; length prefix counts UTF-8 bytes.
        bytes  — arbitrary binary data; length prefix counts raw bytes.

Reference:
    https://protobuf.dev/programming-guides/encoding/
"""

from struct import pack

from .varint import encode_varint


# ── Wire type 0 — Varint ──────────────────────────────────────────────────────


def encode_uint32(value: int) -> bytes:
    """Encode an unsigned 32-bit integer as a protobuf uint32 field value.

    Protobuf uint32 fields use wire type 0 (varint). The value is encoded
    as a plain unsigned varint with no transformation applied.

    Valid range: [0, 2^32 - 1].

    Unlike int32, uint32 has no signed interpretation, so negative inputs
    are not defined. Values in [0, 127] encode to a single byte; larger
    values require more bytes as their magnitude grows.

    Example — encoding 0:

        encode_varint(0) == b'\\x00'

    Example — encoding 300:

        300 = 0b1_0010_1100
        Split into 7-bit groups (little-endian): 0b010_1100, 0b000_0010
        Add continuation bit to first group: 0b1_010_1100 == 0xAC
        Second group (no continuation): 0b000_0010 == 0x02
        Result: b'\\xac\\x02'

    Reference:
        https://protobuf.dev/programming-guides/encoding/
    """
    # uint32 encoding is identical to plain varint encoding — no sign extension,
    # no ZigZag, no transformation. encode_varint raises ValueError for negative
    # inputs, which correctly rejects values outside the uint32 domain.
    return encode_varint(value)


def encode_uint64(value: int) -> bytes:
    """Encode an unsigned 64-bit integer as a protobuf uint64 field value.

    Protobuf uint64 fields use wire type 0 (varint). The value is encoded
    as a plain unsigned varint with no transformation applied.

    Valid range: [0, 2^64 - 1].

    This is the 64-bit counterpart of encode_uint32. The encoding is
    identical — both delegate to encode_varint — but the domain is larger.
    Values up to 2^64 - 1 require at most 10 varint bytes.

    Example — encoding 2^32 (first value that exceeds the uint32 domain):

        2^32 = 4294967296 = 0x1_0000_0000
        Varint encoding requires 5 bytes:
            b'\\x80\\x80\\x80\\x80\\x10'

    Reference:
        https://protobuf.dev/programming-guides/encoding/
    """
    # Identical to encode_uint32 at the implementation level. The separate
    # function exists so call sites can express the .proto field type precisely.
    return encode_varint(value)


def encode_bool(value: bool) -> bytes:
    """Encode a Python bool as a protobuf bool field value.

    Protobuf bool fields use wire type 0 (varint). The encoding guide defines
    exactly two valid encodings:

        False  ->  varint 0  ->  0x00  (one byte)
        True   ->  varint 1  ->  0x01  (one byte)

    The spec states that values other than 0 or 1 are not valid on the wire
    for a bool field. This function enforces that constraint by mapping any
    truthy value to 1 and any falsy value to 0, regardless of the input's
    actual numeric value.

    Reference:
        https://protobuf.dev/programming-guides/encoding/
    """
    # The conditional expression evaluates value in a boolean context.
    #
    # Using (1 if value else 0) instead of int(value) is intentional.
    # int(True) == 1 and int(False) == 0, which would work correctly for
    # actual bool inputs. However, int(5) == 5, and varint 5 is not a valid
    # protobuf bool encoding. The conditional collapses any truthy integer,
    # non-empty string, non-empty list, etc. to exactly 1, and any falsy
    # value to exactly 0, maintaining spec compliance regardless of what
    # the caller passes.
    #
    # Both 0 and 1 fit in a single varint byte (no continuation bit needed),
    # so encode_varint always returns exactly one byte here:
    #
    #     encode_bool(False)  ->  b'\x00'
    #     encode_bool(True)   ->  b'\x01'
    return encode_varint(1 if value else 0)


def encode_int(value: int) -> bytes:
    """Encode a signed integer as a protobuf varint for int32 and int64 fields.

    Protobuf int32 and int64 fields both use wire type 0 (varint). The two
    types share the same wire encoding — int32 values are sign-extended to
    64 bits before encoding, so they produce identical byte sequences to the
    equivalent int64 value.

    Non-negative values pass straight through to encode_varint unchanged.

    Negative values are handled by a rule from the encoding guide:

        If you use int32 or int64 as the type for a negative number, the
        resulting varint is always ten bytes long — it is, effectively,
        treated like a very large unsigned integer.

    The rule comes from how the spec defines the encoding: a negative int32 or
    int64 is sign-extended to a full 64-bit two's complement value before being
    treated as an unsigned integer for varint encoding. A 64-bit value with
    all its high bits set always requires 10 varint bytes regardless of the
    original magnitude.

    Concrete example — encoding -1:

        -1 in two's complement 64-bit:

            0xFFFFFFFFFFFFFFFF  (all 64 bits set to 1)

        That unsigned 64-bit integer requires all 10 varint bytes:

            0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0x01

        Each of the first nine bytes has its continuation bit set (0xFF =
        1111_1111: 7 payload bits all 1, plus the continuation bit). The tenth
        byte 0x01 carries the final payload bits with no continuation bit.

    This fixed 10-byte cost applies to -1 the same as to the most negative
    64-bit integer -2^63. The magnitude of the negative value does not affect
    the byte count. This is why the encoding guide recommends sint32/sint64
    (see encode_sint32 and encode_sint64) for fields that often hold negative
    values.

    Reference:
        https://protobuf.dev/programming-guides/encoding/
    """
    if value >= 0:
        # Non-negative values need no transformation. encode_varint encodes
        # them directly as unsigned varints, which matches the int32/int64
        # wire encoding exactly.
        return encode_varint(value)

    # For negative values, the protobuf spec requires 64-bit sign extension
    # followed by unsigned varint encoding.
    #
    # Python integers have arbitrary precision — there is no native 64-bit
    # boundary. The bitwise AND with 0xFFFFFFFFFFFFFFFF (a mask of 64 ones,
    # equal to 2^64 - 1) extracts exactly the lower 64 bits of value.
    #
    # For any negative integer, Python's two's complement representation means
    # the lower 64 bits equal the 64-bit unsigned two's complement value:
    #
    #     -1   & 0xFFFFFFFFFFFFFFFF == 0xFFFFFFFFFFFFFFFF  (2^64 - 1)
    #     -2   & 0xFFFFFFFFFFFFFFFF == 0xFFFFFFFFFFFFFFFE  (2^64 - 2)
    #     -128 & 0xFFFFFFFFFFFFFFFF == 0xFFFFFFFFFFFFFF80
    #
    # Every result is in the range [2^63, 2^64 - 1], so encode_varint will
    # always produce exactly 10 bytes for any negative input.
    unsigned = value & 0xFFFFFFFFFFFFFFFF
    return encode_varint(unsigned)


def encode_sint32(value: int) -> bytes:
    """Encode a signed 32-bit integer using ZigZag encoding for sint32 fields.

    Protobuf sint32 fields use wire type 0 (varint) but apply a ZigZag
    transformation before varint encoding. ZigZag maps signed integers to
    non-negative integers by interleaving the negative and positive sequences:

        0   ->  0
       -1   ->  1
        1   ->  2
       -2   ->  3
        2   ->  4
       -3   ->  5
        3   ->  6
       ...
     n >= 0  ->  2 * n
     n <  0  ->  -2 * n - 1

    The key property is that the ZigZag output is small whenever the input's
    absolute magnitude is small, regardless of sign. This makes sint32 much
    more efficient than int32 for fields that frequently hold negative values:

        Encoding -1 with encode_int:    10 bytes (64-bit two's complement)
        Encoding -1 with encode_sint32:  1 byte  (ZigZag maps -1 to 1)

        Encoding -64 with encode_int:   10 bytes
        Encoding -64 with encode_sint32: 2 bytes (ZigZag maps -64 to 127)

    The official formula for the 32-bit ZigZag transformation is:

        zigzag32(n) = (n << 1) ^ (n >> 31)

    The right shift (n >> 31) is arithmetic in Python, propagating the sign
    bit: it produces 0 for non-negative n and -1 (all bits set) for negative n.

    Reference:
        https://protobuf.dev/programming-guides/encoding/
    """
    # Step 1: apply the ZigZag transformation.
    #
    # (value << 1) shifts all bits one position left. This doubles the absolute
    # value and frees bit 0 to carry the original sign. For positive n the
    # result is 2*n (an even number). For negative n, the shift operates on the
    # two's complement representation.
    #
    # (value >> 31) is an arithmetic right shift by 31 positions. Python
    # propagates the sign bit into all vacated positions, so:
    #
    #     non-negative n  ->  (n >> 31) ==  0  (binary: all zeros)
    #     negative n      ->  (n >> 31) == -1  (binary: all ones, i.e. 0xFF...FF)
    #
    # XOR with 0 is a no-op, so positive inputs pass through as 2*n.
    # XOR with -1 flips every bit, which is equivalent to bitwise NOT. For
    # negative inputs that produces the ZigZag output -2*n - 1.
    #
    # Worked examples:
    #
    #     n = -1:
    #         (-1 << 1) == -2          binary: ...1111_1110
    #         (-1 >> 31) == -1         binary: ...1111_1111
    #         (-2) ^ (-1) == 1         binary: ...0000_0001   ✓ ZigZag(-1) = 1
    #
    #     n = -2:
    #         (-2 << 1) == -4          binary: ...1111_1100
    #         (-2 >> 31) == -1         binary: ...1111_1111
    #         (-4) ^ (-1) == 3         binary: ...0000_0011   ✓ ZigZag(-2) = 3
    #
    #     n = 1:
    #         (1 << 1) == 2            binary: ...0000_0010
    #         (1 >> 31) == 0           binary: ...0000_0000
    #         2 ^ 0 == 2               binary: ...0000_0010   ✓ ZigZag(1) = 2
    zigzag_value = (value << 1) ^ (value >> 31)

    # Step 2: mask to 32 bits.
    #
    # Python integers have arbitrary precision, so the XOR result above can
    # have more than 32 significant bits for inputs outside the sint32 range
    # [-2^31, 2^31 - 1]. The mask clips the result to the 32-bit unsigned
    # domain [0, 2^32 - 1], which is the correct output range for sint32
    # ZigZag encoding.
    #
    # For valid sint32 inputs the ZigZag result already fits in 32 bits and
    # the mask has no effect.
    #
    # 0xFFFFFFFF == 2^32 - 1 == 32 bits of all ones.
    zigzag_value &= 0xFFFFFFFF

    # Step 3: varint-encode the non-negative ZigZag result.
    #
    # The ZigZag value is now in [0, 2^32 - 1]. encode_varint encodes it in
    # 1–5 bytes depending on its magnitude, compared to the flat 10 bytes that
    # encode_int would use for any negative input.
    return encode_varint(zigzag_value)


def encode_sint64(value: int) -> bytes:
    """Encode a signed 64-bit integer using ZigZag encoding for sint64 fields.

    This is the 64-bit counterpart of encode_sint32. The ZigZag interleaving
    and the three-step structure (transform, mask, varint-encode) are identical.
    The only differences from encode_sint32 are:

        - The arithmetic right shift uses 63 instead of 31, propagating the
          sign bit across all 63 remaining bit positions of a 64-bit value.
        - The mask uses 0xFFFFFFFFFFFFFFFF (64 ones) instead of 0xFFFFFFFF
          (32 ones), constraining the output to [0, 2^64 - 1].
        - The varint output is at most 10 bytes instead of 5.

    The ZigZag mapping is the same interleaving as sint32, extended to 64 bits:

        0    ->  0
       -1    ->  1
        1    ->  2
       -2    ->  3
        2    ->  4
       ...
     n >= 0  ->  2 * n
     n <  0  ->  -2 * n - 1

    The official formula for the 64-bit ZigZag transformation is:

        zigzag64(n) = (n << 1) ^ (n >> 63)

    Worked examples:

        n = -1:
            (-1 << 1) == -2          binary: ...1111_1110
            (-1 >> 63) == -1         binary: ...1111_1111
            (-2) ^ (-1) == 1         binary: ...0000_0001   ✓ ZigZag(-1) = 1
            Encoded: b'\\x01'  (1 byte, vs 10 bytes from encode_int)

        n = -(2**63):     (most negative sint64 value)
            zigzag64(-(2**63)) == 2**64 - 1  (largest 64-bit unsigned integer)
            Encoded: 10 bytes (the worst case for sint64)

        n = 2**63 - 1:    (most positive sint64 value)
            zigzag64(2**63 - 1) == 2**64 - 2
            Encoded: 10 bytes (the worst case alongside the above)

    Reference:
        https://protobuf.dev/programming-guides/encoding/
    """
    # Step 1: apply the 64-bit ZigZag transformation.
    #
    # (value >> 63) produces 0 for non-negative values and -1 for negative
    # values, for the same reason as (value >> 31) in encode_sint32: Python
    # performs arithmetic right shifts that propagate the sign bit.
    #
    # The XOR with 0 leaves positive inputs unchanged (result = 2*n).
    # The XOR with -1 flips every bit for negative inputs (result = -2*n - 1).
    zigzag_value = (value << 1) ^ (value >> 63)

    # Step 2: mask to 64 bits.
    #
    # Same rationale as in encode_sint32: Python integers are unbounded, so
    # the mask constrains the ZigZag result to the valid 64-bit unsigned range
    # [0, 2^64 - 1]. For inputs in the sint64 range [-2^63, 2^63 - 1] the
    # result already fits and the mask is a no-op.
    #
    # 0xFFFFFFFFFFFFFFFF == 2^64 - 1 == 64 bits of all ones.
    zigzag_value &= 0xFFFFFFFFFFFFFFFF

    # Step 3: varint-encode the non-negative ZigZag result.
    #
    # The ZigZag value is in [0, 2^64 - 1], which encode_varint encodes in
    # 1–10 bytes. The maximum 10-byte output only occurs at the extremes of
    # the sint64 range (see worked examples in the docstring above).
    return encode_varint(zigzag_value)


# ── Wire type 5 — 32-bit fixed-width ─────────────────────────────────────────


def encode_float(value: float) -> bytes:
    """Encode a Python float as a protobuf float field value.

    Protobuf float fields use wire type 5 (32-bit fixed-width). The value is
    stored as a 4-byte IEEE 754 single-precision floating-point number in
    little-endian byte order.

    Unlike varint-encoded numbers, wire type 5 always occupies exactly 4 bytes.
    This makes float fields predictable in size but more expensive than varint
    for small integer-valued floats.

    Precision note
    --------------
    Python's float type is a 64-bit IEEE 754 double-precision number. Converting
    to single precision loses approximately 7 significant decimal digits of
    precision (single has ~7, double has ~15-16). pack handles the conversion
    silently; values outside the float32 range become inf or -inf.

    Byte layout — IEEE 754 single precision (32 bits)
    --------------------------------------------------
    The 32 bits are arranged as:

        bit 31:      sign (0 = positive, 1 = negative)
        bits 30–23:  exponent, biased by 127
        bits 22–0:   mantissa (the fractional part, with an implicit leading 1)

    The four bytes are written in little-endian order: the least significant
    byte is first.

    Example — encoding 1.0:

        IEEE 754 single for 1.0:
            sign = 0
            exponent = 127 (biased) = 0b0111_1111
            mantissa = 0 (implicit leading 1, no fractional part)

        Combined 32-bit value: 0x3F800000

        Little-endian bytes: 0x00, 0x00, 0x80, 0x3F

        Result: b'\\x00\\x00\\x80\\x3f'

    Example — encoding -1.0:

        Same as 1.0 but with the sign bit set.

        Combined 32-bit value: 0xBF800000

        Little-endian bytes: 0x00, 0x00, 0x80, 0xBF

        Result: b'\\x00\\x00\\x80\\xbf'

    Reference:
        https://protobuf.dev/programming-guides/encoding/
    """
    # pack with format '<f' encodes value as a 4-byte IEEE 754 single-precision
    # float in little-endian byte order.
    #
    # '<' means little-endian (least significant byte first), which is what
    # the protobuf wire format requires for all fixed-width numeric types.
    #
    # 'f' is the format character for a C float (4 bytes, IEEE 754 single).
    #
    # If value is a Python float (64-bit double), pack rounds it to the nearest
    # representable single-precision value. Special values (inf, -inf, nan) are
    # preserved in their single-precision forms.
    return pack("<f", value)


def encode_fixed32(value: int) -> bytes:
    """Encode an unsigned integer as a protobuf fixed32 field value.

    Protobuf fixed32 fields use wire type 5 (32-bit fixed-width). The value
    is stored as a 4-byte unsigned integer in little-endian byte order.

    The valid range is [0, 2^32 - 1].

    Unlike uint32, which uses a varint and grows with the value's magnitude,
    fixed32 always occupies exactly 4 bytes. This makes fixed32 more efficient
    than uint32 for values that are consistently large (roughly above 2^28,
    where a varint would already require 5 bytes), and less efficient for small
    values.

    Example — encoding 1:

        1 as a 4-byte little-endian unsigned integer:

        byte 0 (LSB): 0x01
        byte 1:       0x00
        byte 2:       0x00
        byte 3 (MSB): 0x00

        Result: b'\\x01\\x00\\x00\\x00'

    Example — encoding 2^32 - 1 (maximum value):

        0xFFFFFFFF as little-endian bytes: 0xFF, 0xFF, 0xFF, 0xFF

        Result: b'\\xff\\xff\\xff\\xff'

    Reference:
        https://protobuf.dev/programming-guides/encoding/
    """
    # pack with format '<I' encodes value as a 4-byte unsigned integer in
    # little-endian byte order.
    #
    # '<' means little-endian.
    # 'I' is the format character for a C unsigned int (4 bytes).
    #
    # pack raises struct.error if value is outside [0, 2^32 - 1].
    return pack("<I", value)


def encode_sfixed32(value: int) -> bytes:
    """Encode a signed integer as a protobuf sfixed32 field value.

    Protobuf sfixed32 fields use wire type 5 (32-bit fixed-width). The value
    is stored as a 4-byte signed integer in little-endian two's complement byte
    order.

    The valid range is [-2^31, 2^31 - 1].

    Unlike int32, which uses a varint and always costs 10 bytes for negative
    values, sfixed32 always occupies exactly 4 bytes regardless of sign. This
    makes sfixed32 more efficient than int32 for negative values and for large
    positive values near 2^31.

    Example — encoding -1:

        -1 in 32-bit two's complement: 0xFFFFFFFF

        Little-endian bytes: 0xFF, 0xFF, 0xFF, 0xFF

        Result: b'\\xff\\xff\\xff\\xff'

    Example — encoding -2^31 (minimum value):

        -2147483648 in 32-bit two's complement: 0x80000000

        Little-endian bytes: 0x00, 0x00, 0x00, 0x80

        Result: b'\\x00\\x00\\x00\\x80'

    Reference:
        https://protobuf.dev/programming-guides/encoding/
    """
    # pack with format '<i' encodes value as a 4-byte signed integer in
    # little-endian two's complement byte order.
    #
    # '<' means little-endian.
    # 'i' is the format character for a C signed int (4 bytes).
    #
    # pack raises struct.error if value is outside [-2^31, 2^31 - 1].
    return pack("<i", value)


# ── Wire type 1 — 64-bit fixed-width ─────────────────────────────────────────


def encode_double(value: float) -> bytes:
    """Encode a Python float as a protobuf double field value.

    Protobuf double fields use wire type 1 (64-bit fixed-width). The value is
    stored as an 8-byte IEEE 754 double-precision floating-point number in
    little-endian byte order.

    Unlike wire type 5 (float), wire type 1 uses 8 bytes and matches Python's
    native float precision exactly — no precision is lost in the conversion.

    Byte layout — IEEE 754 double precision (64 bits)
    --------------------------------------------------
    The 64 bits are arranged as:

        bit 63:      sign (0 = positive, 1 = negative)
        bits 62–52:  exponent, biased by 1023
        bits 51–0:   mantissa (the fractional part, with an implicit leading 1)

    The eight bytes are written in little-endian order.

    Example — encoding 1.0:

        IEEE 754 double for 1.0:
            sign = 0
            exponent = 1023 (biased) = 0b011_1111_1111
            mantissa = 0

        Combined 64-bit value: 0x3FF0000000000000

        Little-endian bytes: 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xF0, 0x3F

        Result: b'\\x00\\x00\\x00\\x00\\x00\\x00\\xf0\\x3f'

    Special values (inf, -inf, nan) are represented in their standard IEEE 754
    double-precision forms and are encoded without error.

    Reference:
        https://protobuf.dev/programming-guides/encoding/
    """
    # pack with format '<d' encodes value as an 8-byte IEEE 754 double-precision
    # float in little-endian byte order.
    #
    # '<' means little-endian.
    # 'd' is the format character for a C double (8 bytes, IEEE 754 double).
    #
    # Python's float is already a 64-bit IEEE 754 double, so this conversion
    # is lossless. The bytes produced are the exact in-memory representation
    # of the Python float, reordered to little-endian if the host is big-endian.
    return pack("<d", value)


def encode_fixed64(value: int) -> bytes:
    """Encode an unsigned integer as a protobuf fixed64 field value.

    Protobuf fixed64 fields use wire type 1 (64-bit fixed-width). The value
    is stored as an 8-byte unsigned integer in little-endian byte order.

    The valid range is [0, 2^64 - 1].

    fixed64 always occupies exactly 8 bytes. It is more efficient than uint64
    (varint) for values consistently above 2^56, where a varint would already
    require 9–10 bytes. For smaller values, uint64's variable length is more
    compact.

    Example — encoding 1:

        1 as an 8-byte little-endian unsigned integer:

        bytes: 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00

        Result: b'\\x01\\x00\\x00\\x00\\x00\\x00\\x00\\x00'

    Example — encoding 2^64 - 1 (maximum value):

        0xFFFFFFFFFFFFFFFF as little-endian bytes: eight 0xFF bytes.

        Result: b'\\xff\\xff\\xff\\xff\\xff\\xff\\xff\\xff'

    Reference:
        https://protobuf.dev/programming-guides/encoding/
    """
    # pack with format '<Q' encodes value as an 8-byte unsigned integer in
    # little-endian byte order.
    #
    # '<' means little-endian.
    # 'Q' is the format character for a C unsigned long long (8 bytes).
    #
    # pack raises struct.error if value is outside [0, 2^64 - 1].
    return pack("<Q", value)


def encode_sfixed64(value: int) -> bytes:
    """Encode a signed integer as a protobuf sfixed64 field value.

    Protobuf sfixed64 fields use wire type 1 (64-bit fixed-width). The value
    is stored as an 8-byte signed integer in little-endian two's complement
    byte order.

    The valid range is [-2^63, 2^63 - 1].

    sfixed64 always occupies exactly 8 bytes regardless of sign. Unlike int64
    (varint), which always costs 10 bytes for negative values, sfixed64 saves
    2 bytes for negative inputs and for large positive values near 2^63.

    Example — encoding -1:

        -1 in 64-bit two's complement: 0xFFFFFFFFFFFFFFFF

        Little-endian bytes: eight 0xFF bytes.

        Result: b'\\xff\\xff\\xff\\xff\\xff\\xff\\xff\\xff'

    Example — encoding -2^63 (minimum value):

        -9223372036854775808 in 64-bit two's complement: 0x8000000000000000

        Little-endian bytes: 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80

        Result: b'\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x80'

    Reference:
        https://protobuf.dev/programming-guides/encoding/
    """
    # pack with format '<q' encodes value as an 8-byte signed integer in
    # little-endian two's complement byte order.
    #
    # '<' means little-endian.
    # 'q' is the format character for a C signed long long (8 bytes).
    #
    # pack raises struct.error if value is outside [-2^63, 2^63 - 1].
    return pack("<q", value)


# ── Wire type 2 — Length-delimited ───────────────────────────────────────────


def encode_string(value: str) -> bytes:
    """Encode a Python str as a protobuf string field value.

    Protobuf string fields use wire type 2 (length-delimited). The encoding
    is a two-part sequence:

        1. A varint giving the number of bytes in the UTF-8 representation of
           the string. This is the byte count, not the character count — they
           differ for any character outside ASCII.
        2. The UTF-8 encoded bytes of the string.

    The protobuf spec requires that string fields contain valid UTF-8. Python
    str objects are always valid Unicode, so encoding to UTF-8 always succeeds
    (Python's str cannot represent unpaired surrogates in normal use).

    The length prefix allows the decoder to know exactly how many bytes to read
    for the string value without scanning for a terminator.

    Example — encoding "hi":

        UTF-8 bytes: b'hi'  (2 bytes, both ASCII)
        Length varint: encode_varint(2) == b'\\x02'
        Result: b'\\x02hi'

    Example — encoding "é" (U+00E9, LATIN SMALL LETTER E WITH ACUTE):

        UTF-8 bytes: b'\\xc3\\xa9'  (2 bytes; this character needs 2 UTF-8 bytes)
        Length varint: encode_varint(2) == b'\\x02'
        Result: b'\\x02\\xc3\\xa9'

    Example — encoding "" (empty string):

        UTF-8 bytes: b''  (0 bytes)
        Length varint: encode_varint(0) == b'\\x00'
        Result: b'\\x00'

    Reference:
        https://protobuf.dev/programming-guides/encoding/
    """
    # Encode the string to UTF-8 bytes.
    #
    # UTF-8 is the only encoding the protobuf spec allows for string fields.
    # The result is a bytes object whose length may be greater than len(value)
    # if the string contains non-ASCII characters (each such character encodes
    # to 2–4 UTF-8 bytes).
    utf8_bytes = value.encode("utf-8")

    # The length prefix is the number of UTF-8 bytes, encoded as a varint.
    #
    # The decoder reads this varint first to know how many bytes to consume
    # for the field value. Without the length prefix, the decoder would have
    # no way to find where the string ends in the byte stream.
    length_prefix = encode_varint(len(utf8_bytes))

    # Concatenate the length prefix and the UTF-8 bytes.
    #
    # The + operator on bytes objects produces a new bytes object containing
    # the bytes of length_prefix followed immediately by the bytes of
    # utf8_bytes. This is the complete wire encoding for the field value.
    return length_prefix + utf8_bytes


def encode_bytes(value: bytes) -> bytes:
    """Encode a Python bytes object as a protobuf bytes field value.

    Protobuf bytes fields use wire type 2 (length-delimited). The encoding
    is a two-part sequence:

        1. A varint giving the number of raw bytes in the payload.
        2. The raw bytes themselves, copied verbatim.

    Unlike string fields, bytes fields impose no encoding constraint on their
    content — any byte sequence is valid, including sequences that are not
    valid UTF-8.

    The length prefix allows the decoder to know exactly how many bytes to read
    for the field value without scanning for a terminator.

    Example — encoding b'\\x00\\x01\\x02':

        Payload length: 3 bytes
        Length varint: encode_varint(3) == b'\\x03'
        Result: b'\\x03\\x00\\x01\\x02'

    Example — encoding b'' (empty bytes):

        Payload length: 0 bytes
        Length varint: encode_varint(0) == b'\\x00'
        Result: b'\\x00'

    Example — encoding b'\\xff\\xff':

        Payload length: 2 bytes
        Length varint: encode_varint(2) == b'\\x02'
        Result: b'\\x02\\xff\\xff'

    Reference:
        https://protobuf.dev/programming-guides/encoding/
    """
    # The length prefix is the number of bytes in value, encoded as a varint.
    #
    # For large payloads (e.g. 128 bytes or more), encode_varint returns a
    # multi-byte varint for the length prefix. For payloads up to 127 bytes
    # the length fits in a single varint byte.
    length_prefix = encode_varint(len(value))

    # Concatenate the length prefix and the raw payload bytes.
    #
    # value is copied verbatim — no transformation is applied to the content.
    return length_prefix + value
