# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=protected-access,unsubscriptable-object

import unittest
from logging import WARNING

from opentelemetry.exporter.otlp.json.common._internal.metrics_encoder import (
    _METRIC_DATA_FIELDS,
    _get_metric_data_field_name,
    split_metrics_data,
)
from opentelemetry.exporter.otlp.json.common.metrics_encoder import (
    encode_metrics,
)
from opentelemetry.proto_json.collector.metrics.v1.metrics_service import (
    ExportMetricsServiceRequest as JSONExportMetricsServiceRequest,
)
from opentelemetry.proto_json.metrics.v1.metrics import (
    NumberDataPoint as JSONNumberDataPoint,
)
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    Buckets,
    ExponentialHistogram,
    ExponentialHistogramDataPoint,
    Gauge,
    Histogram,
    HistogramDataPoint,
    Metric,
    MetricsData,
    NumberDataPoint,
    ResourceMetrics,
    ScopeMetrics,
    Sum,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope

from . import (
    START_TIME,
    TIME,
    make_exponential_histogram,
    make_gauge,
    make_histogram,
    make_metrics_data,
    make_sum,
)


def _get_first_metric(result: JSONExportMetricsServiceRequest) -> Metric:
    return result.resource_metrics[0].scope_metrics[0].metrics[0]


def _number_dp(value: int) -> NumberDataPoint:
    return NumberDataPoint(
        attributes={"a": 1},
        start_time_unix_nano=START_TIME,
        time_unix_nano=TIME,
        value=value,
    )


def _histogram_dp(count: int) -> HistogramDataPoint:
    return HistogramDataPoint(
        attributes={"a": 1},
        start_time_unix_nano=START_TIME,
        time_unix_nano=TIME,
        count=count,
        sum=count,
        bucket_counts=[count],
        explicit_bounds=[],
        min=0,
        max=count,
        exemplars=[],
    )


def _exponential_histogram_dp(count: int) -> ExponentialHistogramDataPoint:
    return ExponentialHistogramDataPoint(
        attributes={"a": 1},
        start_time_unix_nano=START_TIME,
        time_unix_nano=TIME,
        count=count,
        sum=float(count),
        scale=1,
        zero_count=0,
        positive=Buckets(offset=0, bucket_counts=[count]),
        negative=Buckets(offset=0, bucket_counts=[]),
        flags=0,
        min=0.0,
        max=float(count),
        exemplars=[],
    )


def _sum_metric(name: str, values: list[int]) -> Metric:
    return Metric(
        name=name,
        description="desc",
        unit="s",
        data=Sum(
            data_points=[_number_dp(v) for v in values],
            aggregation_temporality=AggregationTemporality.CUMULATIVE,
            is_monotonic=True,
        ),
    )


def _metric_of_type(field_name: str, count: int) -> Metric:
    values = list(range(1, count + 1))
    match field_name:
        case "gauge":
            data = Gauge(data_points=[_number_dp(v) for v in values])
        case "sum":
            data = Sum(
                data_points=[_number_dp(v) for v in values],
                aggregation_temporality=AggregationTemporality.CUMULATIVE,
                is_monotonic=True,
            )
        case "histogram":
            data = Histogram(
                data_points=[_histogram_dp(v) for v in values],
                aggregation_temporality=AggregationTemporality.DELTA,
            )
        case _:  # exponential_histogram
            data = ExponentialHistogram(
                data_points=[_exponential_histogram_dp(v) for v in values],
                aggregation_temporality=AggregationTemporality.CUMULATIVE,
            )
    return Metric(name=field_name, description="desc", unit="u", data=data)


def _scope_metrics(name: str, metrics: list[Metric]) -> ScopeMetrics:
    return ScopeMetrics(
        scope=InstrumentationScope(
            name=name, version="1.0", schema_url="scope_url"
        ),
        metrics=metrics,
        schema_url="scope_url",
    )


def _resource_metrics(
    index: int, scope_metrics_list: list[ScopeMetrics]
) -> ResourceMetrics:
    return ResourceMetrics(
        resource=Resource(
            attributes={"r": index}, schema_url=f"res_url_{index}"
        ),
        scope_metrics=scope_metrics_list,
        schema_url=f"res_url_{index}",
    )


def _data_point_field(data_point: JSONNumberDataPoint) -> int | float:
    return (
        data_point.as_int
        if data_point.as_int is not None
        else data_point.as_double
    )


def _all_values(request: JSONExportMetricsServiceRequest) -> list[int | float]:
    """Flatten every data point value in a request, in hierarchy order."""
    values = []
    for resource_metrics in request.resource_metrics:
        for scope_metrics in resource_metrics.scope_metrics:
            for metric in scope_metrics.metrics:
                field_name = _get_metric_data_field_name(metric)
                for dp in getattr(metric, field_name).data_points:
                    values.append(_data_point_field(dp))
    return values


def _count_data_points(request: JSONExportMetricsServiceRequest) -> int:
    return sum(
        len(getattr(metric, _get_metric_data_field_name(metric)).data_points)
        for resource_metrics in request.resource_metrics
        for scope_metrics in resource_metrics.scope_metrics
        for metric in scope_metrics.metrics
    )


class TestSplitMetricsData(unittest.TestCase):
    def test_get_metric_data_field_name(self):
        cases = {
            "gauge": make_gauge(),
            "sum": make_sum(),
            "histogram": make_histogram(),
            "exponential_histogram": make_exponential_histogram(),
        }
        for expected, metric in cases.items():
            with self.subTest(field_name=expected):
                encoded = _get_first_metric(
                    encode_metrics(make_metrics_data([metric]))
                )
                self.assertEqual(
                    _get_metric_data_field_name(encoded), expected
                )

    def test_get_metric_data_field_name_unsupported(self):
        with self.assertLogs(level=WARNING):
            encoded = _get_first_metric(
                encode_metrics(
                    make_metrics_data(
                        [
                            Metric(
                                name="x", description="d", unit="u", data=None
                            )
                        ]
                    )
                )
            )
        self.assertIsNone(_get_metric_data_field_name(encoded))

    def test_none_batch_size_yields_original_unchanged(self):
        request = encode_metrics(make_metrics_data([make_sum(value=1)]))
        batches = list(split_metrics_data(request, None))
        self.assertEqual(len(batches), 1)
        self.assertIs(batches[0], request)

    def test_split_single_metric_even(self):
        request = encode_metrics(
            make_metrics_data([_sum_metric("s", [0, 1, 2, 3])])
        )
        batches = list(split_metrics_data(request, 2))
        self.assertEqual(len(batches), 2)
        self.assertEqual([_all_values(b) for b in batches], [[0, 1], [2, 3]])

    def test_split_single_metric_uneven(self):
        request = encode_metrics(
            make_metrics_data([_sum_metric("s", [0, 1, 2, 3, 4])])
        )
        batches = list(split_metrics_data(request, 2))
        self.assertEqual(
            [_all_values(b) for b in batches], [[0, 1], [2, 3], [4]]
        )

    def test_split_batch_size_one(self):
        request = encode_metrics(
            make_metrics_data([_sum_metric("s", [7, 8, 9])])
        )
        batches = list(split_metrics_data(request, 1))
        self.assertEqual([_all_values(b) for b in batches], [[7], [8], [9]])

    def test_split_batch_larger_than_total(self):
        request = encode_metrics(
            make_metrics_data([_sum_metric("s", [0, 1, 2])])
        )
        batches = list(split_metrics_data(request, 100))
        self.assertEqual(len(batches), 1)
        self.assertEqual(_all_values(batches[0]), [0, 1, 2])

    def test_split_preserves_metric_metadata(self):
        request = encode_metrics(
            make_metrics_data([_sum_metric("s", [0, 1, 2, 3, 4])])
        )
        for batch in split_metrics_data(request, 2):
            metric = _get_first_metric(batch)
            self.assertEqual(metric.name, "s")
            self.assertEqual(metric.unit, "s")
            self.assertEqual(metric.description, "desc")
            self.assertIsNotNone(metric.sum)
            self.assertEqual(
                metric.sum.aggregation_temporality,
                AggregationTemporality.CUMULATIVE,
            )
            self.assertTrue(metric.sum.is_monotonic)

    def test_split_across_metrics_in_scope(self):
        request = encode_metrics(
            make_metrics_data(
                [_sum_metric("a", [0, 1]), _sum_metric("b", [2, 3])]
            )
        )
        batches = list(split_metrics_data(request, 3))
        self.assertEqual(len(batches), 2)

        first_metrics = batches[0].resource_metrics[0].scope_metrics[0].metrics
        self.assertEqual([m.name for m in first_metrics], ["a", "b"])
        self.assertEqual(_all_values(batches[0]), [0, 1, 2])

        second_metrics = (
            batches[1].resource_metrics[0].scope_metrics[0].metrics
        )
        self.assertEqual([m.name for m in second_metrics], ["b"])
        self.assertEqual(_all_values(batches[1]), [3])

    def test_split_across_scopes(self):
        request = encode_metrics(
            MetricsData(
                resource_metrics=[
                    _resource_metrics(
                        0,
                        [
                            _scope_metrics("s0", [_sum_metric("a", [0, 1])]),
                            _scope_metrics("s1", [_sum_metric("b", [2, 3])]),
                        ],
                    )
                ]
            )
        )
        batches = list(split_metrics_data(request, 3))
        self.assertEqual(len(batches), 2)

        self.assertEqual(len(batches[0].resource_metrics[0].scope_metrics), 2)
        self.assertEqual(_all_values(batches[0]), [0, 1, 2])

        self.assertEqual(len(batches[1].resource_metrics[0].scope_metrics), 1)
        self.assertEqual(
            batches[1].resource_metrics[0].scope_metrics[0].scope.name, "s1"
        )
        self.assertEqual(_all_values(batches[1]), [3])

    def test_split_across_resources(self):
        request = encode_metrics(
            MetricsData(
                resource_metrics=[
                    _resource_metrics(
                        0, [_scope_metrics("s0", [_sum_metric("a", [0, 1])])]
                    ),
                    _resource_metrics(
                        1, [_scope_metrics("s1", [_sum_metric("b", [2, 3])])]
                    ),
                ]
            )
        )
        batches = list(split_metrics_data(request, 3))
        self.assertEqual(len(batches), 2)
        self.assertEqual(len(batches[0].resource_metrics), 2)
        self.assertEqual(_all_values(batches[0]), [0, 1, 2])
        self.assertEqual(len(batches[1].resource_metrics), 1)
        self.assertEqual(_all_values(batches[1]), [3])

    def test_split_all_metric_types(self):
        for field_name in _METRIC_DATA_FIELDS:
            with self.subTest(field_name=field_name):
                request = encode_metrics(
                    make_metrics_data([_metric_of_type(field_name, 3)])
                )
                batches = list(split_metrics_data(request, 2))
                self.assertEqual(len(batches), 2)
                self.assertEqual(_count_data_points(batches[0]), 2)
                self.assertEqual(_count_data_points(batches[1]), 1)
                for batch in batches:
                    metric = _get_first_metric(batch)
                    self.assertEqual(
                        _get_metric_data_field_name(metric), field_name
                    )

    def test_split_preserves_all_data_points(self):
        request = encode_metrics(
            MetricsData(
                resource_metrics=[
                    _resource_metrics(
                        0,
                        [
                            _scope_metrics(
                                "s0",
                                [
                                    _sum_metric("a", [0, 1, 2]),
                                    _sum_metric("b", [3, 4]),
                                ],
                            ),
                            _scope_metrics(
                                "s1", [_sum_metric("c", [5, 6, 7])]
                            ),
                        ],
                    ),
                    _resource_metrics(
                        1, [_scope_metrics("s2", [_sum_metric("d", [8, 9])])]
                    ),
                ]
            )
        )
        expected = _all_values(request)
        self.assertEqual(expected, list(range(10)))
        for batch_size in (1, 2, 3, 4, 7, 1000):
            with self.subTest(batch_size=batch_size):
                batches = list(split_metrics_data(request, batch_size))
                flattened = [v for b in batches for v in _all_values(b)]
                self.assertEqual(flattened, expected)
                self.assertEqual(
                    sum(_count_data_points(b) for b in batches), len(expected)
                )
                for batch in batches:
                    self.assertLessEqual(_count_data_points(batch), batch_size)

    def test_split_skips_unsupported_metric(self):
        request = encode_metrics(
            make_metrics_data(
                [
                    _sum_metric("good", [0, 1]),
                    Metric(name="bad", description="d", unit="u", data=None),
                ]
            )
        )
        with self.assertLogs(level=WARNING) as log_ctx:
            batches = list(split_metrics_data(request, 5))
        self.assertTrue(
            any("unsupported metric type" in m for m in log_ctx.output)
        )
        self.assertEqual(len(batches), 1)
        self.assertEqual(_all_values(batches[0]), [0, 1])
        names = [
            m.name
            for b in batches
            for rm in b.resource_metrics
            for sm in rm.scope_metrics
            for m in sm.metrics
        ]
        self.assertEqual(names, ["good"])

    def test_split_empty_request(self):
        request = JSONExportMetricsServiceRequest(resource_metrics=[])
        self.assertEqual(list(split_metrics_data(request, 5)), [])

    def test_split_metric_with_no_data_points(self):
        metric = Metric(
            name="empty",
            description="d",
            unit="u",
            data=Sum(
                data_points=[],
                aggregation_temporality=AggregationTemporality.CUMULATIVE,
                is_monotonic=True,
            ),
        )
        request = encode_metrics(make_metrics_data([metric]))
        self.assertEqual(list(split_metrics_data(request, 5)), [])
