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

from itertools import permutations
from math import ldexp
from sys import float_info
from types import MethodType
from unittest import TestCase
from unittest.mock import Mock, patch

from opentelemetry.sdk.metrics._internal.aggregation import (
    AggregationTemporality,
    _ExponentialBucketHistogramAggregation,
)
from opentelemetry.sdk.metrics._internal.exponential_histogram.buckets import (
    Buckets,
)
from opentelemetry.sdk.metrics._internal.exponential_histogram.mapping.exponent_mapping import (
    ExponentMapping,
)
from opentelemetry.sdk.metrics._internal.exponential_histogram.mapping.ieee_754 import (
    MAX_NORMAL_EXPONENT,
    MIN_NORMAL_EXPONENT,
)
from opentelemetry.sdk.metrics._internal.exponential_histogram.mapping.logarithm_mapping import (
    LogarithmMapping,
)
from opentelemetry.sdk.metrics._internal.measurement import Measurement


def get_counts(buckets: Buckets) -> int:

    counts = []

    for index in range(len(buckets)):
        counts.append(buckets[index])

    return counts


def center_val(mapping: ExponentMapping, index: int) -> float:
    return (
        mapping.get_lower_boundary(index)
        + mapping.get_lower_boundary(index + 1)
    ) / 2


def swap(
    first: _ExponentialBucketHistogramAggregation,
    second: _ExponentialBucketHistogramAggregation,
):

    for attribute in [
        "_positive",
        "_negative",
        "_sum",
        "_count",
        "_zero_count",
        "_min",
        "_max",
        "_mapping",
    ]:
        temp = getattr(first, attribute)
        setattr(first, attribute, getattr(second, attribute))
        setattr(second, attribute, temp)


class TestExponentialBucketHistogramAggregation(TestCase):
    def assertInEpsilon(self, first, second, epsilon):
        self.assertLessEqual(first, (second * (1 + epsilon)))
        self.assertGreaterEqual(first, (second * (1 - epsilon)))

    def require_equal(self, a, b):

        if a._sum == 0 or b._sum == 0:
            self.assertAlmostEqual(a._sum, b._sum, 1e-6)
        else:
            self.assertInEpsilon(a._sum, b._sum, 1e-6)

        self.assertEqual(a._count, b._count)
        self.assertEqual(a._zero_count, b._zero_count)

        self.assertEqual(a._mapping.scale, b._mapping.scale)

        self.assertEqual(len(a._positive), len(b._positive))
        self.assertEqual(len(a._negative), len(b._negative))

        for index in range(len(a._positive)):
            self.assertEqual(a._positive[index], b._positive[index])

        for index in range(len(a._negative)):
            self.assertEqual(a._negative[index], b._negative[index])

    def test_alternating_growth_0(self):
        """
        Tests insertion of [2, 4, 1].  The index of 2 (i.e., 0) becomes
        `indexBase`, the 4 goes to its right and the 1 goes in the last
        position of the backing array.  With 3 binary orders of magnitude
        and MaxSize=4, this must finish with scale=0; with minimum value 1
        this must finish with offset=-1 (all scales).

        """

        # The corresponding Go test is TestAlternatingGrowth1 where:
        # agg := NewFloat64(NewConfig(WithMaxSize(4)))
        # agg is an instance of github.com/lightstep/otel-launcher-go/lightstep/sdk/metric/aggregator/histogram/structure.Histogram[float64]

        exponential_histogram_aggregation = (
            _ExponentialBucketHistogramAggregation(Mock(), Mock(), max_size=4)
        )

        exponential_histogram_aggregation.aggregate(Measurement(2, Mock()))
        exponential_histogram_aggregation.aggregate(Measurement(4, Mock()))
        exponential_histogram_aggregation.aggregate(Measurement(1, Mock()))

        self.assertEqual(
            exponential_histogram_aggregation._positive.offset, -1
        )
        self.assertEqual(exponential_histogram_aggregation._mapping.scale, 0)
        self.assertEqual(
            get_counts(exponential_histogram_aggregation._positive), [1, 1, 1]
        )

    def test_alternating_growth_1(self):
        """
        Tests insertion of [2, 2, 4, 1, 8, 0.5].  The test proceeds as¶
        above but then downscales once further to scale=-1, thus index -1¶
        holds range [0.25, 1.0), index 0 holds range [1.0, 4), index 1¶
        holds range [4, 16).¶
        """

        exponential_histogram_aggregation = (
            _ExponentialBucketHistogramAggregation(Mock(), Mock(), max_size=4)
        )

        exponential_histogram_aggregation.aggregate(Measurement(2, Mock()))
        exponential_histogram_aggregation.aggregate(Measurement(2, Mock()))
        exponential_histogram_aggregation.aggregate(Measurement(2, Mock()))
        exponential_histogram_aggregation.aggregate(Measurement(1, Mock()))
        exponential_histogram_aggregation.aggregate(Measurement(8, Mock()))
        exponential_histogram_aggregation.aggregate(Measurement(0.5, Mock()))

        self.assertEqual(
            exponential_histogram_aggregation._positive.offset, -1
        )
        self.assertEqual(exponential_histogram_aggregation._mapping.scale, -1)
        self.assertEqual(
            get_counts(exponential_histogram_aggregation._positive), [2, 3, 1]
        )

    def test_permutations(self):
        """
        Tests that every permutation of certain sequences with maxSize=2
        results¶ in the same scale=-1 histogram.
        """

        for test_values, expected in [
            [
                [0.5, 1.0, 2.0],
                {
                    "scale": -1,
                    "offset": -1,
                    "len": 2,
                    "at_0": 2,
                    "at_1": 1,
                },
            ],
            [
                [1.0, 2.0, 4.0],
                {
                    "scale": -1,
                    "offset": -1,
                    "len": 2,
                    "at_0": 1,
                    "at_1": 2,
                },
            ],
            [
                [0.25, 0.5, 1],
                {
                    "scale": -1,
                    "offset": -2,
                    "len": 2,
                    "at_0": 1,
                    "at_1": 2,
                },
            ],
        ]:

            for permutation in permutations(test_values):

                exponential_histogram_aggregation = (
                    _ExponentialBucketHistogramAggregation(
                        Mock(), Mock(), max_size=2
                    )
                )

                for value in permutation:

                    exponential_histogram_aggregation.aggregate(
                        Measurement(value, Mock())
                    )

                self.assertEqual(
                    exponential_histogram_aggregation._mapping.scale,
                    expected["scale"],
                )
                self.assertEqual(
                    exponential_histogram_aggregation._positive.offset,
                    expected["offset"],
                )
                self.assertEqual(
                    len(exponential_histogram_aggregation._positive),
                    expected["len"],
                )
                self.assertEqual(
                    exponential_histogram_aggregation._positive[0],
                    expected["at_0"],
                )
                self.assertEqual(
                    exponential_histogram_aggregation._positive[1],
                    expected["at_1"],
                )

    def test_ascending_sequence(self):

        for max_size in [3, 4, 6, 9]:
            for offset in range(-5, 6):
                for init_scale in [0, 4]:
                    self.ascending_sequence_test(max_size, offset, init_scale)

    def ascending_sequence_test(
        self, max_size: int, offset: int, init_scale: int
    ):

        for step in range(max_size, max_size * 4):

            exponential_histogram_aggregation = (
                _ExponentialBucketHistogramAggregation(
                    Mock(), Mock(), max_size=max_size
                )
            )

            if init_scale <= 0:
                mapping = ExponentMapping(init_scale)
            else:
                mapping = LogarithmMapping(init_scale)

            min_val = center_val(mapping, offset)
            max_val = center_val(mapping, offset + step)

            sum_ = 0.0

            for index in range(max_size):
                value = center_val(mapping, offset + index)
                exponential_histogram_aggregation.aggregate(
                    Measurement(value, Mock())
                )
                sum_ += value

            self.assertEqual(
                init_scale, exponential_histogram_aggregation._mapping._scale
            )
            self.assertEqual(
                offset, exponential_histogram_aggregation._positive.offset
            )

            exponential_histogram_aggregation.aggregate(
                Measurement(max_val, Mock())
            )
            sum_ += max_val

            self.assertNotEqual(
                0, exponential_histogram_aggregation._positive[0]
            )

            # The maximum-index filled bucket is at or
            # above the mid-point, (otherwise we
            # downscaled too much).

            max_fill = 0
            total_count = 0

            for index in range(
                len(exponential_histogram_aggregation._positive)
            ):
                total_count += exponential_histogram_aggregation._positive[
                    index
                ]
                if exponential_histogram_aggregation._positive[index] != 0:
                    max_fill = index

            # FIXME the corresponding Go code is
            # require.GreaterOrEqual(t, maxFill, uint32(maxSize)/2), make sure
            # this is actually equivalent.
            self.assertGreaterEqual(max_fill, int(max_size / 2))

            self.assertGreaterEqual(max_size + 1, total_count)
            self.assertGreaterEqual(
                max_size + 1, exponential_histogram_aggregation._count
            )
            self.assertGreaterEqual(
                sum_, exponential_histogram_aggregation._sum
            )

            if init_scale <= 0:
                mapping = ExponentMapping(
                    exponential_histogram_aggregation._mapping.scale
                )
            else:
                mapping = LogarithmMapping(
                    exponential_histogram_aggregation._mapping.scale
                )
            index = mapping.map_to_index(min_val)

            self.assertEqual(
                index, exponential_histogram_aggregation._positive.offset
            )

            index = mapping.map_to_index(max_val)

            self.assertEqual(
                index,
                exponential_histogram_aggregation._positive.offset
                + len(exponential_histogram_aggregation._positive)
                - 1,
            )

    def test_reset(self):

        for increment in [0x1, 0x100, 0x10000, 0x100000000, 0x200000000]:

            def mock_increment(self, bucket_index: int) -> None:
                """
                Increments a bucket
                """

                self._counts[bucket_index] += increment

            exponential_histogram_aggregation = (
                _ExponentialBucketHistogramAggregation(
                    Mock(), Mock(), max_size=256
                )
            )

            self.assertEqual(
                exponential_histogram_aggregation._count,
                exponential_histogram_aggregation._zero_count,
            )
            self.assertEqual(0, exponential_histogram_aggregation._sum)
            expect = 0

            for value in range(2, 257):
                expect += value * increment
                with patch.object(
                    exponential_histogram_aggregation._positive,
                    "increment_bucket",
                    # new=positive_mock
                    MethodType(
                        mock_increment,
                        exponential_histogram_aggregation._positive,
                    ),
                ):
                    exponential_histogram_aggregation.aggregate(
                        Measurement(value, Mock())
                    )
            exponential_histogram_aggregation._count *= increment
            exponential_histogram_aggregation._sum *= increment

            self.assertEqual(expect, exponential_histogram_aggregation._sum)
            self.assertEqual(
                255 * increment, exponential_histogram_aggregation._count
            )

            # See test_integer_aggregation about why scale is 5, len is
            # 256 - (1 << scale)- 1 and offset is (1 << scale) - 1.
            scale = exponential_histogram_aggregation._mapping.scale
            self.assertEqual(5, scale)

            self.assertEqual(
                256 - ((1 << scale) - 1),
                len(exponential_histogram_aggregation._positive),
            )
            self.assertEqual(
                (1 << scale) - 1,
                exponential_histogram_aggregation._positive.offset,
            )

            for index in range(0, 256):
                self.assertLessEqual(
                    exponential_histogram_aggregation._positive[index],
                    6 * increment,
                )

    def test_move_into(self):

        exponential_histogram_aggregation_0 = (
            _ExponentialBucketHistogramAggregation(
                Mock(), Mock(), max_size=256
            )
        )
        exponential_histogram_aggregation_1 = (
            _ExponentialBucketHistogramAggregation(
                Mock(), Mock(), max_size=256
            )
        )

        expect = 0

        for index in range(2, 257):
            expect += index
            exponential_histogram_aggregation_0.aggregate(
                Measurement(index, Mock())
            )
            exponential_histogram_aggregation_0.aggregate(
                Measurement(0, Mock())
            )

        swap(
            exponential_histogram_aggregation_0,
            exponential_histogram_aggregation_1,
        )

        self.assertEqual(0, exponential_histogram_aggregation_0._sum)
        self.assertEqual(0, exponential_histogram_aggregation_0._count)
        self.assertEqual(0, exponential_histogram_aggregation_0._zero_count)

        self.assertEqual(expect, exponential_histogram_aggregation_1._sum)
        self.assertEqual(255 * 2, exponential_histogram_aggregation_1._count)
        self.assertEqual(255, exponential_histogram_aggregation_1._zero_count)

        scale = exponential_histogram_aggregation_1._mapping.scale
        self.assertEqual(5, scale)

        self.assertEqual(
            256 - ((1 << scale) - 1),
            len(exponential_histogram_aggregation_1._positive),
        )
        self.assertEqual(
            (1 << scale) - 1,
            exponential_histogram_aggregation_1._positive.offset,
        )

        for index in range(0, 256):
            self.assertLessEqual(
                exponential_histogram_aggregation_1._positive[index], 6
            )

    def test_very_large_numbers(self):

        exponential_histogram_aggregation = (
            _ExponentialBucketHistogramAggregation(Mock(), Mock(), max_size=2)
        )

        def expect_balanced(count: int):
            self.assertEqual(
                2, len(exponential_histogram_aggregation._positive)
            )
            self.assertEqual(
                -1, exponential_histogram_aggregation._positive.offset
            )
            self.assertEqual(
                count, exponential_histogram_aggregation._positive[0]
            )
            self.assertEqual(
                count, exponential_histogram_aggregation._positive[1]
            )

        exponential_histogram_aggregation.aggregate(
            Measurement(2**-100, Mock())
        )
        exponential_histogram_aggregation.aggregate(
            Measurement(2**100, Mock())
        )

        self.assertLessEqual(
            2**100, (exponential_histogram_aggregation._sum * (1 + 1e-5))
        )
        self.assertGreaterEqual(
            2**100, (exponential_histogram_aggregation._sum * (1 - 1e-5))
        )

        self.assertEqual(2, exponential_histogram_aggregation._count)
        self.assertEqual(-7, exponential_histogram_aggregation._mapping.scale)

        expect_balanced(1)

        exponential_histogram_aggregation.aggregate(
            Measurement(2**-127, Mock())
        )
        exponential_histogram_aggregation.aggregate(
            Measurement(2**128, Mock())
        )

        self.assertLessEqual(
            2**128, (exponential_histogram_aggregation._sum * (1 + 1e-5))
        )
        self.assertGreaterEqual(
            2**128, (exponential_histogram_aggregation._sum * (1 - 1e-5))
        )

        self.assertEqual(4, exponential_histogram_aggregation._count)
        self.assertEqual(-7, exponential_histogram_aggregation._mapping.scale)

        expect_balanced(2)

        exponential_histogram_aggregation.aggregate(
            Measurement(2**-129, Mock())
        )
        exponential_histogram_aggregation.aggregate(
            Measurement(2**255, Mock())
        )

        self.assertLessEqual(
            2**255, (exponential_histogram_aggregation._sum * (1 + 1e-5))
        )
        self.assertGreaterEqual(
            2**255, (exponential_histogram_aggregation._sum * (1 - 1e-5))
        )
        self.assertEqual(6, exponential_histogram_aggregation._count)
        self.assertEqual(-8, exponential_histogram_aggregation._mapping.scale)

        expect_balanced(3)

    def test_full_range(self):

        exponential_histogram_aggregation = (
            _ExponentialBucketHistogramAggregation(Mock(), Mock(), max_size=2)
        )

        exponential_histogram_aggregation.aggregate(
            Measurement(float_info.max, Mock())
        )
        exponential_histogram_aggregation.aggregate(Measurement(1, Mock()))
        exponential_histogram_aggregation.aggregate(
            Measurement(2**-1074, Mock())
        )

        self.assertEqual(
            float_info.max, exponential_histogram_aggregation._sum
        )
        self.assertEqual(3, exponential_histogram_aggregation._count)
        self.assertEqual(
            ExponentMapping._min_scale,
            exponential_histogram_aggregation._mapping.scale,
        )

        self.assertEqual(
            _ExponentialBucketHistogramAggregation._min_max_size,
            len(exponential_histogram_aggregation._positive),
        )
        self.assertEqual(
            -1, exponential_histogram_aggregation._positive.offset
        )
        self.assertLessEqual(exponential_histogram_aggregation._positive[0], 2)
        self.assertLessEqual(exponential_histogram_aggregation._positive[1], 1)

    def test_aggregator_min_max(self):

        exponential_histogram_aggregation = (
            _ExponentialBucketHistogramAggregation(Mock(), Mock())
        )

        for value in [1, 3, 5, 7, 9]:
            exponential_histogram_aggregation.aggregate(
                Measurement(value, Mock())
            )

        self.assertEqual(1, exponential_histogram_aggregation._min)
        self.assertEqual(9, exponential_histogram_aggregation._max)

        exponential_histogram_aggregation = (
            _ExponentialBucketHistogramAggregation(Mock(), Mock())
        )

        for value in [-1, -3, -5, -7, -9]:
            exponential_histogram_aggregation.aggregate(
                Measurement(value, Mock())
            )

        self.assertEqual(-9, exponential_histogram_aggregation._min)
        self.assertEqual(-1, exponential_histogram_aggregation._max)

    def test_aggregator_copy_swap(self):

        exponential_histogram_aggregation_0 = (
            _ExponentialBucketHistogramAggregation(Mock(), Mock())
        )
        for value in [1, 3, 5, 7, 9, -1, -3, -5]:
            exponential_histogram_aggregation_0.aggregate(
                Measurement(value, Mock())
            )
        exponential_histogram_aggregation_1 = (
            _ExponentialBucketHistogramAggregation(Mock(), Mock())
        )
        for value in [5, 4, 3, 2]:
            exponential_histogram_aggregation_1.aggregate(
                Measurement(value, Mock())
            )
        exponential_histogram_aggregation_2 = (
            _ExponentialBucketHistogramAggregation(Mock(), Mock())
        )

        swap(
            exponential_histogram_aggregation_0,
            exponential_histogram_aggregation_1,
        )

        exponential_histogram_aggregation_2._positive.__init__()
        exponential_histogram_aggregation_2._negative.__init__()
        exponential_histogram_aggregation_2._sum = 0
        exponential_histogram_aggregation_2._count = 0
        exponential_histogram_aggregation_2._zero_count = 0
        exponential_histogram_aggregation_2._min = 0
        exponential_histogram_aggregation_2._max = 0
        exponential_histogram_aggregation_2._mapping = LogarithmMapping(
            LogarithmMapping._max_scale
        )

        for attribute in [
            "_positive",
            "_negative",
            "_sum",
            "_count",
            "_zero_count",
            "_min",
            "_max",
            "_mapping",
        ]:
            setattr(
                exponential_histogram_aggregation_2,
                attribute,
                getattr(exponential_histogram_aggregation_1, attribute),
            )

        self.require_equal(
            exponential_histogram_aggregation_1,
            exponential_histogram_aggregation_2,
        )

    def test_zero_count_by_increment(self):

        exponential_histogram_aggregation_0 = (
            _ExponentialBucketHistogramAggregation(Mock(), Mock())
        )

        increment = 10

        for _ in range(increment):
            exponential_histogram_aggregation_0.aggregate(
                Measurement(0, Mock())
            )
        exponential_histogram_aggregation_1 = (
            _ExponentialBucketHistogramAggregation(Mock(), Mock())
        )

        # positive_mock = Mock(wraps=exponential_histogram_aggregation_1._positive)
        def mock_increment(self, bucket_index: int) -> None:
            """
            Increments a bucket
            """

            self._counts[bucket_index] += increment

        with patch.object(
            exponential_histogram_aggregation_1._positive,
            "increment_bucket",
            # new=positive_mock
            MethodType(
                mock_increment, exponential_histogram_aggregation_1._positive
            ),
        ):
            exponential_histogram_aggregation_1.aggregate(
                Measurement(0, Mock())
            )
            exponential_histogram_aggregation_1._count *= increment
            exponential_histogram_aggregation_1._zero_count *= increment

        self.require_equal(
            exponential_histogram_aggregation_0,
            exponential_histogram_aggregation_1,
        )

    def test_one_count_by_increment(self):

        exponential_histogram_aggregation_0 = (
            _ExponentialBucketHistogramAggregation(Mock(), Mock())
        )

        increment = 10

        for _ in range(increment):
            exponential_histogram_aggregation_0.aggregate(
                Measurement(1, Mock())
            )
        exponential_histogram_aggregation_1 = (
            _ExponentialBucketHistogramAggregation(Mock(), Mock())
        )

        # positive_mock = Mock(wraps=exponential_histogram_aggregation_1._positive)
        def mock_increment(self, bucket_index: int) -> None:
            """
            Increments a bucket
            """

            self._counts[bucket_index] += increment

        with patch.object(
            exponential_histogram_aggregation_1._positive,
            "increment_bucket",
            # new=positive_mock
            MethodType(
                mock_increment, exponential_histogram_aggregation_1._positive
            ),
        ):
            exponential_histogram_aggregation_1.aggregate(
                Measurement(1, Mock())
            )
            exponential_histogram_aggregation_1._count *= increment
            exponential_histogram_aggregation_1._sum *= increment

        self.require_equal(
            exponential_histogram_aggregation_0,
            exponential_histogram_aggregation_1,
        )

    def test_boundary_statistics(self):

        total = MAX_NORMAL_EXPONENT - MIN_NORMAL_EXPONENT + 1

        for scale in range(
            LogarithmMapping._min_scale, LogarithmMapping._max_scale + 1
        ):

            above = 0
            below = 0

            if scale <= 0:
                mapping = ExponentMapping(scale)
            else:
                mapping = LogarithmMapping(scale)

            for exp in range(MIN_NORMAL_EXPONENT, MAX_NORMAL_EXPONENT + 1):
                value = ldexp(1, exp)

                index = mapping.map_to_index(value)

                try:
                    boundary = mapping.get_lower_boundary(index + 1)
                except Exception as error:
                    raise error
                    self.fail(f"Unexpected exception {error} raised")

                if boundary < value:
                    above += 1
                elif boundary > value:
                    below += 1

            self.assertInEpsilon(0.5, above / total, 0.05)
            self.assertInEpsilon(0.5, below / total, 0.06)

    def test_min_max_size(self):
        """
        Tests that the minimum max_size is the right value.
        """

        exponential_histogram_aggregation = (
            _ExponentialBucketHistogramAggregation(
                Mock(),
                Mock(),
                max_size=_ExponentialBucketHistogramAggregation._min_max_size,
            )
        )

        # The minimum and maximum normal floating point values are used here to
        # make sure the mapping can contain the full range of values.
        exponential_histogram_aggregation.aggregate(Mock(value=float_info.min))
        exponential_histogram_aggregation.aggregate(Mock(value=float_info.max))

        # This means the smallest max_scale is enough for the full range of the
        # normal floating point values.
        self.assertEqual(
            len(exponential_histogram_aggregation._positive._counts),
            exponential_histogram_aggregation._min_max_size,
        )

    def test_aggregate_collect(self):
        """
        Tests a repeated cycle of aggregation and collection.
        """
        """
        try:
            exponential_histogram_aggregation = (
                _ExponentialBucketHistogramAggregation(
                    Mock(),
                    Mock(),
                )
            )

            exponential_histogram_aggregation.aggregate(Measurement(2, Mock()))
            exponential_histogram_aggregation.collect(
                AggregationTemporality.CUMULATIVE, 0
            )
            exponential_histogram_aggregation.aggregate(Measurement(2, Mock()))
            exponential_histogram_aggregation.collect(
                AggregationTemporality.CUMULATIVE, 0
            )
            exponential_histogram_aggregation.aggregate(Measurement(2, Mock()))
            exponential_histogram_aggregation.collect(
                AggregationTemporality.CUMULATIVE, 0
            )
        except Exception as error:
            self.fail(f"Unexpected exception raised: {error}")
        """
        exponential_histogram_aggregation = (
            _ExponentialBucketHistogramAggregation(
                Mock(),
                Mock(),
            )
        )

        exponential_histogram_aggregation.aggregate(Measurement(2, Mock()))
        exponential_histogram_aggregation.collect(
            AggregationTemporality.CUMULATIVE, 0
        )
        exponential_histogram_aggregation.aggregate(Measurement(2, Mock()))
        exponential_histogram_aggregation.collect(
            AggregationTemporality.CUMULATIVE, 0
        )
        exponential_histogram_aggregation.aggregate(Measurement(2, Mock()))
        exponential_histogram_aggregation.collect(
            AggregationTemporality.CUMULATIVE, 0
        )

    def test_collect_results_cumulative(self):
        exponential_histogram_aggregation = (
            _ExponentialBucketHistogramAggregation(
                Mock(),
                Mock(),
            )
        )

        self.assertEqual(exponential_histogram_aggregation._mapping._scale, 20)

        exponential_histogram_aggregation.aggregate(Measurement(2, Mock()))
        self.assertEqual(exponential_histogram_aggregation._mapping._scale, 20)

        exponential_histogram_aggregation.aggregate(Measurement(4, Mock()))
        self.assertEqual(exponential_histogram_aggregation._mapping._scale, 7)

        exponential_histogram_aggregation.aggregate(Measurement(1, Mock()))
        self.assertEqual(exponential_histogram_aggregation._mapping._scale, 6)

        collection_0 = exponential_histogram_aggregation.collect(
            AggregationTemporality.CUMULATIVE, Mock()
        )

        self.assertEqual(len(collection_0.positive.bucket_counts), 160)

        self.assertEqual(collection_0.count, 3)
        self.assertEqual(collection_0.sum, 7)
        self.assertEqual(collection_0.scale, 6)
        self.assertEqual(collection_0.zero_count, 0)
        self.assertEqual(
            collection_0.positive.bucket_counts,
            [1, *[0] * 63, 1, *[0] * 31, 1, *[0] * 63],
        )
        self.assertEqual(collection_0.flags, 0)
        self.assertEqual(collection_0.min, 1)
        self.assertEqual(collection_0.max, 4)

        exponential_histogram_aggregation.aggregate(Measurement(1, Mock()))
        exponential_histogram_aggregation.aggregate(Measurement(8, Mock()))
        exponential_histogram_aggregation.aggregate(Measurement(0.5, Mock()))
        exponential_histogram_aggregation.aggregate(Measurement(0.1, Mock()))
        exponential_histogram_aggregation.aggregate(Measurement(0.045, Mock()))

        collection_1 = exponential_histogram_aggregation.collect(
            AggregationTemporality.CUMULATIVE, Mock()
        )

        previous_count = collection_1.positive.bucket_counts[0]

        count_counts = [[previous_count, 0]]

        for count in collection_1.positive.bucket_counts:
            if count == previous_count:
                count_counts[-1][1] += 1
            else:
                previous_count = count
                count_counts.append([previous_count, 1])

        self.assertEqual(collection_1.count, 5)
        self.assertEqual(collection_1.sum, 16.645)
        self.assertEqual(collection_1.scale, 4)
        self.assertEqual(collection_1.zero_count, 0)

        self.assertEqual(
            collection_1.positive.bucket_counts,
            [
                1,
                *[0] * 15,
                1,
                *[0] * 47,
                1,
                *[0] * 40,
                1,
                *[0] * 17,
                1,
                *[0] * 36,
            ],
        )
        self.assertEqual(collection_1.flags, 0)
        self.assertEqual(collection_1.min, 0.045)
        self.assertEqual(collection_1.max, 8)

    def test_merge_collect_cumulative(self):
        exponential_histogram_aggregation = (
            _ExponentialBucketHistogramAggregation(Mock(), Mock(), max_size=4)
        )

        for value in [2, 4, 8, 16]:
            exponential_histogram_aggregation.aggregate(
                Measurement(value, Mock())
            )

        self.assertEqual(exponential_histogram_aggregation._mapping.scale, 0)
        self.assertEqual(exponential_histogram_aggregation._positive.offset, 0)
        self.assertEqual(
            exponential_histogram_aggregation._positive.counts, [1, 1, 1, 1]
        )

        result = exponential_histogram_aggregation.collect(
            AggregationTemporality.CUMULATIVE,
            0,
        )

        for value in [1, 2, 4, 8]:
            exponential_histogram_aggregation.aggregate(
                Measurement(1 / value, Mock())
            )

        self.assertEqual(exponential_histogram_aggregation._mapping.scale, 0)
        self.assertEqual(
            exponential_histogram_aggregation._positive.offset, -4
        )
        self.assertEqual(
            exponential_histogram_aggregation._positive.counts, [1, 1, 1, 1]
        )

        result_1 = exponential_histogram_aggregation.collect(
            AggregationTemporality.CUMULATIVE,
            0,
        )

        self.assertEqual(result.scale, result_1.scale)

    def test_merge_collect_delta(self):
        exponential_histogram_aggregation = (
            _ExponentialBucketHistogramAggregation(Mock(), Mock(), max_size=4)
        )

        for value in [2, 4, 8, 16]:
            exponential_histogram_aggregation.aggregate(
                Measurement(value, Mock())
            )

        self.assertEqual(exponential_histogram_aggregation._mapping.scale, 0)
        self.assertEqual(exponential_histogram_aggregation._positive.offset, 0)
        self.assertEqual(
            exponential_histogram_aggregation._positive.counts, [1, 1, 1, 1]
        )

        result = exponential_histogram_aggregation.collect(
            AggregationTemporality.DELTA,
            0,
        )

        for value in [1, 2, 4, 8]:
            exponential_histogram_aggregation.aggregate(
                Measurement(1 / value, Mock())
            )

        self.assertEqual(exponential_histogram_aggregation._mapping.scale, 0)
        self.assertEqual(
            exponential_histogram_aggregation._positive.offset, -4
        )
        self.assertEqual(
            exponential_histogram_aggregation._positive.counts, [1, 1, 1, 1]
        )

        result_1 = exponential_histogram_aggregation.collect(
            AggregationTemporality.DELTA,
            0,
        )

        self.assertEqual(result.scale, result_1.scale)
