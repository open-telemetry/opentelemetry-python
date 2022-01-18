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
from time import sleep
from unittest import TestCase

from opentelemetry.sdk._metrics.aggregation import (
    AsynchronousSumAggregation,
    ExplicitBucketHistogramAggregation,
    LastValueAggregation,
    SynchronousSumAggregation,
    _InstrumentMonotonicityAwareAggregation,
)
from opentelemetry.sdk._metrics.measurement import Measurement


class TestSynchronousSumAggregation(TestCase):
    def test_instrument_monotonicity_awareness(self):
        """
        `SynchronousSumAggregation` is aware of the instrument monotonicity
        """

        synchronous_sum_aggregation = SynchronousSumAggregation(True)
        self.assertIsInstance(
            synchronous_sum_aggregation,
            _InstrumentMonotonicityAwareAggregation,
        )
        self.assertTrue(synchronous_sum_aggregation._instrument_is_monotonic)

        synchronous_sum_aggregation = SynchronousSumAggregation(False)
        self.assertFalse(synchronous_sum_aggregation._instrument_is_monotonic)

    def test_aggregate(self):
        """
        `SynchronousSumAggregation` aggregates data for sum metric points
        """

        synchronous_sum_aggregation = SynchronousSumAggregation(True)

        synchronous_sum_aggregation.aggregate(Measurement(1))
        synchronous_sum_aggregation.aggregate(Measurement(2))
        synchronous_sum_aggregation.aggregate(Measurement(3))

        self.assertEqual(synchronous_sum_aggregation._value, 6)

        synchronous_sum_aggregation = SynchronousSumAggregation(True)

        synchronous_sum_aggregation.aggregate(Measurement(1))
        synchronous_sum_aggregation.aggregate(Measurement(-2))
        synchronous_sum_aggregation.aggregate(Measurement(3))

        self.assertEqual(synchronous_sum_aggregation._value, 2)

    def test_collect(self):
        """
        `SynchronousSumAggregation` collects sum metric points
        """

        synchronous_sum_aggregation = SynchronousSumAggregation(True)

        synchronous_sum_aggregation.aggregate(Measurement(1))
        first_sum = synchronous_sum_aggregation.collect()

        self.assertEqual(first_sum.value, 1)
        self.assertTrue(first_sum.is_monotonic)

        synchronous_sum_aggregation.aggregate(Measurement(1))
        second_sum = synchronous_sum_aggregation.collect()

        self.assertEqual(second_sum.value, 1)
        self.assertTrue(second_sum.is_monotonic)

        self.assertGreater(
            second_sum.start_time_unix_nano, first_sum.start_time_unix_nano
        )


class TestAsynchronousSumAggregation(TestCase):
    def test_instrument_monotonicity_awareness(self):
        """
        `AsynchronousSumAggregation` is aware of the instrument monotonicity
        """

        asynchronous_sum_aggregation = AsynchronousSumAggregation(True)
        self.assertIsInstance(
            asynchronous_sum_aggregation,
            _InstrumentMonotonicityAwareAggregation,
        )
        self.assertTrue(asynchronous_sum_aggregation._instrument_is_monotonic)

        asynchronous_sum_aggregation = AsynchronousSumAggregation(False)
        self.assertFalse(asynchronous_sum_aggregation._instrument_is_monotonic)

    def test_aggregate(self):
        """
        `AsynchronousSumAggregation` aggregates data for sum metric points
        """

        asynchronous_sum_aggregation = AsynchronousSumAggregation(True)

        asynchronous_sum_aggregation.aggregate(Measurement(1))
        self.assertEqual(asynchronous_sum_aggregation._value, 1)

        asynchronous_sum_aggregation.aggregate(Measurement(2))
        self.assertEqual(asynchronous_sum_aggregation._value, 2)

        asynchronous_sum_aggregation.aggregate(Measurement(3))
        self.assertEqual(asynchronous_sum_aggregation._value, 3)

        asynchronous_sum_aggregation = AsynchronousSumAggregation(True)

        asynchronous_sum_aggregation.aggregate(Measurement(1))
        self.assertEqual(asynchronous_sum_aggregation._value, 1)

        asynchronous_sum_aggregation.aggregate(Measurement(-2))
        self.assertEqual(asynchronous_sum_aggregation._value, -2)

        asynchronous_sum_aggregation.aggregate(Measurement(3))
        self.assertEqual(asynchronous_sum_aggregation._value, 3)

    def test_collect(self):
        """
        `AsynchronousSumAggregation` collects sum metric points
        """

        asynchronous_sum_aggregation = AsynchronousSumAggregation(True)

        self.assertIsNone(asynchronous_sum_aggregation.collect())

        asynchronous_sum_aggregation.aggregate(Measurement(1))
        first_sum = asynchronous_sum_aggregation.collect()

        self.assertEqual(first_sum.value, 1)
        self.assertTrue(first_sum.is_monotonic)

        asynchronous_sum_aggregation.aggregate(Measurement(1))
        second_sum = asynchronous_sum_aggregation.collect()

        self.assertEqual(second_sum.value, 1)
        self.assertTrue(second_sum.is_monotonic)

        self.assertEqual(
            second_sum.start_time_unix_nano, first_sum.start_time_unix_nano
        )


class TestLastValueAggregation(TestCase):
    def test_instrument_monotonicity_awareness(self):
        """
        `LastValueAggregation` is not aware of the instrument monotonicity
        """

        sum_aggregation = LastValueAggregation()
        self.assertNotIsInstance(
            sum_aggregation, _InstrumentMonotonicityAwareAggregation
        )

    def test_aggregate(self):
        """
        `LastValueAggregation` collects data for gauge metric points with delta
        temporality
        """

        last_value_aggregation = LastValueAggregation()

        last_value_aggregation.aggregate(Measurement(1))
        self.assertEqual(last_value_aggregation._value, 1)

        last_value_aggregation.aggregate(Measurement(2))
        self.assertEqual(last_value_aggregation._value, 2)

        last_value_aggregation.aggregate(Measurement(3))
        self.assertEqual(last_value_aggregation._value, 3)

    def test_collect(self):
        """
        `LastValueAggregation` collects sum metric points
        """

        last_value_aggregation = LastValueAggregation()

        self.assertIsNone(last_value_aggregation.collect())

        last_value_aggregation.aggregate(Measurement(1))
        first_gauge = last_value_aggregation.collect()

        self.assertEqual(first_gauge.value, 1)

        last_value_aggregation.aggregate(Measurement(1))

        # CI fails the last assertion without this
        sleep(0.1)

        second_gauge = last_value_aggregation.collect()

        self.assertEqual(second_gauge.value, 1)

        self.assertGreater(
            second_gauge.time_unix_nano, first_gauge.time_unix_nano
        )


class TestExplicitBucketHistogramAggregation(TestCase):
    def test_aggregate(self):
        """
        Test `ExplicitBucketHistogramAggregation with custom boundaries
        """

        explicit_bucket_histogram_aggregation = (
            ExplicitBucketHistogramAggregation(boundaries=[0, 2, 4])
        )

        explicit_bucket_histogram_aggregation.aggregate(Measurement(-1))
        explicit_bucket_histogram_aggregation.aggregate(Measurement(0))
        explicit_bucket_histogram_aggregation.aggregate(Measurement(1))
        explicit_bucket_histogram_aggregation.aggregate(Measurement(2))
        explicit_bucket_histogram_aggregation.aggregate(Measurement(3))
        explicit_bucket_histogram_aggregation.aggregate(Measurement(4))
        explicit_bucket_histogram_aggregation.aggregate(Measurement(5))

        # The first bucket keeps count of values between (-inf, 0] (-1 and 0)
        self.assertEqual(
            explicit_bucket_histogram_aggregation._bucket_counts[0], 2
        )

        # The second bucket keeps count of values between (0, 2] (1 and 2)
        self.assertEqual(
            explicit_bucket_histogram_aggregation._bucket_counts[1], 2
        )

        # The third bucket keeps count of values between (2, 4] (3 and 4)
        self.assertEqual(
            explicit_bucket_histogram_aggregation._bucket_counts[2], 2
        )

        # The fourth bucket keeps count of values between (4, inf) (3 and 4)
        self.assertEqual(
            explicit_bucket_histogram_aggregation._bucket_counts[3], 1
        )

    def test_min_max(self):
        """
        `record_min_max` indicates the aggregator to record the minimum and
        maximum value in the population
        """

        explicit_bucket_histogram_aggregation = (
            ExplicitBucketHistogramAggregation()
        )

        explicit_bucket_histogram_aggregation.aggregate(Measurement(-1))
        explicit_bucket_histogram_aggregation.aggregate(Measurement(2))
        explicit_bucket_histogram_aggregation.aggregate(Measurement(7))
        explicit_bucket_histogram_aggregation.aggregate(Measurement(8))
        explicit_bucket_histogram_aggregation.aggregate(Measurement(9999))

        self.assertEqual(explicit_bucket_histogram_aggregation._min, -1)
        self.assertEqual(explicit_bucket_histogram_aggregation._max, 9999)

        explicit_bucket_histogram_aggregation = (
            ExplicitBucketHistogramAggregation(record_min_max=False)
        )

        explicit_bucket_histogram_aggregation.aggregate(Measurement(-1))
        explicit_bucket_histogram_aggregation.aggregate(Measurement(2))
        explicit_bucket_histogram_aggregation.aggregate(Measurement(7))
        explicit_bucket_histogram_aggregation.aggregate(Measurement(8))
        explicit_bucket_histogram_aggregation.aggregate(Measurement(9999))

        self.assertEqual(explicit_bucket_histogram_aggregation._min, inf)
        self.assertEqual(explicit_bucket_histogram_aggregation._max, -inf)

    def test_collect(self):
        """
        `ExplicitBucketHistogramAggregation` collects sum metric points
        """

        explicit_bucket_histogram_aggregation = (
            ExplicitBucketHistogramAggregation(boundaries=[0, 1, 2])
        )

        explicit_bucket_histogram_aggregation.aggregate(Measurement(1))
        first_histogram = explicit_bucket_histogram_aggregation.collect()

        self.assertEqual(first_histogram.bucket_counts, (0, 1, 0, 0))

        # CI fails the last assertion without this
        sleep(0.1)

        explicit_bucket_histogram_aggregation.aggregate(Measurement(1))
        second_histogram = explicit_bucket_histogram_aggregation.collect()

        self.assertEqual(second_histogram.bucket_counts, (0, 1, 0, 0))

        self.assertGreater(
            second_histogram.time_unix_nano, first_histogram.time_unix_nano
        )
