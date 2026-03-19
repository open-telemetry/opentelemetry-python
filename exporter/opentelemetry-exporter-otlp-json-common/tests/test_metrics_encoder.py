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
    Metric,
)

from tests import (
    SPAN_ID,
    TIME,
    TRACE_ID,
    assert_proto_json_equal,
    make_exponential_histogram,
    make_gauge,
    make_histogram,
    make_metrics_data,
    make_sum,
)


def _get_first_metric(result):
    return result.resource_metrics[0].scope_metrics[0].metrics[0]


class TestOTLPMetricsEncoder(unittest.TestCase):
    def test_encode_sum(self):
        cases = [
            ("int_value", 33, True),
            ("double_value", 2.98, False),
        ]
        for name, value, is_int in cases:
            with self.subTest(name=name):
                result = encode_metrics(
                    make_metrics_data([make_sum(value=value)])
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
                self.assertIsNotNone(dp.start_time_unix_nano)
                self.assertIsNotNone(dp.time_unix_nano)
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
                    make_metrics_data([make_gauge(value=value)])
                )
                encoded = _get_first_metric(result)

                self.assertIsNotNone(encoded.gauge)
                self.assertIsNone(encoded.sum)

                dp = encoded.gauge.data_points[0]
                self.assertIsNotNone(dp.time_unix_nano)
                if is_int:
                    self.assertEqual(dp.as_int, value)
                else:
                    self.assertEqual(dp.as_double, value)

    def test_encode_histogram(self):
        metric = make_histogram(
            exemplars=[
                Exemplar(
                    {"filtered": "banana"}, 298.0, TIME, SPAN_ID, TRACE_ID
                ),
            ],
        )
        result = encode_metrics(make_metrics_data([metric]))
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
            make_metrics_data([make_exponential_histogram()])
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
        metric = make_exponential_histogram(
            attributes={},
            count=0,
            sum_value=0.0,
            zero_count=0,
            positive=Buckets(offset=0, bucket_counts=[]),
            negative=Buckets(offset=0, bucket_counts=[]),
            min_value=0.0,
            max_value=0.0,
        )
        result = encode_metrics(make_metrics_data([metric]))
        dp = _get_first_metric(result).exponential_histogram.data_points[0]
        self.assertIsNone(dp.positive)
        self.assertIsNone(dp.negative)

    def test_encode_exemplars(self):
        cases = [
            (
                "float_with_ids",
                Exemplar({"f": "banana"}, 298.0, TIME, SPAN_ID, TRACE_ID),
                True,
                True,
            ),
            (
                "float_without_ids",
                Exemplar({"f": "banana"}, 298.0, TIME, None, None),
                False,
                True,
            ),
            (
                "int_with_ids",
                Exemplar({"f": "banana"}, 42, TIME, SPAN_ID, TRACE_ID),
                True,
                False,
            ),
        ]
        for name, exemplar, has_ids, is_float in cases:
            with self.subTest(name=name):
                metric = make_histogram(
                    attributes={},
                    count=1,
                    sum_value=exemplar.value,
                    bucket_counts=[1],
                    explicit_bounds=[],
                    min_value=exemplar.value,
                    max_value=exemplar.value,
                    exemplars=[exemplar],
                )
                result = encode_metrics(make_metrics_data([metric]))
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
            make_metrics_data(
                [make_gauge(value=1, attributes={})],
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
            make_metrics_data([make_sum(name="sum_int", value=33)])
        )
        result_dict = result.to_dict()

        self.assertIn("resourceMetrics", result_dict)
        rm = result_dict["resourceMetrics"][0]
        self.assertIn("scopeMetrics", rm)

        dp = rm["scopeMetrics"][0]["metrics"][0]["sum"]["dataPoints"][0]
        self.assertIsInstance(dp["startTimeUnixNano"], str)
        self.assertIsInstance(dp["timeUnixNano"], str)
        self.assertIsInstance(dp["asInt"], str)
        self.assertEqual(dp["asInt"], "33")

    def test_encode_metrics_json_roundtrip(self):
        metrics = [
            make_sum(name="s", value=33),
            make_gauge(name="g", value=52.028),
            make_histogram(
                name="h",
                exemplars=[
                    Exemplar({"f": "b"}, 298.0, TIME, SPAN_ID, TRACE_ID),
                ],
            ),
            make_exponential_histogram(name="eh"),
        ]
        result = encode_metrics(make_metrics_data(metrics))
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
            result = encode_metrics(make_metrics_data([metric]))
        encoded = _get_first_metric(result)
        self.assertEqual(encoded.name, "unsupported")
        self.assertIsNone(encoded.gauge)
        self.assertIsNone(encoded.sum)
        self.assertIsNone(encoded.histogram)
        self.assertIsNone(encoded.exponential_histogram)
