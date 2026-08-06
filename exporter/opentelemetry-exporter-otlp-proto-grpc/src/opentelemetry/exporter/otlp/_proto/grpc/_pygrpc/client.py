# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Unary gRPC calls over the pure-Python HTTP/2 connection."""

import enum
import socket
import struct
import zlib

from .connection import (
    ConnectionTerminated,
    Deadline,
    H2Connection,
    TransportError,
)


class StatusCode(enum.IntEnum):
    """gRPC status codes (subset semantics identical to grpc.StatusCode)."""

    OK = 0
    CANCELLED = 1
    UNKNOWN = 2
    INVALID_ARGUMENT = 3
    DEADLINE_EXCEEDED = 4
    NOT_FOUND = 5
    ALREADY_EXISTS = 6
    PERMISSION_DENIED = 7
    RESOURCE_EXHAUSTED = 8
    FAILED_PRECONDITION = 9
    ABORTED = 10
    OUT_OF_RANGE = 11
    UNIMPLEMENTED = 12
    INTERNAL = 13
    UNAVAILABLE = 14
    DATA_LOSS = 15
    UNAUTHENTICATED = 16


class RpcError(Exception):
    def __init__(self, status_code, details=""):
        super().__init__("{}: {}".format(status_code.name, details))
        self._status_code = status_code
        self._details = details

    def code(self):
        return self._status_code

    def details(self):
        return self._details


def _grpc_timeout_header(timeout_seconds):
    # grpc-timeout is a value plus a unit, with at most 8 digits (gRPC
    # over-HTTP2 spec). Milliseconds keep sub-second precision for normal
    # export timeouts; fall back to coarser units when the millisecond value
    # would overflow 8 digits (~27.7 hours).
    for scale, unit in ((1000, b"m"), (1, b"S"), (1.0 / 60, b"M"), (1.0 / 3600, b"H")):
        value = max(1, int(timeout_seconds * scale))
        if value < 100000000:
            return b"%d%s" % (value, unit)
    return b"99999999H"


# Cap on a single decompressed response message, bounding the amplification a
# gzip bomb from a malicious endpoint can inflict on an in-process client.
# gRPC's own default receive limit is 4 MiB; OTLP export responses are far
# smaller.
MAX_DECOMPRESSED_MESSAGE = 4 << 20


def _gunzip(data, max_size):
    """Decompress a gzip (RFC 1952) gRPC message, rejecting output over
    ``max_size`` bytes so a small compressed payload cannot expand without
    bound."""
    decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
    try:
        out = decompressor.decompress(data, max_size)
        if decompressor.unconsumed_tail:
            raise RpcError(
                StatusCode.RESOURCE_EXHAUSTED,
                "decompressed message exceeds {}-byte limit".format(max_size),
            )
        return out + decompressor.flush()
    except zlib.error as error:
        raise RpcError(
            StatusCode.INTERNAL, "corrupt gzip response: {}".format(error)
        ) from error


def _frame_message(message_bytes, compress):
    if compress:
        # gzip wrapper, not raw deflate: gRPC's "gzip" encoding is RFC 1952.
        compressor = zlib.compressobj(9, zlib.DEFLATED, 16 + zlib.MAX_WBITS)
        message_bytes = compressor.compress(message_bytes) + compressor.flush()
    return struct.pack(">BL", 1 if compress else 0, len(message_bytes)) + message_bytes


def _unframe_messages(body, encoding):
    messages = []
    offset = 0
    while offset < len(body):
        if offset + 5 > len(body):
            raise RpcError(StatusCode.INTERNAL, "truncated gRPC message prefix")
        compressed_flag, length = struct.unpack_from(">BL", body, offset)
        offset += 5
        if offset + length > len(body):
            raise RpcError(StatusCode.INTERNAL, "truncated gRPC message body")
        message = bytes(body[offset : offset + length])
        offset += length
        if compressed_flag:
            if encoding != b"gzip":
                raise RpcError(
                    StatusCode.INTERNAL,
                    "compressed message with unsupported grpc-encoding {!r}".format(
                        encoding
                    ),
                )
            message = _gunzip(message, MAX_DECOMPRESSED_MESSAGE)
        messages.append(message)
    return messages


class Compression(enum.Enum):
    NoCompression = 0
    Gzip = 2


# gRPC's HTTP-status-to-grpc-status mapping for responses that never carry a
# grpc-status trailer (gRPC over HTTP/2 spec, "Responses" section).
_HTTP_TO_GRPC_STATUS = {
    b"400": StatusCode.INTERNAL,
    b"401": StatusCode.UNAUTHENTICATED,
    b"403": StatusCode.PERMISSION_DENIED,
    b"404": StatusCode.UNIMPLEMENTED,
    b"429": StatusCode.UNAVAILABLE,
    b"502": StatusCode.UNAVAILABLE,
    b"503": StatusCode.UNAVAILABLE,
    b"504": StatusCode.UNAVAILABLE,
}


class Channel:
    """A lazily connected channel to one gRPC endpoint, unary calls only.

    ``target`` is ``host:port``. One transparent reconnect per call absorbs
    idle timeouts and graceful GOAWAYs.
    """

    def __init__(self, target, use_tls=True, ssl_context=None):
        host, sep, port = target.rpartition(":")
        if not sep or not host or not port.isdigit():
            raise ValueError(
                "target must be host:port with a numeric port, got {!r}. "
                "Bracket IPv6 literals, e.g. [::1]:4317.".format(target)
            )
        # The authority header keeps the target verbatim (brackets included);
        # the socket and TLS SNI need the IPv6 literal without its brackets.
        if host.startswith("[") and host.endswith("]"):
            host = host[1:-1]
        self._host = host
        self._port = int(port)
        self._authority = target
        self._use_tls = use_tls
        self._ssl_context = ssl_context
        self._connection = None

    def close(self):
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def _connect(self, deadline):
        if self._connection is None:
            self._connection = H2Connection(
                self._host,
                self._port,
                self._use_tls,
                ssl_context=self._ssl_context,
                connect_timeout=deadline.remaining(),
            )
        return self._connection

    def unary_call(
        self,
        path,
        request_bytes,
        metadata=(),
        timeout=10.0,
        compression=Compression.NoCompression,
    ):
        """Invoke ``path`` (``/package.Service/Method``); returns the response
        message bytes, or raises RpcError."""
        # One deadline spans both attempts (connect, TLS, preface, and I/O), so
        # a transparent reconnect cannot double the caller's timeout budget.
        deadline = Deadline(timeout)
        for attempt in (1, 2):
            try:
                return self._unary_call_once(
                    path, request_bytes, metadata, deadline, compression
                )
            except socket.timeout as error:
                # A timeout is terminal: the deadline is shared across attempts,
                # so a retry has no budget left.
                self.close()
                raise RpcError(StatusCode.DEADLINE_EXCEEDED, str(error)) from error
            except ConnectionTerminated as error:
                self.close()
                # Retry only a stream the server did not process (GOAWAY
                # last_stream_id below ours); otherwise a retry could duplicate
                # an export the server already accepted.
                if attempt == 1 and not error.stream_processed:
                    continue
                raise RpcError(StatusCode.UNAVAILABLE, str(error)) from error
            except (TransportError, OSError) as error:
                self.close()
                if attempt == 2:
                    raise RpcError(StatusCode.UNAVAILABLE, str(error)) from error

    def _unary_call_once(self, path, request_bytes, metadata, deadline, compression):
        connection = self._connect(deadline)
        compress = compression == Compression.Gzip

        headers = [
            (b":method", b"POST"),
            (b":scheme", b"https" if self._use_tls else b"http"),
            (b":path", path.encode() if isinstance(path, str) else path),
            (b":authority", self._authority.encode()),
            (b"te", b"trailers"),
            (b"content-type", b"application/grpc"),
            (b"user-agent", b"otlp-pyproto-python/0.1"),
        ]
        # Advertise the remaining budget so the server can abandon work once we
        # would give up; remaining() raises socket.timeout if already expired.
        remaining = deadline.remaining()
        if remaining is not None:
            headers.append((b"grpc-timeout", _grpc_timeout_header(remaining)))
        if compress:
            headers.append((b"grpc-encoding", b"gzip"))
        headers.append((b"grpc-accept-encoding", b"identity, gzip"))
        for name, value in metadata:
            name = name.encode() if isinstance(name, str) else name
            value = value.encode() if isinstance(value, str) else value
            headers.append((name.lower(), value))

        body = _frame_message(request_bytes, compress)
        header_sets, response_body = connection.request(headers, body, deadline)

        response_headers = dict(header_sets[0]) if header_sets else {}
        trailers = dict(header_sets[-1]) if header_sets else {}

        http_status = response_headers.get(b":status")
        if http_status is not None and http_status != b"200":
            raise RpcError(
                _HTTP_TO_GRPC_STATUS.get(http_status, StatusCode.UNKNOWN),
                "HTTP status {}".format(http_status.decode()),
            )

        grpc_status = trailers.get(b"grpc-status")
        if grpc_status is None:
            raise RpcError(StatusCode.INTERNAL, "missing grpc-status trailer")
        try:
            status_code = StatusCode(int(grpc_status))
        except ValueError:
            # Non-numeric, or a numeric code outside the known set: gRPC maps
            # both to UNKNOWN rather than crashing the caller.
            status_code = StatusCode.UNKNOWN
        if status_code != StatusCode.OK:
            message = trailers.get(b"grpc-message", b"")
            raise RpcError(status_code, message.decode("utf-8", "replace"))

        messages = _unframe_messages(
            response_body, response_headers.get(b"grpc-encoding", b"identity")
        )
        if len(messages) != 1:
            raise RpcError(
                StatusCode.INTERNAL,
                "expected exactly 1 response message, got {}".format(len(messages)),
            )
        return messages[0]
