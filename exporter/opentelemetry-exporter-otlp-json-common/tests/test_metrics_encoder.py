# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint: disable=protected-access

import json
import unittest
from logging import WARNING

from opentelemetry.exporter.otlp.json.common.metrics_encoder import (
    encode_metrics,
)
from opentelemetry.proto_json.collector.metrics.v1.metrics_service import (
    ExportMetricsServiceRequest as JSONExportMetricsServiceRequest,
)
from opentelemetry.sdk.metrics import Exemplar
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
from tests import assert_proto_json_equal

_TIME = 1641946016139533244
_START_TIME = 1641946015139533244
_SPAN_ID = int("6e0c63257de34c92", 16)
_TRACE_ID = int("d4cda95b652f4a1592b449d5929fda1b", 16)


def _make_metrics_data(
    metrics,
    resource_attrs=None,
    resource_schema_url=None,
    scope_name="test_scope",
    scope_version="1.0",
    scope_schema_url=None,
):
    return MetricsData(
        resource_metrics=[
            ResourceMetrics(
                resource=Resource(
                    attributes=resource_attrs or {},
                    schema_url=resource_schema_url,
                ),
                scope_metrics=[
                    ScopeMetrics(
                        scope=InstrumentationScope(
                            name=scope_name,
                            version=scope_version,
                            schema_url=scope_schema_url,
                        ),
                        metrics=metrics,
                        schema_url=scope_schema_url,
                    )
                ],
                schema_url=resource_schema_url,
            )
        ]
    )


def _get_first_metric(result):
    return result.resource_metrics[0].scope_metrics[0].metrics[0]


def _make_sum(
    name="test_sum",
    value=33,
    attributes=None,
    temporality=AggregationTemporality.CUMULATIVE,
    is_monotonic=True,
    description="desc",
    unit="s",
):
    return Metric(
        name=name,
        description=description,
        unit=unit,
        data=Sum(
            data_points=[
                NumberDataPoint(
                    attributes=attributes or {"a": 1},
                    start_time_unix_nano=_START_TIME,
                    time_unix_nano=_TIME,
                    value=value,
                )
            ],
            aggregation_temporality=temporality,
            is_monotonic=is_monotonic,
        ),
    )


def _make_gauge(
    name="test_gauge",
    value=9000,
    attributes=None,
    description="desc",
    unit="1",
):
    return Metric(
        name=name,
        description=description,
        unit=unit,
        data=Gauge(
            data_points=[
                NumberDataPoint(
                    attributes=attributes or {"a": 1},
                    start_time_unix_nano=None,
                    time_unix_nano=_TIME,
                    value=value,
                )
            ],
        ),
    )


def _make_histogram(
    name="test_histogram",
    attributes=None,
    count=5,
    sum_value=67,
    bucket_counts=None,
    explicit_bounds=None,
    min_value=8,
    max_value=18,
    exemplars=None,
    temporality=AggregationTemporality.DELTA,
    description="desc",
    unit="ms",
):
    return Metric(
        name=name,
        description=description,
        unit=unit,
        data=Histogram(
            data_points=[
                HistogramDataPoint(
                    attributes=attributes or {"a": 1},
                    start_time_unix_nano=_START_TIME,
                    time_unix_nano=_TIME,
                    count=count,
                    sum=sum_value,
                    bucket_counts=bucket_counts or [1, 4],
                    explicit_bounds=explicit_bounds or [10.0, 20.0],
                    min=min_value,
                    max=max_value,
                    exemplars=exemplars or [],
                )
            ],
            aggregation_temporality=temporality,
        ),
    )


def _make_exponential_histogram(
    name="test_exp_hist",
    attributes=None,
    count=10,
    sum_value=100.5,
    scale=1,
    zero_count=2,
    positive=None,
    negative=None,
    flags=0,
    min_value=1.0,
    max_value=50.0,
    exemplars=None,
    temporality=AggregationTemporality.CUMULATIVE,
    description="desc",
    unit="s",
):
    return Metric(
        name=name,
        description=description,
        unit=unit,
        data=ExponentialHistogram(
            data_points=[
                ExponentialHistogramDataPoint(
                    attributes=attributes or {"a": 1},
                    start_time_unix_nano=_START_TIME,
                    time_unix_nano=_TIME,
                    count=count,
                    sum=sum_value,
                    scale=scale,
                    zero_count=zero_count,
                    positive=positive
                    or Buckets(offset=0, bucket_counts=[1, 2, 3]),
                    negative=negative or Buckets(offset=1, bucket_counts=[1]),
                    flags=flags,
                    min=min_value,
                    max=max_value,
                    exemplars=exemplars or [],
                )
            ],
            aggregation_temporality=temporality,
        ),
    )


class TestOTLPMetricsEncoder(unittest.TestCase):
    def test_encode_sum(self):
        cases = [
            ("int_value", 33, True),
            ("double_value", 2.98, False),
        ]
        for name, value, is_int in cases:
            with self.subTest(name=name):
                result = encode_metrics(
                    _make_metrics_data([_make_sum(value=value)])
                )
                encoded = _get_first_metric(result)

                self.assertIsNotNone(encoded.sum)
                self.assertIsNone(encoded.gauge)
                self.assertEqual(
                    encoded.sum.aggregation_temporality,
                    AggregationTemporality.CUMULATIVE,
                )
                self.assertTrue(encoded.sum.is_monotonic)

                dp = encoded.sum.data_points[0]
                self.assertEqual(dp.start_time_unix_nano, _START_TIME)
                self.assertEqual(dp.time_unix_nano, _TIME)
                if is_int:
                    self.assertEqual(dp.as_int, value)
                    self.assertIsNone(dp.as_double)
                else:
                    self.assertEqual(dp.as_double, value)
                    self.assertIsNone(dp.as_int)

    def test_encode_gauge(self):
        cases = [
            ("int_value", 9000, True),
            ("double_value", 52.028, False),
        ]
        for name, value, is_int in cases:
            with self.subTest(name=name):
                result = encode_metrics(
                    _make_metrics_data([_make_gauge(value=value)])
                )
                encoded = _get_first_metric(result)

                self.assertIsNotNone(encoded.gauge)
                self.assertIsNone(encoded.sum)

                dp = encoded.gauge.data_points[0]
                self.assertEqual(dp.time_unix_nano, _TIME)
                if is_int:
                    self.assertEqual(dp.as_int, value)
                else:
                    self.assertEqual(dp.as_double, value)

    def test_encode_histogram(self):
        metric = _make_histogram(
            exemplars=[
                Exemplar(
                    {"filtered": "banana"}, 298.0, _TIME, _SPAN_ID, _TRACE_ID
                ),
            ],
        )
        result = encode_metrics(_make_metrics_data([metric]))
        encoded = _get_first_metric(result)

        self.assertIsNotNone(encoded.histogram)
        self.assertEqual(
            encoded.histogram.aggregation_temporality,
            AggregationTemporality.DELTA,
        )

        dp = encoded.histogram.data_points[0]
        self.assertEqual(dp.count, 5)
        self.assertEqual(dp.sum, 67)
        self.assertEqual(dp.bucket_counts, [1, 4])
        self.assertEqual(dp.explicit_bounds, [10.0, 20.0])
        self.assertEqual(dp.min, 8)
        self.assertEqual(dp.max, 18)
        self.assertEqual(len(dp.exemplars), 1)

    def test_encode_exponential_histogram(self):
        result = encode_metrics(
            _make_metrics_data([_make_exponential_histogram()])
        )
        encoded = _get_first_metric(result)

        self.assertIsNotNone(encoded.exponential_histogram)
        dp = encoded.exponential_histogram.data_points[0]
        self.assertEqual(dp.count, 10)
        self.assertEqual(dp.sum, 100.5)
        self.assertEqual(dp.scale, 1)
        self.assertEqual(dp.zero_count, 2)
        self.assertIsNotNone(dp.positive)
        self.assertEqual(dp.positive.offset, 0)
        self.assertEqual(dp.positive.bucket_counts, [1, 2, 3])
        self.assertIsNotNone(dp.negative)
        self.assertEqual(dp.negative.offset, 1)
        self.assertEqual(dp.negative.bucket_counts, [1])

    def test_encode_exponential_histogram_empty_buckets(self):
        metric = _make_exponential_histogram(
            attributes={},
            count=0,
            sum_value=0.0,
            zero_count=0,
            positive=Buckets(offset=0, bucket_counts=[]),
            negative=Buckets(offset=0, bucket_counts=[]),
            min_value=0.0,
            max_value=0.0,
        )
        result = encode_metrics(_make_metrics_data([metric]))
        dp = _get_first_metric(result).exponential_histogram.data_points[0]
        self.assertIsNone(dp.positive)
        self.assertIsNone(dp.negative)

    def test_encode_exemplars(self):
        cases = [
            (
                "float_with_ids",
                Exemplar({"f": "banana"}, 298.0, _TIME, _SPAN_ID, _TRACE_ID),
                True,
                True,
            ),
            (
                "float_without_ids",
                Exemplar({"f": "banana"}, 298.0, _TIME, None, None),
                False,
                True,
            ),
            (
                "int_with_ids",
                Exemplar({"f": "banana"}, 42, _TIME, _SPAN_ID, _TRACE_ID),
                True,
                False,
            ),
        ]
        for name, exemplar, has_ids, is_float in cases:
            with self.subTest(name=name):
                metric = _make_histogram(
                    attributes={},
                    count=1,
                    sum_value=exemplar.value,
                    bucket_counts=[1],
                    explicit_bounds=[],
                    min_value=exemplar.value,
                    max_value=exemplar.value,
                    exemplars=[exemplar],
                )
                result = encode_metrics(_make_metrics_data([metric]))
                enc_ex = (
                    _get_first_metric(result)
                    .histogram.data_points[0]
                    .exemplars[0]
                )
                if has_ids:
                    self.assertTrue(enc_ex.span_id)
                    self.assertTrue(enc_ex.trace_id)
                else:
                    self.assertFalse(enc_ex.span_id)
                    self.assertFalse(enc_ex.trace_id)
                if is_float:
                    self.assertEqual(enc_ex.as_double, exemplar.value)
                else:
                    self.assertEqual(enc_ex.as_int, exemplar.value)

    def test_encode_metrics_resource_and_scope(self):
        result = encode_metrics(
            _make_metrics_data(
                [_make_gauge(value=1, attributes={})],
                resource_attrs={"service.name": "test-svc"},
                resource_schema_url="res_schema",
                scope_name="my_lib",
                scope_version="2.0",
                scope_schema_url="scope_schema",
            )
        )
        rm = result.resource_metrics[0]
        self.assertEqual(rm.schema_url, "res_schema")
        self.assertEqual(rm.resource.attributes[0].key, "service.name")

        sm = rm.scope_metrics[0]
        self.assertEqual(sm.schema_url, "scope_schema")
        self.assertEqual(sm.scope.name, "my_lib")
        self.assertEqual(sm.scope.version, "2.0")

    def test_encode_metrics_to_dict(self):
        result = encode_metrics(
            _make_metrics_data([_make_sum(name="sum_int", value=33)])
        )
        result_dict = result.to_dict()

        self.assertIn("resourceMetrics", result_dict)
        rm = result_dict["resourceMetrics"][0]
        self.assertIn("scopeMetrics", rm)

        dp = rm["scopeMetrics"][0]["metrics"][0]["sum"]["dataPoints"][0]
        # int64 fields are string-encoded
        self.assertIsInstance(dp["startTimeUnixNano"], str)
        self.assertIsInstance(dp["timeUnixNano"], str)
        self.assertIsInstance(dp["asInt"], str)
        self.assertEqual(dp["asInt"], "33")

    def test_encode_metrics_json_roundtrip(self):
        metrics = [
            _make_sum(name="s", value=33),
            _make_gauge(name="g", value=52.028),
            _make_histogram(
                name="h",
                exemplars=[
                    Exemplar({"f": "b"}, 298.0, _TIME, _SPAN_ID, _TRACE_ID),
                ],
            ),
            _make_exponential_histogram(name="eh"),
        ]
        result = encode_metrics(_make_metrics_data(metrics))
        json_str = result.to_json()
        roundtripped = JSONExportMetricsServiceRequest.from_dict(
            json.loads(json_str)
        )
        assert_proto_json_equal(self, result, roundtripped)

    def test_unsupported_metric_type(self):
        metric = Metric(
            name="unsupported",
            description="foo",
            unit="s",
            data=None,
        )
        with self.assertLogs(level=WARNING):
            result = encode_metrics(_make_metrics_data([metric]))
        encoded = _get_first_metric(result)
        self.assertEqual(encoded.name, "unsupported")
        self.assertIsNone(encoded.gauge)
        self.assertIsNone(encoded.sum)
        self.assertIsNone(encoded.histogram)
        self.assertIsNone(encoded.exponential_histogram)
