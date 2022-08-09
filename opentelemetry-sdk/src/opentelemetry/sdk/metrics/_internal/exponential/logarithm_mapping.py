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

from math import exp, floor, ldexp, log
from threading import Lock

from opentelemetry.sdk.metrics._internal.exponential.exponential_histogram_mapping import (
    ExponentialHistogramMapping,
    ExponentialMappingOverflowError,
    ExponentialMappingUnderflowError,
)
from opentelemetry.sdk.metrics._internal.exponential.float64 import (
    MAX_NORMAL_EXPONENT,
    MIN_NORMAL_EXPONENT,
    MIN_NORMAL_VALUE,
    get_ieee_754_exponent,
    get_ieee_754_significand,
)

MIN_SCALE = 1
MAX_SCALE = 20


# FIXME Make sure this is a good name
class LogarithmExponentialHistogramMapping(ExponentialHistogramMapping):

    # FIXME make sure this is a good name
    _prebuilt_mappings = {}
    _prebuilt_mappings_lock = Lock()

    # MinScale ensures that the ../exponent mapper is used for
    # zero and negative scale values.  Do not use the logarithm
    # mapper for scales <= 0.
    _min_scale = MIN_SCALE

    # FIXME Go implementation uses a value of 20 here, find out the right
    # value for this implementation.
    _max_scale = MAX_SCALE

    def __new__(cls, scale: int):

        if scale > cls._max_scale:
            raise Exception(f"scale is larger than {cls._max_scale}")

        if scale < cls._min_scale:
            raise Exception(f"scale is smaller than {cls._min_scale}")

        if scale not in cls._prebuilt_mappings.keys():
            cls._prebuilt_mappings[scale] = super().__new__(cls)

        with cls._prebuilt_mappings_lock:
            if scale in cls._prebuilt_mappings:
                cls._prebuilt_mappings[scale] = super().__new__(cls)

        return cls._prebuilt_mappings[scale]

    def __init__(self, scale: int):

        super().__init__(scale)

        if scale < self._min_scale or scale > self._max_scale:
            raise Exception("Scale is out of bounds")

        # FIXME calculate the right value for self._max_index
        self._max_index = 1
        # FIXME calculate the right value for self._min_index
        self._min_index = 1
        # FIXME calculate the right value for self._scale_factor

        ln_2 = log(2)

        # scaleFactor is used and computed as follows:
        # index = log(value) / log(base)
        # = log(value) / log(2^(2^-scale))
        # = log(value) / (2^-scale * log(2))
        # = log(value) * (1/log(2) * 2^scale)
        # = log(value) * scaleFactor
        # where:
        # scaleFactor = (1/log(2) * 2^scale)
        # = math.Log2E * math.Exp2(scale)
        # = math.Ldexp(math.Log2E, scale)
        # Because multiplication is faster than division, we define scaleFactor as a multiplier.
        # This implementation was copied from a Java prototype. See:
        # https://github.com/newrelic-experimental/newrelic-sketch-java/blob/1ce245713603d61ba3a4510f6df930a5479cd3f6/src/main/java/com/newrelic/nrsketch/indexer/LogIndexer.java
        # for the equations used here.
        self._scale_factor = ldexp(1 / ln_2, scale)

        # log(boundary) = index * log(base)
        # log(boundary) = index * log(2^(2^-scale))
        # log(boundary) = index * 2^-scale * log(2)
        # boundary = exp(index * inverseFactor)
        # where:
        # inverseFactor = 2^-scale * log(2)
        # = math.Ldexp(math.Ln2, -scale)
        self._inverse_factor = ldexp(ln_2, -scale)

        # scale is between MinScale and MaxScale. The exponential
        # base is defined as 2**(2**(-scale)).
        self._scale = scale

    def _min_normal_lower_boundary_index(self) -> int:

        """
        minNormalLowerBoundaryIndex is the index such that base**index equals
        MinValue.  A histogram bucket with this index covers the range
        (MinValue, MinValue*base].  One less than this index corresponds
        with the bucket containing values <= MinValue.
        """
        return MIN_NORMAL_EXPONENT << self._scale

    def _max_normal_lower_boundary_index(self) -> int:

        """
        maxNormalLowerBoundaryIndex is the index such that base**index equals the
        greatest representable lower boundary.  A histogram bucket with this
        index covers the range (0x1p+1024/base, 0x1p+1024], which includes
        MaxValue; note that this bucket is incomplete, since the upper
        boundary cannot be represented.  One greater than this index
        corresponds with the bucket containing values > 0x1p1024.
        """
        return ((MAX_NORMAL_EXPONENT + 1) << self._scale) - 1

    def map_to_index(self, value: float) -> int:
        """
        MapToIndex maps positive floating point values to indexes
        corresponding to Scale().  Implementations are not expected
        to handle zeros, +Inf, NaN, or negative values.
        """

        # Note: we can assume not a 0, Inf, or NaN; positive sign bit.
        if value <= MIN_NORMAL_VALUE:
            return self._min_normal_lower_boundary_index() - 1

        # Exact power-of-two correctness: an optional special case.
        if get_ieee_754_significand(value) == 0:
            exponent = get_ieee_754_exponent(value)
            return (exponent << self._scale) - 1

        # Non-power of two cases.  Use Floor(x) to round the scaled
        # logarithm.  We could use Ceil(x)-1 to achieve the same
        # result, though Ceil() is typically defined as -Floor(-x)
        # and typically not performed in hardware, so this is likely
        # less code.
        index = floor(log(value) * self._scale_factor)

        max_ = self._max_normal_lower_boundary_index()

        if index >= max_:
            return max_
        return index

    def get_lower_boundary(self, index: int) -> float:
        """
        LowerBoundary returns the lower boundary of a given bucket
        index.  The index is expected to map onto a range that is
        at least partially inside the range of normalized floating
        point values.  If the corresponding bucket's upper boundary
        is less than or equal to 0x1p-1022, UnderflowError will be
        raised. If the corresponding bucket's lower boundary is
        greater than math.MaxFloat64, OverflowError will be raised.
        """

        # LowerBoundary implements mapping.Mapping.
        max_ = self._max_normal_lower_boundary_index()

        if index >= max_:
            if index == max_:
                # Note that the equation on the last line of this
                # function returns +Inf. Use the alternate equation.
                return 2 * exp(
                    index - (1 << self._scale) * self._inverse_factor
                )
            raise ExponentialMappingOverflowError()
        min_ = self._min_normal_lower_boundary_index()
        if index <= min_:
            if index == min_:
                return MIN_NORMAL_VALUE
            if index == min_ - 1:
                # Similar to the logic above, the math.Exp()
                # formulation is not accurate for subnormal
                # values.
                return (
                    exp(index + (1 << self._scale) * self._inverse_factor) / 2
                )
            raise ExponentialMappingUnderflowError()
        return exp(index * self._inverse_factor)

    @property
    def scale(self) -> int:
        """
        Scale returns the parameter that controls the resolution of
        this mapping.  For details see:
        https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/metrics/datamodel.md#exponential-scale
        """

        return self._scale
