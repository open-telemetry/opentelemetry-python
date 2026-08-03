# tests/performance/test_benchmark_otlp.py
#
# Benchmark: pure-Python pyproto (opentelemetry._proto) vs the real
# google.protobuf implementation (opentelemetry.proto, upb/C backend) on
# *realistic, full OTLP export payloads* — the actual workload the exporters
# put through these message classes.
#
# test_benchmark.py measures the _pyprotobuf primitives (varint, single
# fields, scaling) against synthetic google.protobuf messages built from
# throw-away descriptors. This file instead exercises the real OTLP message
# trees — ExportTraceServiceRequest / ExportLogsServiceRequest /
# ExportMetricsServiceRequest, nested Resource → Scope → Span/LogRecord/Metric
# with attributes, events, links, status and data points — at several batch
# sizes, so the pyproto-vs-protobuf gap can be read off for payloads that look
# like what a real collector export sends.
#
# Both implementations expose an identical constructor + SerializeToString()
# API (the equivalence suite proves the bytes match), so a single builder,
# parameterized by a bundle of classes, drives both sides.
#
#   BUILD + SERIALIZE benchmarks  — one full encode of a logical payload from
#                                   source data, i.e. the per-export cost an
#                                   exporter actually pays.
#   SERIALIZE-ONLY benchmarks     — SerializeToString() on a pre-built message,
#                                   isolating raw encoding from construction.
#
# The real (google.protobuf) classes are only available when the upstream
# ``opentelemetry-proto`` package owns the public ``opentelemetry.proto`` path
# (installed *after* this package so it wins the namespace). When it does not,
# ``opentelemetry.proto`` resolves to this package's pure-Python shim and the
# comparison would be pyproto-vs-pyproto — so the whole module skips, exactly
# like the equivalence suite's conftest guard.
#
# Run (install order matters — real protobuf must win opentelemetry.proto):
#   uv pip install . && uv pip install protobuf opentelemetry-proto pytest-benchmark
#   uv run pytest tests/performance/test_benchmark_otlp.py \
#       --benchmark-sort=fullname --benchmark-group-by=group

from types import SimpleNamespace

from pytest import mark, skip

from opentelemetry._proto.collector.logs.v1 import logs_service_pb2 as _py_coll_logs
from opentelemetry._proto.collector.metrics.v1 import (
    metrics_service_pb2 as _py_coll_metrics,
)
from opentelemetry._proto.collector.trace.v1 import (
    trace_service_pb2 as _py_coll_trace,
)
from opentelemetry._proto.common.v1 import common_pb2 as _py_common
from opentelemetry._proto.logs.v1 import logs_pb2 as _py_logs
from opentelemetry._proto.metrics.v1 import metrics_pb2 as _py_metrics
from opentelemetry._proto.resource.v1 import resource_pb2 as _py_resource
from opentelemetry._proto.trace.v1 import trace_pb2 as _py_trace

# Public path: the real opentelemetry-proto when installed, else this package's
# pure-Python shim. Guard that it is the real package before benchmarking.
from opentelemetry.proto.common.v1 import common_pb2 as _pb_common

if "pyproto" in (_pb_common.__file__ or ""):
    skip(
        "opentelemetry.proto resolves to the pyproto shim "
        f"({_pb_common.__file__}); install the real opentelemetry-proto "
        "package (after this one, so it owns opentelemetry.proto) to compare "
        "pure-Python pyproto against the real google.protobuf implementation.",
        allow_module_level=True,
    )

from opentelemetry.proto.collector.logs.v1 import logs_service_pb2 as _pb_coll_logs
from opentelemetry.proto.collector.metrics.v1 import (
    metrics_service_pb2 as _pb_coll_metrics,
)
from opentelemetry.proto.collector.trace.v1 import (
    trace_service_pb2 as _pb_coll_trace,
)
from opentelemetry.proto.logs.v1 import logs_pb2 as _pb_logs
from opentelemetry.proto.metrics.v1 import metrics_pb2 as _pb_metrics
from opentelemetry.proto.resource.v1 import resource_pb2 as _pb_resource
from opentelemetry.proto.trace.v1 import trace_pb2 as _pb_trace


# ── Class bundles ───────────────────────────────────────────────────────────
#
# Both implementations share the same class names and constructor kwargs, so a
# builder written against one bundle works verbatim against the other.

def _bundle(common, resource, trace, logs, metrics, coll_trace, coll_logs, coll_metrics):
    return SimpleNamespace(
        AnyValue=common.AnyValue,
        KeyValue=common.KeyValue,
        InstrumentationScope=common.InstrumentationScope,
        Resource=resource.Resource,
        Span=trace.Span,
        Status=trace.Status,
        ScopeSpans=trace.ScopeSpans,
        ResourceSpans=trace.ResourceSpans,
        LogRecord=logs.LogRecord,
        ScopeLogs=logs.ScopeLogs,
        ResourceLogs=logs.ResourceLogs,
        NumberDataPoint=metrics.NumberDataPoint,
        Sum=metrics.Sum,
        HistogramDataPoint=metrics.HistogramDataPoint,
        Histogram=metrics.Histogram,
        Metric=metrics.Metric,
        ScopeMetrics=metrics.ScopeMetrics,
        ResourceMetrics=metrics.ResourceMetrics,
        ExportTraceServiceRequest=coll_trace.ExportTraceServiceRequest,
        ExportLogsServiceRequest=coll_logs.ExportLogsServiceRequest,
        ExportMetricsServiceRequest=coll_metrics.ExportMetricsServiceRequest,
    )


PY = _bundle(
    _py_common, _py_resource, _py_trace, _py_logs, _py_metrics,
    _py_coll_trace, _py_coll_logs, _py_coll_metrics,
)
PB = _bundle(
    _pb_common, _pb_resource, _pb_trace, _pb_logs, _pb_metrics,
    _pb_coll_trace, _pb_coll_logs, _pb_coll_metrics,
)


# ── Deterministic source data ───────────────────────────────────────────────
#
# No randomness (scripts/tests must be reproducible); ids and values are
# derived from the element index so every payload is stable across runs.

_SCHEMA_URL = "https://opentelemetry.io/schemas/1.30.0"


def _trace_id(i: int) -> bytes:
    return bytes(((i + b) % 256) for b in range(16))


def _span_id(i: int) -> bytes:
    return bytes(((i * 7 + b) % 256) for b in range(8))


def _resource(M):
    """A resource with the attribute set a real service emits."""
    return M.Resource(
        attributes=[
            M.KeyValue(key="service.name", value=M.AnyValue(string_value="checkout-service")),
            M.KeyValue(key="service.version", value=M.AnyValue(string_value="1.24.0")),
            M.KeyValue(key="service.instance.id", value=M.AnyValue(string_value="pod-7f9c-abc123")),
            M.KeyValue(key="process.pid", value=M.AnyValue(int_value=42317)),
            M.KeyValue(key="host.name", value=M.AnyValue(string_value="ip-10-0-12-34")),
            M.KeyValue(key="telemetry.sdk.language", value=M.AnyValue(string_value="python")),
            M.KeyValue(key="telemetry.sdk.version", value=M.AnyValue(string_value="1.30.0")),
        ]
    )


def _span_attributes(M, i: int):
    return [
        M.KeyValue(key="http.request.method", value=M.AnyValue(string_value="GET")),
        M.KeyValue(key="url.path", value=M.AnyValue(string_value=f"/api/orders/{i}")),
        M.KeyValue(key="http.response.status_code", value=M.AnyValue(int_value=200)),
        M.KeyValue(key="server.address", value=M.AnyValue(string_value="orders.internal")),
        M.KeyValue(key="network.protocol.version", value=M.AnyValue(string_value="1.1")),
        M.KeyValue(key="db.system", value=M.AnyValue(string_value="postgresql")),
    ]


def _span(M, i: int):
    base = 1_700_000_000_000_000_000 + i * 1_000_000
    return M.Span(
        trace_id=_trace_id(i),
        span_id=_span_id(i),
        parent_span_id=_span_id(i + 1),
        name="GET /api/orders/{id}",
        kind=2,  # SPAN_KIND_SERVER
        start_time_unix_nano=base,
        end_time_unix_nano=base + 4_200_000,
        attributes=_span_attributes(M, i),
        events=[
            M.Span.Event(
                time_unix_nano=base + 1_000_000,
                name="cache.miss",
                attributes=[
                    M.KeyValue(key="cache.key", value=M.AnyValue(string_value=f"order:{i}")),
                ],
            ),
            M.Span.Event(
                time_unix_nano=base + 2_500_000,
                name="db.query",
                attributes=[
                    M.KeyValue(key="db.rows", value=M.AnyValue(int_value=17)),
                ],
            ),
        ],
        links=[
            M.Span.Link(
                trace_id=_trace_id(i + 100),
                span_id=_span_id(i + 100),
                trace_state="vendor=abc",
            ),
        ],
        status=M.Status(code=1, message=""),  # STATUS_CODE_OK
        flags=1,
    )


def _log_record(M, i: int):
    base = 1_700_000_000_000_000_000 + i * 1_000_000
    return M.LogRecord(
        time_unix_nano=base,
        observed_time_unix_nano=base + 1_000,
        severity_number=9,  # INFO
        severity_text="INFO",
        body=M.AnyValue(string_value=f"request {i} completed in 4.2ms with status 200"),
        attributes=[
            M.KeyValue(key="log.source", value=M.AnyValue(string_value="access")),
            M.KeyValue(key="http.route", value=M.AnyValue(string_value="/api/orders/{id}")),
            M.KeyValue(key="http.response.status_code", value=M.AnyValue(int_value=200)),
            M.KeyValue(key="thread.id", value=M.AnyValue(int_value=140_234_567)),
        ],
        trace_id=_trace_id(i),
        span_id=_span_id(i),
        flags=1,
    )


def _metric(M, i: int, n_dp: int):
    base = 1_700_000_000_000_000_000 + i * 1_000_000
    return M.Metric(
        name=f"http.server.request.duration.{i}",
        description="Duration of HTTP server requests.",
        unit="s",
        histogram=M.Histogram(
            aggregation_temporality=2,  # CUMULATIVE
            data_points=[
                M.HistogramDataPoint(
                    attributes=[
                        M.KeyValue(key="http.request.method", value=M.AnyValue(string_value="GET")),
                        M.KeyValue(key="http.response.status_code", value=M.AnyValue(int_value=200)),
                    ],
                    start_time_unix_nano=base,
                    time_unix_nano=base + 60_000_000_000,
                    count=1_234,
                    sum=456.789,
                    bucket_counts=[0, 12, 145, 402, 388, 210, 61, 14, 2, 0],
                    explicit_bounds=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
                    min=0.002,
                    max=3.1,
                )
                for _ in range(n_dp)
            ],
        ),
    )


# ── Payload builders (batch of resources × scopes × items) ──────────────────

def build_trace_request(M, n_res: int, n_scope: int, n_span: int):
    return M.ExportTraceServiceRequest(
        resource_spans=[
            M.ResourceSpans(
                resource=_resource(M),
                scope_spans=[
                    M.ScopeSpans(
                        scope=M.InstrumentationScope(name="opentelemetry.instrumentation.flask", version="0.48b0"),
                        spans=[_span(M, i) for i in range(n_span)],
                        schema_url=_SCHEMA_URL,
                    )
                    for _ in range(n_scope)
                ],
                schema_url=_SCHEMA_URL,
            )
            for _ in range(n_res)
        ]
    )


def build_logs_request(M, n_res: int, n_scope: int, n_log: int):
    return M.ExportLogsServiceRequest(
        resource_logs=[
            M.ResourceLogs(
                resource=_resource(M),
                scope_logs=[
                    M.ScopeLogs(
                        scope=M.InstrumentationScope(name="opentelemetry.sdk._logs", version="1.30.0"),
                        log_records=[_log_record(M, i) for i in range(n_log)],
                        schema_url=_SCHEMA_URL,
                    )
                    for _ in range(n_scope)
                ],
                schema_url=_SCHEMA_URL,
            )
            for _ in range(n_res)
        ]
    )


def build_metrics_request(M, n_res: int, n_metric: int, n_dp: int):
    return M.ExportMetricsServiceRequest(
        resource_metrics=[
            M.ResourceMetrics(
                resource=_resource(M),
                scope_metrics=[
                    M.ScopeMetrics(
                        scope=M.InstrumentationScope(name="opentelemetry.sdk.metrics", version="1.30.0"),
                        metrics=[_metric(M, i, n_dp) for i in range(n_metric)],
                        schema_url=_SCHEMA_URL,
                    )
                ],
                schema_url=_SCHEMA_URL,
            )
            for _ in range(n_res)
        ]
    )


# Scale points: (id, dims). Dims meaning is per-builder (see signatures above).
# "single"  — one item, the smallest useful export.
# "scope_N" — one resource/scope, N items: isolates per-item encoding cost.
# "batch"   — several resources/scopes: a full collector-sized export.
_TRACE_SCALES = [
    ("single", (1, 1, 1)),
    ("scope_100", (1, 1, 100)),
    ("batch_512", (4, 2, 64)),
]
_LOG_SCALES = [
    ("single", (1, 1, 1)),
    ("scope_100", (1, 1, 100)),
    ("batch_1000", (2, 1, 500)),
]
_METRIC_SCALES = [
    ("single", (1, 1, 1)),
    ("scope_50", (1, 50, 1)),
    ("batch_500", (2, 25, 10)),
]

_SIGNALS = {
    "trace": (build_trace_request, _TRACE_SCALES),
    "logs": (build_logs_request, _LOG_SCALES),
    "metrics": (build_metrics_request, _METRIC_SCALES),
}


# ── Equivalence guard: the two sides must encode to identical bytes ──────────
#
# The benchmark only means something if both implementations do the same work.
# Proto3 field-order serialization makes the byte streams comparable directly.

_ALL_CASES = [
    (signal, label, dims)
    for signal, (_builder, scales) in _SIGNALS.items()
    for label, dims in scales
]
_ALL_IDS = [f"{signal}-{label}" for signal, label, _ in _ALL_CASES]


@mark.parametrize("signal,label,dims", _ALL_CASES, ids=_ALL_IDS)
def test_otlp_outputs_identical(signal, label, dims) -> None:
    builder = _SIGNALS[signal][0]
    py_bytes = builder(PY, *dims).SerializeToString()
    pb_bytes = builder(PB, *dims).SerializeToString()
    assert py_bytes == pb_bytes, (
        f"{signal}/{label}: pyproto and protobuf disagree "
        f"({len(py_bytes)} vs {len(pb_bytes)} bytes)"
    )


# ── Build + serialize: the real per-export cost ─────────────────────────────
#
# One full encode of a logical payload from source data — construct the message
# tree and serialize it, as an exporter does on every export.

@mark.parametrize("signal,label,dims", _ALL_CASES, ids=_ALL_IDS)
@mark.benchmark(group="build_serialize")
def test_build_serialize_pyproto(benchmark, signal, label, dims) -> None:
    builder = _SIGNALS[signal][0]
    result = benchmark(lambda: builder(PY, *dims).SerializeToString())
    assert len(result) > 0


@mark.parametrize("signal,label,dims", _ALL_CASES, ids=_ALL_IDS)
@mark.benchmark(group="build_serialize")
def test_build_serialize_protobuf(benchmark, signal, label, dims) -> None:
    builder = _SIGNALS[signal][0]
    result = benchmark(lambda: builder(PB, *dims).SerializeToString())
    assert len(result) > 0


# ── Serialize only: raw encoding of a pre-built message ─────────────────────
#
# Isolates SerializeToString() from message construction. pyproto builds nothing
# up front (its constructors just stash references), so its serialize-only and
# build+serialize numbers are close; google.protobuf does real work in both
# construction and serialization, so this split shows where its time goes.

@mark.parametrize("signal,label,dims", _ALL_CASES, ids=_ALL_IDS)
@mark.benchmark(group="serialize_only")
def test_serialize_only_pyproto(benchmark, signal, label, dims) -> None:
    builder = _SIGNALS[signal][0]
    message = builder(PY, *dims)
    result = benchmark(message.SerializeToString)
    assert len(result) > 0


@mark.parametrize("signal,label,dims", _ALL_CASES, ids=_ALL_IDS)
@mark.benchmark(group="serialize_only")
def test_serialize_only_protobuf(benchmark, signal, label, dims) -> None:
    builder = _SIGNALS[signal][0]
    message = builder(PB, *dims)
    result = benchmark(message.SerializeToString)
    assert len(result) > 0
