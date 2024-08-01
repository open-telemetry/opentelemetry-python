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

from math import inf
from time import sleep
from typing import Union
from unittest import TestCase
from unittest.mock import Mock

from opentelemetry.sdk.metrics._internal.aggregation import (
    _ExplicitBucketHistogramAggregation,
    _LastValueAggregation,
    _SumAggregation,
)
from opentelemetry.sdk.metrics._internal.instrument import (
    _Counter,
    _Gauge,
    _Histogram,
    _ObservableCounter,
    _ObservableGauge,
    _ObservableUpDownCounter,
    _UpDownCounter,
)
from opentelemetry.sdk.metrics._internal.measurement import Measurement
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    NumberDataPoint,
)
from opentelemetry.sdk.metrics.view import (
    DefaultAggregation,
    ExplicitBucketHistogramAggregation,
    LastValueAggregation,
    SumAggregation,
)
from opentelemetry.util.types import Attributes


def measurement(
    value: Union[int, float], attributes: Attributes = None
) -> Measurement:
    return Measurement(value, instrument=Mock(), attributes=attributes)


class TestSynchronousSumAggregation(TestCase):
    def test_aggregate_delta(self):
        """
        `SynchronousSumAggregation` aggregates data for sum metric points
        """

        synchronous_sum_aggregation = _SumAggregation(
            Mock(), True, AggregationTemporality.DELTA, 0
        )

        synchronous_sum_aggregation.aggregate(measurement(1))
        synchronous_sum_aggregation.aggregate(measurement(2))
        synchronous_sum_aggregation.aggregate(measurement(3))

        self.assertEqual(synchronous_sum_aggregation._value, 6)

        synchronous_sum_aggregation = _SumAggregation(
            Mock(), True, AggregationTemporality.DELTA, 0
        )

        synchronous_sum_aggregation.aggregate(measurement(1))
        synchronous_sum_aggregation.aggregate(measurement(-2))
        synchronous_sum_aggregation.aggregate(measurement(3))

        self.assertEqual(synchronous_sum_aggregation._value, 2)

    def test_aggregate_cumulative(self):
        """
        `SynchronousSumAggregation` aggregates data for sum metric points
        """

        synchronous_sum_aggregation = _SumAggregation(
            Mock(), True, AggregationTemporality.CUMULATIVE, 0
        )

        synchronous_sum_aggregation.aggregate(measurement(1))
        synchronous_sum_aggregation.aggregate(measurement(2))
        synchronous_sum_aggregation.aggregate(measurement(3))

        self.assertEqual(synchronous_sum_aggregation._value, 6)

        synchronous_sum_aggregation = _SumAggregation(
            Mock(), True, AggregationTemporality.CUMULATIVE, 0
        )

        synchronous_sum_aggregation.aggregate(measurement(1))
        synchronous_sum_aggregation.aggregate(measurement(-2))
        synchronous_sum_aggregation.aggregate(measurement(3))

        self.assertEqual(synchronous_sum_aggregation._value, 2)

    def test_collect_delta(self):
        """
        `SynchronousSumAggregation` collects sum metric points
        """

        synchronous_sum_aggregation = _SumAggregation(
            Mock(), True, AggregationTemporality.DELTA, 0
        )

        synchronous_sum_aggregation.aggregate(measurement(1))
        # 1 is used here directly to simulate the instant the first
        # collection process starts.
        first_sum = synchronous_sum_aggregation.collect(
            AggregationTemporality.CUMULATIVE, 1
        )

        self.assertEqual(first_sum.value, 1)

        synchronous_sum_aggregation.aggregate(measurement(1))
        # 2 is used here directly to simulate the instant the first
        # collection process starts.
        second_sum = synchronous_sum_aggregation.collect(
            AggregationTemporality.CUMULATIVE, 2
        )

        self.assertEqual(second_sum.value, 2)

        self.assertEqual(
            second_sum.start_time_unix_nano, first_sum.start_time_unix_nano
        )

        synchronous_sum_aggregation = _SumAggregation(
            Mock(), True, AggregationTemporality.DELTA, 0
        )

        synchronous_sum_aggregation.aggregate(measurement(1))
        # 1 is used here directly to simulate the instant the first
        # collection process starts.
        first_sum = synchronous_sum_aggregation.collect(
            AggregationTemporality.DELTA, 1
        )

        self.assertEqual(first_sum.value, 1)

        synchronous_sum_aggregation.aggregate(measurement(1))
        # 2 is used here directly to simulate the instant the first
        # collection process starts.
        second_sum = synchronous_sum_aggregation.collect(
            AggregationTemporality.DELTA, 2
        )

        self.assertEqual(second_sum.value, 1)

        self.assertGreater(
            second_sum.start_time_unix_nano, first_sum.start_time_unix_nano
        )

    def test_collect_cumulative(self):
        """
        `SynchronousSumAggregation` collects number data points
        """

        sum_aggregation = _SumAggregation(
            Mock(), True, AggregationTemporality.CUMULATIVE, 0
        )

        sum_aggregation.aggregate(measurement(1))
        first_sum = sum_aggregation.collect(
            AggregationTemporality.CUMULATIVE, 1
        )

        self.assertEqual(first_sum.value, 1)

        # should have been reset after first collect
        sum_aggregation.aggregate(measurement(1))
        second_sum = sum_aggregation.collect(
            AggregationTemporality.CUMULATIVE, 1
        )

        self.assertEqual(second_sum.value, 1)

        self.assertEqual(
            second_sum.start_time_unix_nano, first_sum.start_time_unix_nano
        )

        # if no point seen for a whole interval, should return None
        third_sum = sum_aggregation.collect(
            AggregationTemporality.CUMULATIVE, 1
        )
        self.assertIsNone(third_sum)


class TestLastValueAggregation(TestCase):
    def test_aggregate(self):
        """
        `LastValueAggregation` collects data for gauge metric points with delta
        temporality
        """

        last_value_aggregation = _LastValueAggregation(Mock())

        last_value_aggregation.aggregate(measurement(1))
        self.assertEqual(last_value_aggregation._value, 1)

        last_value_aggregation.aggregate(measurement(2))
        self.assertEqual(last_value_aggregation._value, 2)

        last_value_aggregation.aggregate(measurement(3))
        self.assertEqual(last_value_aggregation._value, 3)

    def test_collect(self):
        """
        `LastValueAggregation` collects number data points
        """

        last_value_aggregation = _LastValueAggregation(Mock())

        self.assertIsNone(
            last_value_aggregation.collect(
                AggregationTemporality.CUMULATIVE, 1
            )
        )

        last_value_aggregation.aggregate(measurement(1))
        # 1 is used here directly to simulate the instant the first
        # collection process starts.
        first_number_data_point = last_value_aggregation.collect(
            AggregationTemporality.CUMULATIVE, 1
        )
        self.assertIsInstance(first_number_data_point, NumberDataPoint)

        self.assertEqual(first_number_data_point.value, 1)

        self.assertIsNone(first_number_data_point.start_time_unix_nano)

        last_value_aggregation.aggregate(measurement(1))

        # CI fails the last assertion without this
        sleep(0.1)

        # 2 is used here directly to simulate the instant the second
        # collection process starts.
        second_number_data_point = last_value_aggregation.collect(
            AggregationTemporality.CUMULATIVE, 2
        )

        self.assertEqual(second_number_data_point.value, 1)

        self.assertIsNone(second_number_data_point.start_time_unix_nano)

        self.assertGreater(
            second_number_data_point.time_unix_nano,
            first_number_data_point.time_unix_nano,
        )

        # 3 is used here directly to simulate the instant the second
        # collection process starts.
        third_number_data_point = last_value_aggregation.collect(
            AggregationTemporality.CUMULATIVE, 3
        )
        self.assertIsNone(third_number_data_point)


class TestExplicitBucketHistogramAggregation(TestCase):
    def test_aggregate(self):
        """
        Test `ExplicitBucketHistogramAggregation with custom boundaries
        """

        explicit_bucket_histogram_aggregation = (
            _ExplicitBucketHistogramAggregation(
                Mock(),
                AggregationTemporality.DELTA,
                0,
                boundaries=[0, 2, 4],
            )
        )

        explicit_bucket_histogram_aggregation.aggregate(measurement(-1))
        explicit_bucket_histogram_aggregation.aggregate(measurement(0))
        explicit_bucket_histogram_aggregation.aggregate(measurement(1))
        explicit_bucket_histogram_aggregation.aggregate(measurement(2))
        explicit_bucket_histogram_aggregation.aggregate(measurement(3))
        explicit_bucket_histogram_aggregation.aggregate(measurement(4))
        explicit_bucket_histogram_aggregation.aggregate(measurement(5))

        # The first bucket keeps count of values between (-inf, 0] (-1 and 0)
        self.assertEqual(explicit_bucket_histogram_aggregation._value[0], 2)

        # The second bucket keeps count of values between (0, 2] (1 and 2)
        self.assertEqual(explicit_bucket_histogram_aggregation._value[1], 2)

        # The third bucket keeps count of values between (2, 4] (3 and 4)
        self.assertEqual(explicit_bucket_histogram_aggregation._value[2], 2)

        # The fourth bucket keeps count of values between (4, inf) (3 and 4)
        self.assertEqual(explicit_bucket_histogram_aggregation._value[3], 1)

        histo = explicit_bucket_histogram_aggregation.collect(
            AggregationTemporality.CUMULATIVE, 1
        )
        self.assertEqual(histo.sum, 14)

    def test_min_max(self):
        """
        `record_min_max` indicates the aggregator to record the minimum and
        maximum value in the population
        """

        explicit_bucket_histogram_aggregation = (
            _ExplicitBucketHistogramAggregation(
                Mock(), AggregationTemporality.CUMULATIVE, 0
            )
        )

        explicit_bucket_histogram_aggregation.aggregate(measurement(-1))
        explicit_bucket_histogram_aggregation.aggregate(measurement(2))
        explicit_bucket_histogram_aggregation.aggregate(measurement(7))
        explicit_bucket_histogram_aggregation.aggregate(measurement(8))
        explicit_bucket_histogram_aggregation.aggregate(measurement(9999))

        self.assertEqual(explicit_bucket_histogram_aggregation._min, -1)
        self.assertEqual(explicit_bucket_histogram_aggregation._max, 9999)

        explicit_bucket_histogram_aggregation = (
            _ExplicitBucketHistogramAggregation(
                Mock(),
                AggregationTemporality.CUMULATIVE,
                0,
                record_min_max=False,
            )
        )

        explicit_bucket_histogram_aggregation.aggregate(measurement(-1))
        explicit_bucket_histogram_aggregation.aggregate(measurement(2))
        explicit_bucket_histogram_aggregation.aggregate(measurement(7))
        explicit_bucket_histogram_aggregation.aggregate(measurement(8))
        explicit_bucket_histogram_aggregation.aggregate(measurement(9999))

        self.assertEqual(explicit_bucket_histogram_aggregation._min, inf)
        self.assertEqual(explicit_bucket_histogram_aggregation._max, -inf)

    def test_collect(self):
        """
        `_ExplicitBucketHistogramAggregation` collects sum metric points
        """

        explicit_bucket_histogram_aggregation = (
            _ExplicitBucketHistogramAggregation(
                Mock(),
                AggregationTemporality.DELTA,
                0,
                boundaries=[0, 1, 2],
            )
        )

        explicit_bucket_histogram_aggregation.aggregate(measurement(1))
        # 1 is used here directly to simulate the instant the first
        # collection process starts.
        first_histogram = explicit_bucket_histogram_aggregation.collect(
            AggregationTemporality.CUMULATIVE, 1
        )

        self.assertEqual(first_histogram.bucket_counts, (0, 1, 0, 0))
        self.assertEqual(first_histogram.sum, 1)

        # CI fails the last assertion without this
        sleep(0.1)

        explicit_bucket_histogram_aggregation.aggregate(measurement(1))
        # 2 is used here directly to simulate the instant the second
        # collection process starts.

        second_histogram = explicit_bucket_histogram_aggregation.collect(
            AggregationTemporality.CUMULATIVE, 2
        )

        self.assertEqual(second_histogram.bucket_counts, (0, 2, 0, 0))
        self.assertEqual(second_histogram.sum, 2)

        self.assertGreater(
            second_histogram.time_unix_nano, first_histogram.time_unix_nano
        )

    def test_boundaries(self):
        self.assertEqual(
            _ExplicitBucketHistogramAggregation(
                Mock(), AggregationTemporality.CUMULATIVE, 0
            )._boundaries,
            (
                0.0,
                5.0,
                10.0,
                25.0,
                50.0,
                75.0,
                100.0,
                250.0,
                500.0,
                750.0,
                1000.0,
                2500.0,
                5000.0,
                7500.0,
                10000.0,
            ),
        )


class TestAggregationFactory(TestCase):
    def test_sum_factory(self):
        counter = _Counter("name", Mock(), Mock())
        factory = SumAggregation()
        aggregation = factory._create_aggregation(counter, Mock(), 0)
        self.assertIsInstance(aggregation, _SumAggregation)
        self.assertTrue(aggregation._instrument_is_monotonic)
        self.assertEqual(
            aggregation._instrument_aggregation_temporality,
            AggregationTemporality.DELTA,
        )
        aggregation2 = factory._create_aggregation(counter, Mock(), 0)
        self.assertNotEqual(aggregation, aggregation2)

        counter = _UpDownCounter("name", Mock(), Mock())
        factory = SumAggregation()
        aggregation = factory._create_aggregation(counter, Mock(), 0)
        self.assertIsInstance(aggregation, _SumAggregation)
        self.assertFalse(aggregation._instrument_is_monotonic)
        self.assertEqual(
            aggregation._instrument_aggregation_temporality,
            AggregationTemporality.DELTA,
        )

        counter = _ObservableCounter("name", Mock(), Mock(), None)
        factory = SumAggregation()
        aggregation = factory._create_aggregation(counter, Mock(), 0)
        self.assertIsInstance(aggregation, _SumAggregation)
        self.assertTrue(aggregation._instrument_is_monotonic)
        self.assertEqual(
            aggregation._instrument_aggregation_temporality,
            AggregationTemporality.CUMULATIVE,
        )

    def test_explicit_bucket_histogram_factory(self):
        histo = _Histogram("name", Mock(), Mock())
        factory = ExplicitBucketHistogramAggregation(
            boundaries=(
                0.0,
                5.0,
            ),
            record_min_max=False,
        )
        aggregation = factory._create_aggregation(histo, Mock(), 0)
        self.assertIsInstance(aggregation, _ExplicitBucketHistogramAggregation)
        self.assertFalse(aggregation._record_min_max)
        self.assertEqual(aggregation._boundaries, (0.0, 5.0))
        aggregation2 = factory._create_aggregation(histo, Mock(), 0)
        self.assertNotEqual(aggregation, aggregation2)

    def test_last_value_factory(self):
        counter = _Counter("name", Mock(), Mock())
        factory = LastValueAggregation()
        aggregation = factory._create_aggregation(counter, Mock(), 0)
        self.assertIsInstance(aggregation, _LastValueAggregation)
        aggregation2 = factory._create_aggregation(counter, Mock(), 0)
        self.assertNotEqual(aggregation, aggregation2)


class TestDefaultAggregation(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.default_aggregation = DefaultAggregation()

    def test_counter(self):

        aggregation = self.default_aggregation._create_aggregation(
            _Counter("name", Mock(), Mock()), Mock(), 0
        )
        self.assertIsInstance(aggregation, _SumAggregation)
        self.assertTrue(aggregation._instrument_is_monotonic)
        self.assertEqual(
            aggregation._instrument_aggregation_temporality,
            AggregationTemporality.DELTA,
        )

    def test_up_down_counter(self):

        aggregation = self.default_aggregation._create_aggregation(
            _UpDownCounter("name", Mock(), Mock()), Mock(), 0
        )
        self.assertIsInstance(aggregation, _SumAggregation)
        self.assertFalse(aggregation._instrument_is_monotonic)
        self.assertEqual(
            aggregation._instrument_aggregation_temporality,
            AggregationTemporality.DELTA,
        )

    def test_observable_counter(self):

        aggregation = self.default_aggregation._create_aggregation(
            _ObservableCounter("name", Mock(), Mock(), callbacks=[Mock()]),
            Mock(),
            0,
        )
        self.assertIsInstance(aggregation, _SumAggregation)
        self.assertTrue(aggregation._instrument_is_monotonic)
        self.assertEqual(
            aggregation._instrument_aggregation_temporality,
            AggregationTemporality.CUMULATIVE,
        )

    def test_observable_up_down_counter(self):

        aggregation = self.default_aggregation._create_aggregation(
            _ObservableUpDownCounter(
                "name", Mock(), Mock(), callbacks=[Mock()]
            ),
            Mock(),
            0,
        )
        self.assertIsInstance(aggregation, _SumAggregation)
        self.assertFalse(aggregation._instrument_is_monotonic)
        self.assertEqual(
            aggregation._instrument_aggregation_temporality,
            AggregationTemporality.CUMULATIVE,
        )

    def test_histogram(self):

        aggregation = self.default_aggregation._create_aggregation(
            _Histogram(
                "name",
                Mock(),
                Mock(),
            ),
            Mock(),
            0,
        )
        self.assertIsInstance(aggregation, _ExplicitBucketHistogramAggregation)

    def test_gauge(self):

        aggregation = self.default_aggregation._create_aggregation(
            _Gauge(
                "name",
                Mock(),
                Mock(),
            ),
            Mock(),
            0,
        )
        self.assertIsInstance(aggregation, _LastValueAggregation)

    def test_observable_gauge(self):

        aggregation = self.default_aggregation._create_aggregation(
            _ObservableGauge(
                "name",
                Mock(),
                Mock(),
                callbacks=[Mock()],
            ),
            Mock(),
            0,
        )
        self.assertIsInstance(aggregation, _LastValueAggregation)
