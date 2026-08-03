# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""A minimal HTTP/2 client connection for unary gRPC calls.

Speaks exactly the subset of RFC 7540 a unary gRPC client needs: connection
preface and SETTINGS exchange, one request stream at a time, flow-control
accounting on both directions, PING replies, and GOAWAY handling.
No server push (disabled via SETTINGS), no priorities, no concurrent streams.
"""

import socket
import ssl
import struct
import time

from . import frames
from .hpack import Decoder as HpackDecoder
from .hpack import HpackError
from .hpack import encode as hpack_encode
from .hpack import encode_dynamic_table_size_update

# Caps on server-controlled sizes, to bound the memory a malicious or
# misconfigured endpoint can make an in-process client allocate. gRPC unary
# OTLP responses are tiny (an empty or small partial-success message), so these
# limits are generous headroom, not tuning knobs.
MAX_RECV_FRAME_SIZE = 1 << 20  # reject any single frame larger than 1 MiB
MAX_RESPONSE_BODY = 4 << 20  # total DATA payload accepted per response
MAX_HEADER_BLOCK = 1 << 20  # total HEADERS + CONTINUATION payload per block


class TransportError(Exception):
    """Connection-level failure: the connection is no longer usable."""


class ConnectionTerminated(TransportError):
    """The peer sent GOAWAY.

    ``last_stream_id`` is the highest stream the peer promises it processed;
    a stream with a higher id was not processed and is safe to retry.
    ``stream_processed`` is set by request() once it knows the active stream id.
    """

    def __init__(self, last_stream_id, error_code, debug_data):
        super().__init__(
            "GOAWAY last_stream_id={} error_code={} debug={!r}".format(
                last_stream_id, error_code, debug_data
            )
        )
        self.last_stream_id = last_stream_id
        self.error_code = error_code
        self.debug_data = debug_data
        self.stream_processed = True  # conservative until request() decides


class StreamReset(TransportError):
    """The peer sent RST_STREAM for the active stream."""

    def __init__(self, error_code):
        super().__init__("RST_STREAM error_code={}".format(error_code))
        self.error_code = error_code


class Deadline:
    def __init__(self, timeout):
        self._expires = None if timeout is None else time.monotonic() + timeout

    def remaining(self):
        if self._expires is None:
            return None
        remaining = self._expires - time.monotonic()
        if remaining <= 0:
            raise socket.timeout("deadline exceeded")
        return remaining


class H2Connection:
    """One HTTP/2 connection; streams are used strictly sequentially."""

    def __init__(
        self, host, port, use_tls, ssl_context=None, connect_timeout=10, sock=None
    ):
        # ``sock`` injects a ready transport (a connected, ALPN-negotiated
        # socket) instead of dialing one. Production callers never pass it; it
        # is the seam unit tests use to drive the protocol over an in-memory
        # socket. When provided, dialing and TLS setup are skipped.
        self._host = host
        self._port = port
        self._next_stream_id = 1
        self._recv_buffer = b""
        self._peer_max_frame_size = frames.DEFAULT_MAX_FRAME_SIZE
        self._peer_initial_window = frames.DEFAULT_INITIAL_WINDOW_SIZE
        self._send_window_connection = frames.DEFAULT_INITIAL_WINDOW_SIZE
        self._hpack_decoder = HpackDecoder()

        if sock is None:
            sock = socket.create_connection((host, port), timeout=connect_timeout)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            if use_tls:
                context = ssl_context or ssl.create_default_context()
                context.set_alpn_protocols(["h2"])
                sock = context.wrap_socket(sock, server_hostname=host)
                negotiated = sock.selected_alpn_protocol()
                if negotiated != "h2":
                    sock.close()
                    raise TransportError(
                        "server did not negotiate HTTP/2 via ALPN (got {!r})".format(
                            negotiated
                        )
                    )
            # Without TLS this is h2c with prior knowledge, which gRPC servers
            # (including grpc-go) accept on their plaintext listeners.
        self._sock = sock

        self._sock.sendall(
            frames.CONNECTION_PREFACE
            + frames.encode_frame(
                frames.settings_frame({frames.SETTINGS_ENABLE_PUSH: 0})
            )
        )

    def close(self):
        try:
            self._sock.close()
        except OSError:
            pass

    # --- low-level I/O ------------------------------------------------------

    def _recv_exactly(self, count, deadline):
        while len(self._recv_buffer) < count:
            self._sock.settimeout(deadline.remaining())
            chunk = self._sock.recv(65536)
            if not chunk:
                raise TransportError("connection closed by peer")
            self._recv_buffer += chunk
        data, self._recv_buffer = (
            self._recv_buffer[:count],
            self._recv_buffer[count:],
        )
        return data

    def _read_frame(self, deadline):
        header = self._recv_exactly(frames.FRAME_HEADER_LEN, deadline)
        length, frame = frames.decode_frame_header(header)
        if length > MAX_RECV_FRAME_SIZE:
            raise TransportError(
                "frame length {} exceeds {}-byte limit".format(
                    length, MAX_RECV_FRAME_SIZE
                )
            )
        if length:
            frame.payload = self._recv_exactly(length, deadline)
        return frame

    def _send_frame(self, frame, deadline):
        self._sock.settimeout(deadline.remaining())
        self._sock.sendall(frames.encode_frame(frame))

    # --- connection-level frame dispatch -------------------------------------

    def _handle_connection_frame(self, frame, stream_id, stream_state, deadline):
        """Process a frame; returns True if it belonged to the active stream."""
        if frame.stream_id == 0:
            if frame.type == frames.SETTINGS and not frame.flags & frames.FLAG_ACK:
                settings = frames.parse_settings(frame)
                if frames.SETTINGS_MAX_FRAME_SIZE in settings:
                    self._peer_max_frame_size = settings[
                        frames.SETTINGS_MAX_FRAME_SIZE
                    ]
                if frames.SETTINGS_INITIAL_WINDOW_SIZE in settings:
                    delta = (
                        settings[frames.SETTINGS_INITIAL_WINDOW_SIZE]
                        - self._peer_initial_window
                    )
                    self._peer_initial_window += delta
                    stream_state["send_window"] += delta
                self._send_frame(frames.settings_frame(ack=True), deadline)
            elif frame.type == frames.PING and not frame.flags & frames.FLAG_ACK:
                self._send_frame(
                    frames.Frame(
                        frames.PING, frames.FLAG_ACK, 0, frame.payload
                    ),
                    deadline,
                )
            elif frame.type == frames.WINDOW_UPDATE:
                (increment,) = struct.unpack(">L", frame.payload)
                self._send_window_connection += increment & 0x7FFFFFFF
            elif frame.type == frames.GOAWAY:
                last_stream_id, error_code, debug_data = frames.parse_goaway(frame)
                raise ConnectionTerminated(last_stream_id, error_code, debug_data)
            return False
        if frame.stream_id != stream_id:
            # Sequential usage: frames for other streams are stale leftovers.
            return False
        if frame.type == frames.WINDOW_UPDATE:
            (increment,) = struct.unpack(">L", frame.payload)
            stream_state["send_window"] += increment & 0x7FFFFFFF
            return False
        if frame.type == frames.RST_STREAM:
            (error_code,) = struct.unpack(">L", frame.payload)
            raise StreamReset(error_code)
        return True

    # --- the one operation this connection exists for ------------------------

    def _send_headers(self, stream_id, header_block, deadline):
        """Send a header block, splitting it across HEADERS + CONTINUATION
        frames when it exceeds the peer's maximum frame size."""
        max_size = self._peer_max_frame_size
        if len(header_block) <= max_size:
            self._send_frame(
                frames.Frame(
                    frames.HEADERS, frames.FLAG_END_HEADERS, stream_id, header_block
                ),
                deadline,
            )
            return
        self._send_frame(
            frames.Frame(frames.HEADERS, 0, stream_id, header_block[:max_size]),
            deadline,
        )
        offset = max_size
        while offset < len(header_block):
            chunk = header_block[offset : offset + max_size]
            offset += len(chunk)
            end_headers = offset >= len(header_block)
            self._send_frame(
                frames.Frame(
                    frames.CONTINUATION,
                    frames.FLAG_END_HEADERS if end_headers else 0,
                    stream_id,
                    chunk,
                ),
                deadline,
            )

    def _process_response_frame(self, frame, stream_id, stream_state, resp, deadline):
        """Fold one active-stream response frame into ``resp`` (a dict with
        ``header_sets``, ``body_chunks``, and ``header_fragments``). Returns
        True once the response stream has ended.

        Connection-level frames (SETTINGS, PING, WINDOW_UPDATE, GOAWAY) and
        stale other-stream frames are delegated to _handle_connection_frame and
        never complete the response.
        """
        if resp["header_fragments"] is not None:
            if frame.type != frames.CONTINUATION or frame.stream_id != stream_id:
                raise TransportError("expected CONTINUATION frame")
            resp["header_fragments"].append(frame.payload)
            resp["header_bytes"] += len(frame.payload)
            if resp["header_bytes"] > MAX_HEADER_BLOCK:
                raise TransportError(
                    "header block exceeds {}-byte limit".format(MAX_HEADER_BLOCK)
                )
            if frame.flags & frames.FLAG_END_HEADERS:
                resp["header_sets"].append(
                    self._hpack_decoder.decode(b"".join(resp["header_fragments"]))
                )
                resp["header_fragments"] = None
                return resp["pending_end_stream"]
            return False
        if not self._handle_connection_frame(
            frame, stream_id, stream_state, deadline
        ):
            return False
        if frame.type == frames.HEADERS:
            fragment = frames.strip_padding(frame)
            resp["pending_end_stream"] = bool(frame.flags & frames.FLAG_END_STREAM)
            if frame.flags & frames.FLAG_END_HEADERS:
                resp["header_sets"].append(self._hpack_decoder.decode(fragment))
                return resp["pending_end_stream"]
            resp["header_fragments"] = [fragment]
            resp["header_bytes"] = len(fragment)
        elif frame.type == frames.DATA:
            data = frames.strip_padding(frame)
            resp["body_chunks"].append(data)
            resp["body_bytes"] += len(data)
            if resp["body_bytes"] > MAX_RESPONSE_BODY:
                raise TransportError(
                    "response body exceeds {}-byte limit".format(MAX_RESPONSE_BODY)
                )
            if frame.payload:
                # Replenish our receive windows for what we consumed.
                self._send_frame(
                    frames.window_update_frame(0, len(frame.payload)), deadline
                )
                if not frame.flags & frames.FLAG_END_STREAM:
                    self._send_frame(
                        frames.window_update_frame(stream_id, len(frame.payload)),
                        deadline,
                    )
            if frame.flags & frames.FLAG_END_STREAM:
                # Stream ended without trailers (not valid gRPC, but the caller
                # decides what to do with what it got).
                return True
        return False

    def request(self, headers, body, deadline):
        """Send one request and return ``(header_sets, body_bytes)``.

        ``header_sets`` is the list of decoded header blocks received on the
        stream, in order: initial response headers, then trailers — or a
        single trailers-only block.

        Sending the body and reading the response share one loop: a server that
        responds early (a trailers-only rejection while we are still uploading,
        blocked on flow control) is honored immediately rather than discarded.
        """
        stream_id = self._next_stream_id
        self._next_stream_id += 2
        stream_state = {"send_window": self._peer_initial_window}
        resp = {
            "header_sets": [],
            "body_chunks": [],
            "body_bytes": 0,
            "header_fragments": None,  # non-None while accumulating a block
            "header_bytes": 0,
            "pending_end_stream": False,
        }

        header_block = hpack_encode(headers)
        if stream_id == 1:
            # First header block on the connection: declare that our encoder
            # will not use the HPACK dynamic table (max size 0).
            header_block = encode_dynamic_table_size_update(0) + header_block
        self._send_headers(stream_id, header_block, deadline)

        offset = 0
        body_sent = False
        while True:
            if not body_sent:
                available = min(
                    self._peer_max_frame_size,
                    stream_state["send_window"],
                    self._send_window_connection,
                )
                if available > 0 or offset >= len(body):
                    chunk = body[offset : offset + available] if available > 0 else b""
                    offset += len(chunk)
                    body_sent = offset >= len(body)
                    self._send_frame(
                        frames.Frame(
                            frames.DATA,
                            frames.FLAG_END_STREAM if body_sent else 0,
                            stream_id,
                            chunk,
                        ),
                        deadline,
                    )
                    stream_state["send_window"] -= len(chunk)
                    self._send_window_connection -= len(chunk)
                    continue
                # Blocked on flow control: fall through and read a frame. It may
                # be a WINDOW_UPDATE that unblocks us, or an early response.

            frame = self._read_frame(deadline)
            try:
                complete = self._process_response_frame(
                    frame, stream_id, stream_state, resp, deadline
                )
            except ConnectionTerminated as error:
                # A stream id above the peer's last_stream_id was not processed,
                # so the request is safe to retry; at or below, it may have been.
                error.stream_processed = stream_id <= error.last_stream_id
                raise
            except (HpackError, ValueError, struct.error) as error:
                # Malformed frame from the peer: the connection can no longer be
                # trusted (HPACK state may be desynced). Surface it as a
                # transport failure so the caller closes and does not reuse it.
                raise TransportError(
                    "malformed frame from peer: {}".format(error)
                ) from error
            if complete:
                return resp["header_sets"], b"".join(resp["body_chunks"])
