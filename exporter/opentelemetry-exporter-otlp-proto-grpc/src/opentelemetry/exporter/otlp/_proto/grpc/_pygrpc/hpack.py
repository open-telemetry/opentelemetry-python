# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Minimal HPACK (RFC 7541) codec for the pure-Python gRPC transport.

The encoder emits only static-table references and literal header fields
without indexing (never-indexed for sensitive headers), and never applies
Huffman coding. That subset is spec-compliant and keeps the encoder trivial;
compression efficiency is irrelevant for the handful of headers a unary gRPC
call sends.

The decoder is complete: indexed fields, all literal forms, dynamic table
maintenance with eviction, dynamic table size updates, and Huffman-coded
string literals, because the peer chooses its own encodings.
"""

from ._huffman_table import HUFFMAN_CODES


class HpackError(Exception):
    """Raised on malformed HPACK input (RFC 7541 section 5.3 decoding error)."""


# RFC 7541 appendix A. Index 1 is STATIC_TABLE[0].
STATIC_TABLE = (
    (b":authority", b""),
    (b":method", b"GET"),
    (b":method", b"POST"),
    (b":path", b"/"),
    (b":path", b"/index.html"),
    (b":scheme", b"http"),
    (b":scheme", b"https"),
    (b":status", b"200"),
    (b":status", b"204"),
    (b":status", b"206"),
    (b":status", b"304"),
    (b":status", b"400"),
    (b":status", b"404"),
    (b":status", b"500"),
    (b"accept-charset", b""),
    (b"accept-encoding", b"gzip, deflate"),
    (b"accept-language", b""),
    (b"accept-ranges", b""),
    (b"accept", b""),
    (b"access-control-allow-origin", b""),
    (b"age", b""),
    (b"allow", b""),
    (b"authorization", b""),
    (b"cache-control", b""),
    (b"content-disposition", b""),
    (b"content-encoding", b""),
    (b"content-language", b""),
    (b"content-length", b""),
    (b"content-location", b""),
    (b"content-range", b""),
    (b"content-type", b""),
    (b"cookie", b""),
    (b"date", b""),
    (b"etag", b""),
    (b"expect", b""),
    (b"expires", b""),
    (b"from", b""),
    (b"host", b""),
    (b"if-match", b""),
    (b"if-modified-since", b""),
    (b"if-none-match", b""),
    (b"if-range", b""),
    (b"if-unmodified-since", b""),
    (b"last-modified", b""),
    (b"link", b""),
    (b"location", b""),
    (b"max-forwards", b""),
    (b"proxy-authenticate", b""),
    (b"proxy-authorization", b""),
    (b"range", b""),
    (b"referer", b""),
    (b"refresh", b""),
    (b"retry-after", b""),
    (b"server", b""),
    (b"set-cookie", b""),
    (b"strict-transport-security", b""),
    (b"transfer-encoding", b""),
    (b"user-agent", b""),
    (b"vary", b""),
    (b"via", b""),
    (b"www-authenticate", b""),
)

_STATIC_PAIR_INDEX = {pair: i + 1 for i, pair in enumerate(STATIC_TABLE)}
_STATIC_NAME_INDEX = {}
for _i, (_name, _value) in enumerate(STATIC_TABLE):
    _STATIC_NAME_INDEX.setdefault(_name, _i + 1)

# Headers whose values must never be compressed or indexed by intermediaries.
_NEVER_INDEXED_NAMES = frozenset((b"authorization", b"proxy-authorization"))


def _encode_integer(value, prefix_bits, first_byte_flags):
    """RFC 7541 section 5.1 integer representation."""
    max_prefix = (1 << prefix_bits) - 1
    if value < max_prefix:
        return bytes((first_byte_flags | value,))
    out = bytearray((first_byte_flags | max_prefix,))
    value -= max_prefix
    while value >= 0x80:
        out.append(0x80 | (value & 0x7F))
        value >>= 7
    out.append(value)
    return bytes(out)


def _encode_string(data):
    # H bit 0: raw octets, no Huffman.
    return _encode_integer(len(data), 7, 0x00) + data


def encode_dynamic_table_size_update(size):
    """Encode a dynamic table size update instruction (RFC 7541 section 6.3).

    This encoder never indexes into the dynamic table, so it declares a
    maximum size of 0 once at the start of a connection's first header block.
    Because 0 is unconditionally at or below any ``SETTINGS_HEADER_TABLE_SIZE``
    the peer advertises, no later settings change can require a further update,
    and strict decoders that expect an explicit size signal are satisfied.
    """
    return _encode_integer(size, 5, 0x20)


def encode(headers):
    """Encode ``[(name, value), ...]`` byte pairs into an HPACK header block.

    Names must already be lowercase; pseudo-headers must come first, as
    required by RFC 7540 section 8.1.2.1 — both are the caller's contract.
    """
    out = bytearray()
    for name, value in headers:
        pair_index = _STATIC_PAIR_INDEX.get((name, value))
        if pair_index is not None:
            out += _encode_integer(pair_index, 7, 0x80)
            continue
        name_index = _STATIC_NAME_INDEX.get(name, 0)
        if name in _NEVER_INDEXED_NAMES:
            out += _encode_integer(name_index, 4, 0x10)
        else:
            out += _encode_integer(name_index, 4, 0x00)
        if name_index == 0:
            out += _encode_string(name)
        out += _encode_string(value)
    return bytes(out)


class _HuffmanDecoder:
    """Bit-walking decoder over the RFC 7541 appendix B code table."""

    def __init__(self, codes):
        # Binary prefix tree: nodes are two-slot lists; leaves are symbols.
        self._root = [None, None]
        for symbol, (code, length) in enumerate(codes):
            node = self._root
            for bit_position in range(length - 1, -1, -1):
                bit = (code >> bit_position) & 1
                if bit_position == 0:
                    node[bit] = symbol
                else:
                    if node[bit] is None:
                        node[bit] = [None, None]
                    node = node[bit]

    def decode(self, data):
        out = bytearray()
        node = self._root
        bits_since_symbol = 0
        all_ones_since_symbol = True
        for byte in data:
            for bit_position in range(7, -1, -1):
                bit = (byte >> bit_position) & 1
                nxt = node[bit]
                if nxt is None:
                    raise HpackError("invalid Huffman code")
                if isinstance(nxt, int):
                    if nxt == 256:
                        # EOS must never appear in the payload proper.
                        raise HpackError("Huffman EOS symbol in payload")
                    out.append(nxt)
                    node = self._root
                    bits_since_symbol = 0
                    all_ones_since_symbol = True
                else:
                    node = nxt
                    bits_since_symbol += 1
                    all_ones_since_symbol = all_ones_since_symbol and bit == 1
        if node is not self._root:
            # Trailing bits must be a strict prefix of EOS: at most 7 bits,
            # all ones (RFC 7541 section 5.2).
            if bits_since_symbol > 7 or not all_ones_since_symbol:
                raise HpackError("invalid Huffman padding")
        return bytes(out)


_HUFFMAN = _HuffmanDecoder(HUFFMAN_CODES)


class Decoder:
    """Stateful HPACK decoder: one instance per HTTP/2 connection direction."""

    def __init__(self, max_dynamic_table_size=4096):
        self._entries = []  # newest first; index 62 is self._entries[0]
        self._size = 0
        self._max_size = max_dynamic_table_size
        # Protocol ceiling from SETTINGS_HEADER_TABLE_SIZE; size updates in
        # the header block must not exceed it.
        self._settings_max_size = max_dynamic_table_size

    def _evict(self):
        while self._size > self._max_size and self._entries:
            name, value = self._entries.pop()
            self._size -= len(name) + len(value) + 32

    def _add(self, name, value):
        self._entries.insert(0, (name, value))
        self._size += len(name) + len(value) + 32
        self._evict()

    def _lookup(self, index):
        if index == 0:
            raise HpackError("header field index 0")
        if index <= len(STATIC_TABLE):
            return STATIC_TABLE[index - 1]
        dynamic_index = index - len(STATIC_TABLE) - 1
        if dynamic_index >= len(self._entries):
            raise HpackError("header field index beyond table: {}".format(index))
        return self._entries[dynamic_index]

    def decode(self, block):
        """Decode one complete header block into ``[(name, value), ...]``."""
        headers = []
        pos = 0
        length = len(block)

        def read_integer(prefix_bits, first_byte):
            nonlocal pos
            max_prefix = (1 << prefix_bits) - 1
            value = first_byte & max_prefix
            if value < max_prefix:
                return value
            shift = 0
            while True:
                if pos >= length:
                    raise HpackError("truncated integer")
                byte = block[pos]
                pos += 1
                value += (byte & 0x7F) << shift
                shift += 7
                if shift > 62:
                    raise HpackError("integer overflow")
                if not byte & 0x80:
                    return value

        def read_string():
            nonlocal pos
            if pos >= length:
                raise HpackError("truncated string")
            first = block[pos]
            pos += 1
            huffman = bool(first & 0x80)
            str_length = read_integer(7, first)
            if pos + str_length > length:
                raise HpackError("truncated string payload")
            data = bytes(block[pos:pos + str_length])
            pos += str_length
            return _HUFFMAN.decode(data) if huffman else data

        while pos < length:
            first = block[pos]
            pos += 1
            if first & 0x80:
                # Indexed header field.
                headers.append(self._lookup(read_integer(7, first)))
            elif first & 0x40:
                # Literal with incremental indexing.
                name_index = read_integer(6, first)
                name = self._lookup(name_index)[0] if name_index else read_string()
                value = read_string()
                self._add(name, value)
                headers.append((name, value))
            elif first & 0x20:
                # Dynamic table size update.
                new_size = read_integer(5, first)
                if new_size > self._settings_max_size:
                    raise HpackError("dynamic table size update beyond SETTINGS limit")
                self._max_size = new_size
                self._evict()
            else:
                # Literal without indexing (0x00) or never indexed (0x10).
                name_index = read_integer(4, first)
                name = self._lookup(name_index)[0] if name_index else read_string()
                value = read_string()
                headers.append((name, value))
        return headers
