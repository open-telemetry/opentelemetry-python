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


from unittest import TestCase
from math import inf

from opentelemetry.sdk.metrics.aggregation import (
    NoneAggregation,
    SumAggregation,
    LastValueAggregation,
    ExplicitBucketHistogramAggregation
)
from opentelemetry.proto.metrics.v1.metrics_pb2 import (
    AGGREGATION_TEMPORALITY_CUMULATIVE,
    AGGREGATION_TEMPORALITY_DELTA
)


class TestNoneAggregation(TestCase):

    def test_aggregate(self):
        """
        `NoneAggregation` drops all measurements.
        """

        none_aggregation = NoneAggregation()

        none_aggregation.aggregate(1)
        none_aggregation.aggregate(2)
        none_aggregation.aggregate(3)

        self.assertIs(none_aggregation.value, 0)


class TestSumAggregation(TestCase):

    def test_default_temporality(self):
        """
        `SumAggregation` default temporality is
        `AGGREGATION_TEMPORALITY_CUMULATIVE`.
        """

        sum_aggregation = SumAggregation()
        self.assertEqual(
            sum_aggregation._temporality,
            AGGREGATION_TEMPORALITY_CUMULATIVE
        )
        sum_aggregation = SumAggregation(
            temporality=AGGREGATION_TEMPORALITY_DELTA
        )
        self.assertEqual(
            sum_aggregation._temporality,
            AGGREGATION_TEMPORALITY_DELTA
        )

    def test_aggregate(self):
        """
        `SumAggregation` collects data for sum metric points
        """

        sum_aggregation = SumAggregation()

        sum_aggregation.aggregate(1)
        sum_aggregation.aggregate(2)
        sum_aggregation.aggregate(3)

        self.assertEqual(sum_aggregation.value, 6)

    def test_delta_temporality(self):
        """
        `SumAggregation` supports delta temporality
        """

        sum_aggregation = SumAggregation(AGGREGATION_TEMPORALITY_DELTA)

        sum_aggregation.aggregate(1)
        sum_aggregation.aggregate(2)
        sum_aggregation.aggregate(3)

        self.assertEqual(sum_aggregation.value, 6)
        self.assertEqual(sum_aggregation.collect(), 6)
        self.assertEqual(sum_aggregation.value, 0)

        sum_aggregation.aggregate(1)
        sum_aggregation.aggregate(2)
        sum_aggregation.aggregate(3)

        self.assertEqual(sum_aggregation.value, 6)
        self.assertEqual(sum_aggregation.collect(), 6)
        self.assertEqual(sum_aggregation.value, 0)

    def test_cumulative_temporality(self):
        """
        `SumAggregation` supports cumulative temporality
        """

        sum_aggregation = SumAggregation(AGGREGATION_TEMPORALITY_CUMULATIVE)

        sum_aggregation.aggregate(1)
        sum_aggregation.aggregate(2)
        sum_aggregation.aggregate(3)

        self.assertEqual(sum_aggregation.value, 6)
        self.assertEqual(sum_aggregation.collect(), 6)
        self.assertEqual(sum_aggregation.value, 6)

        sum_aggregation.aggregate(1)
        sum_aggregation.aggregate(2)
        sum_aggregation.aggregate(3)

        self.assertEqual(sum_aggregation.value, 12)
        self.assertEqual(sum_aggregation.collect(), 12)
        self.assertEqual(sum_aggregation.value, 12)


class TestLastValueAggregation(TestCase):

    def test_aggregate(self):
        """
        `LastValueAggregation` collects data for gauge metric points with delta
        temporality
        """

        last_value_aggregation = LastValueAggregation()

        last_value_aggregation.aggregate(1)
        self.assertEqual(last_value_aggregation.value, 1)

        last_value_aggregation.aggregate(2)
        self.assertEqual(last_value_aggregation.value, 2)

        last_value_aggregation.aggregate(3)
        self.assertEqual(last_value_aggregation.value, 3)


class TestExplicitBucketHistogramAggregation(TestCase):

    def test_default_temporality(self):
        """
        `ExplicitBucketHistogramAggregation` default temporality is
        `AGGREGATION_TEMPORALITY_CUMULATIVE`.
        """

        explicit_bucket_histogram_aggregation = ExplicitBucketHistogramAggregation()
        self.assertEqual(
            explicit_bucket_histogram_aggregation._temporality,
            AGGREGATION_TEMPORALITY_CUMULATIVE
        )
        explicit_bucket_histogram_aggregation = ExplicitBucketHistogramAggregation(
            temporality=AGGREGATION_TEMPORALITY_DELTA
        )
        self.assertEqual(
            explicit_bucket_histogram_aggregation._temporality,
            AGGREGATION_TEMPORALITY_DELTA
        )

    def test_aggregate(self):
        """
        `ExplicitBucketHistogramAggregation` collects data for explicit_bucket_histogram metric points
        """

        explicit_bucket_histogram_aggregation = ExplicitBucketHistogramAggregation()

        explicit_bucket_histogram_aggregation.aggregate(-1)
        explicit_bucket_histogram_aggregation.aggregate(2)
        explicit_bucket_histogram_aggregation.aggregate(7)
        explicit_bucket_histogram_aggregation.aggregate(8)
        explicit_bucket_histogram_aggregation.aggregate(9999)

        self.assertEqual(explicit_bucket_histogram_aggregation.value[0], -1)
        self.assertEqual(explicit_bucket_histogram_aggregation.value[5], 2)
        self.assertEqual(explicit_bucket_histogram_aggregation.value[10], 15)
        self.assertEqual(
            explicit_bucket_histogram_aggregation.value[inf], 9999
        )

    def test_delta_temporality(self):
        """
        `ExplicitBucketHistogramAggregation` supports delta temporality
        """

        explicit_bucket_histogram_aggregation = ExplicitBucketHistogramAggregation(AGGREGATION_TEMPORALITY_DELTA)

        explicit_bucket_histogram_aggregation.aggregate(-1)
        explicit_bucket_histogram_aggregation.aggregate(2)
        explicit_bucket_histogram_aggregation.aggregate(7)
        explicit_bucket_histogram_aggregation.aggregate(8)
        explicit_bucket_histogram_aggregation.aggregate(9999)

        result = explicit_bucket_histogram_aggregation.collect()

        self.assertEqual(result[0], -1)
        self.assertEqual(result[5], 2)
        self.assertEqual(result[10], 15)
        self.assertEqual(result[inf], 9999)

        self.assertEqual(explicit_bucket_histogram_aggregation.value[0], 0)
        self.assertEqual(explicit_bucket_histogram_aggregation.value[5], 0)
        self.assertEqual(explicit_bucket_histogram_aggregation.value[10], 0)
        self.assertEqual(
            explicit_bucket_histogram_aggregation.value[inf], 0
        )

    def test_cumulative_temporality(self):
        """
        `ExplicitBucketHistogramAggregation` supports cumulative temporality
        """

        explicit_bucket_histogram_aggregation = ExplicitBucketHistogramAggregation(AGGREGATION_TEMPORALITY_CUMULATIVE)

        explicit_bucket_histogram_aggregation.aggregate(-1)
        explicit_bucket_histogram_aggregation.aggregate(2)
        explicit_bucket_histogram_aggregation.aggregate(7)
        explicit_bucket_histogram_aggregation.aggregate(8)
        explicit_bucket_histogram_aggregation.aggregate(9999)

        result = explicit_bucket_histogram_aggregation.collect()

        self.assertEqual(result[0], -1)
        self.assertEqual(result[5], 2)
        self.assertEqual(result[10], 15)
        self.assertEqual(result[inf], 9999)

        self.assertEqual(explicit_bucket_histogram_aggregation.value[0], -1)
        self.assertEqual(explicit_bucket_histogram_aggregation.value[5], 2)
        self.assertEqual(explicit_bucket_histogram_aggregation.value[10], 15)
        self.assertEqual(
            explicit_bucket_histogram_aggregation.value[inf], 9999
        )

        explicit_bucket_histogram_aggregation.aggregate(-1)
        explicit_bucket_histogram_aggregation.aggregate(2)
        explicit_bucket_histogram_aggregation.aggregate(7)
        explicit_bucket_histogram_aggregation.aggregate(8)
        explicit_bucket_histogram_aggregation.aggregate(9999)

        result = explicit_bucket_histogram_aggregation.collect()

        self.assertEqual(result[0], -1 * 2)
        self.assertEqual(result[5], 2 * 2)
        self.assertEqual(result[10], 15 * 2)
        self.assertEqual(result[inf], 9999 * 2)

        self.assertEqual(
            explicit_bucket_histogram_aggregation.value[0], -1 * 2
        )
        self.assertEqual(explicit_bucket_histogram_aggregation.value[5], 2 * 2)
        self.assertEqual(
            explicit_bucket_histogram_aggregation.value[10], 15 * 2
        )
        self.assertEqual(
            explicit_bucket_histogram_aggregation.value[inf], 9999 * 2
        )
