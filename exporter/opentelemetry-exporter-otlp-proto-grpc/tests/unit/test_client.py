# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the gRPC message framing and gzip handling in client.py."""

import socket
import zlib

import pytest

from opentelemetry.exporter.otlp._proto.grpc._pygrpc.client import (
    MAX_DECOMPRESSED_MESSAGE,
    Channel,
    RpcError,
    StatusCode,
    _frame_message,
    _gunzip,
    _unframe_messages,
)
from opentelemetry.exporter.otlp._proto.grpc._pygrpc.connection import (
    ConnectionTerminated,
    TransportError,
)


def _gzip(data):
    compressor = zlib.compressobj(9, zlib.DEFLATED, 16 + zlib.MAX_WBITS)
    return compressor.compress(data) + compressor.flush()


def test_frame_unframe_roundtrip_uncompressed():
    body = _frame_message(b"hello", compress=False)
    assert _unframe_messages(body, b"identity") == [b"hello"]


def test_frame_unframe_roundtrip_gzip():
    body = _frame_message(b"hello world" * 50, compress=True)
    assert _unframe_messages(body, b"gzip") == [b"hello world" * 50]


def test_gunzip_roundtrip():
    payload = b"the quick brown fox" * 100
    assert _gunzip(_gzip(payload), 1 << 20) == payload


def test_gunzip_rejects_bomb():
    # ~8 MiB of zeros compresses to a few KiB; decompressing under a 4 MiB cap
    # must raise rather than allocate the full expansion.
    bomb = _gzip(b"\x00" * (8 << 20))
    assert len(bomb) < (1 << 20)
    with pytest.raises(RpcError) as excinfo:
        _gunzip(bomb, MAX_DECOMPRESSED_MESSAGE)
    assert excinfo.value.code() == StatusCode.RESOURCE_EXHAUSTED


def test_unframe_rejects_compressed_flag_under_identity_encoding():
    # compressed_flag=1 but the stream advertised identity encoding.
    framed = _frame_message(b"payload", compress=True)
    with pytest.raises(RpcError) as excinfo:
        _unframe_messages(framed, b"identity")
    assert excinfo.value.code() == StatusCode.INTERNAL


def test_unframe_truncated_prefix():
    with pytest.raises(RpcError):
        _unframe_messages(b"\x00\x00\x00", b"identity")


def _channel_with_fake_once(monkeypatch, once):
    channel = Channel("host:1", use_tls=False)
    monkeypatch.setattr(channel, "_unary_call_once", once)
    monkeypatch.setattr(channel, "close", lambda: None)
    return channel


def test_retry_shares_one_deadline_across_attempts(monkeypatch):
    seen_deadlines = []

    def once(path, request_bytes, metadata, deadline, compression):
        seen_deadlines.append(deadline)
        if len(seen_deadlines) == 1:
            raise TransportError("first attempt fails")
        return b"ok"

    channel = _channel_with_fake_once(monkeypatch, once)
    assert channel.unary_call("/S/M", b"req") == b"ok"
    # Both attempts ran, and both received the same Deadline object — the
    # timeout budget is not restarted on reconnect.
    assert len(seen_deadlines) == 2
    assert seen_deadlines[0] is seen_deadlines[1]


def test_socket_timeout_maps_to_deadline_exceeded_without_retry(monkeypatch):
    attempts = []

    def once(path, request_bytes, metadata, deadline, compression):
        attempts.append(1)
        raise socket.timeout("deadline exceeded")

    channel = _channel_with_fake_once(monkeypatch, once)
    with pytest.raises(RpcError) as excinfo:
        channel.unary_call("/S/M", b"req")
    assert excinfo.value.code() == StatusCode.DEADLINE_EXCEEDED
    assert len(attempts) == 1  # a timeout is terminal, not retried


def test_two_transport_failures_map_to_unavailable(monkeypatch):
    attempts = []

    def once(path, request_bytes, metadata, deadline, compression):
        attempts.append(1)
        raise TransportError("boom")

    channel = _channel_with_fake_once(monkeypatch, once)
    with pytest.raises(RpcError) as excinfo:
        channel.unary_call("/S/M", b"req")
    assert excinfo.value.code() == StatusCode.UNAVAILABLE
    assert len(attempts) == 2


def test_goaway_unprocessed_stream_is_retried(monkeypatch):
    attempts = []

    def once(path, request_bytes, metadata, deadline, compression):
        attempts.append(1)
        if len(attempts) == 1:
            error = ConnectionTerminated(0, 0, b"")  # last_stream_id below ours
            error.stream_processed = False
            raise error
        return b"ok"

    channel = _channel_with_fake_once(monkeypatch, once)
    assert channel.unary_call("/S/M", b"req") == b"ok"
    assert len(attempts) == 2


def test_goaway_processed_stream_is_not_retried(monkeypatch):
    attempts = []

    def once(path, request_bytes, metadata, deadline, compression):
        attempts.append(1)
        error = ConnectionTerminated(99, 0, b"")  # our stream was processed
        error.stream_processed = True
        raise error

    channel = _channel_with_fake_once(monkeypatch, once)
    with pytest.raises(RpcError) as excinfo:
        channel.unary_call("/S/M", b"req")
    assert excinfo.value.code() == StatusCode.UNAVAILABLE
    assert len(attempts) == 1  # no retry: the export may already be applied


class _FakeConnection:
    def __init__(self, header_sets, body=b""):
        self._header_sets = header_sets
        self._body = body

    def request(self, headers, body, deadline):
        return self._header_sets, self._body

    def close(self):
        pass


def _channel_with_response(monkeypatch, header_sets, body=b""):
    channel = Channel("host:1", use_tls=False)
    fake = _FakeConnection(header_sets, body)
    monkeypatch.setattr(channel, "_connect", lambda deadline: fake)
    return channel


def test_ok_response_returns_message(monkeypatch):
    channel = _channel_with_response(
        monkeypatch,
        [
            [(b":status", b"200"), (b"content-type", b"application/grpc")],
            [(b"grpc-status", b"0")],
        ],
        body=_frame_message(b"response", compress=False),
    )
    assert channel.unary_call("/S/M", b"req") == b"response"


@pytest.mark.parametrize(
    "http_status,expected",
    [
        (b"401", StatusCode.UNAUTHENTICATED),
        (b"403", StatusCode.PERMISSION_DENIED),
        (b"404", StatusCode.UNIMPLEMENTED),
        (b"503", StatusCode.UNAVAILABLE),
        (b"418", StatusCode.UNKNOWN),  # unmapped -> UNKNOWN, not blanket UNAVAILABLE
    ],
)
def test_non_200_http_status_mapping(monkeypatch, http_status, expected):
    channel = _channel_with_response(monkeypatch, [[(b":status", http_status)]])
    with pytest.raises(RpcError) as excinfo:
        channel.unary_call("/S/M", b"req")
    assert excinfo.value.code() == expected


def test_unknown_numeric_grpc_status_maps_to_unknown(monkeypatch):
    # A numeric status outside the known set must map to UNKNOWN, not crash.
    channel = _channel_with_response(
        monkeypatch,
        [
            [(b":status", b"200"), (b"content-type", b"application/grpc")],
            [(b"grpc-status", b"999")],
        ],
    )
    with pytest.raises(RpcError) as excinfo:
        channel.unary_call("/S/M", b"req")
    assert excinfo.value.code() == StatusCode.UNKNOWN


def test_ipv6_target_strips_brackets_but_keeps_authority():
    channel = Channel("[::1]:4317", use_tls=False)
    assert channel._host == "::1"
    assert channel._port == 4317
    assert channel._authority == "[::1]:4317"


def test_target_requires_numeric_port():
    with pytest.raises(ValueError):
        Channel("host:notaport", use_tls=False)
    with pytest.raises(ValueError):
        Channel("hostwithoutport", use_tls=False)
