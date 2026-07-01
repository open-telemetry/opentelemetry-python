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
    assert_proto_json_equal,
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


def _metric_of_type(
    field_name: str, values: list[int], name: str | None = None
) -> Metric:
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
    return Metric(
        name=name or field_name, description="desc", unit="u", data=data
    )


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


def _data_point_value(data_point: JSONNumberDataPoint) -> int | float:
    return (
        data_point.as_int
        if data_point.as_int is not None
        else data_point.as_double
    )


def _data_point_values(
    request: JSONExportMetricsServiceRequest,
) -> list[int | float]:
    values = []
    for resource_metrics in request.resource_metrics:
        for scope_metrics in resource_metrics.scope_metrics:
            for metric in scope_metrics.metrics:
                field_name = _get_metric_data_field_name(metric)
                for dp in getattr(metric, field_name).data_points:
                    values.append(_data_point_value(dp))
    return values


def _count_data_points(request: JSONExportMetricsServiceRequest) -> int:
    return sum(
        len(getattr(metric, _get_metric_data_field_name(metric)).data_points)
        for resource_metrics in request.resource_metrics
        for scope_metrics in resource_metrics.scope_metrics
        for metric in scope_metrics.metrics
    )


def _flatten_with_context(
    request: JSONExportMetricsServiceRequest,
) -> dict[int, dict]:
    context = {}
    for resource_metrics in request.resource_metrics:
        for scope_metrics in resource_metrics.scope_metrics:
            for metric in scope_metrics.metrics:
                field_name = _get_metric_data_field_name(metric)
                for dp in getattr(metric, field_name).data_points:
                    context[id(dp)] = {
                        "data_point": dp,
                        "resource": resource_metrics.resource,
                        "resource_schema_url": resource_metrics.schema_url,
                        "scope": scope_metrics.scope,
                        "scope_schema_url": scope_metrics.schema_url,
                        "metric_name": metric.name,
                        "metric_unit": metric.unit,
                        "metric_description": metric.description,
                        "field_name": field_name,
                    }
    return context


def _assert_no_empty_metrics(
    batch: JSONExportMetricsServiceRequest,
) -> None:
    for resource_metrics in batch.resource_metrics:
        assert resource_metrics.scope_metrics, "empty scope_metrics list"
        for scope_metrics in resource_metrics.scope_metrics:
            assert scope_metrics.metrics, "empty metrics list"
            for metric in scope_metrics.metrics:
                field_name = _get_metric_data_field_name(metric)
                data_points = getattr(metric, field_name).data_points
                assert data_points, (
                    f"metric {metric.name!r} has no data points"
                )


class TestSplitMetricsData(unittest.TestCase):
    def test_none_batch_size_yields_original(self):
        request = encode_metrics(make_metrics_data([make_sum(value=1)]))
        batches = list(split_metrics_data(request, None))
        self.assertEqual(len(batches), 1)
        self.assertIs(batches[0], request)

    def test_split_batch_sizes(self):
        cases = [
            ("even", [0, 1, 2, 3], 2, [[0, 1], [2, 3]]),
            ("uneven", [0, 1, 2, 3, 4], 2, [[0, 1], [2, 3], [4]]),
            ("batch_size_one", [7, 8, 9], 1, [[7], [8], [9]]),
            ("batch_larger_than_total", [0, 1, 2], 100, [[0, 1, 2]]),
        ]
        for label, values, batch_size, expected_batches in cases:
            with self.subTest(case=label):
                request = encode_metrics(
                    make_metrics_data([_metric_of_type("sum", values, "s")])
                )
                batches = list(split_metrics_data(request, batch_size))
                self.assertEqual(len(batches), len(expected_batches))
                self.assertEqual(
                    [_data_point_values(b) for b in batches],
                    expected_batches,
                )

    def test_split_preserves_metadata(self):
        request = encode_metrics(
            make_metrics_data([_metric_of_type("sum", [0, 1, 2, 3, 4], "s")])
        )
        for batch in split_metrics_data(request, 2):
            metric = _get_first_metric(batch)
            self.assertEqual(metric.name, "s")
            self.assertEqual(metric.unit, "u")
            self.assertEqual(metric.description, "desc")
            self.assertIsNotNone(metric.sum)
            self.assertEqual(
                metric.sum.aggregation_temporality,
                AggregationTemporality.CUMULATIVE,
            )
            self.assertTrue(metric.sum.is_monotonic)

    def test_split_with_empty_metric(self):
        empty_metric = Metric(
            name="empty",
            description="d",
            unit="u",
            data=Sum(
                data_points=[],
                aggregation_temporality=AggregationTemporality.CUMULATIVE,
                is_monotonic=True,
            ),
        )
        request = encode_metrics(
            make_metrics_data(
                [
                    _metric_of_type("sum", [0, 1], "a"),
                    empty_metric,
                    _metric_of_type("sum", [2, 3], "b"),
                ]
            )
        )
        batches = list(split_metrics_data(request, 100))
        self.assertEqual(len(batches), 1)
        _assert_no_empty_metrics(batches[0])
        names = [
            m.name
            for rm in batches[0].resource_metrics
            for sm in rm.scope_metrics
            for m in sm.metrics
        ]
        self.assertEqual(names, ["a", "b"])
        self.assertEqual(_data_point_values(batches[0]), [0, 1, 2, 3])

    def test_split_across_metrics(self):
        request = encode_metrics(
            make_metrics_data(
                [
                    _metric_of_type("sum", [0, 1], "a"),
                    _metric_of_type("sum", [2, 3], "b"),
                ]
            )
        )
        batches = list(split_metrics_data(request, 3))
        self.assertEqual(len(batches), 2)

        first_metrics = batches[0].resource_metrics[0].scope_metrics[0].metrics
        self.assertEqual([m.name for m in first_metrics], ["a", "b"])
        self.assertEqual(_data_point_values(batches[0]), [0, 1, 2])

        second_metrics = (
            batches[1].resource_metrics[0].scope_metrics[0].metrics
        )
        self.assertEqual([m.name for m in second_metrics], ["b"])
        self.assertEqual(_data_point_values(batches[1]), [3])

    def test_split_across_scopes(self):
        request = encode_metrics(
            MetricsData(
                resource_metrics=[
                    _resource_metrics(
                        0,
                        [
                            _scope_metrics(
                                "s0",
                                [_metric_of_type("sum", [0, 1], "a")],
                            ),
                            _scope_metrics(
                                "s1",
                                [_metric_of_type("sum", [2, 3], "b")],
                            ),
                        ],
                    )
                ]
            )
        )
        batches = list(split_metrics_data(request, 3))
        self.assertEqual(len(batches), 2)

        self.assertEqual(len(batches[0].resource_metrics[0].scope_metrics), 2)
        self.assertEqual(_data_point_values(batches[0]), [0, 1, 2])

        self.assertEqual(len(batches[1].resource_metrics[0].scope_metrics), 1)
        self.assertEqual(
            batches[1].resource_metrics[0].scope_metrics[0].scope.name, "s1"
        )
        self.assertEqual(_data_point_values(batches[1]), [3])

    def test_split_across_resources(self):
        request = encode_metrics(
            MetricsData(
                resource_metrics=[
                    _resource_metrics(
                        0,
                        [
                            _scope_metrics(
                                "s0",
                                [_metric_of_type("sum", [0, 1], "a")],
                            )
                        ],
                    ),
                    _resource_metrics(
                        1,
                        [
                            _scope_metrics(
                                "s1",
                                [_metric_of_type("sum", [2, 3], "b")],
                            )
                        ],
                    ),
                ]
            )
        )
        batches = list(split_metrics_data(request, 3))
        self.assertEqual(len(batches), 2)
        self.assertEqual(len(batches[0].resource_metrics), 2)
        self.assertEqual(_data_point_values(batches[0]), [0, 1, 2])
        self.assertEqual(len(batches[1].resource_metrics), 1)
        self.assertEqual(_data_point_values(batches[1]), [3])

    def test_split_all_metric_types(self):
        for field_name in _METRIC_DATA_FIELDS:
            # Exclude "summary" metrics (not generated by the SDK)
            if field_name == "summary":
                continue
            with self.subTest(field_name=field_name):
                request = encode_metrics(
                    make_metrics_data([_metric_of_type(field_name, [1, 2, 3])])
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

    def test_split_preserves_data_points(self):
        request = encode_metrics(
            MetricsData(
                resource_metrics=[
                    _resource_metrics(
                        0,
                        [
                            _scope_metrics(
                                "s0",
                                [
                                    _metric_of_type("sum", [0, 1, 2], "a"),
                                    _metric_of_type("sum", [3, 4], "b"),
                                ],
                            ),
                            _scope_metrics(
                                "s1",
                                [_metric_of_type("sum", [5, 6, 7], "c")],
                            ),
                        ],
                    ),
                    _resource_metrics(
                        1,
                        [
                            _scope_metrics(
                                "s2",
                                [_metric_of_type("sum", [8, 9], "d")],
                            )
                        ],
                    ),
                ]
            )
        )
        expected = _data_point_values(request)
        self.assertEqual(expected, list(range(10)))
        for batch_size in (1, 2, 3, 4, 7, 1000):
            with self.subTest(batch_size=batch_size):
                batches = list(split_metrics_data(request, batch_size))
                flattened = [v for b in batches for v in _data_point_values(b)]
                self.assertEqual(flattened, expected)
                self.assertEqual(
                    sum(_count_data_points(b) for b in batches), len(expected)
                )
                for batch in batches:
                    self.assertLessEqual(_count_data_points(batch), batch_size)
                    _assert_no_empty_metrics(batch)

    def test_split_preserves_hierarchy_and_attributes(self):
        cases = [
            (
                "single_metric",
                encode_metrics(
                    make_metrics_data(
                        [_metric_of_type("sum", [0, 1, 2, 3, 4], "only")]
                    )
                ),
                5,
            ),
            (
                "multi_scope_same_resource",
                encode_metrics(
                    MetricsData(
                        resource_metrics=[
                            _resource_metrics(
                                0,
                                [
                                    _scope_metrics(
                                        "s0",
                                        [_metric_of_type("gauge", [1, 2, 3])],
                                    ),
                                    _scope_metrics(
                                        "s1",
                                        [_metric_of_type("histogram", [1, 2])],
                                    ),
                                ],
                            )
                        ]
                    )
                ),
                5,
            ),
            (
                "multi_resource_mixed_types",
                encode_metrics(
                    MetricsData(
                        resource_metrics=[
                            _resource_metrics(
                                0,
                                [
                                    _scope_metrics(
                                        "s0",
                                        [
                                            _metric_of_type(
                                                "sum", [0, 1, 2], "a"
                                            ),
                                            _metric_of_type(
                                                "histogram", [1, 2]
                                            ),
                                        ],
                                    ),
                                    _scope_metrics(
                                        "s1",
                                        [_metric_of_type("gauge", [1, 2, 3])],
                                    ),
                                ],
                            ),
                            _resource_metrics(
                                1,
                                [
                                    _scope_metrics(
                                        "s2",
                                        [
                                            _metric_of_type(
                                                "exponential_histogram",
                                                [1, 2],
                                            )
                                        ],
                                    )
                                ],
                            ),
                        ]
                    )
                ),
                10,
            ),
            (
                "empty_metric_interspersed",
                encode_metrics(
                    make_metrics_data(
                        [
                            _metric_of_type("sum", [0, 1], "a"),
                            Metric(
                                name="empty",
                                description="d",
                                unit="u",
                                data=Sum(
                                    data_points=[],
                                    aggregation_temporality=(
                                        AggregationTemporality.CUMULATIVE
                                    ),
                                    is_monotonic=True,
                                ),
                            ),
                            _metric_of_type("sum", [2, 3], "b"),
                        ]
                    )
                ),
                4,
            ),
        ]

        for label, request, expected_count in cases:
            with self.subTest(case=label):
                ground_truth = _flatten_with_context(request)
                self.assertEqual(len(ground_truth), expected_count)

                for batch_size in (1, 2, 3, 4, 7, 1000):
                    with self.subTest(case=label, batch_size=batch_size):
                        seen: dict[int, dict] = {}
                        for batch in split_metrics_data(request, batch_size):
                            _assert_no_empty_metrics(batch)
                            batch_context = _flatten_with_context(batch)
                            for dp_id in batch_context:
                                self.assertNotIn(
                                    dp_id,
                                    seen,
                                    "data point yielded in more than one batch",
                                )
                            seen.update(batch_context)

                        self.assertEqual(set(seen), set(ground_truth))
                        for dp_id, ctx in seen.items():
                            expected = ground_truth[dp_id]
                            self.assertIs(
                                ctx["data_point"], expected["data_point"]
                            )
                            assert_proto_json_equal(
                                self, ctx["resource"], expected["resource"]
                            )
                            self.assertEqual(
                                ctx["resource_schema_url"],
                                expected["resource_schema_url"],
                            )
                            assert_proto_json_equal(
                                self, ctx["scope"], expected["scope"]
                            )
                            self.assertEqual(
                                ctx["scope_schema_url"],
                                expected["scope_schema_url"],
                            )
                            self.assertEqual(
                                ctx["metric_name"], expected["metric_name"]
                            )
                            self.assertEqual(
                                ctx["metric_unit"], expected["metric_unit"]
                            )
                            self.assertEqual(
                                ctx["metric_description"],
                                expected["metric_description"],
                            )
                            self.assertEqual(
                                ctx["field_name"], expected["field_name"]
                            )

    def test_split_skips_unsupported_metric(self):
        request = encode_metrics(
            make_metrics_data(
                [
                    _metric_of_type("sum", [0, 1], "good"),
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
        self.assertEqual(_data_point_values(batches[0]), [0, 1])
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

    def test_split_with_no_data_points(self):
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
