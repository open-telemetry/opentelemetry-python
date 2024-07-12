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

from math import sqrt
from unittest import TestCase
from unittest.mock import patch

from opentelemetry.sdk.metrics._internal.exponential_histogram.mapping.errors import (
    MappingOverflowError,
    MappingUnderflowError,
)
from opentelemetry.sdk.metrics._internal.exponential_histogram.mapping.ieee_754 import (
    MAX_NORMAL_EXPONENT,
    MAX_NORMAL_VALUE,
    MIN_NORMAL_EXPONENT,
    MIN_NORMAL_VALUE,
)
from opentelemetry.sdk.metrics._internal.exponential_histogram.mapping.logarithm_mapping import (
    LogarithmMapping,
)


def left_boundary(scale: int, index: int) -> float:

    # This is implemented in this way to avoid using a third-party bigfloat
    # package. The Go implementation uses a bigfloat package that is part of
    # their standard library. The assumption here is that the smallest float
    # available in Python is 2  **  -1022 (from sys.float_info.min).
    while scale > 0:
        if index < -1022:
            index /= 2
            scale -= 1
        else:
            break

    result = 2**index

    for _ in range(scale, 0, -1):
        result = sqrt(result)

    return result


class TestLogarithmMapping(TestCase):
    # pylint: disable=invalid-name
    def assertInEpsilon(self, first, second, epsilon):
        self.assertLessEqual(first, (second * (1 + epsilon)))
        self.assertGreaterEqual(first, (second * (1 - epsilon)))

    @patch(
        "opentelemetry.sdk.metrics._internal.exponential_histogram.mapping."
        "logarithm_mapping.LogarithmMapping._mappings",
        new={},
    )
    @patch(
        "opentelemetry.sdk.metrics._internal.exponential_histogram.mapping."
        "logarithm_mapping.LogarithmMapping._init"
    )
    def test_init_called_once(self, mock_init):  # pylint: disable=no-self-use

        LogarithmMapping(3)
        LogarithmMapping(3)

        mock_init.assert_called_once()

    def test_invalid_scale(self):
        with self.assertRaises(Exception):
            LogarithmMapping(-1)

    def test_logarithm_mapping_scale_one(self):

        # The exponentiation factor for this logarithm exponent histogram
        # mapping is square_root(2).
        # Scale 1 means 1 division between every power of two, having
        # a factor sqare_root(2) times the lower boundary.
        logarithm_exponent_histogram_mapping = LogarithmMapping(1)

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
            logarithm_exponent_histogram_mapping = LogarithmMapping(scale)

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

                self.assertInEpsilon(
                    lower_boundary, left_boundary(scale, index), 1e-9
                )

    def test_logarithm_index_max(self):

        for scale in range(
            LogarithmMapping._min_scale, LogarithmMapping._max_scale + 1
        ):
            logarithm_mapping = LogarithmMapping(scale)

            index = logarithm_mapping.map_to_index(MAX_NORMAL_VALUE)

            max_index = ((MAX_NORMAL_EXPONENT + 1) << scale) - 1

            # We do not check for max_index to be lesser than the
            # greatest integer because the greatest integer in Python is inf.

            self.assertEqual(index, max_index)

            boundary = logarithm_mapping.get_lower_boundary(index)

            base = logarithm_mapping.get_lower_boundary(1)

            self.assertLess(boundary, MAX_NORMAL_VALUE)

            self.assertInEpsilon(
                (MAX_NORMAL_VALUE - boundary) / boundary, base - 1, 1e-6
            )

            with self.assertRaises(MappingOverflowError):
                logarithm_mapping.get_lower_boundary(index + 1)

            with self.assertRaises(MappingOverflowError):
                logarithm_mapping.get_lower_boundary(index + 2)

    def test_logarithm_index_min(self):
        for scale in range(
            LogarithmMapping._min_scale, LogarithmMapping._max_scale + 1
        ):
            logarithm_mapping = LogarithmMapping(scale)

            min_index = logarithm_mapping.map_to_index(MIN_NORMAL_VALUE)

            correct_min_index = (MIN_NORMAL_EXPONENT << scale) - 1
            self.assertEqual(min_index, correct_min_index)

            correct_mapped = left_boundary(scale, correct_min_index)
            self.assertLess(correct_mapped, MIN_NORMAL_VALUE)

            correct_mapped_upper = left_boundary(scale, correct_min_index + 1)
            self.assertEqual(correct_mapped_upper, MIN_NORMAL_VALUE)

            mapped = logarithm_mapping.get_lower_boundary(min_index + 1)

            self.assertInEpsilon(mapped, MIN_NORMAL_VALUE, 1e-6)

            self.assertEqual(
                logarithm_mapping.map_to_index(MIN_NORMAL_VALUE / 2),
                correct_min_index,
            )
            self.assertEqual(
                logarithm_mapping.map_to_index(MIN_NORMAL_VALUE / 3),
                correct_min_index,
            )
            self.assertEqual(
                logarithm_mapping.map_to_index(MIN_NORMAL_VALUE / 100),
                correct_min_index,
            )
            self.assertEqual(
                logarithm_mapping.map_to_index(2**-1050), correct_min_index
            )
            self.assertEqual(
                logarithm_mapping.map_to_index(2**-1073), correct_min_index
            )
            self.assertEqual(
                logarithm_mapping.map_to_index(1.1 * 2**-1073),
                correct_min_index,
            )
            self.assertEqual(
                logarithm_mapping.map_to_index(2**-1074), correct_min_index
            )

            mapped_lower = logarithm_mapping.get_lower_boundary(min_index)
            self.assertInEpsilon(correct_mapped, mapped_lower, 1e-6)

            with self.assertRaises(MappingUnderflowError):
                logarithm_mapping.get_lower_boundary(min_index - 1)
