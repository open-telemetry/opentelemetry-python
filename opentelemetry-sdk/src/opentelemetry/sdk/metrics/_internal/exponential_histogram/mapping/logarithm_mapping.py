# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""The mapping used for exponential histogram scales of 1 and above."""

from math import exp, floor, ldexp, log
from threading import Lock

from opentelemetry.sdk.metrics._internal.exponential_histogram.mapping import (
    Mapping,
)
from opentelemetry.sdk.metrics._internal.exponential_histogram.mapping.errors import (
    MappingOverflowError,
    MappingUnderflowError,
)
from opentelemetry.sdk.metrics._internal.exponential_histogram.mapping.ieee_754 import (
    MAX_NORMAL_EXPONENT,
    MIN_NORMAL_EXPONENT,
    MIN_NORMAL_VALUE,
    get_ieee_754_exponent,
    get_ieee_754_mantissa,
)


class LogarithmMapping(Mapping):
    """Maps a value to a bucket index by taking its logarithm.

    This mapping covers scales 1 through 20, where each power of two is
    split into ``2 ** scale`` buckets, so the index cannot be read out of
    the IEEE 754 exponent alone. ``map_to_index`` computes
    ``floor(log(value) * _scale_factor)``, where ``_scale_factor`` is
    precomputed so that a multiplication stands in for a division by
    ``log(base)``.

    Scales of 0 and below belong to ``ExponentMapping``, which needs no
    logarithm.

    Args:
        scale: Resolution of the mapping, from 1 to 20. ``Mapping.__new__``
            returns the single cached instance for that scale.
    """

    # Reference implementation here:
    # https://github.com/open-telemetry/opentelemetry-go/blob/0e6f9c29c10d6078e8131418e1d1d166c7195d61/sdk/metric/aggregator/exponential/mapping/logarithm/logarithm.go

    _mappings = {}
    _mappings_lock = Lock()

    _min_scale = 1
    _max_scale = 20

    def _get_min_scale(self):
        """Return the lowest scale this mapping serves.

        Returns:
            ``_min_scale``, which is 1. Scale 0 and the negative scales go
            to ``ExponentMapping`` instead.
        """
        # _min_scale ensures that ExponentMapping is used for zero and negative
        # scale values.
        return self._min_scale

    def _get_max_scale(self):
        """Return the highest scale this mapping serves.

        Returns:
            ``_max_scale``, which is 20. At scale 21 the largest bucket
            index reaches the top of the signed 32-bit range that the
            OpenTelemetry specification requires indexes to fit in.
        """
        # _max_scale is 20. The OpenTelemetry specification requires that
        # bucket indices fit within a signed 32-bit integer. At scale 20,
        # the maximum bucket index is ((MAX_NORMAL_EXPONENT + 1) << 20) - 1,
        # which fits within this range. At scale 21, the maximum bucket
        # index reaches the upper limit of a signed 32-bit integer, making
        # it difficult to test correctness. See:
        # https://github.com/lightstep/otel-launcher-go/blob/c9ca8483be067a39ab306b09060446e7fda65f35/lightstep/sdk/metric/aggregator/histogram/structure/README.md#mapping-function
        # https://github.com/open-telemetry/opentelemetry-go/blob/0e6f9c29c10d6078e8131418e1d1d166c7195d61/sdk/metric/aggregator/exponential/mapping/logarithm/logarithm.go#L32-L45
        return self._max_scale

    def _init(self, scale: int):
        """Precompute the scale factor and the two boundary indexes.

        ``Mapping._init`` runs first and rejects a scale outside 1 to 20.
        What is derived here is ``_scale_factor``, the multiplier that
        replaces a division by ``log(base)`` in ``map_to_index``, and the
        indexes of the lowest and highest buckets whose lower boundary is
        a representable float.

        Args:
            scale: Resolution of the mapping, from 1 to 20.

        Raises:
            Exception: If ``scale`` is outside that range.
        """
        # pylint: disable=attribute-defined-outside-init

        super()._init(scale)

        # self._scale_factor is defined as a multiplier because multiplication
        # is faster than division. self._scale_factor is defined as:
        # index = log(value) * self._scale_factor
        # Where:
        # index = log(value) / log(base)
        # index = log(value) / log(2 ** (2 ** -scale))
        # index = log(value) / ((2 ** -scale) * log(2))
        # index = log(value) * ((1 / log(2)) * (2 ** scale))
        # self._scale_factor = ((1 / log(2)) * (2 ** scale))
        # self._scale_factor = (1 /log(2)) * (2 ** scale)
        # self._scale_factor = ldexp(1 / log(2), scale)
        # This implementation was copied from a Java prototype. See:
        # https://github.com/newrelic-experimental/newrelic-sketch-java/blob/1ce245713603d61ba3a4510f6df930a5479cd3f6/src/main/java/com/newrelic/nrsketch/indexer/LogIndexer.java
        # for the equations used here.
        self._scale_factor = ldexp(1 / log(2), scale)

        # self._min_normal_lower_boundary_index is the index such that
        # base ** index == MIN_NORMAL_VALUE. An exponential histogram bucket
        # with this index covers the range
        # (MIN_NORMAL_VALUE, MIN_NORMAL_VALUE * base]. One less than this index
        # corresponds with the bucket containing values <= MIN_NORMAL_VALUE.
        self._min_normal_lower_boundary_index = MIN_NORMAL_EXPONENT << self._scale

        # self._max_normal_lower_boundary_index is the index such that
        # base ** index equals the greatest representable lower boundary. An
        # exponential histogram bucket with this index covers the range
        # ((2 ** 1024) / base, 2 ** 1024], which includes opentelemetry.sdk.
        # metrics._internal.exponential_histogram.ieee_754.MAX_NORMAL_VALUE.
        # This bucket is incomplete, since the upper boundary cannot be
        # represented. One greater than this index corresponds with the bucket
        # containing values > 2 ** 1024.
        self._max_normal_lower_boundary_index = ((MAX_NORMAL_EXPONENT + 1) << self._scale) - 1

    def map_to_index(self, value: float) -> int:
        """
        Maps positive floating point values to indexes corresponding to scale.

        Three cases are separated. A value at or below the smallest normal
        float goes into the single bucket below
        ``_min_normal_lower_boundary_index``, which collects every
        subnormal value and zero. An exact power of two is given the index
        of the bucket whose upper boundary it is, so that a boundary
        belongs to the bucket below it, which a floating point logarithm
        would not place reliably. Every other value is the floor of its
        logarithm times ``_scale_factor``, held down to
        ``_max_normal_lower_boundary_index``.

        Args:
            value: A finite, positive measurement. Negative values, +inf
                and NaN are not handled here.

        Returns:
            The index of the bucket holding ``value``.
        """

        # value is subnormal
        if value <= MIN_NORMAL_VALUE:
            return self._min_normal_lower_boundary_index - 1

        # value is an exact power of two.
        if get_ieee_754_mantissa(value) == 0:
            exponent = get_ieee_754_exponent(value)
            return (exponent << self._scale) - 1

        return min(
            floor(log(value) * self._scale_factor),
            self._max_normal_lower_boundary_index,
        )

    def get_lower_boundary(self, index: int) -> float:
        """Return the lower boundary of the bucket with this index.

        Args:
            index: The bucket index to get the lower boundary of.

        Returns:
            ``exp(index / _scale_factor)`` for an index strictly inside
            the normal range. The three indexes at the ends of that range
            are computed differently so that the expression above does not
            overflow or underflow:
            ``_min_normal_lower_boundary_index`` returns
            ``sys.float_info.min`` exactly, the index one below it halves
            the boundary computed one power of two higher, and
            ``_max_normal_lower_boundary_index`` doubles the boundary
            computed one power of two lower.

        Raises:
            MappingOverflowError: If ``index`` is above
                ``_max_normal_lower_boundary_index``.
            MappingUnderflowError: If ``index`` is more than one below
                ``_min_normal_lower_boundary_index``.
        """
        if index >= self._max_normal_lower_boundary_index:
            if index == self._max_normal_lower_boundary_index:
                return 2 * exp((index - (1 << self._scale)) / self._scale_factor)
            raise MappingOverflowError()

        if index <= self._min_normal_lower_boundary_index:
            if index == self._min_normal_lower_boundary_index:
                return MIN_NORMAL_VALUE
            if index == self._min_normal_lower_boundary_index - 1:
                return exp((index + (1 << self._scale)) / self._scale_factor) / 2
            raise MappingUnderflowError()

        return exp(index / self._scale_factor)

    @property
    def scale(self) -> int:
        """Return the scale this instance was built for.

        Returns:
            A value between 1 and 20, fixed when the instance was created.
            An aggregation that needs a coarser mapping asks for another
            instance rather than changing this one.
        """
        return self._scale
