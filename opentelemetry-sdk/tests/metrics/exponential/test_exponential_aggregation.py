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
from random import random, seed
from sys import float_info
from typing import Sequence
from unittest import TestCase
from unittest.mock import Mock

from opentelemetry.sdk.metrics._internal.exponential.aggregation import (
    _ExponentialBucketHistogramAggregation,
)
from opentelemetry.sdk.metrics._internal.exponential.buckets import Buckets
from opentelemetry.sdk.metrics._internal.exponential.config import MIN_MAX_SIZE
from opentelemetry.sdk.metrics._internal.exponential.exponent import (
    MIN_SCALE as EXPONENT_MIN_SCALE,
)
from opentelemetry.sdk.metrics._internal.exponential.exponent import (
    ExponentMapping,
)
from opentelemetry.sdk.metrics._internal.exponential.exponential_histogram_mapping import (
    ExponentialHistogramMapping,
)
from opentelemetry.sdk.metrics._internal.exponential.float64 import (
    MAX_NORMAL_EXPONENT,
    MIN_NORMAL_EXPONENT,
)
from opentelemetry.sdk.metrics._internal.exponential.logarithm_mapping import (
    MAX_SCALE as LOGARITHM_MAX_SCALE,
)
from opentelemetry.sdk.metrics._internal.exponential.logarithm_mapping import (
    MIN_SCALE as LOGARITHM_MIN_SCALE,
)
from opentelemetry.sdk.metrics._internal.exponential.logarithm_mapping import (
    LogarithmExponentialHistogramMapping,
)
from opentelemetry.sdk.metrics._internal.measurement import Measurement


def get_counts(buckets: Buckets) -> int:

    counts = []

    for index in range(buckets.len()):
        counts.append(buckets.at(index))

    return counts


def center_val(mapping: ExponentialHistogramMapping, index: int) -> float:
    return (
        mapping.get_lower_boundary(index)
        + mapping.get_lower_boundary(index + 1)
    ) / 2


class TestAggregation(TestCase):
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
        self.assertEqual(a._scale, b._scale)

        self.assertEqual(a._positive.len(), b._positive.len())
        self.assertEqual(a._negative.len(), b._negative.len())

        for index in range(a._positive.len()):
            self.assertEqual(a._positive.at(index), b._positive.at(index))

        for index in range(a._negative.len()):
            self.assertEqual(a._negative.at(index), b._negative.at(index))

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
            exponential_histogram_aggregation._positive.offset(), -1
        )
        self.assertEqual(exponential_histogram_aggregation._scale, 0)
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
            exponential_histogram_aggregation._positive.offset(), -1
        )
        self.assertEqual(exponential_histogram_aggregation._scale, -1)
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
                    exponential_histogram_aggregation._scale, expected["scale"]
                )
                self.assertEqual(
                    exponential_histogram_aggregation._positive.offset(),
                    expected["offset"],
                )
                self.assertEqual(
                    exponential_histogram_aggregation._positive.len(),
                    expected["len"],
                )
                self.assertEqual(
                    exponential_histogram_aggregation._positive.at(0),
                    expected["at_0"],
                )
                self.assertEqual(
                    exponential_histogram_aggregation._positive.at(1),
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
                mapping = LogarithmExponentialHistogramMapping(init_scale)

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
                init_scale, exponential_histogram_aggregation._scale
            )
            self.assertEqual(
                offset, exponential_histogram_aggregation._positive.offset()
            )

            exponential_histogram_aggregation.aggregate(
                Measurement(max_val, Mock())
            )
            sum_ += max_val

            self.assertNotEqual(
                0, exponential_histogram_aggregation._positive.at(0)
            )

            # The maximum-index filled bucket is at or
            # above the mid-point, (otherwise we
            # downscaled too much).

            max_fill = 0
            total_count = 0

            for index in range(
                exponential_histogram_aggregation._positive.len()
            ):
                total_count += exponential_histogram_aggregation._positive.at(
                    index
                )
                if exponential_histogram_aggregation._positive.at(index) != 0:
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
                    exponential_histogram_aggregation._scale
                )
            else:
                mapping = LogarithmExponentialHistogramMapping(
                    exponential_histogram_aggregation._scale
                )
            index = mapping.map_to_index(min_val)

            self.assertEqual(
                index, exponential_histogram_aggregation._positive.offset()
            )

            index = mapping.map_to_index(max_val)

            self.assertEqual(
                index,
                exponential_histogram_aggregation._positive.offset()
                + exponential_histogram_aggregation._positive.len()
                - 1,
            )

    def test_merge_simple_event(self):

        exponential_histogram_aggregation_0 = (
            _ExponentialBucketHistogramAggregation(Mock(), Mock(), max_size=4)
        )
        exponential_histogram_aggregation_1 = (
            _ExponentialBucketHistogramAggregation(Mock(), Mock(), max_size=4)
        )
        exponential_histogram_aggregation_2 = (
            _ExponentialBucketHistogramAggregation(Mock(), Mock(), max_size=4)
        )
        exponential_histogram_aggregation_2._flag = True

        for index in range(4):
            value_0 = 2 << index
            value_1 = 1 / (1 << index)

            exponential_histogram_aggregation_0.aggregate(
                Measurement(value_0, Mock())
            )
            exponential_histogram_aggregation_1.aggregate(
                Measurement(value_1, Mock())
            )
            exponential_histogram_aggregation_2.aggregate(
                Measurement(value_0, Mock())
            )
            exponential_histogram_aggregation_2.aggregate(
                Measurement(value_1, Mock())
            )

        self.assertEqual(0, exponential_histogram_aggregation_0._scale)
        self.assertEqual(0, exponential_histogram_aggregation_1._scale)
        self.assertEqual(-1, exponential_histogram_aggregation_2._scale)

        self.assertEqual(
            0, exponential_histogram_aggregation_0._positive.offset()
        )
        self.assertEqual(
            -4, exponential_histogram_aggregation_1._positive.offset()
        )
        self.assertEqual(
            -2, exponential_histogram_aggregation_2._positive.offset()
        )

        self.assertEqual(
            [1, 1, 1, 1],
            get_counts(exponential_histogram_aggregation_0._positive),
        )
        self.assertEqual(
            [1, 1, 1, 1],
            get_counts(exponential_histogram_aggregation_1._positive),
        )
        self.assertEqual(
            [2, 2, 2, 2],
            get_counts(exponential_histogram_aggregation_2._positive),
        )

        exponential_histogram_aggregation_0._merge_from(
            exponential_histogram_aggregation_1
        )

        self.assertEqual(-1, exponential_histogram_aggregation_0._scale)
        self.assertEqual(-1, exponential_histogram_aggregation_2._scale)

        self.require_equal(
            exponential_histogram_aggregation_0,
            exponential_histogram_aggregation_2,
        )

    def test_merge_simple_odd(self):

        exponential_histogram_aggregation_0 = (
            _ExponentialBucketHistogramAggregation(Mock(), Mock(), max_size=4)
        )
        exponential_histogram_aggregation_1 = (
            _ExponentialBucketHistogramAggregation(Mock(), Mock(), max_size=4)
        )
        exponential_histogram_aggregation_2 = (
            _ExponentialBucketHistogramAggregation(Mock(), Mock(), max_size=4)
        )
        exponential_histogram_aggregation_2._flag = True

        for index in range(4):
            value_0 = 2 << index
            value_1 = 2 / (1 << index)

            exponential_histogram_aggregation_0.aggregate(
                Measurement(value_0, Mock())
            )
            exponential_histogram_aggregation_1.aggregate(
                Measurement(value_1, Mock())
            )
            exponential_histogram_aggregation_2.aggregate(
                Measurement(value_0, Mock())
            )
            exponential_histogram_aggregation_2.aggregate(
                Measurement(value_1, Mock())
            )

        self.assertEqual(4, exponential_histogram_aggregation_0._count)
        self.assertEqual(4, exponential_histogram_aggregation_1._count)
        self.assertEqual(8, exponential_histogram_aggregation_2._count)

        self.assertEqual(0, exponential_histogram_aggregation_0._scale)
        self.assertEqual(0, exponential_histogram_aggregation_1._scale)
        self.assertEqual(-1, exponential_histogram_aggregation_2._scale)

        self.assertEqual(
            0, exponential_histogram_aggregation_0._positive.offset()
        )
        self.assertEqual(
            -3, exponential_histogram_aggregation_1._positive.offset()
        )
        self.assertEqual(
            -2, exponential_histogram_aggregation_2._positive.offset()
        )

        self.assertEqual(
            [1, 1, 1, 1],
            get_counts(exponential_histogram_aggregation_0._positive),
        )
        self.assertEqual(
            [1, 1, 1, 1],
            get_counts(exponential_histogram_aggregation_1._positive),
        )
        self.assertEqual(
            [1, 2, 3, 2],
            get_counts(exponential_histogram_aggregation_2._positive),
        )

        exponential_histogram_aggregation_0._merge_from(
            exponential_histogram_aggregation_1
        )

        self.assertEqual(-1, exponential_histogram_aggregation_0._scale)
        self.assertEqual(-1, exponential_histogram_aggregation_2._scale)

        self.require_equal(
            exponential_histogram_aggregation_0,
            exponential_histogram_aggregation_2,
        )

    def test_merge_exhaustive(self):

        factor = 1024.0
        count = 16

        means = [0.0, factor]
        stddevs = [1.0, factor]

        for mean in means:
            for stddev in stddevs:
                seed(77777677777)

                values = []

                for _ in range(count):
                    # FIXME random() is not equivalent to the corresponding
                    # function in the Go implementation.
                    values.append(mean + random() * stddev)

                for partition in range(1, count):

                    for size in [2, 6, 8, 9, 16]:
                        for incr in [
                            int(1),
                            int(0x100),
                            int(0x10000),
                            int(0x100000000),
                        ]:
                            self._test_merge_exhaustive(
                                values[0:partition],
                                values[partition:count],
                                size,
                                incr,
                            )

    def _test_merge_exhaustive(
        self,
        values_0: Sequence[float],
        values_1: Sequence[float],
        size: int,
        incr: int,
    ):

        exponential_histogram_aggregation_0 = (
            _ExponentialBucketHistogramAggregation(
                Mock(), Mock(), max_size=size
            )
        )
        exponential_histogram_aggregation_1 = (
            _ExponentialBucketHistogramAggregation(
                Mock(), Mock(), max_size=size
            )
        )
        exponential_histogram_aggregation_2 = (
            _ExponentialBucketHistogramAggregation(
                Mock(), Mock(), max_size=size
            )
        )

        for value_0 in values_0:
            exponential_histogram_aggregation_0._update_by_incr(value_0, incr)
            exponential_histogram_aggregation_2._update_by_incr(value_0, incr)

        for value_1 in values_1:
            exponential_histogram_aggregation_1._update_by_incr(value_1, incr)
            exponential_histogram_aggregation_2._update_by_incr(value_1, incr)

        exponential_histogram_aggregation_0._merge_from(
            exponential_histogram_aggregation_1
        )

        self.require_equal(
            exponential_histogram_aggregation_2,
            exponential_histogram_aggregation_0,
        )

    def test_integer_aggregation(self):
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
            exponential_histogram_aggregation_1.aggregate(
                Measurement(index, Mock())
            )

        self.assertEqual(expect, exponential_histogram_aggregation_0._sum)
        self.assertEqual(255, exponential_histogram_aggregation_0._count)

        # Scale should be 5. The upper power-of-two is 256 == 2 ** 8. The
        # exponential base 2 ** (2 ** -5) raised to the 256th power should be
        # 256:
        # 2 ** ((2 ** -5) * 256) =
        # 2 ** ((2 ** -5) * (2 ** 8)) =
        # 2 ** (2 ** 3) =
        # 2 ** 8

        scale = exponential_histogram_aggregation_0._scale
        self.assertEqual(5, scale)

        def expect_0(buckets: Buckets):
            self.assertEqual(0, buckets.len())

        def expect_256(buckets: Buckets, factor: int):
            # The minimum value 2 has index (1 << scale) - 1, which determines
            # the length and the offset:

            self.assertEqual(256 - ((1 << scale) - 1), buckets.len())
            self.assertEqual((1 << scale) - 1, buckets.offset())

            for index in range(256):
                self.assertLessEqual(buckets.at(index), int(6 * factor))

        expect_256(exponential_histogram_aggregation_0._positive, 1)
        expect_0(exponential_histogram_aggregation_0._negative)

        exponential_histogram_aggregation_0._merge_from(
            exponential_histogram_aggregation_1
        )
        expect_256(exponential_histogram_aggregation_0._positive, 2)

        self.assertEqual(2 * expect, exponential_histogram_aggregation_0._sum)

        exponential_histogram_aggregation_0._clear()
        exponential_histogram_aggregation_1._clear()

        expect = 0

        for index in range(2, 257):
            expect -= index

            exponential_histogram_aggregation_0.aggregate(
                Measurement(-index, Mock())
            )
            exponential_histogram_aggregation_1.aggregate(
                Measurement(-index, Mock())
            )

        self.assertEqual(expect, exponential_histogram_aggregation_0._sum)
        self.assertEqual(255, exponential_histogram_aggregation_0._count)

        expect_256(exponential_histogram_aggregation_0._negative, 1)
        expect_0(exponential_histogram_aggregation_0._positive)

        exponential_histogram_aggregation_0._merge_from(
            exponential_histogram_aggregation_1
        )

        expect_256(exponential_histogram_aggregation_0._negative, 2)

        self.assertEqual(2 * expect, exponential_histogram_aggregation_0._sum)
        self.assertEqual(5, exponential_histogram_aggregation_0._scale)

    def test_reset(self):

        exponential_histogram_aggregation = (
            _ExponentialBucketHistogramAggregation(
                Mock(), Mock(), max_size=256
            )
        )

        for incr in [0x1, 0x100, 0x10000, 0x100000000, 0x200000000]:
            exponential_histogram_aggregation._clear()

            self.assertEqual(0, exponential_histogram_aggregation._scale)
            expect = 0

            for index in range(2, 257):
                expect += index * incr
                exponential_histogram_aggregation._update_by_incr(index, incr)

            self.assertEqual(expect, exponential_histogram_aggregation._sum)
            self.assertEqual(
                255 * incr, exponential_histogram_aggregation._count
            )

            # See test_integer_aggregation about why scale is 5, len is
            # 256 - (1 << scale)- 1 and offset is (1 << scale) - 1.
            scale = exponential_histogram_aggregation._scale
            self.assertEqual(5, scale)

            self.assertEqual(
                256 - ((1 << scale) - 1),
                exponential_histogram_aggregation._positive.len(),
            )
            self.assertEqual(
                (1 << scale) - 1,
                exponential_histogram_aggregation._positive.offset(),
            )

            for index in range(0, 256):
                self.assertLessEqual(
                    exponential_histogram_aggregation._positive.at(index),
                    6 * incr,
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

        exponential_histogram_aggregation_0._swap(
            exponential_histogram_aggregation_1
        )

        self.assertEqual(0, exponential_histogram_aggregation_0._sum)
        self.assertEqual(0, exponential_histogram_aggregation_0._count)
        self.assertEqual(0, exponential_histogram_aggregation_0._zero_count)
        self.assertEqual(0, exponential_histogram_aggregation_0._scale)

        self.assertEqual(expect, exponential_histogram_aggregation_1._sum)
        self.assertEqual(255 * 2, exponential_histogram_aggregation_1._count)
        self.assertEqual(255, exponential_histogram_aggregation_1._zero_count)

        scale = exponential_histogram_aggregation_1._scale
        self.assertEqual(5, scale)

        self.assertEqual(
            256 - ((1 << scale) - 1),
            exponential_histogram_aggregation_1._positive.len(),
        )
        self.assertEqual(
            (1 << scale) - 1,
            exponential_histogram_aggregation_1._positive.offset(),
        )

        for index in range(0, 256):
            self.assertLessEqual(
                exponential_histogram_aggregation_1._positive.at(index), 6
            )

    def test_very_large_numbers(self):

        exponential_histogram_aggregation = (
            _ExponentialBucketHistogramAggregation(Mock(), Mock(), max_size=2)
        )

        def expect_balanced(count: int):
            self.assertEqual(
                2, exponential_histogram_aggregation._positive.len()
            )
            self.assertEqual(
                -1, exponential_histogram_aggregation._positive.offset()
            )
            self.assertEqual(
                count, exponential_histogram_aggregation._positive.at(0)
            )
            self.assertEqual(
                count, exponential_histogram_aggregation._positive.at(1)
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
        self.assertEqual(-7, exponential_histogram_aggregation._scale)

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
        self.assertEqual(-7, exponential_histogram_aggregation._scale)

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
        self.assertEqual(-8, exponential_histogram_aggregation._scale)

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
            EXPONENT_MIN_SCALE, exponential_histogram_aggregation._scale
        )

        self.assertEqual(
            MIN_MAX_SIZE, exponential_histogram_aggregation._positive.len()
        )
        self.assertEqual(
            -1, exponential_histogram_aggregation._positive.offset()
        )
        self.assertLessEqual(
            exponential_histogram_aggregation._positive.at(0), 2
        )
        self.assertLessEqual(
            exponential_histogram_aggregation._positive.at(1), 1
        )

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

        exponential_histogram_aggregation_0._swap(
            exponential_histogram_aggregation_1
        )
        exponential_histogram_aggregation_1._copy_into(
            exponential_histogram_aggregation_2
        )

        self.require_equal(
            exponential_histogram_aggregation_1,
            exponential_histogram_aggregation_2,
        )

    def test_zero_count_by_incr(self):

        exponential_histogram_aggregation_0 = (
            _ExponentialBucketHistogramAggregation(Mock(), Mock())
        )
        for _ in range(10):
            exponential_histogram_aggregation_0.aggregate(
                Measurement(0, Mock())
            )
        exponential_histogram_aggregation_1 = (
            _ExponentialBucketHistogramAggregation(Mock(), Mock())
        )

        exponential_histogram_aggregation_1._update_by_incr(0, 10)

        self.require_equal(
            exponential_histogram_aggregation_0,
            exponential_histogram_aggregation_1,
        )

    def test_boundary_statistics(self):

        total = MAX_NORMAL_EXPONENT - MIN_NORMAL_EXPONENT + 1

        for scale in range(LOGARITHM_MIN_SCALE, LOGARITHM_MAX_SCALE + 1):

            above = 0
            below = 0

            if scale <= 0:
                mapping = ExponentMapping(scale)
            else:
                mapping = LogarithmExponentialHistogramMapping(scale)

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
