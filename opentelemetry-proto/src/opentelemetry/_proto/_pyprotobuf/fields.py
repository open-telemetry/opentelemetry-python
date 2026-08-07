"""Proto3 field-level encoding helpers for SerializeToString() implementations.

Why this module exists
----------------------
The other modules in this package (varint, tag, scalars, enum) provide the
raw encoding kernel: functions that take a Python value and return its bytes
representation in the protobuf wire format. Those functions know nothing about
proto3 messages. They do not know about field numbers, wire-type tags, or the
rule that says a field whose value equals the proto3 default must be omitted
from the serialised output.

This module sits one level above that kernel. It provides one helper per
proto3 scalar category (uint64, sint32, double, string, bytes, bool, fixed32,
fixed64) plus helpers for embedded messages and packed repeated fields. Each
helper combines three operations that every SerializeToString() method must
perform for every field it writes:

    1. Apply the proto3 default-omission rule — if the value equals the type's
       default (0, 0.0, False, b"", ""), return b"" immediately.
    2. Encode the tag — (field_number << 3) | wire_type, then varint-encoded.
    3. Encode the value — using the appropriate primitive from this package.

Without these helpers, every SerializeToString() method would repeat that
three-step pattern inline for every field, cluttering the message classes with
low-level wire-format details and making the default-omission logic easy to get
wrong or forget.

Why it is named "fields"
------------------------
Each function in this module encodes one proto3 field: it takes a field number
and a value, and returns the complete on-wire bytes for that field — tag plus
encoded value, or b"" when the value is the proto3 default. The word "field"
is the right abstraction because a proto3 field is exactly this: a field number,
a wire type, a default-omission rule, and a value encoding. The other modules
in this package encode raw values; this module encodes fields.

Layering within _pyprotobuf
----------------------------
    varint.py    — encode a varint integer to bytes
    tag.py       — encode a (field_number, wire_type) tag using varint
    scalars.py   — encode all proto3 scalar types to bytes
    enum.py      — encode a proto3 enum value (thin wrapper over scalars)
    fields.py    — encode a complete proto3 field (tag + default check + value)

The message classes (common_pb2.py, metrics_pb2.py, etc.) use this
module directly. They import the encode_* primitives from the package root
(__init__.py) and the field helpers from here.

Wire-type constants
-------------------
The protobuf specification defines six wire types. The wire type is stored in
the three lowest bits of every tag integer. Only four wire types appear in
proto3 messages (wire types 3 and 4, the deprecated group delimiters, do not
appear in new proto3 code):

    WT_VARINT = 0  — one or more bytes with a continuation bit in the MSB of
                      each byte. Used for: int32, int64, uint32, uint64, sint32,
                      sint64, bool, enum.
    WT_64BIT  = 1  — exactly 8 bytes, little-endian. Used for: double,
                      fixed64, sfixed64.
    WT_LEN    = 2  — a varint length prefix followed by that many bytes. Used
                      for: string, bytes, embedded messages, packed repeated
                      fields.
    WT_32BIT  = 5  — exactly 4 bytes, little-endian. Used for: float, fixed32,
                      sfixed32.

Reference: https://protobuf.dev/programming-guides/encoding/
"""

from __future__ import annotations

from struct import pack

from .scalars import encode_fixed32, encode_fixed64, encode_sint32
from .tag import encode_tag
from .varint import encode_varint

WT_VARINT = 0  # int32, int64, uint32, uint64, bool, enum
WT_64BIT = 1   # double, fixed64, sfixed64
WT_LEN = 2     # string, bytes, embedded messages, packed arrays
WT_32BIT = 5   # float, fixed32, sfixed32


def msg(field: int, content: bytes) -> bytes:
    """Encode an embedded message or group as a length-delimited field.

    In the protobuf wire format, an embedded message is a length-delimited
    field (wire type 2). The layout on the wire is:

        tag (varint) | byte_length (varint) | content (bytes)

    The tag encodes the field number and wire type 2. The byte_length is the
    number of bytes in the already-serialised sub-message. The content is the
    verbatim output of the sub-message's own SerializeToString() call.

    Unlike the scalar helpers, msg does not apply an omission rule for empty
    content. An embedded message with no fields set serialises to b"" (zero
    bytes), and the caller decides whether to write it at all. In practice,
    message fields are either written unconditionally when present or guarded
    by an explicit ``if self.field is not None`` check in the caller; the empty
    check is the caller's responsibility, not this helper's.

    This helper is also used for oneof sub-messages, repeated message fields
    (called once per element), and any other length-delimited payload.

    Parameters
    ----------
    field:
        The field number as declared in the .proto schema.
    content:
        The serialised bytes of the sub-message (the return value of
        sub_message.SerializeToString()).

    Returns
    -------
    bytes
        tag + varint(len(content)) + content
    """
    return encode_tag(field, WT_LEN) + encode_varint(len(content)) + content


def string(field: int, value: str) -> bytes:
    """Encode a proto3 string field, omitting it when the value is empty.

    Proto3 defines the default value for string fields as the empty string
    "". A field equal to its default must not be written to the wire, so this
    helper returns b"" when value is "".

    The encoding on the wire is:

        tag (varint) | byte_length (varint) | utf-8 bytes

    The proto3 specification requires that string fields contain valid UTF-8.
    Python's str.encode("utf-8") enforces this at the encoding step.

    Parameters
    ----------
    field:
        The field number as declared in the .proto schema.
    value:
        The string to encode. An empty string causes this helper to return
        b"" (field omitted).

    Returns
    -------
    bytes
        b"" if value is empty, otherwise tag + varint(len(utf8)) + utf8.
    """
    if not value:
        return b""
    utf8 = value.encode("utf-8")
    return encode_tag(field, WT_LEN) + encode_varint(len(utf8)) + utf8


def byt(field: int, value: bytes) -> bytes:
    """Encode a proto3 bytes field, omitting it when the value is empty.

    Proto3 defines the default value for bytes fields as the empty byte
    string b"". A field equal to its default must not be written, so this
    helper returns b"" when value is b"".

    The encoding on the wire is identical to a string field:

        tag (varint) | byte_length (varint) | raw bytes

    Unlike string, no UTF-8 encoding step is needed because the caller already
    holds raw bytes. This helper is used for span_id, trace_id, and any other
    proto3 bytes field.

    Parameters
    ----------
    field:
        The field number as declared in the .proto schema.
    value:
        The bytes to encode. An empty bytes object causes this helper to
        return b"" (field omitted).

    Returns
    -------
    bytes
        b"" if value is empty, otherwise tag + varint(len(value)) + value.
    """
    if not value:
        return b""
    return encode_tag(field, WT_LEN) + encode_varint(len(value)) + value


def u64(field: int, value: int) -> bytes:
    """Encode a proto3 uint64 (or any varint-encoded integer) field.

    This helper covers all proto3 field types whose wire type is WT_VARINT
    and whose value is a non-negative integer: uint32, uint64, int32 (when
    non-negative), int64 (when non-negative), bool (encoded as 0 or 1), and
    enum (encoded as its integer value).

    Proto3 defines the default value for these types as 0. A zero value must
    not be written to the wire.

    The encoding on the wire is:

        tag (varint) | value (varint)

    Parameters
    ----------
    field:
        The field number as declared in the .proto schema.
    value:
        A non-negative integer. Zero causes this helper to return b""
        (field omitted).

    Returns
    -------
    bytes
        b"" if value is 0, otherwise tag + varint(value).
    """
    if value == 0:
        return b""
    return encode_tag(field, WT_VARINT) + encode_varint(value)


def bool_field(field: int, value: bool) -> bytes:
    """Encode a proto3 bool field, omitting it when False.

    Proto3 defines the default value for bool as False (encoded as 0). A
    False value must not be written to the wire.

    A True value is encoded as varint 1. The wire layout is:

        tag (varint) | 0x01

    This helper is separate from u64 because booleans carry different
    semantic meaning even though they share wire type 0 (varint). Keeping
    them distinct makes SerializeToString() implementations easier to read.

    Parameters
    ----------
    field:
        The field number as declared in the .proto schema.
    value:
        The boolean to encode. False causes this helper to return b""
        (field omitted). True is encoded as varint 1.

    Returns
    -------
    bytes
        b"" if value is False, otherwise tag + 0x01.
    """
    if not value:
        return b""
    return encode_tag(field, WT_VARINT) + encode_varint(1)


def fix32(field: int, value: int) -> bytes:
    """Encode a proto3 fixed32 field (4-byte little-endian uint32).

    fixed32 uses wire type WT_32BIT. The decoder reads exactly 4 bytes after
    the tag. This makes fixed32 more efficient than uint32 for values that are
    frequently large (close to 2^32), because it avoids varint overhead.

    Proto3 default is 0. A zero value must not be written to the wire.

    The encoding on the wire is:

        tag (varint) | 4-byte little-endian uint32

    Parameters
    ----------
    field:
        The field number as declared in the .proto schema.
    value:
        An unsigned 32-bit integer. Zero causes this helper to return b""
        (field omitted).

    Returns
    -------
    bytes
        b"" if value is 0, otherwise tag + 4 bytes little-endian.
    """
    if value == 0:
        return b""
    return encode_tag(field, WT_32BIT) + encode_fixed32(value)


def fix64(field: int, value: int) -> bytes:
    """Encode a proto3 fixed64 field (8-byte little-endian uint64).

    fixed64 uses wire type WT_64BIT. The decoder reads exactly 8 bytes after
    the tag. In the OTel proto schemas, fixed64 is used for nanosecond
    timestamps (start_time_unix_nano, time_unix_nano), counts, and bucket
    counts that are guaranteed to be non-negative.

    Proto3 default is 0. A zero value must not be written to the wire.

    The encoding on the wire is:

        tag (varint) | 8-byte little-endian uint64

    Parameters
    ----------
    field:
        The field number as declared in the .proto schema.
    value:
        An unsigned 64-bit integer. Zero causes this helper to return b""
        (field omitted).

    Returns
    -------
    bytes
        b"" if value is 0, otherwise tag + 8 bytes little-endian.
    """
    if value == 0:
        return b""
    return encode_tag(field, WT_64BIT) + encode_fixed64(value)


def dbl(field: int, value: float) -> bytes:
    """Encode a proto3 double field (8-byte IEEE 754), omitting when zero.

    double uses wire type WT_64BIT. The decoder reads exactly 8 bytes and
    interprets them as an IEEE 754 double-precision floating-point number in
    little-endian byte order.

    Proto3 default is 0.0. A zero value must not be written to the wire.
    Note that -0.0 compares equal to 0.0 in Python, so dbl(field, -0.0)
    returns b"" — if that distinction matters, use opt_dbl instead.

    This helper is used for scalar double fields that have a meaningful zero
    default and should be omitted when zero: for example, the `sum` field of
    SummaryDataPoint and the `zero_threshold` field of
    ExponentialHistogramDataPoint.

    Parameters
    ----------
    field:
        The field number as declared in the .proto schema.
    value:
        An IEEE 754 double. 0.0 causes this helper to return b""
        (field omitted). Infinity and NaN are encoded as-is.

    Returns
    -------
    bytes
        b"" if value == 0.0, otherwise tag + 8-byte little-endian double.
    """
    if value == 0.0:
        return b""
    return encode_tag(field, WT_64BIT) + pack("<d", value)


def opt_dbl(field: int, value: float | None) -> bytes:
    """Encode an optional proto3 double field, written even when 0.0.

    Some double fields in the OTel proto schemas are declared optional
    (proto3 optional syntax), which means the presence of the field is
    significant regardless of its value. A value of 0.0 is a meaningful
    measurement and must be written; only None (field not set) causes the
    field to be omitted.

    This is distinct from dbl, which omits 0.0 as the proto3 default.
    opt_dbl is used for fields such as `sum`, `min`, and `max` on histogram
    data points, where None means "not present" and 0.0 means "present and
    measured as zero".

    The encoding on the wire is identical to dbl when the value is present:

        tag (varint) | 8-byte little-endian double

    Parameters
    ----------
    field:
        The field number as declared in the .proto schema.
    value:
        An IEEE 754 double, or None. None causes this helper to return b""
        (field omitted). Any float, including 0.0, -0.0, inf, and nan, is
        encoded and written to the wire.

    Returns
    -------
    bytes
        b"" if value is None, otherwise tag + 8-byte little-endian double.
    """
    if value is None:
        return b""
    return encode_tag(field, WT_64BIT) + pack("<d", value)


def sint32(field: int, value: int) -> bytes:
    """Encode a proto3 sint32 field (ZigZag varint), omitting when zero.

    sint32 uses wire type WT_VARINT but applies ZigZag encoding before the
    varint step. ZigZag maps signed integers to unsigned integers so that
    small negative values produce short varints rather than the ten-byte
    varints that two's-complement representation would require:

        0  →  0
       -1  →  1
        1  →  2
       -2  →  3
        n  →  2*n        (for n >= 0)
        n  →  -2*n - 1   (for n < 0)

    This is the correct encoding for the proto3 `sint32` type. It is NOT used
    for `int32` fields (use u64 for non-negative int32, or encode_int from
    the package for signed int32).

    In the OTel proto schemas, sint32 appears on the `scale` field of
    ExponentialHistogramDataPoint and the `offset` field of its Buckets
    sub-message. These fields represent signed exponents and can be negative.

    Proto3 default is 0. A zero value must not be written to the wire.

    Parameters
    ----------
    field:
        The field number as declared in the .proto schema.
    value:
        A signed 32-bit integer. Zero causes this helper to return b""
        (field omitted).

    Returns
    -------
    bytes
        b"" if value is 0, otherwise tag + ZigZag-encoded varint.
    """
    if value == 0:
        return b""
    return encode_tag(field, WT_VARINT) + encode_sint32(value)


def packed_uint64(field: int, values: list[int]) -> bytes:
    """Encode a packed repeated uint64 field.

    In proto3, repeated scalar fields are packed by default. "Packed" means
    all elements are encoded contiguously without a tag before each one.
    Instead, a single tag and a single length prefix wrap the entire payload:

        tag (varint) | payload_length (varint) | element0 (varint) | element1 (varint) | ...

    Each element is encoded as an independent varint, exactly as encode_varint
    would encode it if the field were scalar. The decoder knows how many
    elements are present by tracking how many bytes it has consumed relative
    to payload_length.

    An empty list produces b"" (field omitted). This matches proto3 behaviour:
    a repeated field with zero elements is indistinguishable from the field
    being absent.

    This helper is used for fields such as bucket_counts in
    ExponentialHistogramDataPoint.Buckets.

    Parameters
    ----------
    field:
        The field number as declared in the .proto schema.
    values:
        A list of non-negative integers. An empty list causes this helper
        to return b"" (field omitted).

    Returns
    -------
    bytes
        b"" if values is empty, otherwise tag + varint(len(payload)) + payload,
        where payload is the concatenation of varint-encoded elements.
    """
    if not values:
        return b""
    payload = b"".join(encode_varint(v) for v in values)
    return encode_tag(field, WT_LEN) + encode_varint(len(payload)) + payload


def packed_fix64(field: int, values: list[int]) -> bytes:
    """Encode a packed repeated fixed64 field.

    Like packed_uint64 but each element is encoded as an 8-byte
    little-endian uint64 rather than a varint. The wire layout is:

        tag (varint) | payload_length (varint) | element0 (8 bytes) | element1 (8 bytes) | ...

    fixed64 encoding is efficient for values that are close to 2^64 or are
    accessed in bulk (the payload is a flat array of 8-byte little-endian
    words, amenable to memcpy).

    An empty list produces b"" (field omitted).

    This helper is used for the bucket_counts field of HistogramDataPoint,
    where counts are non-negative 64-bit integers.

    Parameters
    ----------
    field:
        The field number as declared in the .proto schema.
    values:
        A list of non-negative 64-bit integers. An empty list causes this
        helper to return b"" (field omitted).

    Returns
    -------
    bytes
        b"" if values is empty, otherwise tag + varint(len(payload)) + payload,
        where payload is the concatenation of 8-byte little-endian encodings.
    """
    if not values:
        return b""
    payload = b"".join(encode_fixed64(v) for v in values)
    return encode_tag(field, WT_LEN) + encode_varint(len(payload)) + payload


def packed_double(field: int, values: list[float]) -> bytes:
    """Encode a packed repeated double field.

    Like packed_uint64 but each element is an IEEE 754 double (8 bytes,
    little-endian). The wire layout is:

        tag (varint) | payload_length (varint) | element0 (8 bytes) | element1 (8 bytes) | ...

    struct.pack with format "<Nd" (N doubles, little-endian) encodes all
    elements in one call, which is more efficient than iterating and
    concatenating individually.

    An empty list produces b"" (field omitted).

    This helper is used for the explicit_bounds field of HistogramDataPoint,
    which lists the upper bounds of each histogram bucket.

    Parameters
    ----------
    field:
        The field number as declared in the .proto schema.
    values:
        A list of IEEE 754 doubles. An empty list causes this helper to
        return b"" (field omitted).

    Returns
    -------
    bytes
        b"" if values is empty, otherwise tag + varint(len(payload)) + payload,
        where payload is the concatenation of 8-byte little-endian doubles.
    """
    if not values:
        return b""
    payload = pack(f"<{len(values)}d", *values)
    return encode_tag(field, WT_LEN) + encode_varint(len(payload)) + payload
