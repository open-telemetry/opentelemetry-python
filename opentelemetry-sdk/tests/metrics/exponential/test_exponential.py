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
    get_ieee_754_64_binary,
)


class TestExponential(TestCase):
    def test_get_ieee_754_64_binary(self):
        """
        Bit 0: 1 for negative values, 0 for positive values
        Bits 1 - 11: exponent, subtract 1023 from it to get the actual value
        Bits 12 - 63: mantissa, a leading 1 is implicit
        """

        # 0
        # 10000000001 == 1025 -> 1025 - 1023 == 2
        # 0000000000000000000000000000000000000000000000000000

        result = get_ieee_754_64_binary(4.0)

        self.assertEqual(result["sign"], "0")
        self.assertEqual(result["exponent"], "10000000001")
        self.assertEqual(
            result["mantissa"],
            "0000000000000000000000000000000000000000000000000000",
        )
        self.assertEqual(result["decimal"], "4")

        result = get_ieee_754_64_binary(4.5)

        self.assertEqual(result["sign"], "0")
        self.assertEqual(result["exponent"], "10000000001")
        self.assertEqual(
            result["mantissa"],
            "0010000000000000000000000000000000000000000000000000",
        )
        self.assertEqual(result["decimal"], "4.500")

        result = get_ieee_754_64_binary(-4.5)

        self.assertEqual(result["sign"], "1")
        self.assertEqual(result["exponent"], "10000000001")
        self.assertEqual(
            result["mantissa"],
            "0010000000000000000000000000000000000000000000000000",
        )
        self.assertEqual(result["decimal"], "-4.500")

        result = get_ieee_754_64_binary(0.0)

        self.assertEqual(result["sign"], "0")
        self.assertEqual(result["exponent"], "00000000000")
        self.assertEqual(
            result["mantissa"],
            "0000000000000000000000000000000000000000000000000000",
        )
        self.assertEqual(result["decimal"], "0")

        result = get_ieee_754_64_binary(-0.0)

        self.assertEqual(result["sign"], "1")
        self.assertEqual(result["exponent"], "00000000000")
        self.assertEqual(
            result["mantissa"],
            "0000000000000000000000000000000000000000000000000000",
        )
        self.assertEqual(result["decimal"], "-0")

        result = get_ieee_754_64_binary(4.3)

        self.assertEqual(result["sign"], "0")
        self.assertEqual(result["exponent"], "10000000001")
        self.assertEqual(
            result["mantissa"],
            "0001001100110011001100110011001100110011001100110011",
        )
        self.assertEqual(result["decimal"], "4.299999999999999822364316064")
