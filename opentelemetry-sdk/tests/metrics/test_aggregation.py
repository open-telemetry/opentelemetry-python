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

from dataclasses import replace
from logging import WARNING
from math import inf
from time import sleep
from typing import Union
from unittest import TestCase
from unittest.mock import Mock

from opentelemetry.sdk._metrics import instrument
from opentelemetry.sdk._metrics.aggregation import (
    AggregationTemporality,
    DefaultAggregation,
    ExplicitBucketHistogramAggregation,
    LastValueAggregation,
    SumAggregation,
    _convert_aggregation_temporality,
    _ExplicitBucketHistogramAggregation,
    _LastValueAggregation,
    _SumAggregation,
)
from opentelemetry.sdk._metrics.instrument import (
    Counter,
    Histogram,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.sdk._metrics.measurement import Measurement
from opentelemetry.sdk._metrics.point import Gauge
from opentelemetry.sdk._metrics.point import Histogram as HistogramPoint
from opentelemetry.sdk._metrics.point import Sum
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
            True, AggregationTemporality.DELTA
        )

        synchronous_sum_aggregation.aggregate(measurement(1))
        synchronous_sum_aggregation.aggregate(measurement(2))
        synchronous_sum_aggregation.aggregate(measurement(3))

        self.assertEqual(synchronous_sum_aggregation._value, 6)

        synchronous_sum_aggregation = _SumAggregation(
            True, AggregationTemporality.DELTA
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
            True, AggregationTemporality.CUMULATIVE
        )

        synchronous_sum_aggregation.aggregate(measurement(1))
        synchronous_sum_aggregation.aggregate(measurement(2))
        synchronous_sum_aggregation.aggregate(measurement(3))

        self.assertEqual(synchronous_sum_aggregation._value, 6)

        synchronous_sum_aggregation = _SumAggregation(
            True, AggregationTemporality.CUMULATIVE
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
            True, AggregationTemporality.DELTA
        )

        synchronous_sum_aggregation.aggregate(measurement(1))
        first_sum = synchronous_sum_aggregation.collect()

        self.assertEqual(first_sum.value, 1)
        self.assertTrue(first_sum.is_monotonic)

        synchronous_sum_aggregation.aggregate(measurement(1))
        second_sum = synchronous_sum_aggregation.collect()

        self.assertEqual(second_sum.value, 1)
        self.assertTrue(second_sum.is_monotonic)

        self.assertGreater(
            second_sum.start_time_unix_nano, first_sum.start_time_unix_nano
        )

    def test_collect_cumulative(self):
        """
        `SynchronousSumAggregation` collects sum metric points
        """

        sum_aggregation = _SumAggregation(
            True, AggregationTemporality.CUMULATIVE
        )

        sum_aggregation.aggregate(measurement(1))
        first_sum = sum_aggregation.collect()

        self.assertEqual(first_sum.value, 1)
        self.assertTrue(first_sum.is_monotonic)

        # should have been reset after first collect
        sum_aggregation.aggregate(measurement(1))
        second_sum = sum_aggregation.collect()

        self.assertEqual(second_sum.value, 1)
        self.assertTrue(second_sum.is_monotonic)

        self.assertEqual(
            second_sum.start_time_unix_nano, first_sum.start_time_unix_nano
        )

        # if no point seen for a whole interval, should return None
        third_sum = sum_aggregation.collect()
        self.assertIsNone(third_sum)


class TestLastValueAggregation(TestCase):
    def test_aggregate(self):
        """
        `LastValueAggregation` collects data for gauge metric points with delta
        temporality
        """

        last_value_aggregation = _LastValueAggregation()

        last_value_aggregation.aggregate(measurement(1))
        self.assertEqual(last_value_aggregation._value, 1)

        last_value_aggregation.aggregate(measurement(2))
        self.assertEqual(last_value_aggregation._value, 2)

        last_value_aggregation.aggregate(measurement(3))
        self.assertEqual(last_value_aggregation._value, 3)

    def test_collect(self):
        """
        `LastValueAggregation` collects sum metric points
        """

        last_value_aggregation = _LastValueAggregation()

        self.assertIsNone(last_value_aggregation.collect())

        last_value_aggregation.aggregate(measurement(1))
        first_gauge = last_value_aggregation.collect()
        self.assertIsInstance(first_gauge, Gauge)

        self.assertEqual(first_gauge.value, 1)

        last_value_aggregation.aggregate(measurement(1))

        # CI fails the last assertion without this
        sleep(0.1)

        second_gauge = last_value_aggregation.collect()

        self.assertEqual(second_gauge.value, 1)

        self.assertGreater(
            second_gauge.time_unix_nano, first_gauge.time_unix_nano
        )

        # if no observation seen for the interval, it should return None
        third_gauge = last_value_aggregation.collect()
        self.assertIsNone(third_gauge)


class TestExplicitBucketHistogramAggregation(TestCase):
    def test_aggregate(self):
        """
        Test `ExplicitBucketHistogramAggregation with custom boundaries
        """

        explicit_bucket_histogram_aggregation = (
            _ExplicitBucketHistogramAggregation(boundaries=[0, 2, 4])
        )

        explicit_bucket_histogram_aggregation.aggregate(measurement(-1))
        explicit_bucket_histogram_aggregation.aggregate(measurement(0))
        explicit_bucket_histogram_aggregation.aggregate(measurement(1))
        explicit_bucket_histogram_aggregation.aggregate(measurement(2))
        explicit_bucket_histogram_aggregation.aggregate(measurement(3))
        explicit_bucket_histogram_aggregation.aggregate(measurement(4))
        explicit_bucket_histogram_aggregation.aggregate(measurement(5))

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

        histo = explicit_bucket_histogram_aggregation.collect()
        self.assertEqual(histo.sum, 14)

    def test_min_max(self):
        """
        `record_min_max` indicates the aggregator to record the minimum and
        maximum value in the population
        """

        explicit_bucket_histogram_aggregation = (
            _ExplicitBucketHistogramAggregation()
        )

        explicit_bucket_histogram_aggregation.aggregate(measurement(-1))
        explicit_bucket_histogram_aggregation.aggregate(measurement(2))
        explicit_bucket_histogram_aggregation.aggregate(measurement(7))
        explicit_bucket_histogram_aggregation.aggregate(measurement(8))
        explicit_bucket_histogram_aggregation.aggregate(measurement(9999))

        self.assertEqual(explicit_bucket_histogram_aggregation._min, -1)
        self.assertEqual(explicit_bucket_histogram_aggregation._max, 9999)

        explicit_bucket_histogram_aggregation = (
            _ExplicitBucketHistogramAggregation(record_min_max=False)
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
            _ExplicitBucketHistogramAggregation(boundaries=[0, 1, 2])
        )

        explicit_bucket_histogram_aggregation.aggregate(measurement(1))
        first_histogram = explicit_bucket_histogram_aggregation.collect()

        self.assertEqual(first_histogram.bucket_counts, (0, 1, 0, 0))
        self.assertEqual(first_histogram.sum, 1)

        # CI fails the last assertion without this
        sleep(0.1)

        explicit_bucket_histogram_aggregation.aggregate(measurement(1))
        second_histogram = explicit_bucket_histogram_aggregation.collect()

        self.assertEqual(second_histogram.bucket_counts, (0, 1, 0, 0))
        self.assertEqual(second_histogram.sum, 1)

        self.assertGreater(
            second_histogram.time_unix_nano, first_histogram.time_unix_nano
        )


class TestConvertAggregationTemporality(TestCase):
    """
    Test aggregation temporality conversion algorithm
    """

    def test_previous_point_non_cumulative(self):

        with self.assertRaises(Exception):

            _convert_aggregation_temporality(
                Sum(
                    start_time_unix_nano=0,
                    time_unix_nano=0,
                    value=0,
                    aggregation_temporality=AggregationTemporality.DELTA,
                    is_monotonic=False,
                ),
                Sum(
                    start_time_unix_nano=0,
                    time_unix_nano=0,
                    value=0,
                    aggregation_temporality=AggregationTemporality.DELTA,
                    is_monotonic=False,
                ),
                AggregationTemporality.DELTA,
            ),

    def test_mismatched_point_types(self):

        current_point = Sum(
            start_time_unix_nano=0,
            time_unix_nano=0,
            value=0,
            aggregation_temporality=AggregationTemporality.DELTA,
            is_monotonic=False,
        )

        with self.assertLogs(level=WARNING):
            self.assertIs(
                _convert_aggregation_temporality(
                    Gauge(time_unix_nano=0, value=0),
                    current_point,
                    AggregationTemporality.DELTA,
                ),
                current_point,
            )

        with self.assertRaises(AssertionError):
            with self.assertLogs(level=WARNING):
                self.assertIs(
                    _convert_aggregation_temporality(
                        Gauge(time_unix_nano=0, value=0),
                        None,
                        AggregationTemporality.DELTA,
                    ),
                    current_point,
                )

    def test_current_point_sum_previous_point_none(self):

        current_point = Sum(
            start_time_unix_nano=0,
            time_unix_nano=0,
            value=0,
            aggregation_temporality=AggregationTemporality.DELTA,
            is_monotonic=False,
        )

        self.assertEqual(
            _convert_aggregation_temporality(
                None, current_point, AggregationTemporality.CUMULATIVE
            ),
            replace(
                current_point,
                aggregation_temporality=AggregationTemporality.CUMULATIVE,
            ),
        )

    def test_current_point_sum_current_point_same_aggregation_temporality(
        self,
    ):

        current_point = Sum(
            start_time_unix_nano=0,
            time_unix_nano=0,
            value=0,
            aggregation_temporality=AggregationTemporality.DELTA,
            is_monotonic=False,
        )

        self.assertEqual(
            _convert_aggregation_temporality(
                Sum(
                    start_time_unix_nano=0,
                    time_unix_nano=0,
                    value=0,
                    aggregation_temporality=AggregationTemporality.CUMULATIVE,
                    is_monotonic=False,
                ),
                current_point,
                AggregationTemporality.DELTA,
            ),
            current_point,
        )

        current_point = Sum(
            start_time_unix_nano=0,
            time_unix_nano=0,
            value=0,
            aggregation_temporality=AggregationTemporality.CUMULATIVE,
            is_monotonic=False,
        )

        self.assertEqual(
            _convert_aggregation_temporality(
                Sum(
                    start_time_unix_nano=0,
                    time_unix_nano=0,
                    value=0,
                    aggregation_temporality=AggregationTemporality.CUMULATIVE,
                    is_monotonic=False,
                ),
                current_point,
                AggregationTemporality.CUMULATIVE,
            ),
            current_point,
        )

    def test_current_point_sum_aggregation_temporality_delta(self):

        self.assertEqual(
            _convert_aggregation_temporality(
                Sum(
                    start_time_unix_nano=1,
                    time_unix_nano=2,
                    value=3,
                    aggregation_temporality=AggregationTemporality.CUMULATIVE,
                    is_monotonic=False,
                ),
                Sum(
                    start_time_unix_nano=4,
                    time_unix_nano=5,
                    value=6,
                    aggregation_temporality=AggregationTemporality.CUMULATIVE,
                    is_monotonic=False,
                ),
                AggregationTemporality.DELTA,
            ),
            Sum(
                start_time_unix_nano=2,
                time_unix_nano=5,
                value=3,
                aggregation_temporality=AggregationTemporality.DELTA,
                is_monotonic=False,
            ),
        )

        self.assertEqual(
            _convert_aggregation_temporality(
                Sum(
                    start_time_unix_nano=1,
                    time_unix_nano=2,
                    value=3,
                    aggregation_temporality=AggregationTemporality.CUMULATIVE,
                    is_monotonic=True,
                ),
                Sum(
                    start_time_unix_nano=4,
                    time_unix_nano=5,
                    value=6,
                    aggregation_temporality=AggregationTemporality.CUMULATIVE,
                    is_monotonic=False,
                ),
                AggregationTemporality.DELTA,
            ),
            Sum(
                start_time_unix_nano=2,
                time_unix_nano=5,
                value=3,
                aggregation_temporality=AggregationTemporality.DELTA,
                is_monotonic=False,
            ),
        )

        self.assertEqual(
            _convert_aggregation_temporality(
                Sum(
                    start_time_unix_nano=1,
                    time_unix_nano=2,
                    value=3,
                    aggregation_temporality=AggregationTemporality.CUMULATIVE,
                    is_monotonic=True,
                ),
                Sum(
                    start_time_unix_nano=4,
                    time_unix_nano=5,
                    value=6,
                    aggregation_temporality=AggregationTemporality.CUMULATIVE,
                    is_monotonic=True,
                ),
                AggregationTemporality.DELTA,
            ),
            Sum(
                start_time_unix_nano=2,
                time_unix_nano=5,
                value=3,
                aggregation_temporality=AggregationTemporality.DELTA,
                is_monotonic=True,
            ),
        )

    def test_current_point_sum_aggregation_temporality_cumulative(self):

        self.assertEqual(
            _convert_aggregation_temporality(
                Sum(
                    start_time_unix_nano=1,
                    time_unix_nano=2,
                    value=3,
                    aggregation_temporality=AggregationTemporality.CUMULATIVE,
                    is_monotonic=False,
                ),
                Sum(
                    start_time_unix_nano=4,
                    time_unix_nano=5,
                    value=6,
                    aggregation_temporality=AggregationTemporality.DELTA,
                    is_monotonic=False,
                ),
                AggregationTemporality.CUMULATIVE,
            ),
            Sum(
                start_time_unix_nano=1,
                time_unix_nano=5,
                value=9,
                aggregation_temporality=AggregationTemporality.CUMULATIVE,
                is_monotonic=False,
            ),
        )

        self.assertEqual(
            _convert_aggregation_temporality(
                Sum(
                    start_time_unix_nano=1,
                    time_unix_nano=2,
                    value=3,
                    aggregation_temporality=AggregationTemporality.CUMULATIVE,
                    is_monotonic=True,
                ),
                Sum(
                    start_time_unix_nano=4,
                    time_unix_nano=5,
                    value=6,
                    aggregation_temporality=AggregationTemporality.DELTA,
                    is_monotonic=False,
                ),
                AggregationTemporality.CUMULATIVE,
            ),
            Sum(
                start_time_unix_nano=1,
                time_unix_nano=5,
                value=9,
                aggregation_temporality=AggregationTemporality.CUMULATIVE,
                is_monotonic=False,
            ),
        )

        self.assertEqual(
            _convert_aggregation_temporality(
                Sum(
                    start_time_unix_nano=1,
                    time_unix_nano=2,
                    value=3,
                    aggregation_temporality=AggregationTemporality.CUMULATIVE,
                    is_monotonic=True,
                ),
                Sum(
                    start_time_unix_nano=4,
                    time_unix_nano=5,
                    value=6,
                    aggregation_temporality=AggregationTemporality.DELTA,
                    is_monotonic=True,
                ),
                AggregationTemporality.CUMULATIVE,
            ),
            Sum(
                start_time_unix_nano=1,
                time_unix_nano=5,
                value=9,
                aggregation_temporality=AggregationTemporality.CUMULATIVE,
                is_monotonic=True,
            ),
        )

    def test_current_point_gauge(self):

        current_point = Gauge(time_unix_nano=1, value=0)
        self.assertEqual(
            _convert_aggregation_temporality(
                Gauge(time_unix_nano=0, value=0),
                current_point,
                AggregationTemporality.CUMULATIVE,
            ),
            current_point,
        )


class TestHistogramConvertAggregationTemporality(TestCase):
    def test_previous_point_none(self):

        current_point = HistogramPoint(
            aggregation_temporality=AggregationTemporality.DELTA,
            bucket_counts=[0, 2, 1, 2, 0],
            explicit_bounds=[0, 5, 10, 25],
            max=24,
            min=2,
            start_time_unix_nano=0,
            sum=70,
            time_unix_nano=1,
        )

        self.assertEqual(
            _convert_aggregation_temporality(
                None, current_point, AggregationTemporality.CUMULATIVE
            ),
            replace(
                current_point,
                aggregation_temporality=AggregationTemporality.CUMULATIVE,
            ),
        )

    def test_previous_point_non_cumulative(self):

        with self.assertRaises(Exception):

            _convert_aggregation_temporality(
                HistogramPoint(
                    aggregation_temporality=AggregationTemporality.DELTA,
                    bucket_counts=[0, 2, 1, 2, 0],
                    explicit_bounds=[0, 5, 10, 25],
                    max=24,
                    min=2,
                    start_time_unix_nano=0,
                    sum=70,
                    time_unix_nano=1,
                ),
                HistogramPoint(
                    aggregation_temporality=AggregationTemporality.DELTA,
                    bucket_counts=[0, 1, 3, 0, 0],
                    explicit_bounds=[0, 5, 10, 25],
                    max=9,
                    min=2,
                    start_time_unix_nano=1,
                    sum=35,
                    time_unix_nano=2,
                ),
                AggregationTemporality.DELTA,
            ),

    def test_same_aggregation_temporality_cumulative(self):
        current_point = HistogramPoint(
            aggregation_temporality=AggregationTemporality.CUMULATIVE,
            bucket_counts=[0, 3, 4, 2, 0],
            explicit_bounds=[0, 5, 10, 25],
            max=24,
            min=1,
            start_time_unix_nano=0,
            sum=105,
            time_unix_nano=2,
        )
        self.assertEqual(
            _convert_aggregation_temporality(
                HistogramPoint(
                    aggregation_temporality=AggregationTemporality.CUMULATIVE,
                    bucket_counts=[0, 2, 1, 2, 0],
                    explicit_bounds=[0, 5, 10, 25],
                    max=24,
                    min=1,
                    start_time_unix_nano=0,
                    sum=70,
                    time_unix_nano=1,
                ),
                current_point,
                AggregationTemporality.CUMULATIVE,
            ),
            current_point,
        )

    def test_same_aggregation_temporality_delta(self):
        current_point = HistogramPoint(
            aggregation_temporality=AggregationTemporality.DELTA,
            bucket_counts=[0, 1, 3, 0, 0],
            explicit_bounds=[0, 5, 10, 25],
            max=9,
            min=1,
            start_time_unix_nano=1,
            sum=35,
            time_unix_nano=2,
        )

        self.assertEqual(
            _convert_aggregation_temporality(
                HistogramPoint(
                    aggregation_temporality=AggregationTemporality.CUMULATIVE,
                    bucket_counts=[0, 3, 4, 2, 0],
                    explicit_bounds=[0, 5, 10, 25],
                    max=24,
                    min=1,
                    start_time_unix_nano=0,
                    sum=105,
                    time_unix_nano=2,
                ),
                current_point,
                AggregationTemporality.DELTA,
            ),
            current_point,
        )

    def test_aggregation_temporality_to_cumulative(self):
        current_point = HistogramPoint(
            aggregation_temporality=AggregationTemporality.DELTA,
            bucket_counts=[0, 1, 3, 0, 0],
            explicit_bounds=[0, 5, 10, 25],
            max=24,
            min=1,
            start_time_unix_nano=1,
            sum=35,
            time_unix_nano=2,
        )

        self.assertEqual(
            _convert_aggregation_temporality(
                HistogramPoint(
                    aggregation_temporality=AggregationTemporality.CUMULATIVE,
                    bucket_counts=[0, 2, 1, 2, 0],
                    explicit_bounds=[0, 5, 10, 25],
                    max=24,
                    min=1,
                    start_time_unix_nano=0,
                    sum=70,
                    time_unix_nano=1,
                ),
                current_point,
                AggregationTemporality.CUMULATIVE,
            ),
            HistogramPoint(
                aggregation_temporality=AggregationTemporality.CUMULATIVE,
                bucket_counts=[0, 3, 4, 2, 0],
                explicit_bounds=[0, 5, 10, 25],
                max=24,
                min=1,
                start_time_unix_nano=0,
                sum=105,
                time_unix_nano=2,
            ),
        )

    def test_aggregation_temporality_to_delta(self):
        current_point = HistogramPoint(
            aggregation_temporality=AggregationTemporality.CUMULATIVE,
            bucket_counts=[0, 3, 4, 2, 0],
            explicit_bounds=[0, 5, 10, 25],
            max=22,
            min=3,
            start_time_unix_nano=0,
            sum=105,
            time_unix_nano=2,
        )

        self.assertEqual(
            _convert_aggregation_temporality(
                HistogramPoint(
                    aggregation_temporality=AggregationTemporality.CUMULATIVE,
                    bucket_counts=[0, 2, 1, 2, 0],
                    explicit_bounds=[0, 5, 10, 25],
                    max=24,
                    min=1,
                    start_time_unix_nano=0,
                    sum=70,
                    time_unix_nano=1,
                ),
                current_point,
                AggregationTemporality.DELTA,
            ),
            HistogramPoint(
                aggregation_temporality=AggregationTemporality.DELTA,
                bucket_counts=[0, 1, 3, 0, 0],
                explicit_bounds=[0, 5, 10, 25],
                max=22,
                min=3,
                start_time_unix_nano=1,
                sum=35,
                time_unix_nano=2,
            ),
        )


class TestAggregationFactory(TestCase):
    def test_sum_factory(self):
        counter = instrument.Counter("name", Mock(), Mock())
        factory = SumAggregation()
        aggregation = factory._create_aggregation(counter)
        self.assertIsInstance(aggregation, _SumAggregation)
        self.assertTrue(aggregation._instrument_is_monotonic)
        self.assertEqual(
            aggregation._instrument_temporality, AggregationTemporality.DELTA
        )
        aggregation2 = factory._create_aggregation(counter)
        self.assertNotEqual(aggregation, aggregation2)

        counter = instrument.UpDownCounter("name", Mock(), Mock())
        factory = SumAggregation()
        aggregation = factory._create_aggregation(counter)
        self.assertIsInstance(aggregation, _SumAggregation)
        self.assertFalse(aggregation._instrument_is_monotonic)
        self.assertEqual(
            aggregation._instrument_temporality, AggregationTemporality.DELTA
        )

        counter = instrument.ObservableCounter("name", Mock(), Mock(), None)
        factory = SumAggregation()
        aggregation = factory._create_aggregation(counter)
        self.assertIsInstance(aggregation, _SumAggregation)
        self.assertTrue(aggregation._instrument_is_monotonic)
        self.assertEqual(
            aggregation._instrument_temporality,
            AggregationTemporality.CUMULATIVE,
        )

    def test_explicit_bucket_histogram_factory(self):
        histo = instrument.Histogram("name", Mock(), Mock())
        factory = ExplicitBucketHistogramAggregation(
            boundaries=(
                0.0,
                5.0,
            ),
            record_min_max=False,
        )
        aggregation = factory._create_aggregation(histo)
        self.assertIsInstance(aggregation, _ExplicitBucketHistogramAggregation)
        self.assertFalse(aggregation._record_min_max)
        self.assertEqual(aggregation._boundaries, (0.0, 5.0))
        aggregation2 = factory._create_aggregation(histo)
        self.assertNotEqual(aggregation, aggregation2)

    def test_last_value_factory(self):
        counter = instrument.Counter("name", Mock(), Mock())
        factory = LastValueAggregation()
        aggregation = factory._create_aggregation(counter)
        self.assertIsInstance(aggregation, _LastValueAggregation)
        aggregation2 = factory._create_aggregation(counter)
        self.assertNotEqual(aggregation, aggregation2)


class TestDefaultAggregation(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.default_aggregation = DefaultAggregation()

    def test_counter(self):

        aggregation = self.default_aggregation._create_aggregation(
            Counter(Mock(), Mock(), Mock())
        )
        self.assertIsInstance(aggregation, _SumAggregation)
        self.assertTrue(aggregation._instrument_is_monotonic)
        self.assertEqual(
            aggregation._instrument_temporality, AggregationTemporality.DELTA
        )

    def test_up_down_counter(self):

        aggregation = self.default_aggregation._create_aggregation(
            UpDownCounter(Mock(), Mock(), Mock())
        )
        self.assertIsInstance(aggregation, _SumAggregation)
        self.assertFalse(aggregation._instrument_is_monotonic)
        self.assertEqual(
            aggregation._instrument_temporality, AggregationTemporality.DELTA
        )

    def test_observable_counter(self):

        aggregation = self.default_aggregation._create_aggregation(
            ObservableCounter(Mock(), Mock(), Mock(), callbacks=[Mock()])
        )
        self.assertIsInstance(aggregation, _SumAggregation)
        self.assertTrue(aggregation._instrument_is_monotonic)
        self.assertEqual(
            aggregation._instrument_temporality,
            AggregationTemporality.CUMULATIVE,
        )

    def test_observable_up_down_counter(self):

        aggregation = self.default_aggregation._create_aggregation(
            ObservableUpDownCounter(Mock(), Mock(), Mock(), callbacks=[Mock()])
        )
        self.assertIsInstance(aggregation, _SumAggregation)
        self.assertFalse(aggregation._instrument_is_monotonic)
        self.assertEqual(
            aggregation._instrument_temporality,
            AggregationTemporality.CUMULATIVE,
        )

    def test_histogram(self):

        aggregation = self.default_aggregation._create_aggregation(
            Histogram(
                Mock(),
                Mock(),
                Mock(),
                Mock(),
                Mock(),
            )
        )
        self.assertIsInstance(aggregation, _ExplicitBucketHistogramAggregation)

    def test_observable_gauge(self):

        aggregation = self.default_aggregation._create_aggregation(
            ObservableGauge(
                Mock(),
                Mock(),
                Mock(),
                callbacks=[Mock()],
            )
        )
        self.assertIsInstance(aggregation, _LastValueAggregation)
