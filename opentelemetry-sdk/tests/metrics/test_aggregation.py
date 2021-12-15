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
    SynchronousSumAggregation,
)
from opentelemetry.sdk._metrics.measurement import Measurement


class TestSynchronousSumAggregation(TestCase):
    def test_aggregate(self):
        """
        `SynchronousSumAggregation` collects data for sum metric points
        """

        sum_aggregation = SynchronousSumAggregation(True)

        sum_aggregation.aggregate(Measurement(1))
        sum_aggregation.aggregate(Measurement(2))
        sum_aggregation.aggregate(Measurement(3))

        self.assertEqual(sum_aggregation.value, 6)

        sum_aggregation = SynchronousSumAggregation(True)

        sum_aggregation.aggregate(Measurement(1))
        sum_aggregation.aggregate(Measurement(-2))
        sum_aggregation.aggregate(Measurement(3))

        self.assertEqual(sum_aggregation.value, 2)


class TestLastValueAggregation(TestCase):
    def test_aggregate(self):
        """
        `LastValueAggregation` collects data for gauge metric points with delta
        temporality
        """

        last_value_aggregation = LastValueAggregation(True)

        last_value_aggregation.aggregate(Measurement(1))
        self.assertEqual(last_value_aggregation.value, 1)

        last_value_aggregation.aggregate(Measurement(2))
        self.assertEqual(last_value_aggregation.value, 2)

        last_value_aggregation.aggregate(Measurement(3))
        self.assertEqual(last_value_aggregation.value, 3)


class TestExplicitBucketHistogramAggregation(TestCase):
    def test_aggregate(self):
        """
        `ExplicitBucketHistogramAggregation` collects data for explicit_bucket_histogram metric points
        """

        explicit_bucket_histogram_aggregation = (
            ExplicitBucketHistogramAggregation(True)
        )

        explicit_bucket_histogram_aggregation.aggregate(Measurement(-1))
        explicit_bucket_histogram_aggregation.aggregate(Measurement(2))
        explicit_bucket_histogram_aggregation.aggregate(Measurement(7))
        explicit_bucket_histogram_aggregation.aggregate(Measurement(8))
        explicit_bucket_histogram_aggregation.aggregate(Measurement(9999))

        self.assertEqual(explicit_bucket_histogram_aggregation.value[0], -1)
        self.assertEqual(explicit_bucket_histogram_aggregation.value[5], 2)
        self.assertEqual(explicit_bucket_histogram_aggregation.value[10], 15)
        self.assertEqual(
            explicit_bucket_histogram_aggregation.value[inf], 9999
        )

    def test_min_max(self):
        """
        `record_min_max` indicates the aggregator to record the minimum and
        maximum value in the population
        """

        explicit_bucket_histogram_aggregation = (
            ExplicitBucketHistogramAggregation(True)
        )

        explicit_bucket_histogram_aggregation.aggregate(Measurement(-1))
        explicit_bucket_histogram_aggregation.aggregate(Measurement(2))
        explicit_bucket_histogram_aggregation.aggregate(Measurement(7))
        explicit_bucket_histogram_aggregation.aggregate(Measurement(8))
        explicit_bucket_histogram_aggregation.aggregate(Measurement(9999))

        self.assertEqual(explicit_bucket_histogram_aggregation._min, -1)
        self.assertEqual(explicit_bucket_histogram_aggregation._max, 9999)

        explicit_bucket_histogram_aggregation = (
            ExplicitBucketHistogramAggregation(True, record_min_max=False)
        )

        explicit_bucket_histogram_aggregation.aggregate(Measurement(-1))
        explicit_bucket_histogram_aggregation.aggregate(Measurement(2))
        explicit_bucket_histogram_aggregation.aggregate(Measurement(7))
        explicit_bucket_histogram_aggregation.aggregate(Measurement(8))
        explicit_bucket_histogram_aggregation.aggregate(Measurement(9999))

        self.assertEqual(explicit_bucket_histogram_aggregation._min, inf)
        self.assertEqual(explicit_bucket_histogram_aggregation._max, -inf)
