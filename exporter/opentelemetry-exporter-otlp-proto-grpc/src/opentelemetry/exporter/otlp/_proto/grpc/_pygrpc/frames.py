# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""HTTP/2 (RFC 7540) frame codec — the subset a unary gRPC client needs."""

import struct

FRAME_HEADER_LEN = 9

# Frame types.
DATA = 0x0
HEADERS = 0x1
PRIORITY = 0x2
RST_STREAM = 0x3
SETTINGS = 0x4
PUSH_PROMISE = 0x5
PING = 0x6
GOAWAY = 0x7
WINDOW_UPDATE = 0x8
CONTINUATION = 0x9

# Flags.
FLAG_END_STREAM = 0x1  # DATA, HEADERS
FLAG_ACK = 0x1  # SETTINGS, PING
FLAG_END_HEADERS = 0x4  # HEADERS, CONTINUATION
FLAG_PADDED = 0x8  # DATA, HEADERS
FLAG_PRIORITY = 0x20  # HEADERS

# SETTINGS identifiers.
SETTINGS_HEADER_TABLE_SIZE = 0x1
SETTINGS_ENABLE_PUSH = 0x2
SETTINGS_MAX_CONCURRENT_STREAMS = 0x3
SETTINGS_INITIAL_WINDOW_SIZE = 0x4
SETTINGS_MAX_FRAME_SIZE = 0x5
SETTINGS_MAX_HEADER_LIST_SIZE = 0x6

CONNECTION_PREFACE = b"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"

DEFAULT_INITIAL_WINDOW_SIZE = 65535
DEFAULT_MAX_FRAME_SIZE = 16384


class Frame:
    __slots__ = ("type", "flags", "stream_id", "payload")

    def __init__(self, frame_type, flags, stream_id, payload=b""):
        self.type = frame_type
        self.flags = flags
        self.stream_id = stream_id
        self.payload = payload

    def __repr__(self):
        return "Frame(type=0x{:x}, flags=0x{:x}, stream={}, len={})".format(
            self.type, self.flags, self.stream_id, len(self.payload)
        )


def encode_frame(frame):
    length = len(frame.payload)
    if length > 0xFFFFFF:
        raise ValueError(
            "frame payload {} exceeds the 24-bit length field".format(length)
        )
    header = struct.pack(
        ">BHBBL",
        (length >> 16) & 0xFF,
        length & 0xFFFF,
        frame.type,
        frame.flags,
        frame.stream_id & 0x7FFFFFFF,
    )
    return header + frame.payload


def decode_frame_header(header):
    """Decode the 9-octet frame header; returns ``(length, Frame)`` with an
    empty payload the caller fills once it has read ``length`` more octets."""
    high, low, frame_type, flags, stream_id = struct.unpack(">BHBBL", header)
    length = (high << 16) | low
    return length, Frame(frame_type, flags, stream_id & 0x7FFFFFFF)


def strip_padding(frame):
    """Return the payload of a DATA or HEADERS frame with padding removed."""
    payload = frame.payload
    if frame.flags & FLAG_PADDED:
        if not payload:
            raise ValueError("padded frame with empty payload")
        pad_length = payload[0]
        payload = payload[1:]
        if pad_length > len(payload):
            raise ValueError("padding longer than payload")
        payload = payload[: len(payload) - pad_length]
    if frame.type == HEADERS and frame.flags & FLAG_PRIORITY:
        if len(payload) < 5:
            raise ValueError("HEADERS priority section truncated")
        payload = payload[5:]
    return payload


def settings_frame(settings=None, ack=False):
    if ack:
        return Frame(SETTINGS, FLAG_ACK, 0)
    payload = b"".join(
        struct.pack(">HL", key, value) for key, value in (settings or {}).items()
    )
    return Frame(SETTINGS, 0, 0, payload)


def parse_settings(frame):
    if len(frame.payload) % 6:
        raise ValueError("SETTINGS payload not a multiple of 6")
    return {
        struct.unpack_from(">HL", frame.payload, offset)[0]: struct.unpack_from(
            ">HL", frame.payload, offset
        )[1]
        for offset in range(0, len(frame.payload), 6)
    }


def window_update_frame(stream_id, increment):
    return Frame(WINDOW_UPDATE, 0, stream_id, struct.pack(">L", increment))


def rst_stream_frame(stream_id, error_code):
    return Frame(RST_STREAM, 0, stream_id, struct.pack(">L", error_code))


def goaway_frame(last_stream_id, error_code):
    return Frame(GOAWAY, 0, 0, struct.pack(">LL", last_stream_id, error_code))


def parse_goaway(frame):
    last_stream_id, error_code = struct.unpack_from(">LL", frame.payload, 0)
    debug_data = frame.payload[8:]
    return last_stream_id & 0x7FFFFFFF, error_code, debug_data
