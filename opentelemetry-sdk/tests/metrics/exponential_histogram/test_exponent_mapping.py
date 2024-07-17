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
from sys import float_info, version_info
from unittest.mock import patch

from pytest import mark

from opentelemetry.sdk.metrics._internal.exponential_histogram.mapping.errors import (
    MappingUnderflowError,
)
from opentelemetry.sdk.metrics._internal.exponential_histogram.mapping.exponent_mapping import (
    ExponentMapping,
)
from opentelemetry.sdk.metrics._internal.exponential_histogram.mapping.ieee_754 import (
    MAX_NORMAL_EXPONENT,
    MAX_NORMAL_VALUE,
    MIN_NORMAL_EXPONENT,
    MIN_NORMAL_VALUE,
)
from opentelemetry.test import TestCase

if version_info >= (3, 9):
    from math import nextafter


def right_boundary(scale: int, index: int) -> float:
    result = 2**index

    for _ in range(scale, 0):
        result = result * result

    return result


class TestExponentMapping(TestCase):
    def test_singleton(self):

        self.assertIs(ExponentMapping(-3), ExponentMapping(-3))
        self.assertIsNot(ExponentMapping(-3), ExponentMapping(-5))

    @patch(
        "opentelemetry.sdk.metrics._internal.exponential_histogram.mapping."
        "exponent_mapping.ExponentMapping._mappings",
        new={},
    )
    @patch(
        "opentelemetry.sdk.metrics._internal.exponential_histogram.mapping."
        "exponent_mapping.ExponentMapping._init"
    )
    def test_init_called_once(self, mock_init):  # pylint: disable=no-self-use

        ExponentMapping(-3)
        ExponentMapping(-3)

        mock_init.assert_called_once()

    def test_exponent_mapping_0(self):

        with self.assertNotRaises(Exception):
            ExponentMapping(0)

    def test_exponent_mapping_zero(self):

        exponent_mapping = ExponentMapping(0)

        # This is the equivalent to 1.1 in hexadecimal
        hex_1_1 = 1 + (1 / 16)

        # Testing with values near +inf
        self.assertEqual(
            exponent_mapping.map_to_index(MAX_NORMAL_VALUE),
            MAX_NORMAL_EXPONENT,
        )
        self.assertEqual(exponent_mapping.map_to_index(MAX_NORMAL_VALUE), 1023)
        self.assertEqual(exponent_mapping.map_to_index(2**1023), 1022)
        self.assertEqual(exponent_mapping.map_to_index(2**1022), 1021)
        self.assertEqual(
            exponent_mapping.map_to_index(hex_1_1 * (2**1023)), 1023
        )
        self.assertEqual(
            exponent_mapping.map_to_index(hex_1_1 * (2**1022)), 1022
        )

        # Testing with values near 1
        self.assertEqual(exponent_mapping.map_to_index(4), 1)
        self.assertEqual(exponent_mapping.map_to_index(3), 1)
        self.assertEqual(exponent_mapping.map_to_index(2), 0)
        self.assertEqual(exponent_mapping.map_to_index(1), -1)
        self.assertEqual(exponent_mapping.map_to_index(0.75), -1)
        self.assertEqual(exponent_mapping.map_to_index(0.51), -1)
        self.assertEqual(exponent_mapping.map_to_index(0.5), -2)
        self.assertEqual(exponent_mapping.map_to_index(0.26), -2)
        self.assertEqual(exponent_mapping.map_to_index(0.25), -3)
        self.assertEqual(exponent_mapping.map_to_index(0.126), -3)
        self.assertEqual(exponent_mapping.map_to_index(0.125), -4)

        # Testing with values near 0
        self.assertEqual(exponent_mapping.map_to_index(2**-1022), -1023)
        self.assertEqual(
            exponent_mapping.map_to_index(hex_1_1 * (2**-1022)), -1022
        )
        self.assertEqual(exponent_mapping.map_to_index(2**-1021), -1022)
        self.assertEqual(
            exponent_mapping.map_to_index(hex_1_1 * (2**-1021)), -1021
        )
        self.assertEqual(
            exponent_mapping.map_to_index(2**-1022), MIN_NORMAL_EXPONENT - 1
        )
        self.assertEqual(
            exponent_mapping.map_to_index(2**-1021), MIN_NORMAL_EXPONENT
        )
        # The smallest subnormal value is 2 **  -1074 = 5e-324.
        # This value is also the result of:
        # s = 1
        # while s / 2:
        #     s = s / 2
        # s == 5e-324
        self.assertEqual(
            exponent_mapping.map_to_index(2**-1074), MIN_NORMAL_EXPONENT - 1
        )

    def test_exponent_mapping_min_scale(self):

        exponent_mapping = ExponentMapping(ExponentMapping._min_scale)
        self.assertEqual(exponent_mapping.map_to_index(1.000001), 0)
        self.assertEqual(exponent_mapping.map_to_index(1), -1)
        self.assertEqual(exponent_mapping.map_to_index(float_info.max), 0)
        self.assertEqual(exponent_mapping.map_to_index(float_info.min), -1)

    def test_invalid_scale(self):
        with self.assertRaises(Exception):
            ExponentMapping(1)

        with self.assertRaises(Exception):
            ExponentMapping(ExponentMapping._min_scale - 1)

    def test_exponent_mapping_neg_one(self):
        exponent_mapping = ExponentMapping(-1)
        self.assertEqual(exponent_mapping.map_to_index(17), 2)
        self.assertEqual(exponent_mapping.map_to_index(16), 1)
        self.assertEqual(exponent_mapping.map_to_index(15), 1)
        self.assertEqual(exponent_mapping.map_to_index(9), 1)
        self.assertEqual(exponent_mapping.map_to_index(8), 1)
        self.assertEqual(exponent_mapping.map_to_index(5), 1)
        self.assertEqual(exponent_mapping.map_to_index(4), 0)
        self.assertEqual(exponent_mapping.map_to_index(3), 0)
        self.assertEqual(exponent_mapping.map_to_index(2), 0)
        self.assertEqual(exponent_mapping.map_to_index(1.5), 0)
        self.assertEqual(exponent_mapping.map_to_index(1), -1)
        self.assertEqual(exponent_mapping.map_to_index(0.75), -1)
        self.assertEqual(exponent_mapping.map_to_index(0.5), -1)
        self.assertEqual(exponent_mapping.map_to_index(0.25), -2)
        self.assertEqual(exponent_mapping.map_to_index(0.20), -2)
        self.assertEqual(exponent_mapping.map_to_index(0.13), -2)
        self.assertEqual(exponent_mapping.map_to_index(0.125), -2)
        self.assertEqual(exponent_mapping.map_to_index(0.10), -2)
        self.assertEqual(exponent_mapping.map_to_index(0.0625), -3)
        self.assertEqual(exponent_mapping.map_to_index(0.06), -3)

    def test_exponent_mapping_neg_four(self):
        # pylint: disable=too-many-statements
        exponent_mapping = ExponentMapping(-4)
        self.assertEqual(exponent_mapping.map_to_index(float(0x1)), -1)
        self.assertEqual(exponent_mapping.map_to_index(float(0x10)), 0)
        self.assertEqual(exponent_mapping.map_to_index(float(0x100)), 0)
        self.assertEqual(exponent_mapping.map_to_index(float(0x1000)), 0)
        self.assertEqual(
            exponent_mapping.map_to_index(float(0x10000)), 0
        )  # base == 2 **  16
        self.assertEqual(exponent_mapping.map_to_index(float(0x100000)), 1)
        self.assertEqual(exponent_mapping.map_to_index(float(0x1000000)), 1)
        self.assertEqual(exponent_mapping.map_to_index(float(0x10000000)), 1)
        self.assertEqual(
            exponent_mapping.map_to_index(float(0x100000000)), 1
        )  # base == 2 **  32

        self.assertEqual(exponent_mapping.map_to_index(float(0x1000000000)), 2)
        self.assertEqual(
            exponent_mapping.map_to_index(float(0x10000000000)), 2
        )
        self.assertEqual(
            exponent_mapping.map_to_index(float(0x100000000000)), 2
        )
        self.assertEqual(
            exponent_mapping.map_to_index(float(0x1000000000000)), 2
        )  # base == 2 **  48

        self.assertEqual(
            exponent_mapping.map_to_index(float(0x10000000000000)), 3
        )
        self.assertEqual(
            exponent_mapping.map_to_index(float(0x100000000000000)), 3
        )
        self.assertEqual(
            exponent_mapping.map_to_index(float(0x1000000000000000)), 3
        )
        self.assertEqual(
            exponent_mapping.map_to_index(float(0x10000000000000000)), 3
        )  # base == 2 **  64

        self.assertEqual(
            exponent_mapping.map_to_index(float(0x100000000000000000)), 4
        )
        self.assertEqual(
            exponent_mapping.map_to_index(float(0x1000000000000000000)), 4
        )
        self.assertEqual(
            exponent_mapping.map_to_index(float(0x10000000000000000000)), 4
        )
        self.assertEqual(
            exponent_mapping.map_to_index(float(0x100000000000000000000)), 4
        )  # base == 2 **  80
        self.assertEqual(
            exponent_mapping.map_to_index(float(0x1000000000000000000000)), 5
        )

        self.assertEqual(exponent_mapping.map_to_index(1 / float(0x1)), -1)
        self.assertEqual(exponent_mapping.map_to_index(1 / float(0x10)), -1)
        self.assertEqual(exponent_mapping.map_to_index(1 / float(0x100)), -1)
        self.assertEqual(exponent_mapping.map_to_index(1 / float(0x1000)), -1)
        self.assertEqual(
            exponent_mapping.map_to_index(1 / float(0x10000)), -2
        )  # base == 2 **  -16
        self.assertEqual(
            exponent_mapping.map_to_index(1 / float(0x100000)), -2
        )
        self.assertEqual(
            exponent_mapping.map_to_index(1 / float(0x1000000)), -2
        )
        self.assertEqual(
            exponent_mapping.map_to_index(1 / float(0x10000000)), -2
        )
        self.assertEqual(
            exponent_mapping.map_to_index(1 / float(0x100000000)), -3
        )  # base == 2 **  -32
        self.assertEqual(
            exponent_mapping.map_to_index(1 / float(0x1000000000)), -3
        )
        self.assertEqual(
            exponent_mapping.map_to_index(1 / float(0x10000000000)), -3
        )
        self.assertEqual(
            exponent_mapping.map_to_index(1 / float(0x100000000000)), -3
        )
        self.assertEqual(
            exponent_mapping.map_to_index(1 / float(0x1000000000000)), -4
        )  # base == 2 **  -32
        self.assertEqual(
            exponent_mapping.map_to_index(1 / float(0x10000000000000)), -4
        )
        self.assertEqual(
            exponent_mapping.map_to_index(1 / float(0x100000000000000)), -4
        )
        self.assertEqual(
            exponent_mapping.map_to_index(1 / float(0x1000000000000000)), -4
        )
        self.assertEqual(
            exponent_mapping.map_to_index(1 / float(0x10000000000000000)), -5
        )  # base == 2 **  -64
        self.assertEqual(
            exponent_mapping.map_to_index(1 / float(0x100000000000000000)), -5
        )

        self.assertEqual(exponent_mapping.map_to_index(float_info.max), 63)
        self.assertEqual(exponent_mapping.map_to_index(2**1023), 63)
        self.assertEqual(exponent_mapping.map_to_index(2**1019), 63)
        self.assertEqual(exponent_mapping.map_to_index(2**1009), 63)
        self.assertEqual(exponent_mapping.map_to_index(2**1008), 62)
        self.assertEqual(exponent_mapping.map_to_index(2**1007), 62)
        self.assertEqual(exponent_mapping.map_to_index(2**1000), 62)
        self.assertEqual(exponent_mapping.map_to_index(2**993), 62)
        self.assertEqual(exponent_mapping.map_to_index(2**992), 61)
        self.assertEqual(exponent_mapping.map_to_index(2**991), 61)

        self.assertEqual(exponent_mapping.map_to_index(2**-1074), -64)
        self.assertEqual(exponent_mapping.map_to_index(2**-1073), -64)
        self.assertEqual(exponent_mapping.map_to_index(2**-1072), -64)
        self.assertEqual(exponent_mapping.map_to_index(2**-1057), -64)
        self.assertEqual(exponent_mapping.map_to_index(2**-1056), -64)
        self.assertEqual(exponent_mapping.map_to_index(2**-1041), -64)
        self.assertEqual(exponent_mapping.map_to_index(2**-1040), -64)
        self.assertEqual(exponent_mapping.map_to_index(2**-1025), -64)
        self.assertEqual(exponent_mapping.map_to_index(2**-1024), -64)
        self.assertEqual(exponent_mapping.map_to_index(2**-1023), -64)
        self.assertEqual(exponent_mapping.map_to_index(2**-1022), -64)
        self.assertEqual(exponent_mapping.map_to_index(2**-1009), -64)
        self.assertEqual(exponent_mapping.map_to_index(2**-1008), -64)
        self.assertEqual(exponent_mapping.map_to_index(2**-1007), -63)
        self.assertEqual(exponent_mapping.map_to_index(2**-993), -63)
        self.assertEqual(exponent_mapping.map_to_index(2**-992), -63)
        self.assertEqual(exponent_mapping.map_to_index(2**-991), -62)
        self.assertEqual(exponent_mapping.map_to_index(2**-977), -62)
        self.assertEqual(exponent_mapping.map_to_index(2**-976), -62)
        self.assertEqual(exponent_mapping.map_to_index(2**-975), -61)

    def test_exponent_index_max(self):

        for scale in range(
            ExponentMapping._min_scale, ExponentMapping._max_scale
        ):
            exponent_mapping = ExponentMapping(scale)

            index = exponent_mapping.map_to_index(MAX_NORMAL_VALUE)

            max_index = ((MAX_NORMAL_EXPONENT + 1) >> -scale) - 1

            self.assertEqual(index, max_index)

            boundary = exponent_mapping.get_lower_boundary(index)

            self.assertEqual(boundary, right_boundary(scale, max_index))

            with self.assertRaises(Exception):
                exponent_mapping.get_lower_boundary(index + 1)

    @mark.skipif(
        version_info < (3, 9),
        reason="math.nextafter is only available for Python >= 3.9",
    )
    def test_exponent_index_min(self):
        for scale in range(
            ExponentMapping._min_scale, ExponentMapping._max_scale + 1
        ):
            exponent_mapping = ExponentMapping(scale)

            min_index = exponent_mapping.map_to_index(MIN_NORMAL_VALUE)
            boundary = exponent_mapping.get_lower_boundary(min_index)

            correct_min_index = MIN_NORMAL_EXPONENT >> -scale

            if MIN_NORMAL_EXPONENT % (1 << -scale) == 0:
                correct_min_index -= 1

            # We do not check for correct_min_index to be greater than the
            # smallest integer because the smallest integer in Python is -inf.

            self.assertEqual(correct_min_index, min_index)

            correct_boundary = right_boundary(scale, correct_min_index)

            self.assertEqual(correct_boundary, boundary)
            self.assertGreater(
                right_boundary(scale, correct_min_index + 1), boundary
            )

            self.assertEqual(
                correct_min_index,
                exponent_mapping.map_to_index(MIN_NORMAL_VALUE / 2),
            )
            self.assertEqual(
                correct_min_index,
                exponent_mapping.map_to_index(MIN_NORMAL_VALUE / 3),
            )
            self.assertEqual(
                correct_min_index,
                exponent_mapping.map_to_index(MIN_NORMAL_VALUE / 100),
            )
            self.assertEqual(
                correct_min_index, exponent_mapping.map_to_index(2**-1050)
            )
            self.assertEqual(
                correct_min_index, exponent_mapping.map_to_index(2**-1073)
            )
            self.assertEqual(
                correct_min_index,
                exponent_mapping.map_to_index(1.1 * (2**-1073)),
            )
            self.assertEqual(
                correct_min_index, exponent_mapping.map_to_index(2**-1074)
            )

            with self.assertRaises(MappingUnderflowError):
                exponent_mapping.get_lower_boundary(min_index - 1)

            self.assertEqual(
                exponent_mapping.map_to_index(
                    nextafter(MIN_NORMAL_VALUE, inf)
                ),
                MIN_NORMAL_EXPONENT >> -scale,
            )
