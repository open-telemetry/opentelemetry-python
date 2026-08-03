# tests/performance/test_benchmark_encoder.py
#
# Benchmark: the pure-Python OTLP encoders (opentelemetry.exporter.otlp._proto
# .common) vs the real google.protobuf-backed encoders (opentelemetry.exporter
# .otlp.proto.common) on the exporter's actual production hot path — real SDK
# spans / metrics / logs in, serialized OTLP export-request bytes out.
#
# This is the end-to-end counterpart to opentelemetry-pyproto's
# test_benchmark_otlp.py: instead of hand-built proto message trees, it drives
# encode_spans / encode_metrics / encode_logs with genuine SDK objects, so the
# numbers reflect what an exporter pays per export (SDK data -> proto messages
# -> wire bytes).
#
# Both encoder paths share an identical call signature and return objects with
# SerializeToString(); a byte-equality guard asserts they encode identically so
# the comparison is fair.
#
# The real encoders are only present when the upstream
# ``opentelemetry-exporter-otlp-proto-common`` owns the public
# ``opentelemetry.exporter.otlp.proto.common`` path (installed after this
# package so it wins the namespace). Otherwise that path is this package's
# re-export shim and the whole module skips, like the equivalence conftest.
#
# Run (install order matters — real protobuf encoder must win the public path):
#   uv pip install . && uv pip install \
#       opentelemetry-sdk protobuf opentelemetry-proto \
#       opentelemetry-exporter-otlp-proto-common pytest-benchmark
#   uv run pytest tests/performance/test_benchmark_encoder.py \
#       --benchmark-group-by=param --benchmark-sort=fullname

from pytest import mark, skip

# Public path: real upstream encoder when installed, else this package's shim.
from opentelemetry.exporter.otlp.proto.common import (
    trace_encoder as _public_trace_encoder,
)

if "pyproto" in (_public_trace_encoder.__file__ or ""):
    skip(
        "opentelemetry.exporter.otlp.proto.common resolves to the pyproto shim "
        f"({_public_trace_encoder.__file__}); install the real "
        "opentelemetry-exporter-otlp-proto-common (after this package) to "
        "benchmark the pure-Python encoders against the real protobuf ones.",
        allow_module_level=True,
    )

from opentelemetry.exporter.otlp.proto.common.trace_encoder import (
    encode_spans as proto_encode_spans,
)
from opentelemetry.exporter.otlp.proto.common.metrics_encoder import (
    encode_metrics as proto_encode_metrics,
)
from opentelemetry.exporter.otlp.proto.common._log_encoder import (
    encode_logs as proto_encode_logs,
)
from opentelemetry.exporter.otlp._proto.common._internal.trace_encoder import (
    encode_spans as pyproto_encode_spans,
)
from opentelemetry.exporter.otlp._proto.common._internal.metrics_encoder import (
    encode_metrics as pyproto_encode_metrics,
)
from opentelemetry.exporter.otlp._proto.common._internal._log_encoder import (
    encode_logs as pyproto_encode_logs,
)

from opentelemetry._logs import LogRecord, SeverityNumber
from opentelemetry.sdk._logs import ReadWriteLogRecord
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    Histogram as HistogramType,
    HistogramDataPoint,
    Metric,
    MetricsData,
    ResourceMetrics,
    ScopeMetrics,
)
from opentelemetry.sdk.resources import Resource as SDKResource
from opentelemetry.sdk.trace import Event as SDKEvent
from opentelemetry.sdk.trace import SpanContext as SDKSpanContext
from opentelemetry.sdk.trace import _Span as SDKSpan
from opentelemetry.sdk.util.instrumentation import (
    InstrumentationScope as SDKInstrumentationScope,
)
from opentelemetry.trace import Link as SDKLink
from opentelemetry.trace import (
    NonRecordingSpan,
    SpanContext,
    SpanKind as SDKSpanKind,
    TraceFlags as SDKTraceFlags,
    set_span_in_context,
)
from opentelemetry.trace.status import Status as SDKStatus
from opentelemetry.trace.status import StatusCode as SDKStatusCode


# ── Shared SDK fixtures ─────────────────────────────────────────────────────
#
# One resource + scope shared across all items so a batch collapses into a
# single ResourceSpans/ScopeSpans, as a real per-service export does. Values
# are index-derived (no randomness) for reproducibility.

_BASE_NS = 1_700_000_000_000_000_000
_TRACE_ID = 0x3E0C63257DE34C926F9EFCD03927272E
_PARENT_SPAN_ID = 0x1111111111111111

_RESOURCE = SDKResource(
    {
        "service.name": "checkout-service",
        "service.version": "1.24.0",
        "service.instance.id": "pod-7f9c-abc123",
        "process.pid": 42317,
        "host.name": "ip-10-0-12-34",
        "telemetry.sdk.language": "python",
        "telemetry.sdk.version": "1.30.0",
    },
    "https://opentelemetry.io/schemas/1.30.0",
)
_TRACE_SCOPE = SDKInstrumentationScope(
    "opentelemetry.instrumentation.flask", "0.48b0"
)
_METRIC_SCOPE = SDKInstrumentationScope("opentelemetry.sdk.metrics", "1.30.0")
_LOG_SCOPE = SDKInstrumentationScope("opentelemetry.sdk._logs", "1.30.0")


def _make_span(i: int) -> SDKSpan:
    start = _BASE_NS + i * 1_000_000
    span = SDKSpan(
        name="GET /api/orders/{id}",
        context=SDKSpanContext(
            _TRACE_ID + i,
            0x34BF92DEEFC58C92 ^ i,
            is_remote=False,
            trace_flags=SDKTraceFlags(SDKTraceFlags.SAMPLED),
        ),
        parent=SDKSpanContext(_TRACE_ID + i, _PARENT_SPAN_ID, is_remote=True),
        kind=SDKSpanKind.SERVER,
        events=(
            SDKEvent(
                name="cache.miss",
                timestamp=start + 1_000_000,
                attributes={"cache.key": f"order:{i}"},
            ),
            SDKEvent(
                name="db.query",
                timestamp=start + 2_500_000,
                attributes={"db.rows": 17, "db.statement": "SELECT 1"},
            ),
        ),
        links=(
            SDKLink(
                context=SDKSpanContext(
                    _TRACE_ID + i + 100, 0x2222222222222222, is_remote=False
                ),
                attributes={"link.kind": "follows_from"},
            ),
        ),
        resource=_RESOURCE,
        instrumentation_scope=_TRACE_SCOPE,
    )
    span.start(start_time=start)
    span.set_attribute("http.request.method", "GET")
    span.set_attribute("url.path", f"/api/orders/{i}")
    span.set_attribute("http.response.status_code", 200)
    span.set_attribute("server.address", "orders.internal")
    span.set_attribute("network.protocol.version", "1.1")
    span.set_attribute("db.system", "postgresql")
    span.set_status(SDKStatus(SDKStatusCode.OK))
    span.end(end_time=start + 4_200_000)
    return span


def _make_spans(n: int) -> list:
    return [_make_span(i) for i in range(n)]


def _make_metric(i: int, n_dp: int) -> Metric:
    start = _BASE_NS
    return Metric(
        name=f"http.server.request.duration.{i}",
        description="Duration of HTTP server requests.",
        unit="s",
        data=HistogramType(
            data_points=[
                HistogramDataPoint(
                    attributes={
                        "http.request.method": "GET",
                        "http.response.status_code": 200 + d,
                    },
                    start_time_unix_nano=start,
                    time_unix_nano=start + 60_000_000_000,
                    count=1_234,
                    sum=456.789,
                    bucket_counts=[0, 12, 145, 402, 388, 210, 61, 14, 2, 0],
                    explicit_bounds=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
                    min=0.002,
                    max=3.1,
                    exemplars=[],
                )
                for d in range(n_dp)
            ],
            aggregation_temporality=AggregationTemporality.CUMULATIVE,
        ),
    )


def _make_metrics_data(n_metric: int, n_dp: int) -> MetricsData:
    return MetricsData(
        resource_metrics=[
            ResourceMetrics(
                resource=_RESOURCE,
                scope_metrics=[
                    ScopeMetrics(
                        scope=_METRIC_SCOPE,
                        metrics=[_make_metric(i, n_dp) for i in range(n_metric)],
                        schema_url="",
                    )
                ],
                schema_url="",
            )
        ]
    )


_LOG_CONTEXT = set_span_in_context(
    NonRecordingSpan(
        SpanContext(_TRACE_ID, 0x34BF92DEEFC58C92, False, SDKTraceFlags(0x01))
    )
)


def _make_log(i: int) -> ReadWriteLogRecord:
    ts = _BASE_NS + i * 1_000_000
    return ReadWriteLogRecord(
        LogRecord(
            timestamp=ts,
            observed_timestamp=ts + 1_000,
            context=_LOG_CONTEXT,
            severity_text="INFO",
            severity_number=SeverityNumber.INFO,
            body=f"request {i} completed in 4.2ms with status 200",
            attributes={
                "log.source": "access",
                "http.route": "/api/orders/{id}",
                "http.response.status_code": 200,
                "thread.id": 140_234_567,
            },
        ),
        resource=_RESOURCE,
        instrumentation_scope=_LOG_SCOPE,
    )


def _make_logs(n: int) -> list:
    return [_make_log(i) for i in range(n)]


# Encoders + payload factories, keyed by signal. Each factory takes the scale
# tuple and returns the encoder input.
_SIGNALS = {
    "trace": (
        pyproto_encode_spans,
        proto_encode_spans,
        lambda dims: _make_spans(*dims),
        [("single", (1,)), ("batch_100", (100,)), ("batch_500", (500,))],
    ),
    "metrics": (
        pyproto_encode_metrics,
        proto_encode_metrics,
        lambda dims: _make_metrics_data(*dims),
        [("single", (1, 1)), ("metrics_50", (50, 1)), ("dp_200", (20, 10))],
    ),
    "logs": (
        pyproto_encode_logs,
        proto_encode_logs,
        lambda dims: _make_logs(*dims),
        [("single", (1,)), ("batch_100", (100,)), ("batch_500", (500,))],
    ),
}

_ALL_CASES = [
    (signal, label, dims)
    for signal, (_py, _pb, _factory, scales) in _SIGNALS.items()
    for label, dims in scales
]
_ALL_IDS = [f"{signal}-{label}" for signal, label, _ in _ALL_CASES]


# ── Fairness guard: both encoders must produce identical bytes ──────────────

@mark.parametrize("signal,label,dims", _ALL_CASES, ids=_ALL_IDS)
def test_encoder_outputs_identical(signal, label, dims) -> None:
    py_encode, pb_encode, factory, _ = _SIGNALS[signal]
    payload = factory(dims)
    py_bytes = py_encode(payload).SerializeToString()
    pb_bytes = pb_encode(payload).SerializeToString()
    assert py_bytes == pb_bytes, (
        f"{signal}/{label}: pyproto and protobuf encoders disagree "
        f"({len(py_bytes)} vs {len(pb_bytes)} bytes)"
    )


# ── Encode + serialize: the per-export cost an exporter actually pays ───────

@mark.parametrize("signal,label,dims", _ALL_CASES, ids=_ALL_IDS)
def test_encode_pyproto(benchmark, signal, label, dims) -> None:
    py_encode, _pb, factory, _ = _SIGNALS[signal]
    payload = factory(dims)
    result = benchmark(lambda: py_encode(payload).SerializeToString())
    assert len(result) > 0


@mark.parametrize("signal,label,dims", _ALL_CASES, ids=_ALL_IDS)
def test_encode_protobuf(benchmark, signal, label, dims) -> None:
    _py, pb_encode, factory, _ = _SIGNALS[signal]
    payload = factory(dims)
    result = benchmark(lambda: pb_encode(payload).SerializeToString())
    assert len(result) > 0
