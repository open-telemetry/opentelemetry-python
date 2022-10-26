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

from ctypes import c_double, c_uint64
from sys import float_info

# IEEE 754 is a standard that defines a way to represent floating point numbers
# (normalized and denormalized), and also special numbers like zero, infinite
# and NaN using 64-bit binary numbers. First we'll explain how floating point
# numbers are represented and special numbers will be explained later.
#
# IEEE 754 represents floating point numbers using an exponential notation with
# 4 components: sign, mantissa, base and exponent:
#
# floating_point_number = sign * mantissa * (base ** exponent)
#
# Here:
# 1. sign can be 1 or -1.
# 2. mantissa is a positive fractional number whose integer part is 1 for
#    normalized floating point numbers and 0 for denormalized floating point
#    numbers.
# 3. base is always 2.
# 4. exponent is an integer in the range [-1022, 1023] for normalized floating
#    point numbers and -1022 for denormalized floating point numbers.
#
# The smallest value a normalized floating point number can have is
# -1 * 1.0 * (2 ** -1022) == 2.2250738585072014e-308.
# As mentioned before, IEEE 754 defines how floating point numbers are
# represented using a 64-bit binary number, for this number:
#
# 1. The first bit represents the sign.
# 2. The next 11 bits represent the exponent.
# 3. The next 52 bits represent the mantissa.
#
# The sign is positive if the sign bit is 0 and negative if the sign bit is 1.
#
# There are 11 bits for the exponent
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


def get_ieee_754_exponent(value: float) -> int:
    """
    Gets the exponent of the IEEE 754 representation of a float.
    """

    return (
        (
            # This step gives the integer that corresponds to the IEEE 754
            # representation of a float. For example, consider
            # -MAX_NORMAL_VALUE for an example. We choose this value because
            # of its binary representation which makes easy to understand the
            # subsequent operations.
            #
            # c_uint64.from_buffer(c_double(-MAX_NORMAL_VALUE)).value == 18442240474082181119
            # bin(18442240474082181119) == '0b1111111111101111111111111111111111111111111111111111111111111111'
            #
            # The first bit of the previous binary number is the sign bit: 1 (1 means negative, 0 means positive)
            # The next 11 bits are the exponent bits: 11111111110
            # The next 52 bits are the significand bits: 1111111111111111111111111111111111111111111111111111
            #
            # This step isolates the exponent bits, turning every bit outside
            # of the exponent field (sign and significand bits) to 0.
            c_uint64.from_buffer(c_double(-MAX_NORMAL_VALUE)).value
            & EXPONENT_MASK
            # For the example this means:
            # 18442240474082181119 & EXPONENT_MASK == 9214364837600034816
            # bin(9214364837600034816) == '0b111111111100000000000000000000000000000000000000000000000000000'
            # Notice that the previous binary representation does not include
            # leading zeroes, so the sign bit is not included since it is a
            # zero.
        )
        # This step moves the exponent bits to the right, removing the
        # significand bits that were set to 0 by the previous step. This
        # leaves the IEEE 754 exponent value, ready for the next step.
        >> SIGNIFICAND_WIDTH
        # For the example this means:
        # 9214364837600034816 >> SIGNIFICAND_WIDTH == 2046
        # bin(2046) == '0b11111111110'
        # As shown above, these are the original 11 bits that correspond to the
        # exponent.
        # This step subtracts the exponent bias from the IEEE 754 value,
        # leaving the actual exponent value.
    ) - EXPONENT_BIAS
    # For the example this means:
    # 2046 - EXPONENT_BIAS == 1023
    # As mentioned in a comment above, the largest value for the exponent is


def get_ieee_754_significand(value: float) -> int:
    return (
        c_uint64.from_buffer(c_double(value)).value
        # This step isolates the significand bits. There is no need to do any
        # bit shifting as the significand bits are already the rightmost field
        # in an IEEE 754 representation.
        & SIGNIFICAND_MASK
    )
