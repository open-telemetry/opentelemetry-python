# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import pytest

from opentelemetry.exporter.otlp._proto.grpc._pygrpc import frames


def roundtrip(frame):
    encoded = frames.encode_frame(frame)
    length, decoded = frames.decode_frame_header(encoded[: frames.FRAME_HEADER_LEN])
    decoded.payload = encoded[frames.FRAME_HEADER_LEN :]
    assert length == len(decoded.payload)
    return decoded


def test_data_frame_roundtrip():
    frame = roundtrip(
        frames.Frame(frames.DATA, frames.FLAG_END_STREAM, 3, b"payload")
    )
    assert (frame.type, frame.flags, frame.stream_id, frame.payload) == (
        frames.DATA,
        frames.FLAG_END_STREAM,
        3,
        b"payload",
    )


def test_settings_roundtrip():
    frame = roundtrip(
        frames.settings_frame(
            {
                frames.SETTINGS_MAX_FRAME_SIZE: 1 << 20,
                frames.SETTINGS_INITIAL_WINDOW_SIZE: 12345,
            }
        )
    )
    assert frames.parse_settings(frame) == {
        frames.SETTINGS_MAX_FRAME_SIZE: 1 << 20,
        frames.SETTINGS_INITIAL_WINDOW_SIZE: 12345,
    }


def test_settings_ack_has_empty_payload():
    frame = frames.settings_frame(ack=True)
    assert frame.flags == frames.FLAG_ACK and frame.payload == b""


def test_goaway_roundtrip():
    frame = roundtrip(frames.goaway_frame(7, 2))
    last_stream_id, error_code, debug = frames.parse_goaway(frame)
    assert (last_stream_id, error_code, debug) == (7, 2, b"")


def test_padded_data_frame_stripping():
    # PADDED flag: first octet is the pad length, padding trails the data.
    payload = bytes((3,)) + b"data" + b"\x00" * 3
    frame = frames.Frame(frames.DATA, frames.FLAG_PADDED, 1, payload)
    assert frames.strip_padding(frame) == b"data"


def test_padding_longer_than_payload_is_an_error():
    frame = frames.Frame(frames.DATA, frames.FLAG_PADDED, 1, bytes((200,)) + b"x")
    with pytest.raises(ValueError):
        frames.strip_padding(frame)


def test_headers_priority_section_stripping():
    payload = b"\x00\x00\x00\x01\x10headerblock"
    frame = frames.Frame(frames.HEADERS, frames.FLAG_PRIORITY, 1, payload)
    assert frames.strip_padding(frame) == b"headerblock"


def test_stream_id_high_bit_is_masked():
    frame = roundtrip(frames.Frame(frames.DATA, 0, 0xFFFFFFFF, b""))
    assert frame.stream_id == 0x7FFFFFFF


def test_encode_frame_rejects_payload_over_24_bits():
    class _HugePayload:
        # Reports an over-limit length without allocating 16 MiB.
        def __len__(self):
            return 0x1000000

    with pytest.raises(ValueError):
        frames.encode_frame(frames.Frame(frames.DATA, 0, 1, _HugePayload()))
