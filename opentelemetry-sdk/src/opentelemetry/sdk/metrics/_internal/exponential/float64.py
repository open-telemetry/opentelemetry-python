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

import ctypes
from decimal import Decimal
from sys import float_info

# An IEEE 754 double-precision (64 bit) floating point number is represented
# as: 1 bit for sign, 11 bits for exponent and 52 bits for significand. Since
# these numbers are in a normalized form (in scientific notation), the first
# bit of the significand will always be 1. Because of that, that bit is not
# stored but implicit, to make room for one more bit and more precision.

SIGNIFICAND_WIDTH = 52
EXPONENT_WIDTH = 11

# This mask is equivalent to 52 "1" bits (there are 13 hexadecimal 4-bit "f"s
# in the significand mask, 13 * 4 == 52) or 0xfffffffffffff in hexadecimal.
SIGNIFICAND_MASK = (1 << SIGNIFICAND_WIDTH) - 1

# There are 11 bits for the exponent, but the exponent bias values 0 (11 "0"
# bits) and 2047 (11 "1" bits) have special meanings so the exponent range is
# from 1 to 2046. To calculate the exponent value, 1023 is subtracted from the
# exponent, so the exponent value range is from -1022 to +1023.
EXPONENT_BIAS = (2 ** (EXPONENT_WIDTH - 1)) - 1

# All the exponent mask bits are set to 1 for the 11 exponent bits.
EXPONENT_MASK = ((1 << EXPONENT_WIDTH) - 1) << SIGNIFICAND_WIDTH

# The exponent mask bit is to 1 for the sign bit.
SIGN_MASK = 1 << (EXPONENT_WIDTH + SIGNIFICAND_WIDTH)

MIN_NORMAL_EXPONENT = -EXPONENT_BIAS + 1
MAX_NORMAL_EXPONENT = EXPONENT_BIAS

# Smallest possible normal value (2.2250738585072014e-308)
# This value is the result of using the smallest possible number in the
# mantissa, 1.0000000000000000000000000000000000000000000000000000 (52 "0"s in
# the fractional part) = 1.0000000000000000 and a single "1" in the exponent.
# Finally 1.0000000000000000 * 2 ** -1022 = 2.2250738585072014e-308.
MIN_NORMAL_VALUE = float_info.min

# Greatest possible normal value (1.7976931348623157e+308)
# The binary representation of a float in scientific notation uses (for the
# significand) one bit for the integer part (which is implicit) and 52 bits for
# the fractional part. Consider a float binary 1.111. It is equal to 1 + 1/2 +
# 1/4 + 1/8. The greatest possible value in the 52-bit significand would be
# then 1.1111111111111111111111111111111111111111111111111111 (52 "1"s in the
# fractional part) = 1.9999999999999998. Finally,
# 1.9999999999999998 * 2 ** 1023 = 1.7976931348623157e+308.
MAX_NORMAL_VALUE = float_info.max


def get_ieee_754_64_binary(value: float):
    """
    The purpose of this function is to more easily illustrate the IEEE 754
    64-bit float representation.
    """
    result = bin(ctypes.c_uint64.from_buffer(ctypes.c_double(value)).value)[2:]

    if result == "0":
        result = result * 64

    if value > 0:
        result = f"0{result}"

    decimal_exponent = 0

    exponent = result[1:12]

    for index, bit in enumerate(reversed(exponent)):
        if int(bit):
            decimal_exponent += 2**index

    # 0 has a special representation in IEE 574, all exponent and mantissa bits
    # are 0. The sign bit still represents its sign, so there is 0 (all bits
    # are set to 0) and -0 (the first bit is 1, the rest are 0).
    if value == 0:
        implicit_bit = 0
    else:
        implicit_bit = 1

    decimal_exponent -= 1023 * implicit_bit

    decimal_mantissa = Decimal(implicit_bit)

    mantissa = result[12:]

    for index, bit in enumerate(mantissa):
        if int(bit):
            decimal_mantissa += Decimal(1) / Decimal(2 ** (index + 1))

    sign = result[0]

    return {
        "sign": sign,
        "exponent": exponent,
        "mantissa": mantissa,
        # IEEE 754 can only exactly represent a discrete series of numbers, the
        # intention of this field is to show the actual decimal value that is
        # represented.
        "decimal": str(
            Decimal(-1 if int(sign) else 1)
            * Decimal(2**decimal_exponent)
            * decimal_mantissa
        ),
    }


def get_ieee_754_exponent(value: float) -> int:
    """
    Gets the exponent of the IEEE 754 representation of a float.
    """

    # 0000 -> 0
    # 0001 -> 1
    # 0010 -> 2
    # 0011 -> 3

    # 0100 -> 4
    # 0101 -> 5
    # 0110 -> 6
    # 0111 -> 7

    # 1000 -> 8
    # 1001 -> 9
    # 1010 -> 10
    # 1011 -> 11

    # 1100 -> 12
    # 1101 -> 13
    # 1110 -> 14
    # 1111 -> 15

    # 0 & 10 == 0
    # 1 & 10 == 0
    # 2 & 10 == 2
    # 3 & 10 == 2
    # 4 & 10 == 0
    # 6 & 10 == 2

    # 12 >> 2 == 3
    # 1 >> 2 == 0

    return (
        (
            # This step gives the integer that corresponds to the IEEE 754
            # representation of a float.
            ctypes.c_uint64.from_buffer(ctypes.c_double(value)).value
            # This step isolates the exponent bits, turning every bit
            # outside of the exponent field to 0.
            & EXPONENT_MASK
        )
        # This step moves the exponent bits to the right, removing the
        # mantissa bits that were set to 0 by the previous step. This
        # leaves the IEEE 754 exponent value, ready for the next step.
        >> SIGNIFICAND_WIDTH
        # This step subtracts the exponent bias from the IEEE 754 value,
        # leaving the actual exponent value.
    ) - EXPONENT_BIAS


def get_ieee_754_significand(value: float) -> int:
    return (
        ctypes.c_uint64.from_buffer(ctypes.c_double(value)).value
        # This stepe isolates the significand bits. There is no need to do any
        # bit shifting as the significand bits are already the rightmost field
        # in an IEEE 754 representation.
        & SIGNIFICAND_MASK
    )
