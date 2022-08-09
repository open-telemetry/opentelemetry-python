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

from math import ldexp

from opentelemetry.sdk.metrics._internal.exponential.exponential_histogram_mapping import (
    ExponentialHistogramMapping,
    ExponentialMappingOverflowError,
    ExponentialMappingUnderflowError,
)
from opentelemetry.sdk.metrics._internal.exponential.float64 import (
    MAX_NORMAL_EXPONENT,
    MIN_NORMAL_EXPONENT,
    MIN_NORMAL_VALUE,
    SIGNIFICAND_WIDTH,
    get_ieee_754_exponent,
    get_ieee_754_significand,
)

# The size of the exponential histogram buckets is determined by a parameter
# known as scale, larger values of scale will produce smaller buckets. Bucket
# boundaries of the exponential histogram are located at integer powers of the
# base, where:

# base = 2 ** (2 ** (-scale))

# MinScale defines the point at which the exponential mapping
# function becomes useless for float64. With scale -10, ignoring
# subnormal values, bucket indices range from -1 to 1.
MIN_SCALE = -10

# MaxScale is the largest scale supported by exponential mapping.  Use
# ../logarithm for larger scales.
MAX_SCALE = 0


# FIXME Fix this name
class ExponentMapping(ExponentialHistogramMapping):

    _exponent_mappings = {}

    def __new__(cls, scale):

        if scale > MAX_SCALE:
            raise Exception(f"scale is larger than {MAX_SCALE}")

        if scale < MIN_SCALE:
            raise Exception(f"scale is smaller than {MIN_SCALE}")

        if scale not in cls._exponent_mappings.keys():
            cls._exponent_mappings[scale] = super().__new__(cls)

        return cls._exponent_mappings[scale]

    def __init__(self, scale: int):
        super().__init__(scale)
        self._shift = -self._scale

    def _min_normal_lower_boundary_index(self) -> int:
        """
        Returns the largest index such that base ** index <=
        opentelemetry.sdk.metrics._internal.exponential.float64.MIN_VALUE.
        histogram bucket with this index covers the range
        (base**index, base**(index+1)], including MinValue.
        """
        index = MIN_NORMAL_EXPONENT >> self._shift

        if self._shift < 2:
            index -= 1

        return index

    def _max_normal_lower_boundary_index(self) -> int:
        """
        Returns the index such that base ** index equals the largest
        representable boundary.  A histogram bucket with this
        index covers the range ((2 ** 1024)/base, 2 ** 1024], which includes
        opentelemetry.sdk.metrics._internal.exponential.float64.MAX_VALUE.
        Note that this bucket is incomplete, since the upper
        boundary cannot be represented (FIXME Why?). One greater than this
        index corresponds with the bucket containing values > 2 ** 1024.
        """
        return MAX_NORMAL_EXPONENT >> self._shift

    def map_to_index(self, value: float) -> int:
        if value < MIN_NORMAL_VALUE:
            return self._min_normal_lower_boundary_index()

        exponent = get_ieee_754_exponent(value)

        # Positive integers are represented in binary as having an infinite
        # amount of leading zeroes, for example 2 is represented as ...00010.

        # A negative integer -x is represented in binary as the complement of
        # (x - 1). For example, -4 is represented as the complement of 4 - 1
        # == 3. 3 is represented as ...00011. Its compliment is ...11100, the
        # binary representation of -4.

        # get_ieee_754_significand(value) gets the positive integer made up
        # from the rightmost SIGNIFICAND_WIDTH bits (the mantissa) of the IEEE
        # 754 representation of value. If value is an exact power of 2, all
        # these SIGNIFICAND_WIDTH bits would be all zeroes, and when 1 is
        # subtracted the resulting value is -1. The binary representation of
        # -1 is ...111, so when these bits are right shifted SIGNIFICAND_WIDTH
        # places, the resulting value for correction is -1. If value is not an
        # exact power of 2, at least one of the rightmost SIGNIFICAND_WIDTH
        # bits would be 1 (even for values whose decimal part is 0, like 5.0
        # since the IEEE 754 of such number is too the product of a power of 2
        # (defined in the exponent part of the IEEE 754 representation) and the
        # value defined in the mantissa). Having at least one of the rightmost
        # SIGNIFICAND_WIDTH bit being 1 means that get_ieee_754(value) will
        # always be greater or equal to 1, and when 1 is subtracted, the
        # result will be greater or equal to 0, whose representation in binary
        # will be of at most SIGNIFICAND_WIDTH ones that have an infinite
        # amount of leading zeroes. When those SIGNIFICAND_WIDTH bits are
        # shifted to the right SIGNIFICAND_WIDTH places, the resulting value
        # will be 0.

        # In summary, correction will be -1 if value is a power of 2, 0 if not.

        # FIXME Document why we can assume value will not be 0, inf, or NaN.
        correction = (get_ieee_754_significand(value) - 1) >> SIGNIFICAND_WIDTH

        # FIXME understand this
        return (exponent + correction) >> self._shift

    # FIXME Should this be a property?
    def get_lower_boundary(self, index: int) -> float:
        if index < self._min_normal_lower_boundary_index():
            raise ExponentialMappingUnderflowError()

        if index > self._max_normal_lower_boundary_index():
            raise ExponentialMappingOverflowError()

        return ldexp(1, index << self._shift)

    @property
    def scale(self) -> int:
        return -self._shift
