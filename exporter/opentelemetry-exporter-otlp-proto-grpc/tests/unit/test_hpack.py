# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""HPACK codec tests.

Cross-checked against the reference MIT-licensed ``hpack`` package when it is
installed (it is a dev-only dependency of this suite); the RFC 7541 appendix C
stories run unconditionally.
"""

import pytest

from opentelemetry.exporter.otlp._proto.grpc._pygrpc.hpack import (
    Decoder,
    HpackError,
    encode,
    encode_dynamic_table_size_update,
)

try:
    import hpack as ref_hpack
except ImportError:  # pragma: no cover
    ref_hpack = None

requires_ref = pytest.mark.skipif(
    ref_hpack is None, reason="reference hpack package not installed"
)


GRPC_REQUEST_HEADERS = [
    (b":method", b"POST"),
    (b":scheme", b"https"),
    (b":path", b"/opentelemetry.proto.collector.trace.v1.TraceService/Export"),
    (b":authority", b"ingress.example.com:4317"),
    (b"te", b"trailers"),
    (b"content-type", b"application/grpc"),
    (b"grpc-timeout", b"10S"),
    (b"user-agent", b"otel-otlp-pyproto-exporter"),
    (b"authorization", b"Bearer sekrit token"),
]


# --- RFC 7541 appendix C stories (hand-transcribed request examples) -------


def test_rfc7541_c_2_1_literal_with_indexing():
    block = bytes.fromhex(
        "400a637573746f6d2d6b65790d637573746f6d2d686561646572"
    )
    decoder = Decoder()
    assert decoder.decode(block) == [(b"custom-key", b"custom-header")]
    # The entry must have been added to the dynamic table (index 62).
    assert decoder.decode(bytes((0x80 | 62,))) == [
        (b"custom-key", b"custom-header")
    ]


def test_rfc7541_c_2_2_literal_without_indexing():
    block = bytes.fromhex("040c2f73616d706c652f70617468")
    assert Decoder().decode(block) == [(b":path", b"/sample/path")]


def test_rfc7541_c_2_3_literal_never_indexed():
    block = bytes.fromhex("100870617373776f726406736563726574")
    assert Decoder().decode(block) == [(b"password", b"secret")]


def test_rfc7541_c_2_4_indexed_field():
    assert Decoder().decode(bytes((0x82,))) == [(b":method", b"GET")]


def test_rfc7541_c_3_request_examples_without_huffman():
    decoder = Decoder()
    first = bytes.fromhex("828684410f7777772e6578616d706c652e636f6d")
    assert decoder.decode(first) == [
        (b":method", b"GET"),
        (b":scheme", b"http"),
        (b":path", b"/"),
        (b":authority", b"www.example.com"),
    ]
    second = bytes.fromhex("828684be58086e6f2d6361636865")
    assert decoder.decode(second) == [
        (b":method", b"GET"),
        (b":scheme", b"http"),
        (b":path", b"/"),
        (b":authority", b"www.example.com"),
        (b"cache-control", b"no-cache"),
    ]
    third = bytes.fromhex(
        "828785bf400a637573746f6d2d6b65790c637573746f6d2d76616c7565"
    )
    assert decoder.decode(third) == [
        (b":method", b"GET"),
        (b":scheme", b"https"),
        (b":path", b"/index.html"),
        (b":authority", b"www.example.com"),
        (b"custom-key", b"custom-value"),
    ]


def test_rfc7541_c_4_request_examples_with_huffman():
    decoder = Decoder()
    first = bytes.fromhex("828684418cf1e3c2e5f23a6ba0ab90f4ff")
    assert decoder.decode(first) == [
        (b":method", b"GET"),
        (b":scheme", b"http"),
        (b":path", b"/"),
        (b":authority", b"www.example.com"),
    ]
    second = bytes.fromhex("828684be5886a8eb10649cbf")
    assert decoder.decode(second) == [
        (b":method", b"GET"),
        (b":scheme", b"http"),
        (b":path", b"/"),
        (b":authority", b"www.example.com"),
        (b"cache-control", b"no-cache"),
    ]
    third = bytes.fromhex(
        "828785bf408825a849e95ba97d7f8925a849e95bb8e8b4bf"
    )
    assert decoder.decode(third) == [
        (b":method", b"GET"),
        (b":scheme", b"https"),
        (b":path", b"/index.html"),
        (b":authority", b"www.example.com"),
        (b"custom-key", b"custom-value"),
    ]


# --- Error handling ---------------------------------------------------------


def test_dynamic_table_size_update_encoding():
    # 001 prefix (0x20) with a 5-bit integer; size 0 is a single 0x20 byte.
    assert encode_dynamic_table_size_update(0) == b"\x20"
    assert encode_dynamic_table_size_update(4096) == bytes.fromhex("3fe11f")


def test_decoder_accepts_leading_size_update_then_headers():
    block = encode_dynamic_table_size_update(0) + encode(
        [(b":method", b"POST"), (b"content-type", b"application/grpc")]
    )
    assert Decoder().decode(block) == [
        (b":method", b"POST"),
        (b"content-type", b"application/grpc"),
    ]


@requires_ref
def test_reference_decoder_accepts_our_leading_size_update():
    block = encode_dynamic_table_size_update(0) + encode(GRPC_REQUEST_HEADERS)
    decoded = ref_hpack.Decoder().decode(block, raw=True)
    assert [(bytes(n), bytes(v)) for n, v in decoded] == GRPC_REQUEST_HEADERS


def test_index_zero_is_an_error():
    with pytest.raises(HpackError):
        Decoder().decode(bytes((0x80,)))


def test_index_beyond_tables_is_an_error():
    with pytest.raises(HpackError):
        Decoder().decode(bytes((0x80 | 0x7F, 0x7F)))


def test_truncated_string_is_an_error():
    with pytest.raises(HpackError):
        Decoder().decode(bytes((0x00, 0x05, 0x61)))


def test_invalid_huffman_padding_is_an_error():
    # Literal without indexing, new name, Huffman-coded, padding of zeros.
    with pytest.raises(HpackError):
        Decoder().decode(bytes((0x00, 0x81, 0x00, 0x01, 0x61)))


# --- Round trips against the reference implementation -----------------------


@requires_ref
def test_our_encoder_against_reference_decoder():
    block = encode(GRPC_REQUEST_HEADERS)
    decoded = ref_hpack.Decoder().decode(block, raw=True)
    assert [(bytes(n), bytes(v)) for n, v in decoded] == GRPC_REQUEST_HEADERS


@requires_ref
@pytest.mark.parametrize("huffman", [False, True])
def test_reference_encoder_against_our_decoder(huffman):
    encoder = ref_hpack.Encoder()
    encoder.huffman = huffman
    decoder = Decoder()
    # Multiple blocks over one connection: exercises the dynamic table.
    for round_number in range(3):
        headers = [
            (b":status", b"200"),
            (b"content-type", b"application/grpc"),
            (b"grpc-status", b"0"),
            (b"grpc-message", b""),
            (b"x-round", str(round_number).encode()),
            (b"x-large", (b"v" * 300)),
        ]
        block = encoder.encode(headers, huffman=huffman)
        assert decoder.decode(block) == headers


@requires_ref
def test_dynamic_table_eviction_against_reference():
    encoder = ref_hpack.Encoder()
    encoder.header_table_size = 128  # emits a size-update instruction
    decoder = Decoder()
    for round_number in range(20):
        headers = [
            (
                "x-key-{}".format(round_number).encode(),
                ("value-{}".format(round_number) * 5).encode(),
            ),
        ]
        block = encoder.encode(headers, huffman=True)
        assert decoder.decode(block) == headers


@requires_ref
def test_huffman_all_byte_values_round_trip():
    payload = bytes(range(256))
    encoder = ref_hpack.Encoder()
    block = encoder.encode([(b"x-bin", payload)], huffman=True)
    assert Decoder().decode(block) == [(b"x-bin", payload)]
