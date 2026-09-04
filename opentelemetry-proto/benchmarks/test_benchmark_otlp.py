# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

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
# The real (google.protobuf) classes come from the protobuf-backed reference
# set under ``opentelemetry.proto._test`` (the ``[test]`` extra of
# opentelemetry-proto), which wraps the upb/C backend. That set serializes to
# the same wire bytes as the pure-Python classes (the equivalence suite proves
# it), so the two can be compared field for field.
#
# Run:
#   uv pip install '.[test]' pytest-benchmark
#   uv run pytest benchmarks/test_benchmark_otlp.py \
#       --benchmark-sort=fullname --benchmark-group-by=group

from types import SimpleNamespace

from pytest import mark

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

# Real side: the protobuf-backed reference set under opentelemetry.proto._test
# (the [test] extra), which wraps the google.protobuf/upb implementation.
from opentelemetry.proto._test.collector.logs.v1 import logs_service_pb2 as _pb_coll_logs
from opentelemetry.proto._test.collector.metrics.v1 import (
    metrics_service_pb2 as _pb_coll_metrics,
)
from opentelemetry.proto._test.collector.trace.v1 import (
    trace_service_pb2 as _pb_coll_trace,
)
from opentelemetry.proto._test.common.v1 import common_pb2 as _pb_common
from opentelemetry.proto._test.logs.v1 import logs_pb2 as _pb_logs
from opentelemetry.proto._test.metrics.v1 import metrics_pb2 as _pb_metrics
from opentelemetry.proto._test.resource.v1 import resource_pb2 as _pb_resource
from opentelemetry.proto._test.trace.v1 import trace_pb2 as _pb_trace

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
    _py_common,
    _py_resource,
    _py_trace,
    _py_logs,
    _py_metrics,
    _py_coll_trace,
    _py_coll_logs,
    _py_coll_metrics,
)
PB = _bundle(
    _pb_common,
    _pb_resource,
    _pb_trace,
    _pb_logs,
    _pb_metrics,
    _pb_coll_trace,
    _pb_coll_logs,
    _pb_coll_metrics,
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


def _resource(messages):
    """A resource with the attribute set a real service emits."""
    return messages.Resource(
        attributes=[
            messages.KeyValue(key="service.name", value=messages.AnyValue(string_value="checkout-service")),
            messages.KeyValue(key="service.version", value=messages.AnyValue(string_value="1.24.0")),
            messages.KeyValue(key="service.instance.id", value=messages.AnyValue(string_value="pod-7f9c-abc123")),
            messages.KeyValue(key="process.pid", value=messages.AnyValue(int_value=42317)),
            messages.KeyValue(key="host.name", value=messages.AnyValue(string_value="ip-10-0-12-34")),
            messages.KeyValue(key="telemetry.sdk.language", value=messages.AnyValue(string_value="python")),
            messages.KeyValue(key="telemetry.sdk.version", value=messages.AnyValue(string_value="1.30.0")),
        ]
    )


def _span_attributes(messages, i: int):
    return [
        messages.KeyValue(key="http.request.method", value=messages.AnyValue(string_value="GET")),
        messages.KeyValue(key="url.path", value=messages.AnyValue(string_value=f"/api/orders/{i}")),
        messages.KeyValue(key="http.response.status_code", value=messages.AnyValue(int_value=200)),
        messages.KeyValue(key="server.address", value=messages.AnyValue(string_value="orders.internal")),
        messages.KeyValue(key="network.protocol.version", value=messages.AnyValue(string_value="1.1")),
        messages.KeyValue(key="db.system", value=messages.AnyValue(string_value="postgresql")),
    ]


def _span(messages, i: int):
    base = 1_700_000_000_000_000_000 + i * 1_000_000
    return messages.Span(
        trace_id=_trace_id(i),
        span_id=_span_id(i),
        parent_span_id=_span_id(i + 1),
        name="GET /api/orders/{id}",
        kind=2,  # SPAN_KIND_SERVER
        start_time_unix_nano=base,
        end_time_unix_nano=base + 4_200_000,
        attributes=_span_attributes(messages, i),
        events=[
            messages.Span.Event(
                time_unix_nano=base + 1_000_000,
                name="cache.miss",
                attributes=[
                    messages.KeyValue(key="cache.key", value=messages.AnyValue(string_value=f"order:{i}")),
                ],
            ),
            messages.Span.Event(
                time_unix_nano=base + 2_500_000,
                name="db.query",
                attributes=[
                    messages.KeyValue(key="db.rows", value=messages.AnyValue(int_value=17)),
                ],
            ),
        ],
        links=[
            messages.Span.Link(
                trace_id=_trace_id(i + 100),
                span_id=_span_id(i + 100),
                trace_state="vendor=abc",
            ),
        ],
        status=messages.Status(code=1, message=""),  # STATUS_CODE_OK
        flags=1,
    )


def _log_record(messages, i: int):
    base = 1_700_000_000_000_000_000 + i * 1_000_000
    return messages.LogRecord(
        time_unix_nano=base,
        observed_time_unix_nano=base + 1_000,
        severity_number=9,  # INFO
        severity_text="INFO",
        body=messages.AnyValue(string_value=f"request {i} completed in 4.2ms with status 200"),
        attributes=[
            messages.KeyValue(key="log.source", value=messages.AnyValue(string_value="access")),
            messages.KeyValue(key="http.route", value=messages.AnyValue(string_value="/api/orders/{id}")),
            messages.KeyValue(key="http.response.status_code", value=messages.AnyValue(int_value=200)),
            messages.KeyValue(key="thread.id", value=messages.AnyValue(int_value=140_234_567)),
        ],
        trace_id=_trace_id(i),
        span_id=_span_id(i),
        flags=1,
    )


def _metric(messages, i: int, n_dp: int):
    base = 1_700_000_000_000_000_000 + i * 1_000_000
    return messages.Metric(
        name=f"http.server.request.duration.{i}",
        description="Duration of HTTP server requests.",
        unit="s",
        histogram=messages.Histogram(
            aggregation_temporality=2,  # CUMULATIVE
            data_points=[
                messages.HistogramDataPoint(
                    attributes=[
                        messages.KeyValue(key="http.request.method", value=messages.AnyValue(string_value="GET")),
                        messages.KeyValue(key="http.response.status_code", value=messages.AnyValue(int_value=200)),
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


def build_trace_request(messages, n_res: int, n_scope: int, n_span: int):
    return messages.ExportTraceServiceRequest(
        resource_spans=[
            messages.ResourceSpans(
                resource=_resource(messages),
                scope_spans=[
                    messages.ScopeSpans(
                        scope=messages.InstrumentationScope(
                            name="opentelemetry.instrumentation.flask", version="0.48b0"
                        ),
                        spans=[_span(messages, i) for i in range(n_span)],
                        schema_url=_SCHEMA_URL,
                    )
                    for _ in range(n_scope)
                ],
                schema_url=_SCHEMA_URL,
            )
            for _ in range(n_res)
        ]
    )


def build_logs_request(messages, n_res: int, n_scope: int, n_log: int):
    return messages.ExportLogsServiceRequest(
        resource_logs=[
            messages.ResourceLogs(
                resource=_resource(messages),
                scope_logs=[
                    messages.ScopeLogs(
                        scope=messages.InstrumentationScope(name="opentelemetry.sdk._logs", version="1.30.0"),
                        log_records=[_log_record(messages, i) for i in range(n_log)],
                        schema_url=_SCHEMA_URL,
                    )
                    for _ in range(n_scope)
                ],
                schema_url=_SCHEMA_URL,
            )
            for _ in range(n_res)
        ]
    )


def build_metrics_request(messages, n_res: int, n_metric: int, n_dp: int):
    return messages.ExportMetricsServiceRequest(
        resource_metrics=[
            messages.ResourceMetrics(
                resource=_resource(messages),
                scope_metrics=[
                    messages.ScopeMetrics(
                        scope=messages.InstrumentationScope(name="opentelemetry.sdk.metrics", version="1.30.0"),
                        metrics=[_metric(messages, i, n_dp) for i in range(n_metric)],
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

_ALL_CASES = [(signal, label, dims) for signal, (_builder, scales) in _SIGNALS.items() for label, dims in scales]
_ALL_IDS = [f"{signal}-{label}" for signal, label, _ in _ALL_CASES]


@mark.parametrize("signal,label,dims", _ALL_CASES, ids=_ALL_IDS)
def test_otlp_outputs_identical(signal, label, dims) -> None:
    builder = _SIGNALS[signal][0]
    py_bytes = builder(PY, *dims).SerializeToString()
    pb_bytes = builder(PB, *dims).SerializeToString()
    assert py_bytes == pb_bytes, (
        f"{signal}/{label}: pyproto and protobuf disagree ({len(py_bytes)} vs {len(pb_bytes)} bytes)"
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
