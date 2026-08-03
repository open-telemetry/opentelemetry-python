# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for H2Connection.request() driven by an in-memory socket.

The fake socket feeds a scripted sequence of server frames and captures what
the client sends, so the full request state machine — flow control, early
responses, trailers, CONTINUATION, RST_STREAM, GOAWAY — is exercised without a
network. Server-side header blocks are built with this package's own HPACK
encoder, which the client's decoder reads back.
"""

import struct

import pytest

from opentelemetry.exporter.otlp._proto.grpc._pygrpc import connection as conn_mod
from opentelemetry.exporter.otlp._proto.grpc._pygrpc import frames
from opentelemetry.exporter.otlp._proto.grpc._pygrpc.connection import (
    ConnectionTerminated,
    Deadline,
    H2Connection,
    StreamReset,
    TransportError,
)
from opentelemetry.exporter.otlp._proto.grpc._pygrpc.hpack import encode as hpack_encode


class FakeSocket:
    """A scripted, in-memory stand-in for a connected socket."""

    def __init__(self, inbound=b""):
        self._inbound = bytearray(inbound)
        self.sent = bytearray()
        self.closed = False

    def settimeout(self, _timeout):
        pass

    def setsockopt(self, *_args):
        pass

    def recv(self, size):
        if not self._inbound:
            return b""  # EOF -> TransportError in the client
        chunk = bytes(self._inbound[:size])
        del self._inbound[:size]
        return chunk

    def sendall(self, data):
        self.sent += data

    def feed(self, data):
        self._inbound += data

    def close(self):
        self.closed = True


def headers_frame(stream_id, header_list, end_stream, end_headers=True):
    flags = 0
    if end_headers:
        flags |= frames.FLAG_END_HEADERS
    if end_stream:
        flags |= frames.FLAG_END_STREAM
    return frames.encode_frame(
        frames.Frame(frames.HEADERS, flags, stream_id, hpack_encode(header_list))
    )


def continuation_frame(stream_id, header_block, end_headers):
    flags = frames.FLAG_END_HEADERS if end_headers else 0
    return frames.encode_frame(
        frames.Frame(frames.CONTINUATION, flags, stream_id, header_block)
    )


def data_frame(stream_id, payload, end_stream):
    flags = frames.FLAG_END_STREAM if end_stream else 0
    return frames.encode_frame(frames.Frame(frames.DATA, flags, stream_id, payload))


def settings_frame():
    return frames.encode_frame(frames.settings_frame({}))


def make_connection(inbound):
    sock = FakeSocket(inbound)
    conn = H2Connection("example.com", 443, use_tls=False, sock=sock)
    return conn, sock


OK_RESPONSE_HEADERS = [(b":status", b"200"), (b"content-type", b"application/grpc")]
OK_TRAILERS = [(b"grpc-status", b"0")]


def sent_frames(sock, skip_preface=True):
    """Decode the frames the client sent, skipping the connection preface."""
    data = bytes(sock.sent)
    if skip_preface:
        assert data.startswith(frames.CONNECTION_PREFACE)
        data = data[len(frames.CONNECTION_PREFACE) :]
    out = []
    offset = 0
    while offset + frames.FRAME_HEADER_LEN <= len(data):
        length, frame = frames.decode_frame_header(
            data[offset : offset + frames.FRAME_HEADER_LEN]
        )
        offset += frames.FRAME_HEADER_LEN
        frame.payload = data[offset : offset + length]
        offset += length
        out.append(frame)
    return out


def test_first_header_block_declares_zero_dynamic_table():
    inbound = settings_frame() + headers_frame(
        1, [(b":status", b"200"), (b"grpc-status", b"0")], end_stream=True
    )
    conn, sock = make_connection(inbound)
    conn.request([(b":method", b"POST")], b"req", Deadline(5))
    first_headers = next(f for f in sent_frames(sock) if f.type == frames.HEADERS)
    # Leading byte 0x20 is the dynamic-table-size-update-to-0 instruction.
    assert first_headers.payload[0] == 0x20


def test_large_header_block_split_into_continuation():
    inbound = settings_frame() + headers_frame(
        1, [(b":status", b"200"), (b"grpc-status", b"0")], end_stream=True
    )
    conn, sock = make_connection(inbound)
    conn._peer_max_frame_size = 20  # force the header block across frames
    conn.request(
        [(b":method", b"POST"), (b"x-big", b"v" * 100)], b"req", Deadline(5)
    )
    sent = sent_frames(sock)
    header_frames = [f for f in sent if f.type == frames.HEADERS]
    continuations = [f for f in sent if f.type == frames.CONTINUATION]
    assert len(header_frames) == 1
    assert len(continuations) >= 1
    # The HEADERS frame must not carry END_HEADERS; the last CONTINUATION must.
    assert not header_frames[0].flags & frames.FLAG_END_HEADERS
    assert continuations[-1].flags & frames.FLAG_END_HEADERS
    assert not continuations[0].flags & frames.FLAG_END_HEADERS or len(
        continuations
    ) == 1


def test_happy_path_headers_data_trailers():
    inbound = (
        settings_frame()
        + headers_frame(1, OK_RESPONSE_HEADERS, end_stream=False)
        + data_frame(1, b"\x00\x00\x00\x00\x03abc", end_stream=False)
        + headers_frame(1, OK_TRAILERS, end_stream=True)
    )
    conn, _sock = make_connection(inbound)
    header_sets, body = conn.request(
        [(b":method", b"POST"), (b":path", b"/S/M")], b"request-body", Deadline(5)
    )
    assert dict(header_sets[0])[b":status"] == b"200"
    assert dict(header_sets[-1])[b"grpc-status"] == b"0"
    assert body == b"\x00\x00\x00\x00\x03abc"


def test_trailers_only_response():
    inbound = settings_frame() + headers_frame(
        1, [(b":status", b"200"), (b"grpc-status", b"12")], end_stream=True
    )
    conn, _sock = make_connection(inbound)
    header_sets, body = conn.request(
        [(b":method", b"POST")], b"req", Deadline(5)
    )
    assert len(header_sets) == 1
    assert dict(header_sets[0])[b"grpc-status"] == b"12"
    assert body == b""


def test_early_trailers_only_response_while_blocked_on_flow_control():
    # Regression test for the flow-control-blocked-send discard bug: the server
    # rejects a large upload (bigger than the 65535-byte connection send
    # window) with a trailers-only response before draining the body. The
    # client must surface that response, not spin until the deadline.
    body = b"x" * 70000
    inbound = settings_frame() + headers_frame(
        1, [(b":status", b"200"), (b"grpc-status", b"8")], end_stream=True
    )
    conn, sock = make_connection(inbound)
    header_sets, response_body = conn.request(
        [(b":method", b"POST")], body, Deadline(5)
    )
    assert dict(header_sets[-1])[b"grpc-status"] == b"8"
    assert response_body == b""
    # The client stopped uploading once the response arrived: it sent the
    # HEADERS plus at most the first window of DATA, never the whole body.
    data_bytes_sent = sum(
        len(f.payload) for f in sent_frames(sock) if f.type == frames.DATA
    )
    assert data_bytes_sent <= 65535


def test_flow_control_resumes_after_window_update():
    # Body exceeds the connection send window; the server opens it with a
    # WINDOW_UPDATE, then completes normally. The whole body must be sent.
    body = b"y" * 70000
    inbound = (
        settings_frame()
        + frames.encode_frame(frames.window_update_frame(0, 1 << 20))
        + frames.encode_frame(frames.window_update_frame(1, 1 << 20))
        + headers_frame(1, OK_RESPONSE_HEADERS, end_stream=False)
        + headers_frame(1, OK_TRAILERS, end_stream=True)
    )
    conn, sock = make_connection(inbound)
    header_sets, _body = conn.request([(b":method", b"POST")], body, Deadline(5))
    assert dict(header_sets[-1])[b"grpc-status"] == b"0"
    data_bytes_sent = sum(
        len(f.payload) for f in sent_frames(sock) if f.type == frames.DATA
    )
    assert data_bytes_sent == 70000


def test_continuation_reassembly_for_trailers():
    # The trailer header block is split across a HEADERS frame (END_STREAM set,
    # END_HEADERS unset) and a following CONTINUATION frame that ends it.
    block = hpack_encode(OK_TRAILERS)
    split = len(block) // 2
    inbound = (
        settings_frame()
        + headers_frame(1, OK_RESPONSE_HEADERS, end_stream=False)
        + frames.encode_frame(
            frames.Frame(frames.HEADERS, frames.FLAG_END_STREAM, 1, block[:split])
        )
        + continuation_frame(1, block[split:], end_headers=True)
    )
    conn, _sock = make_connection(inbound)
    header_sets, _body = conn.request([(b":method", b"POST")], b"req", Deadline(5))
    assert dict(header_sets[-1])[b"grpc-status"] == b"0"


def test_rst_stream_raises_stream_reset():
    inbound = settings_frame() + frames.encode_frame(
        frames.rst_stream_frame(1, 2)
    )
    conn, _sock = make_connection(inbound)
    with pytest.raises(StreamReset):
        conn.request([(b":method", b"POST")], b"req", Deadline(5))


def test_goaway_raises_connection_terminated():
    inbound = settings_frame() + frames.encode_frame(frames.goaway_frame(0, 1))
    conn, _sock = make_connection(inbound)
    with pytest.raises(ConnectionTerminated):
        conn.request([(b":method", b"POST")], b"req", Deadline(5))


def test_ping_is_acked():
    inbound = (
        settings_frame()
        + frames.encode_frame(frames.Frame(frames.PING, 0, 0, b"12345678"))
        + headers_frame(1, [(b":status", b"200"), (b"grpc-status", b"0")], end_stream=True)
    )
    conn, sock = make_connection(inbound)
    conn.request([(b":method", b"POST")], b"req", Deadline(5))
    ping_acks = [
        f
        for f in sent_frames(sock)
        if f.type == frames.PING and f.flags & frames.FLAG_ACK
    ]
    assert len(ping_acks) == 1 and ping_acks[0].payload == b"12345678"


def test_peer_closed_connection_raises_transport_error():
    conn, _sock = make_connection(settings_frame())  # no response, then EOF
    with pytest.raises(TransportError):
        conn.request([(b":method", b"POST")], b"req", Deadline(5))


def test_malformed_hpack_in_response_raises_transport_error():
    # A response HEADERS block that decodes to header index 0 is an HPACK
    # error; it must surface as TransportError, not a raw HpackError.
    bad_block = b"\x80"  # indexed header field, index 0 -> illegal
    inbound = settings_frame() + frames.encode_frame(
        frames.Frame(
            frames.HEADERS,
            frames.FLAG_END_HEADERS | frames.FLAG_END_STREAM,
            1,
            bad_block,
        )
    )
    conn, _sock = make_connection(inbound)
    with pytest.raises(TransportError):
        conn.request([(b":method", b"POST")], b"req", Deadline(5))


def test_truncated_control_frame_raises_transport_error():
    # A WINDOW_UPDATE with a 1-byte payload cannot be unpacked; the raw
    # struct.error must be converted to TransportError.
    inbound = settings_frame() + frames.encode_frame(
        frames.Frame(frames.WINDOW_UPDATE, 0, 0, b"\x01")
    )
    conn, _sock = make_connection(inbound)
    with pytest.raises(TransportError):
        conn.request([(b":method", b"POST")], b"req", Deadline(5))


def test_oversized_frame_rejected_before_payload_read():
    # A frame header declaring a length over the cap must be rejected on the
    # 9-byte header alone, before any payload is allocated.
    big = conn_mod.MAX_RECV_FRAME_SIZE + 1
    oversized_header = struct.pack(
        ">BHBBL", (big >> 16) & 0xFF, big & 0xFFFF, frames.DATA, 0, 1
    )
    conn, _sock = make_connection(settings_frame() + oversized_header)
    with pytest.raises(TransportError):
        conn.request([(b":method", b"POST")], b"req", Deadline(5))


def test_response_body_cap(monkeypatch):
    monkeypatch.setattr(conn_mod, "MAX_RESPONSE_BODY", 10)
    inbound = (
        settings_frame()
        + headers_frame(1, OK_RESPONSE_HEADERS, end_stream=False)
        + data_frame(1, b"x" * 20, end_stream=False)
    )
    conn, _sock = make_connection(inbound)
    with pytest.raises(TransportError):
        conn.request([(b":method", b"POST")], b"req", Deadline(5))


def test_header_block_cap(monkeypatch):
    monkeypatch.setattr(conn_mod, "MAX_HEADER_BLOCK", 4)
    block = hpack_encode(OK_TRAILERS)
    inbound = (
        settings_frame()
        + headers_frame(1, OK_RESPONSE_HEADERS, end_stream=False)
        + frames.encode_frame(
            frames.Frame(frames.HEADERS, frames.FLAG_END_STREAM, 1, block[:1])
        )
        + continuation_frame(1, block[1:], end_headers=True)
    )
    conn, _sock = make_connection(inbound)
    with pytest.raises(TransportError):
        conn.request([(b":method", b"POST")], b"req", Deadline(5))
