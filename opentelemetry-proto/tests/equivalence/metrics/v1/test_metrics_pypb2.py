from opentelemetry.proto.common.v1.common_pb2 import (
    AnyValue as ProtoAnyValue,
    InstrumentationScope as ProtoInstrumentationScope,
    KeyValue as ProtoKeyValue,
)
from opentelemetry.proto.metrics.v1.metrics_pb2 import (
    Exemplar as ProtoExemplar,
    ExponentialHistogram as ProtoExponentialHistogram,
    ExponentialHistogramDataPoint as ProtoExponentialHistogramDataPoint,
    Gauge as ProtoGauge,
    Histogram as ProtoHistogram,
    HistogramDataPoint as ProtoHistogramDataPoint,
    Metric as ProtoMetric,
    NumberDataPoint as ProtoNumberDataPoint,
    ResourceMetrics as ProtoResourceMetrics,
    ScopeMetrics as ProtoScopeMetrics,
    Sum as ProtoSum,
    Summary as ProtoSummary,
    SummaryDataPoint as ProtoSummaryDataPoint,
)
from opentelemetry.proto.resource.v1.resource_pb2 import Resource as ProtoResource

from opentelemetry._proto.common.v1.common_pb2 import (
    AnyValue,
    InstrumentationScope,
    KeyValue,
)
from opentelemetry._proto.metrics.v1.metrics_pb2 import (
    Exemplar,
    ExponentialHistogram,
    ExponentialHistogramDataPoint,
    Gauge,
    Histogram,
    HistogramDataPoint,
    Metric,
    NumberDataPoint,
    ResourceMetrics,
    ScopeMetrics,
    Sum,
    Summary,
    SummaryDataPoint,
)
from opentelemetry._proto.resource.v1.resource_pb2 import Resource


# ── Exemplar ──────────────────────────────────────────────────────────────────

def test_exemplar_empty() -> None:
    assert Exemplar().SerializeToString() == b""


def test_exemplar_empty_matches_proto() -> None:
    assert Exemplar().SerializeToString() == ProtoExemplar().SerializeToString()


def test_exemplar_as_double() -> None:
    our = Exemplar(as_double=1.5, time_unix_nano=1_000)
    proto = ProtoExemplar(as_double=1.5, time_unix_nano=1_000)
    assert our.SerializeToString() == proto.SerializeToString()


def test_exemplar_as_int() -> None:
    our = Exemplar(as_int=42, time_unix_nano=2_000)
    proto = ProtoExemplar(as_int=42, time_unix_nano=2_000)
    assert our.SerializeToString() == proto.SerializeToString()


def test_exemplar_with_span_trace_id() -> None:
    our = Exemplar(as_double=3.0, span_id=b"\x01" * 8, trace_id=b"\x02" * 16)
    proto = ProtoExemplar(as_double=3.0, span_id=b"\x01" * 8, trace_id=b"\x02" * 16)
    assert our.SerializeToString() == proto.SerializeToString()


def test_exemplar_with_filtered_attributes() -> None:
    # filtered_attributes is field 7; test it alone to avoid field-ordering
    # differences between our fixed-order encoding and proto's ascending order.
    attr = KeyValue(key="k", value=AnyValue(string_value="v"))
    proto_attr = ProtoKeyValue(key="k", value=ProtoAnyValue(string_value="v"))
    our = Exemplar(filtered_attributes=[attr])
    proto = ProtoExemplar(filtered_attributes=[proto_attr])
    assert our.SerializeToString() == proto.SerializeToString()


# ── NumberDataPoint ───────────────────────────────────────────────────────────

def test_number_data_point_empty() -> None:
    assert NumberDataPoint().SerializeToString() == b""


def test_number_data_point_empty_matches_proto() -> None:
    assert NumberDataPoint().SerializeToString() == ProtoNumberDataPoint().SerializeToString()


def test_number_data_point_as_double() -> None:
    our = NumberDataPoint(as_double=1.5, time_unix_nano=1_000_000)
    proto = ProtoNumberDataPoint(as_double=1.5, time_unix_nano=1_000_000)
    assert our.SerializeToString() == proto.SerializeToString()


def test_number_data_point_as_int() -> None:
    our = NumberDataPoint(as_int=42, time_unix_nano=1_000_000)
    proto = ProtoNumberDataPoint(as_int=42, time_unix_nano=1_000_000)
    assert our.SerializeToString() == proto.SerializeToString()


def test_number_data_point_with_attributes() -> None:
    # attributes is field 7, flags is field 8 — both high-numbered and in the
    # right relative order in our encoding, so no ordering difference with proto.
    attr = KeyValue(key="env", value=AnyValue(string_value="prod"))
    proto_attr = ProtoKeyValue(key="env", value=ProtoAnyValue(string_value="prod"))
    our = NumberDataPoint(attributes=[attr], flags=1)
    proto = ProtoNumberDataPoint(attributes=[proto_attr], flags=1)
    assert our.SerializeToString() == proto.SerializeToString()


def test_number_data_point_with_exemplar() -> None:
    our = NumberDataPoint(
        as_double=5.0,
        start_time_unix_nano=1_000,
        time_unix_nano=2_000,
        exemplars=[Exemplar(as_double=5.0)],
    )
    proto = ProtoNumberDataPoint(
        as_double=5.0,
        start_time_unix_nano=1_000,
        time_unix_nano=2_000,
        exemplars=[ProtoExemplar(as_double=5.0)],
    )
    assert our.SerializeToString() == proto.SerializeToString()


# ── Gauge ─────────────────────────────────────────────────────────────────────

def test_gauge_empty() -> None:
    assert Gauge().SerializeToString() == b""


def test_gauge_empty_matches_proto() -> None:
    assert Gauge().SerializeToString() == ProtoGauge().SerializeToString()


def test_gauge_with_data_point() -> None:
    our = Gauge(data_points=[NumberDataPoint(as_double=1.5)])
    proto = ProtoGauge(data_points=[ProtoNumberDataPoint(as_double=1.5)])
    assert our.SerializeToString() == proto.SerializeToString()


# ── Sum ───────────────────────────────────────────────────────────────────────

def test_sum_empty() -> None:
    assert Sum().SerializeToString() == b""


def test_sum_empty_matches_proto() -> None:
    assert Sum().SerializeToString() == ProtoSum().SerializeToString()


def test_sum_with_data_and_temporality() -> None:
    our = Sum(
        data_points=[NumberDataPoint(as_int=10)],
        aggregation_temporality=1,
        is_monotonic=True,
    )
    proto = ProtoSum(
        data_points=[ProtoNumberDataPoint(as_int=10)],
        aggregation_temporality=1,
        is_monotonic=True,
    )
    assert our.SerializeToString() == proto.SerializeToString()


# ── HistogramDataPoint ────────────────────────────────────────────────────────

def test_histogram_data_point_empty() -> None:
    assert HistogramDataPoint().SerializeToString() == b""


def test_histogram_data_point_empty_matches_proto() -> None:
    assert (
        HistogramDataPoint().SerializeToString()
        == ProtoHistogramDataPoint().SerializeToString()
    )


def test_histogram_data_point_with_count_and_buckets() -> None:
    our = HistogramDataPoint(
        time_unix_nano=1_000,
        count=5,
        sum=100.0,
        bucket_counts=[2, 3],
        explicit_bounds=[50.0],
    )
    proto = ProtoHistogramDataPoint(
        time_unix_nano=1_000,
        count=5,
        sum=100.0,
        bucket_counts=[2, 3],
        explicit_bounds=[50.0],
    )
    assert our.SerializeToString() == proto.SerializeToString()


def test_histogram_data_point_with_min_max() -> None:
    our = HistogramDataPoint(time_unix_nano=1_000, count=3, min=0.0, max=10.0)
    proto = ProtoHistogramDataPoint(time_unix_nano=1_000, count=3, min=0.0, max=10.0)
    assert our.SerializeToString() == proto.SerializeToString()


# ── Histogram ─────────────────────────────────────────────────────────────────

def test_histogram_empty() -> None:
    assert Histogram().SerializeToString() == b""


def test_histogram_empty_matches_proto() -> None:
    assert Histogram().SerializeToString() == ProtoHistogram().SerializeToString()


def test_histogram_with_data_and_temporality() -> None:
    our = Histogram(
        data_points=[HistogramDataPoint(count=5, time_unix_nano=1_000)],
        aggregation_temporality=2,
    )
    proto = ProtoHistogram(
        data_points=[ProtoHistogramDataPoint(count=5, time_unix_nano=1_000)],
        aggregation_temporality=2,
    )
    assert our.SerializeToString() == proto.SerializeToString()


# ── ExponentialHistogramDataPoint.Buckets ─────────────────────────────────────

def test_exp_histogram_buckets_empty() -> None:
    assert ExponentialHistogramDataPoint.Buckets().SerializeToString() == b""


def test_exp_histogram_buckets_empty_matches_proto() -> None:
    assert (
        ExponentialHistogramDataPoint.Buckets().SerializeToString()
        == ProtoExponentialHistogramDataPoint.Buckets().SerializeToString()
    )


def test_exp_histogram_buckets_with_data() -> None:
    our = ExponentialHistogramDataPoint.Buckets(offset=2, bucket_counts=[1, 2, 3])
    proto = ProtoExponentialHistogramDataPoint.Buckets(offset=2, bucket_counts=[1, 2, 3])
    assert our.SerializeToString() == proto.SerializeToString()


def test_exp_histogram_buckets_negative_offset() -> None:
    our = ExponentialHistogramDataPoint.Buckets(offset=-3, bucket_counts=[4, 5])
    proto = ProtoExponentialHistogramDataPoint.Buckets(offset=-3, bucket_counts=[4, 5])
    assert our.SerializeToString() == proto.SerializeToString()


# ── ExponentialHistogramDataPoint ─────────────────────────────────────────────

def test_exp_histogram_data_point_empty() -> None:
    assert ExponentialHistogramDataPoint().SerializeToString() == b""


def test_exp_histogram_data_point_empty_matches_proto() -> None:
    assert (
        ExponentialHistogramDataPoint().SerializeToString()
        == ProtoExponentialHistogramDataPoint().SerializeToString()
    )


def test_exp_histogram_data_point_with_scale_and_count() -> None:
    our = ExponentialHistogramDataPoint(
        time_unix_nano=1_000,
        count=10,
        scale=-1,
        zero_count=2,
    )
    proto = ProtoExponentialHistogramDataPoint(
        time_unix_nano=1_000,
        count=10,
        scale=-1,
        zero_count=2,
    )
    assert our.SerializeToString() == proto.SerializeToString()


def test_exp_histogram_data_point_with_buckets() -> None:
    pos = ExponentialHistogramDataPoint.Buckets(offset=1, bucket_counts=[3, 4])
    neg = ExponentialHistogramDataPoint.Buckets(offset=-1, bucket_counts=[1])
    proto_pos = ProtoExponentialHistogramDataPoint.Buckets(offset=1, bucket_counts=[3, 4])
    proto_neg = ProtoExponentialHistogramDataPoint.Buckets(offset=-1, bucket_counts=[1])
    our = ExponentialHistogramDataPoint(
        count=8, scale=2, positive=pos, negative=neg, time_unix_nano=1_000
    )
    proto = ProtoExponentialHistogramDataPoint(
        count=8, scale=2, positive=proto_pos, negative=proto_neg, time_unix_nano=1_000
    )
    assert our.SerializeToString() == proto.SerializeToString()


# ── ExponentialHistogram ──────────────────────────────────────────────────────

def test_exp_histogram_empty() -> None:
    assert ExponentialHistogram().SerializeToString() == b""


def test_exp_histogram_empty_matches_proto() -> None:
    assert (
        ExponentialHistogram().SerializeToString()
        == ProtoExponentialHistogram().SerializeToString()
    )


def test_exp_histogram_with_data() -> None:
    our = ExponentialHistogram(
        data_points=[ExponentialHistogramDataPoint(count=5, time_unix_nano=1_000)],
        aggregation_temporality=1,
    )
    proto = ProtoExponentialHistogram(
        data_points=[ProtoExponentialHistogramDataPoint(count=5, time_unix_nano=1_000)],
        aggregation_temporality=1,
    )
    assert our.SerializeToString() == proto.SerializeToString()


# ── SummaryDataPoint.ValueAtQuantile ──────────────────────────────────────────

def test_value_at_quantile_empty() -> None:
    assert SummaryDataPoint.ValueAtQuantile().SerializeToString() == b""


def test_value_at_quantile_empty_matches_proto() -> None:
    assert (
        SummaryDataPoint.ValueAtQuantile().SerializeToString()
        == ProtoSummaryDataPoint.ValueAtQuantile().SerializeToString()
    )


def test_value_at_quantile() -> None:
    our = SummaryDataPoint.ValueAtQuantile(quantile=0.5, value=100.0)
    proto = ProtoSummaryDataPoint.ValueAtQuantile(quantile=0.5, value=100.0)
    assert our.SerializeToString() == proto.SerializeToString()


def test_value_at_quantile_p99() -> None:
    our = SummaryDataPoint.ValueAtQuantile(quantile=0.99, value=500.0)
    proto = ProtoSummaryDataPoint.ValueAtQuantile(quantile=0.99, value=500.0)
    assert our.SerializeToString() == proto.SerializeToString()


# ── SummaryDataPoint ──────────────────────────────────────────────────────────

def test_summary_data_point_empty() -> None:
    assert SummaryDataPoint().SerializeToString() == b""


def test_summary_data_point_empty_matches_proto() -> None:
    assert (
        SummaryDataPoint().SerializeToString()
        == ProtoSummaryDataPoint().SerializeToString()
    )


def test_summary_data_point_with_count_and_sum() -> None:
    our = SummaryDataPoint(count=10, sum=500.0, time_unix_nano=1_000)
    proto = ProtoSummaryDataPoint(count=10, sum=500.0, time_unix_nano=1_000)
    assert our.SerializeToString() == proto.SerializeToString()


def test_summary_data_point_with_quantiles() -> None:
    our = SummaryDataPoint(
        count=100,
        sum=5000.0,
        quantile_values=[
            SummaryDataPoint.ValueAtQuantile(quantile=0.5, value=45.0),
            SummaryDataPoint.ValueAtQuantile(quantile=0.99, value=200.0),
        ],
    )
    proto = ProtoSummaryDataPoint(
        count=100,
        sum=5000.0,
        quantile_values=[
            ProtoSummaryDataPoint.ValueAtQuantile(quantile=0.5, value=45.0),
            ProtoSummaryDataPoint.ValueAtQuantile(quantile=0.99, value=200.0),
        ],
    )
    assert our.SerializeToString() == proto.SerializeToString()


# ── Summary ───────────────────────────────────────────────────────────────────

def test_summary_empty() -> None:
    assert Summary().SerializeToString() == b""


def test_summary_empty_matches_proto() -> None:
    assert Summary().SerializeToString() == ProtoSummary().SerializeToString()


def test_summary_with_data_point() -> None:
    our = Summary(data_points=[SummaryDataPoint(count=10, sum=500.0)])
    proto = ProtoSummary(data_points=[ProtoSummaryDataPoint(count=10, sum=500.0)])
    assert our.SerializeToString() == proto.SerializeToString()


# ── Metric ────────────────────────────────────────────────────────────────────

def test_metric_empty() -> None:
    assert Metric().SerializeToString() == b""


def test_metric_empty_matches_proto() -> None:
    assert Metric().SerializeToString() == ProtoMetric().SerializeToString()


def test_metric_gauge() -> None:
    our = Metric(name="cpu", description="CPU usage", unit="%", gauge=Gauge(
        data_points=[NumberDataPoint(as_double=0.75)]
    ))
    proto = ProtoMetric(name="cpu", description="CPU usage", unit="%", gauge=ProtoGauge(
        data_points=[ProtoNumberDataPoint(as_double=0.75)]
    ))
    assert our.SerializeToString() == proto.SerializeToString()


def test_metric_sum() -> None:
    our = Metric(name="requests", unit="1", sum=Sum(
        data_points=[NumberDataPoint(as_int=100)],
        aggregation_temporality=2,
        is_monotonic=True,
    ))
    proto = ProtoMetric(name="requests", unit="1", sum=ProtoSum(
        data_points=[ProtoNumberDataPoint(as_int=100)],
        aggregation_temporality=2,
        is_monotonic=True,
    ))
    assert our.SerializeToString() == proto.SerializeToString()


def test_metric_histogram() -> None:
    our = Metric(name="latency", histogram=Histogram(
        data_points=[HistogramDataPoint(count=5, time_unix_nano=1_000)],
        aggregation_temporality=1,
    ))
    proto = ProtoMetric(name="latency", histogram=ProtoHistogram(
        data_points=[ProtoHistogramDataPoint(count=5, time_unix_nano=1_000)],
        aggregation_temporality=1,
    ))
    assert our.SerializeToString() == proto.SerializeToString()


def test_metric_summary() -> None:
    our = Metric(name="duration", summary=Summary(
        data_points=[SummaryDataPoint(count=10, sum=500.0)],
    ))
    proto = ProtoMetric(name="duration", summary=ProtoSummary(
        data_points=[ProtoSummaryDataPoint(count=10, sum=500.0)],
    ))
    assert our.SerializeToString() == proto.SerializeToString()


def test_metric_exponential_histogram() -> None:
    our = Metric(name="exp_lat", exponential_histogram=ExponentialHistogram(
        data_points=[ExponentialHistogramDataPoint(count=3, time_unix_nano=1_000)],
        aggregation_temporality=2,
    ))
    proto = ProtoMetric(name="exp_lat", exponential_histogram=ProtoExponentialHistogram(
        data_points=[ProtoExponentialHistogramDataPoint(count=3, time_unix_nano=1_000)],
        aggregation_temporality=2,
    ))
    assert our.SerializeToString() == proto.SerializeToString()


# ── ScopeMetrics ──────────────────────────────────────────────────────────────

def test_scope_metrics_empty() -> None:
    assert ScopeMetrics().SerializeToString() == b""


def test_scope_metrics_empty_matches_proto() -> None:
    assert ScopeMetrics().SerializeToString() == ProtoScopeMetrics().SerializeToString()


def test_scope_metrics_schema_url() -> None:
    our = ScopeMetrics(schema_url="https://example.com")
    proto = ProtoScopeMetrics(schema_url="https://example.com")
    assert our.SerializeToString() == proto.SerializeToString()


def test_scope_metrics_with_scope_and_metric() -> None:
    scope = InstrumentationScope(name="mylib", version="1.0")
    proto_scope = ProtoInstrumentationScope(name="mylib", version="1.0")
    metric = Metric(name="cpu", gauge=Gauge(data_points=[NumberDataPoint(as_double=0.5)]))
    proto_metric = ProtoMetric(name="cpu", gauge=ProtoGauge(data_points=[ProtoNumberDataPoint(as_double=0.5)]))
    our = ScopeMetrics(scope=scope, metrics=[metric], schema_url="s")
    proto = ProtoScopeMetrics(scope=proto_scope, metrics=[proto_metric], schema_url="s")
    assert our.SerializeToString() == proto.SerializeToString()


# ── ResourceMetrics ───────────────────────────────────────────────────────────

def test_resource_metrics_empty() -> None:
    assert ResourceMetrics().SerializeToString() == b""


def test_resource_metrics_empty_matches_proto() -> None:
    assert ResourceMetrics().SerializeToString() == ProtoResourceMetrics().SerializeToString()


def test_resource_metrics_schema_url() -> None:
    our = ResourceMetrics(schema_url="https://example.com")
    proto = ProtoResourceMetrics(schema_url="https://example.com")
    assert our.SerializeToString() == proto.SerializeToString()


def test_resource_metrics_with_resource() -> None:
    res = Resource(attributes=[KeyValue(key="k", value=AnyValue(string_value="v"))])
    proto_res = ProtoResource(attributes=[ProtoKeyValue(key="k", value=ProtoAnyValue(string_value="v"))])
    our = ResourceMetrics(resource=res, schema_url="s")
    proto = ProtoResourceMetrics(resource=proto_res, schema_url="s")
    assert our.SerializeToString() == proto.SerializeToString()


def test_resource_metrics_with_scope_metrics() -> None:
    sm = ScopeMetrics(metrics=[Metric(name="cpu", gauge=Gauge())])
    proto_sm = ProtoScopeMetrics(metrics=[ProtoMetric(name="cpu", gauge=ProtoGauge())])
    our = ResourceMetrics(scope_metrics=[sm])
    proto = ProtoResourceMetrics(scope_metrics=[proto_sm])
    assert our.SerializeToString() == proto.SerializeToString()
