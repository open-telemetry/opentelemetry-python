# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""The mapping used for exponential histogram scales of 0 and below."""

from math import ldexp
from threading import Lock

from opentelemetry.sdk.metrics._internal.exponential_histogram.mapping import (
    Mapping,
)
from opentelemetry.sdk.metrics._internal.exponential_histogram.mapping.errors import (
    MappingOverflowError,
    MappingUnderflowError,
)
from opentelemetry.sdk.metrics._internal.exponential_histogram.mapping.ieee_754 import (
    MANTISSA_WIDTH,
    MAX_NORMAL_EXPONENT,
    MIN_NORMAL_EXPONENT,
    MIN_NORMAL_VALUE,
    get_ieee_754_exponent,
    get_ieee_754_mantissa,
)


class ExponentMapping(Mapping):
    """Maps a value to a bucket index by reading its IEEE 754 exponent.

    This mapping covers scales -10 through 0. At scale 0 a bucket holds
    exactly one power of two, so the index is the exponent of the value,
    and each step down merges two neighbouring buckets, which is a right
    shift of the exponent by ``-scale``. No logarithm is computed.

    Scales of 1 and above belong to ``LogarithmMapping``, where a power of
    two is split across several buckets and the exponent alone no longer
    determines the index.

    Args:
        scale: Resolution of the mapping, from -10 to 0.
            ``Mapping.__new__`` returns the single cached instance for
            that scale.
    """

    # Reference implementation here:
    # https://github.com/open-telemetry/opentelemetry-go/blob/0e6f9c29c10d6078e8131418e1d1d166c7195d61/sdk/metric/aggregator/exponential/mapping/exponent/exponent.go

    _mappings = {}
    _mappings_lock = Lock()

    _min_scale = -10
    _max_scale = 0

    def _get_min_scale(self):
        """Return the lowest scale this mapping serves.

        Returns:
            -10, below which the mapping stops being useful for 64-bit
            floats: at scale -10 every normal value already falls into one
            of the two buckets with index -1 or 0, and
            ``get_lower_boundary(1)`` raises ``MappingOverflowError``.
        """
        # _min_scale defines the point at which the exponential mapping
        # function becomes useless for 64-bit floats. With scale -10, ignoring
        # subnormal values, bucket indices range from -1 to 1.
        return -10

    def _get_max_scale(self):
        """Return the highest scale this mapping serves.

        Returns:
            0. A positive scale splits one power of two across several
            buckets, which reading the exponent cannot express, so those
            scales go to ``LogarithmMapping``.
        """
        # _max_scale is the largest scale supported by exponential mapping. Use
        # a logarithm mapping for larger scales.
        return 0

    def _init(self, scale: int):
        """Precompute the lowest and highest usable bucket indexes.

        ``Mapping._init`` runs first and rejects a scale outside -10 to 0.
        ``_min_normal_lower_boundary_index`` ends up as the index of the
        bucket that contains the smallest normal float, and
        ``_max_normal_lower_boundary_index`` as the index of the bucket
        containing the largest one. At scales -1 and 0 the smallest normal
        float is itself a bucket boundary, so the index is lowered by one
        to keep that value inside the bucket rather than at its edge.

        Args:
            scale: Resolution of the mapping, from -10 to 0.

        Raises:
            Exception: If ``scale`` is outside that range.
        """
        # pylint: disable=attribute-defined-outside-init

        super()._init(scale)

        # self._min_normal_lower_boundary_index is the largest index such that
        # base ** index < MIN_NORMAL_VALUE and
        # base ** (index + 1) >= MIN_NORMAL_VALUE. An exponential histogram
        # bucket with this index covers the range
        # (base ** index, base (index + 1)], including MIN_NORMAL_VALUE. This
        # is the smallest valid index that contains at least one normal value.
        index = MIN_NORMAL_EXPONENT >> -self._scale

        if -self._scale < 2:
            # For scales -1 and 0, the maximum value 2 ** -1022 is a
            # power-of-two multiple, meaning base ** index == MIN_NORMAL_VALUE.
            # Subtracting 1 so that base ** (index + 1) == MIN_NORMAL_VALUE.
            index -= 1

        self._min_normal_lower_boundary_index = index

        # self._max_normal_lower_boundary_index is the index such that
        # base**index equals the greatest representable lower boundary. An
        # exponential histogram bucket with this index covers the range
        # ((2 ** 1024) / base, 2 ** 1024], which includes opentelemetry.sdk.
        # metrics._internal.exponential_histogram.ieee_754.MAX_NORMAL_VALUE.
        # This bucket is incomplete, since the upper boundary cannot be
        # represented. One greater than this index corresponds with the bucket
        # containing values > 2 ** 1024.
        self._max_normal_lower_boundary_index = MAX_NORMAL_EXPONENT >> -self._scale

    def map_to_index(self, value: float) -> int:
        """Return the index of the bucket that holds ``value``.

        The IEEE 754 exponent of ``value`` is read directly, then a
        correction of -1 is applied when ``value`` is an exact power of
        two, so that a boundary belongs to the bucket below it. The result
        is right shifted by ``-scale``, which merges ``2 ** -scale``
        neighbouring powers of two into one bucket.

        Args:
            value: A finite, positive measurement. Anything below the
                smallest normal float, zero and the subnormal values
                included, returns ``_min_normal_lower_boundary_index``.
                +inf and NaN get past that guard and produce a
                meaningless index, so the caller screens them out.

        Returns:
            The index of the bucket holding ``value``.
        """
        if value < MIN_NORMAL_VALUE:
            return self._min_normal_lower_boundary_index

        exponent = get_ieee_754_exponent(value)

        # Positive integers are represented in binary as having an infinite
        # amount of leading zeroes, for example 2 is represented as ...00010.

        # A negative integer -x is represented in binary as the complement of
        # (x - 1). For example, -4 is represented as the complement of 4 - 1
        # == 3. 3 is represented as ...00011. Its compliment is ...11100, the
        # binary representation of -4.

        # get_ieee_754_mantissa(value) gets the positive integer made up
        # from the rightmost MANTISSA_WIDTH bits (the mantissa) of the IEEE
        # 754 representation of value. If value is an exact power of 2, all
        # these MANTISSA_WIDTH bits would be all zeroes, and when 1 is
        # subtracted the resulting value is -1. The binary representation of
        # -1 is ...111, so when these bits are right shifted MANTISSA_WIDTH
        # places, the resulting value for correction is -1. If value is not an
        # exact power of 2, at least one of the rightmost MANTISSA_WIDTH
        # bits would be 1 (even for values whose decimal part is 0, like 5.0
        # since the IEEE 754 of such number is too the product of a power of 2
        # (defined in the exponent part of the IEEE 754 representation) and the
        # value defined in the mantissa). Having at least one of the rightmost
        # MANTISSA_WIDTH bit being 1 means that get_ieee_754(value) will
        # always be greater or equal to 1, and when 1 is subtracted, the
        # result will be greater or equal to 0, whose representation in binary
        # will be of at most MANTISSA_WIDTH ones that have an infinite
        # amount of leading zeroes. When those MANTISSA_WIDTH bits are
        # shifted to the right MANTISSA_WIDTH places, the resulting value
        # will be 0.

        # In summary, correction will be -1 if value is a power of 2, 0 if not.

        # map_to_index requires value to be a finite, positive real number.
        # 0, inf, and NaN violate this precondition.

        # Zero is represented in IEEE 754 with all exponent bits set to 0,
        # giving get_ieee_754_exponent a result of -1023. Since -1023 is less
        # than MIN_NORMAL_EXPONENT (-1022), zero is caught by the guard above
        # and returned early.

        # Inf is represented in IEEE 754 with all 11 exponent bits set to 1
        # and a mantissa of 0, giving get_ieee_754_exponent a result of 1024
        # and correction a value of -1.

        # NaN is represented in IEEE 754 with all 11 exponent bits set to 1
        # and a non-zero mantissa of unspecified bit pattern, producing an
        # unspecified correction value.

        # Inf and NaN are not caught by the guard above. Callers must ensure
        # that only finite, positive values are passed to map_to_index.
        correction = (get_ieee_754_mantissa(value) - 1) >> MANTISSA_WIDTH

        return (exponent + correction) >> -self._scale

    def get_lower_boundary(self, index: int) -> float:
        """Return the lower boundary of the bucket with this index.

        Args:
            index: The bucket index to get the lower boundary of.

        Returns:
            ``2 ** (index << -scale)``, built with ``ldexp`` so that the
            result is exact and no rounding enters.

        Raises:
            MappingUnderflowError: If ``index`` is below
                ``_min_normal_lower_boundary_index``.
            MappingOverflowError: If ``index`` is above
                ``_max_normal_lower_boundary_index``.
        """
        if index < self._min_normal_lower_boundary_index:
            raise MappingUnderflowError()

        if index > self._max_normal_lower_boundary_index:
            raise MappingOverflowError()

        return ldexp(1, index << -self._scale)

    @property
    def scale(self) -> int:
        """Return the scale this instance was built for.

        Returns:
            A value between -10 and 0, fixed when the instance was
            created. An aggregation that needs a coarser mapping asks for
            another instance rather than changing this one.
        """
        return self._scale
