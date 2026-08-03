# tests/_pyprotobuf/test_benchmark.py
#
# Benchmark: _pyprotobuf (pure-Python) vs google.protobuf (C extension)
# encoding speed.  Four benchmark categories:
#
#   Full message  — one round-trip of a Record containing every field type.
#   Per field     — each field helper in isolation against google.protobuf.
#   Scaling       — string, bytes, and packed-repeated at 3 payload sizes.
#   Varint        — encode_varint at 1-, 2-, 3-, and 5-byte bit widths.
#
# All proto schemas are built at import time via the descriptor / message-
# factory API — no .proto files or protoc step required.
#
# Run:
#   uv run pytest tests/_pyprotobuf/test_benchmark.py -v --benchmark-sort=mean

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory
from pytest import mark

from opentelemetry._proto._pyprotobuf import encode_varint
from opentelemetry._proto._pyprotobuf.fields import (
    bool_field,
    byt,
    dbl,
    fix32,
    fix64,
    msg,
    packed_double,
    packed_uint64,
    sint32,
    string,
    u64,
)

_T = descriptor_pb2.FieldDescriptorProto


# ── Proto builders ─────────────────────────────────────────────────────────────

def _build_full_record_classes():
    """Record message with one field of every type (full-message benchmark)."""
    fp = descriptor_pb2.FileDescriptorProto()
    fp.name = "pyproto_benchmark.proto"
    fp.syntax = "proto3"

    inner = fp.message_type.add()
    inner.name = "Inner"
    for name, number, tid in (("label", 1, _T.TYPE_STRING), ("seq", 2, _T.TYPE_UINT64)):
        f = inner.field.add()
        f.name = name; f.number = number; f.type = tid; f.label = _T.LABEL_OPTIONAL

    rec = fp.message_type.add()
    rec.name = "Record"
    for name, number, tid, lbl in (
        ("name",          1,  _T.TYPE_STRING,  _T.LABEL_OPTIONAL),
        ("count",         2,  _T.TYPE_UINT64,  _T.LABEL_OPTIONAL),
        ("value",         3,  _T.TYPE_DOUBLE,  _T.LABEL_OPTIONAL),
        ("active",        4,  _T.TYPE_BOOL,    _T.LABEL_OPTIONAL),
        ("data",          5,  _T.TYPE_BYTES,   _T.LABEL_OPTIONAL),
        ("timestamp_ns",  6,  _T.TYPE_FIXED64, _T.LABEL_OPTIONAL),
        ("flags",         7,  _T.TYPE_FIXED32, _T.LABEL_OPTIONAL),
        ("bucket_counts", 9,  _T.TYPE_UINT64,  _T.LABEL_REPEATED),
        ("bounds",        10, _T.TYPE_DOUBLE,  _T.LABEL_REPEATED),
    ):
        f = rec.field.add()
        f.name = name; f.number = number; f.type = tid; f.label = lbl

    mf = rec.field.add()
    mf.name = "inner"; mf.number = 8; mf.type = _T.TYPE_MESSAGE
    mf.label = _T.LABEL_OPTIONAL; mf.type_name = "Inner"

    pool = descriptor_pool.DescriptorPool()
    pool.Add(fp)
    return (
        message_factory.GetMessageClass(pool.FindMessageTypeByName("Inner")),
        message_factory.GetMessageClass(pool.FindMessageTypeByName("Record")),
    )


def _build_field_msg_classes():
    """FieldMsg with one field per type — per-field and scaling benchmarks."""
    fp = descriptor_pb2.FileDescriptorProto()
    fp.name = "pyproto_field_benchmark.proto"
    fp.syntax = "proto3"

    fi = fp.message_type.add()
    fi.name = "FieldInner"
    f = fi.field.add()
    f.name = "v"; f.number = 1; f.type = _T.TYPE_UINT64; f.label = _T.LABEL_OPTIONAL

    fm = fp.message_type.add()
    fm.name = "FieldMsg"
    for name, number, tid, lbl in (
        ("f_uint64",     1,  _T.TYPE_UINT64,  _T.LABEL_OPTIONAL),
        ("f_string",     2,  _T.TYPE_STRING,  _T.LABEL_OPTIONAL),
        ("f_bytes",      3,  _T.TYPE_BYTES,   _T.LABEL_OPTIONAL),
        ("f_double",     4,  _T.TYPE_DOUBLE,  _T.LABEL_OPTIONAL),
        ("f_bool",       5,  _T.TYPE_BOOL,    _T.LABEL_OPTIONAL),
        ("f_fixed64",    6,  _T.TYPE_FIXED64, _T.LABEL_OPTIONAL),
        ("f_fixed32",    7,  _T.TYPE_FIXED32, _T.LABEL_OPTIONAL),
        ("f_sint32",     8,  _T.TYPE_SINT32,  _T.LABEL_OPTIONAL),
        ("f_packed_u64", 9,  _T.TYPE_UINT64,  _T.LABEL_REPEATED),
        ("f_packed_dbl", 10, _T.TYPE_DOUBLE,  _T.LABEL_REPEATED),
    ):
        f = fm.field.add()
        f.name = name; f.number = number; f.type = tid; f.label = lbl

    mf = fm.field.add()
    mf.name = "f_msg"; mf.number = 11; mf.type = _T.TYPE_MESSAGE
    mf.label = _T.LABEL_OPTIONAL; mf.type_name = "FieldInner"

    pool = descriptor_pool.DescriptorPool()
    pool.Add(fp)
    return (
        message_factory.GetMessageClass(pool.FindMessageTypeByName("FieldInner")),
        message_factory.GetMessageClass(pool.FindMessageTypeByName("FieldMsg")),
    )


def _build_repeated_msg_classes():
    """Item + Container — repeated embedded message benchmark."""
    fp = descriptor_pb2.FileDescriptorProto()
    fp.name = "pyproto_repeated_benchmark.proto"
    fp.syntax = "proto3"

    item = fp.message_type.add()
    item.name = "Item"
    for name, number, tid in (
        ("label", 1, _T.TYPE_STRING),
        ("count", 2, _T.TYPE_UINT64),
        ("value", 3, _T.TYPE_DOUBLE),
    ):
        f = item.field.add()
        f.name = name; f.number = number; f.type = tid; f.label = _T.LABEL_OPTIONAL

    container = fp.message_type.add()
    container.name = "Container"
    rf = container.field.add()
    rf.name = "items"; rf.number = 1; rf.type = _T.TYPE_MESSAGE
    rf.label = _T.LABEL_REPEATED; rf.type_name = "Item"

    pool = descriptor_pool.DescriptorPool()
    pool.Add(fp)
    return (
        message_factory.GetMessageClass(pool.FindMessageTypeByName("Item")),
        message_factory.GetMessageClass(pool.FindMessageTypeByName("Container")),
    )


_Inner,     _Record    = _build_full_record_classes()
_FieldInner, _FieldMsg  = _build_field_msg_classes()
_Item,       _Container = _build_repeated_msg_classes()


# ── Shared benchmark data ──────────────────────────────────────────────────────

_NAME          = "benchmark.record.example"
_COUNT         = 9_876_543_210
_VALUE         = 3.141592653589793
_DATA          = b"\xde\xad\xbe\xef" * 8
_TS            = 1_782_401_900_556_236_527
_FLAGS         = 0xDEAD
_INNER_LABEL   = "inner.label"
_INNER_SEQ     = 42
_BUCKET_COUNTS = [0, 1, 4, 12, 35, 78, 120, 89, 42, 15, 4, 1, 0]
_BOUNDS        = [0.0, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]

_FIELD_INNER_BYTES = _FieldInner(v=42).SerializeToString()

# Item data for repeated-message benchmarks: (label, count, value) tuples.
# All values are non-default so every field is serialized.
_REPEATED_SIZES = [1, 5, 20]
_ITEM_DATA = [
    (f"item.label.{i}", (i + 1) * 100, (i + 1) * 0.5)
    for i in range(max(_REPEATED_SIZES))
]

# Pre-built google.protobuf objects — construction cost excluded from
# serialization-only benchmarks in section 7.
_PRE_BUILT_RECORD = _Record(
    name=_NAME, count=_COUNT, value=_VALUE, active=True,
    data=_DATA, timestamp_ns=_TS, flags=_FLAGS,
    inner=_Inner(label=_INNER_LABEL, seq=_INNER_SEQ),
    bucket_counts=_BUCKET_COUNTS, bounds=_BOUNDS,
)

_PRE_BUILT_FIELD_PB = {
    "uint64":        _FieldMsg(f_uint64=_COUNT),
    "string":        _FieldMsg(f_string=_NAME),
    "bytes":         _FieldMsg(f_bytes=_DATA),
    "double":        _FieldMsg(f_double=_VALUE),
    "bool":          _FieldMsg(f_bool=True),
    "fixed64":       _FieldMsg(f_fixed64=_TS),
    "fixed32":       _FieldMsg(f_fixed32=_FLAGS),
    "sint32":        _FieldMsg(f_sint32=-12345),
    "packed_uint64": _FieldMsg(f_packed_u64=_BUCKET_COUNTS),
    "packed_double": _FieldMsg(f_packed_dbl=_BOUNDS),
    "msg":           _FieldMsg(f_msg=_FieldInner(v=42)),
}


# ══════════════════════════════════════════════════════════════════════════════
# 1. Full-message benchmark
# ══════════════════════════════════════════════════════════════════════════════

def _pyproto_encode() -> bytes:
    inner = string(1, _INNER_LABEL) + u64(2, _INNER_SEQ)
    return (
        string(1, _NAME)
        + u64(2, _COUNT)
        + dbl(3, _VALUE)
        + bool_field(4, True)
        + byt(5, _DATA)
        + fix64(6, _TS)
        + fix32(7, _FLAGS)
        + msg(8, inner)
        + packed_uint64(9, _BUCKET_COUNTS)
        + packed_double(10, _BOUNDS)
    )


def _pb_encode() -> bytes:
    return _Record(
        name=_NAME,
        count=_COUNT,
        value=_VALUE,
        active=True,
        data=_DATA,
        timestamp_ns=_TS,
        flags=_FLAGS,
        inner=_Inner(label=_INNER_LABEL, seq=_INNER_SEQ),
        bucket_counts=_BUCKET_COUNTS,
        bounds=_BOUNDS,
    ).SerializeToString()


def test_encode_outputs_identical() -> None:
    assert _pyproto_encode() == _pb_encode()


def test_encode_pyproto(benchmark) -> None:
    result = benchmark(_pyproto_encode)
    assert len(result) > 0


def test_encode_protobuf(benchmark) -> None:
    result = benchmark(_pb_encode)
    assert len(result) > 0


# ══════════════════════════════════════════════════════════════════════════════
# 2. Per-field-type benchmarks
#
# Each pyproto field helper is benchmarked against google.protobuf encoding
# the same single field.  Both sides include message-construction overhead
# where applicable (there is no separate "build" vs "serialize" step in the
# pyproto API — it is a pure function call).
# ══════════════════════════════════════════════════════════════════════════════

_PER_FIELD = [
    ("uint64",       lambda: u64(1, _COUNT),
                     lambda: _FieldMsg(f_uint64=_COUNT).SerializeToString()),
    ("string",       lambda: string(2, _NAME),
                     lambda: _FieldMsg(f_string=_NAME).SerializeToString()),
    ("bytes",        lambda: byt(3, _DATA),
                     lambda: _FieldMsg(f_bytes=_DATA).SerializeToString()),
    ("double",       lambda: dbl(4, _VALUE),
                     lambda: _FieldMsg(f_double=_VALUE).SerializeToString()),
    ("bool",         lambda: bool_field(5, True),
                     lambda: _FieldMsg(f_bool=True).SerializeToString()),
    ("fixed64",      lambda: fix64(6, _TS),
                     lambda: _FieldMsg(f_fixed64=_TS).SerializeToString()),
    ("fixed32",      lambda: fix32(7, _FLAGS),
                     lambda: _FieldMsg(f_fixed32=_FLAGS).SerializeToString()),
    ("sint32",       lambda: sint32(8, -12345),
                     lambda: _FieldMsg(f_sint32=-12345).SerializeToString()),
    ("packed_uint64",lambda: packed_uint64(9, _BUCKET_COUNTS),
                     lambda: _FieldMsg(f_packed_u64=_BUCKET_COUNTS).SerializeToString()),
    ("packed_double",lambda: packed_double(10, _BOUNDS),
                     lambda: _FieldMsg(f_packed_dbl=_BOUNDS).SerializeToString()),
    ("msg",          lambda: msg(11, _FIELD_INNER_BYTES),
                     lambda: _FieldMsg(f_msg=_FieldInner(v=42)).SerializeToString()),
]

_FIELD_IDS = [name for name, _, _ in _PER_FIELD]


@mark.parametrize("name,pyproto_fn,pb_fn", _PER_FIELD, ids=_FIELD_IDS)
def test_field_outputs_identical(name, pyproto_fn, pb_fn) -> None:
    assert pyproto_fn() == pb_fn(), f"encoding mismatch for field type: {name}"


@mark.parametrize("fn", [p for _, p, _ in _PER_FIELD], ids=_FIELD_IDS)
def test_field_pyproto(benchmark, fn) -> None:
    result = benchmark(fn)
    assert len(result) > 0


@mark.parametrize("fn", [pb for _, _, pb in _PER_FIELD], ids=_FIELD_IDS)
def test_field_protobuf(benchmark, fn) -> None:
    result = benchmark(fn)
    assert len(result) > 0


# ══════════════════════════════════════════════════════════════════════════════
# 3. Scaling benchmarks
#
# How encoding time grows with payload size for the three field types whose
# cost is proportional to data length: string, bytes, and packed repeated.
# Data is pre-built outside the benchmark loop; only the encoding is timed.
# ══════════════════════════════════════════════════════════════════════════════

_STR_SIZES    = [4, 256, 16_384]
_BYTES_SIZES  = [4, 256, 16_384]
_PACKED_SIZES = [10, 100, 1_000]


@mark.parametrize("n", _STR_SIZES, ids=["4B", "256B", "16KB"])
def test_scale_string_pyproto(benchmark, n) -> None:
    s = "x" * n
    result = benchmark(lambda: string(2, s))
    assert len(result) > 0


@mark.parametrize("n", _STR_SIZES, ids=["4B", "256B", "16KB"])
def test_scale_string_protobuf(benchmark, n) -> None:
    s = "x" * n
    result = benchmark(lambda: _FieldMsg(f_string=s).SerializeToString())
    assert len(result) > 0


@mark.parametrize("n", _BYTES_SIZES, ids=["4B", "256B", "16KB"])
def test_scale_bytes_pyproto(benchmark, n) -> None:
    data = b"x" * n
    result = benchmark(lambda: byt(3, data))
    assert len(result) > 0


@mark.parametrize("n", _BYTES_SIZES, ids=["4B", "256B", "16KB"])
def test_scale_bytes_protobuf(benchmark, n) -> None:
    data = b"x" * n
    result = benchmark(lambda: _FieldMsg(f_bytes=data).SerializeToString())
    assert len(result) > 0


@mark.parametrize("n", _PACKED_SIZES, ids=["10", "100", "1000"])
def test_scale_packed_uint64_pyproto(benchmark, n) -> None:
    values = list(range(n))
    result = benchmark(lambda: packed_uint64(9, values))
    assert len(result) > 0


@mark.parametrize("n", _PACKED_SIZES, ids=["10", "100", "1000"])
def test_scale_packed_uint64_protobuf(benchmark, n) -> None:
    values = list(range(n))
    result = benchmark(lambda: _FieldMsg(f_packed_u64=values).SerializeToString())
    assert len(result) > 0


@mark.parametrize("n", _PACKED_SIZES, ids=["10", "100", "1000"])
def test_scale_packed_double_pyproto(benchmark, n) -> None:
    values = [float(i) * 0.1 for i in range(n)]
    result = benchmark(lambda: packed_double(10, values))
    assert len(result) > 0


@mark.parametrize("n", _PACKED_SIZES, ids=["10", "100", "1000"])
def test_scale_packed_double_protobuf(benchmark, n) -> None:
    values = [float(i) * 0.1 for i in range(n)]
    result = benchmark(lambda: _FieldMsg(f_packed_dbl=values).SerializeToString())
    assert len(result) > 0


# ══════════════════════════════════════════════════════════════════════════════
# 4. Varint bit-width benchmarks
#
# encode_varint is the hottest path in _pyprotobuf: every tag and every
# varint-type field value goes through it.  These benchmarks measure how
# encoding time scales with the number of continuation bytes (bit width).
#
# The google.protobuf column encodes the same integer as a uint64 field
# (including message-object construction and tag overhead), which is the
# closest available comparison point since protobuf does not expose a
# standalone varint encoder.  Use the pyproto column to track raw varint
# speed; use the ratio to see the combined tag+field overhead gap.
# ══════════════════════════════════════════════════════════════════════════════

_VARINT_CASES = [
    ("1byte",  63),          # fits in 1 byte  (0x00–0x7f)
    ("2byte",  300),         # requires 2 bytes (0x80–0x3fff)
    ("3byte",  100_000),     # requires 3 bytes (0x4000–0x1fffff)
    ("5byte",  2**32 - 1),   # requires 5 bytes (max uint32)
]

_VARINT_IDS    = [c[0] for c in _VARINT_CASES]
_VARINT_VALUES = [c[1] for c in _VARINT_CASES]


@mark.parametrize("v", _VARINT_VALUES, ids=_VARINT_IDS)
def test_varint_pyproto(benchmark, v) -> None:
    result = benchmark(lambda: encode_varint(v))
    assert len(result) > 0


@mark.parametrize("v", _VARINT_VALUES, ids=_VARINT_IDS)
def test_varint_protobuf(benchmark, v) -> None:
    result = benchmark(lambda: _FieldMsg(f_uint64=v).SerializeToString())
    assert len(result) > 0


# ══════════════════════════════════════════════════════════════════════════════
# 5. Concatenation strategy: `+` vs `b"".join()`
#
# The current SerializeToString() pattern chains field results with `+`,
# creating N-1 intermediate bytes objects (one per addition).  b"".join()
# allocates the final buffer once and copies each part exactly once.
# These two tests use the same field data so the only variable is the
# concatenation strategy.
# ══════════════════════════════════════════════════════════════════════════════

def _pyproto_encode_join() -> bytes:
    inner = b"".join([string(1, _INNER_LABEL), u64(2, _INNER_SEQ)])
    return b"".join([
        string(1, _NAME),
        u64(2, _COUNT),
        dbl(3, _VALUE),
        bool_field(4, True),
        byt(5, _DATA),
        fix64(6, _TS),
        fix32(7, _FLAGS),
        msg(8, inner),
        packed_uint64(9, _BUCKET_COUNTS),
        packed_double(10, _BOUNDS),
    ])


def test_concat_strategy_outputs_identical() -> None:
    assert _pyproto_encode() == _pyproto_encode_join()


def test_encode_concat_pyproto(benchmark) -> None:
    result = benchmark(_pyproto_encode)
    assert len(result) > 0


def test_encode_join_pyproto(benchmark) -> None:
    result = benchmark(_pyproto_encode_join)
    assert len(result) > 0


# ══════════════════════════════════════════════════════════════════════════════
# 6. All-default fields (fast path)
#
# Proto3 omits fields whose value equals the type default (0, "", b"", False,
# 0.0, []).  Each _pyprotobuf helper returns b"" immediately for defaults.
# This benchmark measures the minimum cost of SerializeToString() — calling
# every helper in a message when none produce any output.
# ══════════════════════════════════════════════════════════════════════════════

def _pyproto_encode_all_defaults() -> bytes:
    # Embedded message field omitted: real SerializeToString() guards with
    # `if self.field is not None`.  Every helper here returns b"".
    return (
        string(1, "")
        + u64(2, 0)
        + dbl(3, 0.0)
        + bool_field(4, False)
        + byt(5, b"")
        + fix64(6, 0)
        + fix32(7, 0)
        + packed_uint64(9, [])
        + packed_double(10, [])
    )


def test_all_defaults_pyproto(benchmark) -> None:
    result = benchmark(_pyproto_encode_all_defaults)
    assert result == b""


def test_all_defaults_protobuf(benchmark) -> None:
    result = benchmark(lambda: _Record().SerializeToString())
    assert result == b""


# ══════════════════════════════════════════════════════════════════════════════
# 7. google.protobuf: construction vs serialization split
#
# Previous benchmarks bundle message-object construction and serialization
# together for google.protobuf.  pyproto has no construction phase — it is a
# pure function call.  Separating the two phases shows where google.protobuf's
# time actually goes and gives a fairer encoding-only comparison.
#
# Read these alongside the existing test_encode_pyproto / test_encode_protobuf:
#   test_encode_pyproto              — pyproto: pure call, no object
#   test_encode_protobuf_construct   — google.protobuf: construction only
#   test_encode_protobuf_serialize   — google.protobuf: serialization only
#   test_encode_protobuf             — google.protobuf: construction + serialization
# ══════════════════════════════════════════════════════════════════════════════

def _pb_construct():
    return _Record(
        name=_NAME, count=_COUNT, value=_VALUE, active=True,
        data=_DATA, timestamp_ns=_TS, flags=_FLAGS,
        inner=_Inner(label=_INNER_LABEL, seq=_INNER_SEQ),
        bucket_counts=_BUCKET_COUNTS, bounds=_BOUNDS,
    )


def test_encode_protobuf_construct(benchmark) -> None:
    result = benchmark(_pb_construct)
    assert result is not None


def test_encode_protobuf_serialize(benchmark) -> None:
    result = benchmark(_PRE_BUILT_RECORD.SerializeToString)
    assert len(result) > 0


@mark.parametrize("name", list(_PRE_BUILT_FIELD_PB), ids=list(_PRE_BUILT_FIELD_PB))
def test_field_serialize_only_protobuf(benchmark, name) -> None:
    result = benchmark(_PRE_BUILT_FIELD_PB[name].SerializeToString)
    assert len(result) > 0


# ══════════════════════════════════════════════════════════════════════════════
# 8. Repeated embedded messages
#
# Encodes a Container with N Item sub-messages.  Each Item has a string,
# uint64, and double field.  Unlike packed repeated scalars, repeated messages
# require one SerializeToString-equivalent call per element plus one msg()
# wrapper per element — this tests whether per-element overhead compounds
# or stays flat.
#
# pyproto side:  b"".join(msg(1, string(1,l)+u64(2,c)+dbl(3,v)) for ...)
# protobuf side: _Container(items=[_Item(...), ...]).SerializeToString()
# ══════════════════════════════════════════════════════════════════════════════

def _pyproto_encode_repeated(n: int) -> bytes:
    return b"".join(
        msg(1, string(1, label) + u64(2, count) + dbl(3, value))
        for label, count, value in _ITEM_DATA[:n]
    )


def _pb_encode_repeated(n: int) -> bytes:
    return _Container(
        items=[
            _Item(label=label, count=count, value=value)
            for label, count, value in _ITEM_DATA[:n]
        ]
    ).SerializeToString()


@mark.parametrize("n", _REPEATED_SIZES, ids=["1", "5", "20"])
def test_repeated_msg_outputs_identical(n) -> None:
    assert _pyproto_encode_repeated(n) == _pb_encode_repeated(n)


@mark.parametrize("n", _REPEATED_SIZES, ids=["1", "5", "20"])
def test_repeated_msg_pyproto(benchmark, n) -> None:
    result = benchmark(lambda: _pyproto_encode_repeated(n))
    assert len(result) > 0


@mark.parametrize("n", _REPEATED_SIZES, ids=["1", "5", "20"])
def test_repeated_msg_protobuf(benchmark, n) -> None:
    result = benchmark(lambda: _pb_encode_repeated(n))
    assert len(result) > 0
