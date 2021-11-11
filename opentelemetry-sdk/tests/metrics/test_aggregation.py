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


from math import inf
from unittest import TestCase

from opentelemetry.sdk._metrics.aggregation import (
    ExplicitBucketHistogramAggregation,
    LastValueAggregation,
    NoneAggregation,
    SumAggregation,
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

        self.assertIs(none_aggregation.value, None)


class TestSumAggregation(TestCase):
    def test_aggregate(self):
        """
        `SumAggregation` collects data for sum metric points
        """

        sum_aggregation = SumAggregation()

        sum_aggregation.aggregate(1)
        sum_aggregation.aggregate(2)
        sum_aggregation.aggregate(3)

        self.assertEqual(sum_aggregation.value, 6)


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
    def test_aggregate(self):
        """
        `ExplicitBucketHistogramAggregation` collects data for explicit_bucket_histogram metric points
        """

        explicit_bucket_histogram_aggregation = (
            ExplicitBucketHistogramAggregation()
        )

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
