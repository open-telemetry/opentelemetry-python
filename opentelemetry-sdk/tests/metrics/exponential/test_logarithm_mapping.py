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

from opentelemetry.sdk.metrics._internal.exponential.float64 import (
    MAX_NORMAL_VALUE,
)
from opentelemetry.sdk.metrics._internal.exponential.logarithm_mapping import (
    LogarithmExponentialHistogramMapping,
)

MAX_NORMAL_VALUE


class TestLogarithmMapping(TestCase):
    def test_invalid_scale(self):
        with self.assertRaises(Exception):
            LogarithmExponentialHistogramMapping(-1)

    def test_logarithm_mapping_scale_one(self):

        # The exponentiation factor for this logarithm exponent histogram
        # mapping is square_root(2).
        # Scale 1 means 1 division between every power of two, having
        # a factor sqare_root(2) times the lower boundary.
        logarithm_exponent_histogram_mapping = (
            LogarithmExponentialHistogramMapping(1)
        )

        self.assertEqual(logarithm_exponent_histogram_mapping.scale, 1)

        # Note: Do not test exact boundaries, with the exception of
        # 1, because we expect errors in that case (e.g.,
        # MapToIndex(8) returns 5, an off-by-one.  See the following
        # test.
        self.assertEqual(
            logarithm_exponent_histogram_mapping.map_to_index(15), 7
        )
        self.assertEqual(
            logarithm_exponent_histogram_mapping.map_to_index(9), 6
        )
        self.assertEqual(
            logarithm_exponent_histogram_mapping.map_to_index(7), 5
        )
        self.assertEqual(
            logarithm_exponent_histogram_mapping.map_to_index(5), 4
        )
        self.assertEqual(
            logarithm_exponent_histogram_mapping.map_to_index(3), 3
        )
        self.assertEqual(
            logarithm_exponent_histogram_mapping.map_to_index(2.5), 2
        )
        self.assertEqual(
            logarithm_exponent_histogram_mapping.map_to_index(1.5), 1
        )
        self.assertEqual(
            logarithm_exponent_histogram_mapping.map_to_index(1.2), 0
        )
        # This one is actually an exact test
        self.assertEqual(
            logarithm_exponent_histogram_mapping.map_to_index(1), -1
        )
        self.assertEqual(
            logarithm_exponent_histogram_mapping.map_to_index(0.75), -1
        )
        self.assertEqual(
            logarithm_exponent_histogram_mapping.map_to_index(0.55), -2
        )
        self.assertEqual(
            logarithm_exponent_histogram_mapping.map_to_index(0.45), -3
        )

    def test_logarithm_boundary(self):

        for scale in [1, 2, 3, 4, 10, 15]:
            logarithm_exponent_histogram_mapping = (
                LogarithmExponentialHistogramMapping(scale)
            )

            for index in [-100, -10, -1, 0, 1, 10, 100]:

                lower_boundary = (
                    logarithm_exponent_histogram_mapping.get_lower_boundary(
                        index
                    )
                )

                mapped_index = (
                    logarithm_exponent_histogram_mapping.map_to_index(
                        lower_boundary
                    )
                )

                self.assertLessEqual(index - 1, mapped_index)
                self.assertGreaterEqual(index, mapped_index)

                # FIXME assert that the difference between lower boundary and
                # rounded lower boundary is very small.
