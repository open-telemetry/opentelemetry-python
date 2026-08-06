# tests/performance/test_benchmark_pygrpc.py
#
# Benchmark: the pure-Python gRPC transport (_pygrpc) send-side hot path.
#
# The distribution replaces grpcio's C-core HTTP/2 stack with a hand-rolled
# pure-Python one. Unlike protobuf encoding (amortized over a whole export
# batch), this cost is paid *per RPC*: every export HPACK-encodes the request
# headers and builds HTTP/2 HEADERS + DATA frames. HPACK (with Huffman) and
# frame construction are tight byte-loops — exactly where pure-Python is
# slowest — so this file measures that per-RPC overhead in absolute terms.
#
# grpcio does not expose HPACK/framing as callable units (it is buried in the C
# core), so there is no drop-in C baseline. Where a fair pure-Python reference
# exists — the MIT-licensed ``hpack`` package used by h2 — we benchmark against
# it to show our codec is competitive; that comparison is skipped when the
# package is absent. The absolute numbers stand on their own regardless.
#
# Run:
#   uv pip install . && uv pip install pytest-benchmark hpack
#   uv run pytest tests/performance/test_benchmark_pygrpc.py \
#       --benchmark-group-by=group,param --benchmark-sort=fullname

from pytest import mark, skip

from opentelemetry.exporter.otlp._proto.grpc._pygrpc import frames
from opentelemetry.exporter.otlp._proto.grpc._pygrpc.hpack import (
    Decoder,
    encode as hpack_encode,
)
from opentelemetry.exporter.otlp._proto.grpc._pygrpc.client import _frame_message

try:
    import hpack as ref_hpack
except ImportError:  # pragma: no cover
    ref_hpack = None


# Headers a unary OTLP/gRPC export sends (mirrors _pygrpc.client.unary_call).
_GRPC_REQUEST_HEADERS = [
    (b":method", b"POST"),
    (b":scheme", b"https"),
    (b":path", b"/opentelemetry.proto.collector.trace.v1.TraceService/Export"),
    (b":authority", b"ingress.example.com:4317"),
    (b"te", b"trailers"),
    (b"content-type", b"application/grpc"),
    (b"grpc-timeout", b"10S"),
    (b"grpc-encoding", b"identity"),
    (b"grpc-accept-encoding", b"identity, gzip"),
    (b"user-agent", b"otel-otlp-pyproto-exporter"),
    (b"authorization", b"Bearer sekrit-token"),
]

# OTLP export message-body sizes: a single small span, a typical batch, and a
# large batch. Content is irrelevant to framing cost, only length matters.
_MESSAGE_SIZES = [("small_200B", 200), ("batch_16KB", 16_384), ("large_256KB", 262_144)]
_STREAM_ID = 1


def _grpc_data_frame(message_bytes: bytes) -> bytes:
    """gRPC length-prefix a message and wrap it in an end-of-stream DATA frame."""
    framed = _frame_message(message_bytes, compress=False)
    return frames.encode_frame(
        frames.Frame(frames.DATA, frames.FLAG_END_STREAM, _STREAM_ID, framed)
    )


def _full_request_send(message_bytes: bytes) -> bytes:
    """The complete pure-Python send-side CPU cost of one unary export RPC:
    HPACK-encode headers, build the HEADERS frame, gRPC-frame the message, and
    build the DATA frame."""
    header_block = hpack_encode(_GRPC_REQUEST_HEADERS)
    headers_frame = frames.encode_frame(
        frames.Frame(
            frames.HEADERS, frames.FLAG_END_HEADERS, _STREAM_ID, header_block
        )
    )
    return headers_frame + _grpc_data_frame(message_bytes)


# ── Fairness / validity guards ──────────────────────────────────────────────

def test_hpack_roundtrips() -> None:
    block = hpack_encode(_GRPC_REQUEST_HEADERS)
    assert Decoder().decode(block) == _GRPC_REQUEST_HEADERS


@mark.skipif(ref_hpack is None, reason="reference hpack package not installed")
def test_hpack_output_decodes_under_reference() -> None:
    # Our block need not be byte-identical to the reference encoder's (indexing
    # strategies differ), but it must be valid HPACK the reference can read.
    decoded = ref_hpack.Decoder().decode(hpack_encode(_GRPC_REQUEST_HEADERS), raw=True)
    assert decoded == _GRPC_REQUEST_HEADERS


# ── HPACK header encoding: ours vs the reference pure-Python codec ──────────

@mark.benchmark(group="hpack_encode_headers")
def test_hpack_headers_pygrpc(benchmark) -> None:
    result = benchmark(lambda: hpack_encode(_GRPC_REQUEST_HEADERS))
    assert len(result) > 0


@mark.skipif(ref_hpack is None, reason="reference hpack package not installed")
@mark.benchmark(group="hpack_encode_headers")
def test_hpack_headers_reference(benchmark) -> None:
    # Fresh encoder per call to match our stateless module-level encode().
    result = benchmark(lambda: ref_hpack.Encoder().encode(_GRPC_REQUEST_HEADERS))
    assert len(result) > 0


# ── HTTP/2 DATA-frame construction, by message size ─────────────────────────

@mark.parametrize("label,size", _MESSAGE_SIZES, ids=[s[0] for s in _MESSAGE_SIZES])
@mark.benchmark(group="data_frame")
def test_data_frame_pygrpc(benchmark, label, size) -> None:
    message = b"\x7f" * size
    result = benchmark(lambda: _grpc_data_frame(message))
    assert len(result) > size


# ── Full per-RPC send-side (headers + framing), by message size ─────────────

@mark.parametrize("label,size", _MESSAGE_SIZES, ids=[s[0] for s in _MESSAGE_SIZES])
@mark.benchmark(group="full_request_send")
def test_full_request_send_pygrpc(benchmark, label, size) -> None:
    message = b"\x7f" * size
    result = benchmark(lambda: _full_request_send(message))
    assert len(result) > size
