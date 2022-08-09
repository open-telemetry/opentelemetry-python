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

from opentelemetry.sdk.metrics._internal.exponential.exponent import (
    ExponentMapping,
)
from opentelemetry.sdk.metrics._internal.exponential.float64 import (
    MAX_NORMAL_EXPONENT,
    MAX_NORMAL_VALUE,
    MIN_NORMAL_EXPONENT,
)


class TestExponentMapping(TestCase):
    def test_singleton(self):

        self.assertIs(ExponentMapping(-3), ExponentMapping(-3))
        self.assertIsNot(ExponentMapping(-3), ExponentMapping(-5))

    def test_exponent_mapping_0(self):

        try:
            ExponentMapping(0)

        except Exception as error:
            self.fail(f"Unexpected exception raised: {error}")

    def test_map_to_index(self):

        exponent_mapping = ExponentMapping(0)

        # This is the equivalent to 1.1 in hexadecimal
        hex_1_1 = 1 + (1 / 16)

        # Testing with values near +infinite
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
        # The smallest subnormal value in Python is 2 ** -1074 = 5e-324.
        # This value is also the result of:
        # s = 1
        # while s / 2:
        #     s = s / 2
        # s == 5e-324
        self.assertEqual(
            exponent_mapping.map_to_index(2**-1074), MIN_NORMAL_EXPONENT - 1
        )
