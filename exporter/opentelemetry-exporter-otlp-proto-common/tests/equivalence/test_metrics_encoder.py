# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry.exporter.otlp.proto.common.metrics_encoder import (
    encode_metrics as proto_encode_metrics,
)
from opentelemetry.exporter.otlp._proto.common._internal.metrics_encoder import (
    encode_metrics as pyproto_encode_metrics,
)
from opentelemetry.sdk.metrics import Exemplar
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    Buckets,
    ExponentialHistogramDataPoint,
    HistogramDataPoint,
    Metric,
    MetricsData,
    ResourceMetrics,
    ScopeMetrics,
)
from opentelemetry.sdk.metrics.export import (
    ExponentialHistogram as ExponentialHistogramType,
)
from opentelemetry.sdk.metrics.export import Histogram as HistogramType
from opentelemetry.sdk.metrics.export import Gauge as SDKGauge
from opentelemetry.sdk.metrics.export import Sum as SDKSum
from opentelemetry.sdk.metrics.export import NumberDataPoint
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import (
    InstrumentationScope as SDKInstrumentationScope,
)


_SPAN_ID = int("6e0c63257de34c92", 16)
_TRACE_ID = int("d4cda95b652f4a1592b449d5929fda1b", 16)


def _wrap(metric: Metric) -> MetricsData:
    return MetricsData(
        resource_metrics=[
            ResourceMetrics(
                resource=Resource({"service.name": "test"}),
                scope_metrics=[
                    ScopeMetrics(
                        scope=SDKInstrumentationScope("test_scope", "1.0"),
                        metrics=[metric],
                        schema_url="",
                    )
                ],
                schema_url="",
            )
        ]
    )


# ── Gauge ─────────────────────────────────────────────────────────────────────

def test_encode_gauge_int_matches_proto() -> None:
    data = _wrap(Metric(
        name="my.gauge",
        description="A gauge",
        unit="1",
        data=SDKGauge(data_points=[
            NumberDataPoint(
                attributes={"host": "localhost"},
                start_time_unix_nano=0,
                time_unix_nano=1641946016139533244,
                value=42,
                exemplars=[],
            )
        ]),
    ))
    assert pyproto_encode_metrics(data).SerializeToString() == proto_encode_metrics(data).SerializeToString()


def test_encode_gauge_double_matches_proto() -> None:
    data = _wrap(Metric(
        name="my.gauge.double",
        description="",
        unit="s",
        data=SDKGauge(data_points=[
            NumberDataPoint(
                attributes={"env": "prod"},
                start_time_unix_nano=0,
                time_unix_nano=1641946016139533244,
                value=3.14,
                exemplars=[],
            )
        ]),
    ))
    assert pyproto_encode_metrics(data).SerializeToString() == proto_encode_metrics(data).SerializeToString()


def test_encode_gauge_with_exemplar_matches_proto() -> None:
    data = _wrap(Metric(
        name="gauge.exemplar",
        description="",
        unit="1",
        data=SDKGauge(data_points=[
            NumberDataPoint(
                attributes={},
                start_time_unix_nano=0,
                time_unix_nano=1641946016139533244,
                value=100.0,
                exemplars=[
                    Exemplar(
                        {"filtered": "yes"},
                        50.0,
                        1641946016139533400,
                        _SPAN_ID,
                        _TRACE_ID,
                    )
                ],
            )
        ]),
    ))
    assert pyproto_encode_metrics(data).SerializeToString() == proto_encode_metrics(data).SerializeToString()


# ── Sum ───────────────────────────────────────────────────────────────────────

def test_encode_sum_int_matches_proto() -> None:
    data = _wrap(Metric(
        name="my.counter",
        description="A counter",
        unit="1",
        data=SDKSum(
            data_points=[
                NumberDataPoint(
                    attributes={"a": 1, "b": False},
                    start_time_unix_nano=1641946016139533000,
                    time_unix_nano=1641946016139533244,
                    value=10,
                    exemplars=[],
                )
            ],
            aggregation_temporality=AggregationTemporality.CUMULATIVE,
            is_monotonic=True,
        ),
    ))
    assert pyproto_encode_metrics(data).SerializeToString() == proto_encode_metrics(data).SerializeToString()


def test_encode_sum_double_delta_matches_proto() -> None:
    data = _wrap(Metric(
        name="my.updown",
        description="",
        unit="By",
        data=SDKSum(
            data_points=[
                NumberDataPoint(
                    attributes={"direction": "in"},
                    start_time_unix_nano=1641946016139533000,
                    time_unix_nano=1641946016139533244,
                    value=2.5,
                    exemplars=[],
                )
            ],
            aggregation_temporality=AggregationTemporality.DELTA,
            is_monotonic=False,
        ),
    ))
    assert pyproto_encode_metrics(data).SerializeToString() == proto_encode_metrics(data).SerializeToString()


# ── Histogram ─────────────────────────────────────────────────────────────────

def test_encode_histogram_matches_proto() -> None:
    data = _wrap(Metric(
        name="my.histogram",
        description="A histogram",
        unit="s",
        data=HistogramType(
            data_points=[
                HistogramDataPoint(
                    attributes={"a": 1, "b": True},
                    start_time_unix_nano=1641946016139533244,
                    time_unix_nano=1641946016139533244,
                    exemplars=[
                        Exemplar(
                            {"filtered": "banana"},
                            298.0,
                            1641946016139533400,
                            _SPAN_ID,
                            _TRACE_ID,
                        ),
                        Exemplar(
                            {"filtered": "banana"},
                            298.0,
                            1641946016139533400,
                            None,
                            None,
                        ),
                    ],
                    count=5,
                    sum=67,
                    bucket_counts=[1, 4],
                    explicit_bounds=[10.0, 20.0],
                    min=8,
                    max=18,
                )
            ],
            aggregation_temporality=AggregationTemporality.DELTA,
        ),
    ))
    assert pyproto_encode_metrics(data).SerializeToString() == proto_encode_metrics(data).SerializeToString()


def test_encode_histogram_no_exemplars_matches_proto() -> None:
    data = _wrap(Metric(
        name="simple.histogram",
        description="",
        unit="ms",
        data=HistogramType(
            data_points=[
                HistogramDataPoint(
                    attributes={"region": "us-east"},
                    start_time_unix_nano=1641946016000000000,
                    time_unix_nano=1641946016139533244,
                    exemplars=[],
                    count=10,
                    sum=500.0,
                    bucket_counts=[2, 3, 5],
                    explicit_bounds=[100.0, 200.0],
                    min=10.0,
                    max=200.0,
                )
            ],
            aggregation_temporality=AggregationTemporality.CUMULATIVE,
        ),
    ))
    assert pyproto_encode_metrics(data).SerializeToString() == proto_encode_metrics(data).SerializeToString()


# ── ExponentialHistogram ──────────────────────────────────────────────────────

def test_encode_exponential_histogram_matches_proto() -> None:
    data = _wrap(Metric(
        name="exp.histogram",
        description="",
        unit="1",
        data=ExponentialHistogramType(
            data_points=[
                ExponentialHistogramDataPoint(
                    attributes={"host": "node1"},
                    start_time_unix_nano=1641946016000000000,
                    time_unix_nano=1641946016139533244,
                    exemplars=[],
                    count=8,
                    sum=100.0,
                    scale=2,
                    zero_count=1,
                    positive=Buckets(offset=1, bucket_counts=[3, 4]),
                    negative=Buckets(offset=-1, bucket_counts=[1]),
                    flags=0,
                    min=1.0,
                    max=50.0,
                )
            ],
            aggregation_temporality=AggregationTemporality.DELTA,
        ),
    ))
    assert pyproto_encode_metrics(data).SerializeToString() == proto_encode_metrics(data).SerializeToString()


# ── Multiple metrics and resources ────────────────────────────────────────────

def test_encode_multiple_metrics_matches_proto() -> None:
    gauge_metric = Metric(
        name="gauge",
        description="",
        unit="1",
        data=SDKGauge(data_points=[
            NumberDataPoint(
                attributes={},
                start_time_unix_nano=0,
                time_unix_nano=1641946016139533244,
                value=1,
                exemplars=[],
            )
        ]),
    )
    counter_metric = Metric(
        name="counter",
        description="",
        unit="1",
        data=SDKSum(
            data_points=[
                NumberDataPoint(
                    attributes={},
                    start_time_unix_nano=1641946016000000000,
                    time_unix_nano=1641946016139533244,
                    value=5,
                    exemplars=[],
                )
            ],
            aggregation_temporality=AggregationTemporality.CUMULATIVE,
            is_monotonic=True,
        ),
    )
    data = MetricsData(
        resource_metrics=[
            ResourceMetrics(
                resource=Resource({"service.name": "svc-a"}),
                scope_metrics=[
                    ScopeMetrics(
                        scope=SDKInstrumentationScope("lib_a", "1.0"),
                        metrics=[gauge_metric, counter_metric],
                        schema_url="",
                    )
                ],
                schema_url="",
            ),
            ResourceMetrics(
                resource=Resource({"service.name": "svc-b"}),
                scope_metrics=[
                    ScopeMetrics(
                        scope=SDKInstrumentationScope("lib_b", "2.0"),
                        metrics=[gauge_metric],
                        schema_url="",
                    )
                ],
                schema_url="resource_schema_url",
            ),
        ]
    )
    assert pyproto_encode_metrics(data).SerializeToString() == proto_encode_metrics(data).SerializeToString()


def test_encode_metrics_empty_matches_proto() -> None:
    data = MetricsData(resource_metrics=[])
    assert pyproto_encode_metrics(data).SerializeToString() == proto_encode_metrics(data).SerializeToString()
