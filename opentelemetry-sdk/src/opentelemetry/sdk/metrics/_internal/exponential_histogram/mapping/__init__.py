# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""The interface that turns a measured value into a bucket index.

``Mapping`` declares that interface and holds the per-scale instance
cache. Two implementations complete it: ``ExponentMapping`` for scales of
0 and below, where a bucket spans whole powers of two, and
``LogarithmMapping`` for scales of 1 and above, where a power of two is
split across several buckets.
"""

from abc import ABC, abstractmethod
from threading import Lock


class Mapping(ABC):
    """
    Parent class for `LogarithmMapping` and `ExponentialMapping`.

    A mapping is immutable once built and carries no per-measurement
    state, so one instance per scale is shared by every histogram using
    that scale. ``__new__`` keeps that cache. Each concrete subclass
    declares its own ``_mappings`` dictionary and ``_mappings_lock``, so
    the two subclasses never share an entry even for a scale both could
    serve.

    Args:
        scale: Resolution of the mapping. A larger scale gives smaller
            buckets, since bucket boundaries sit at integer powers of
            ``2 ** (2 ** -scale)``. The accepted range is whatever
            ``_get_min_scale`` and ``_get_max_scale`` of the subclass
            report.
    """

    _mappings: dict[int, "Mapping"]
    _mappings_lock: Lock

    _min_scale: int
    _max_scale: int

    # pylint: disable=no-member
    def __new__(cls, scale: int):
        """Return the one instance of ``cls`` that serves ``scale``.

        Every parameter is documented on the class itself, since that is
        the form the API reference renders. The instance is built and
        initialized the first time a scale is asked for, and handed back
        unchanged afterwards.

        Raises:
            Exception: If ``scale`` is outside the range the subclass
                supports. ``_init`` raises it, so only the first request
                for a given scale can.
        """
        with cls._mappings_lock:
            # cls._mappings and cls._mappings_lock are implemented in each of
            # the child classes as a dictionary and a lock, respectively. They
            # are not instantiated here because that would lead to both child
            # classes having the same instance of cls._mappings and
            # cls._mappings_lock.
            if scale not in cls._mappings:
                cls._mappings[scale] = super().__new__(cls)
                cls._mappings[scale]._init(scale)

        return cls._mappings[scale]

    @abstractmethod
    def _init(self, scale: int) -> None:
        """Check ``scale`` against the subclass range and store it.

        ``__new__`` calls this once, on the instance it has just built for
        a scale. A subclass overrides it to precompute whatever it derives
        from the scale, and calls this implementation first so that the
        range check happens before anything is derived.

        Args:
            scale: Resolution of the mapping to store on the instance.

        Raises:
            Exception: If ``scale`` is above ``_get_max_scale()`` or below
                ``_get_min_scale()``. A plain ``Exception`` is raised, so
                a caller cannot tell the two cases apart except by the
                message.
        """
        # pylint: disable=attribute-defined-outside-init

        if scale > self._get_max_scale():
            # pylint: disable=broad-exception-raised
            raise Exception(f"scale is larger than {self._max_scale}")

        if scale < self._get_min_scale():
            # pylint: disable=broad-exception-raised
            raise Exception(f"scale is smaller than {self._min_scale}")

        # The size of the exponential histogram buckets is determined by a
        # parameter known as scale, larger values of scale will produce smaller
        # buckets. Bucket boundaries of the exponential histogram are located
        # at integer powers of the base, where:
        #
        # base = 2 ** (2 ** (-scale))
        # https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/metrics/data-model.md#all-scales-use-the-logarithm-function
        self._scale = scale

    @abstractmethod
    def _get_min_scale(self) -> int:
        """
        Return the smallest possible value for the mapping scale

        Returns:
            The lowest scale the subclass can represent. ``_init`` rejects
            anything below it, which is what sends the remaining scales to
            the other subclass.
        """

    @abstractmethod
    def _get_max_scale(self) -> int:
        """
        Return the largest possible value for the mapping scale

        Returns:
            The highest scale the subclass can represent. ``_init``
            rejects anything above it.
        """

    @abstractmethod
    def map_to_index(self, value: float) -> int:
        """
        Maps positive floating point values to indexes corresponding to
        `Mapping.scale`. Implementations are not expected to handle zeros,
        +inf, NaN, or negative values.

        Args:
            value: A finite, positive measurement. One of the excluded
                values gives a meaningless index rather than an error, so
                the caller screens them out first.

        Returns:
            The index of the bucket holding ``value``, that is, the only
            ``index`` for which ``get_lower_boundary(index) < value`` and
            ``value <= get_lower_boundary(index + 1)``.
        """

    @abstractmethod
    def get_lower_boundary(self, index: int) -> float:
        """
        Returns the lower boundary of a given bucket index. The index is
        expected to map onto a range that is at least partially inside the
        range of normal floating point values.  If the corresponding
        bucket's upper boundary is less than or equal to 2 ** -1022,
        ``MappingUnderflowError`` will be raised. If the corresponding
        bucket's lower boundary is greater than ``sys.float_info.max``,
        ``MappingOverflowError`` will be raised. Both classes are defined in
        the sibling module
        ``opentelemetry.sdk.metrics._internal.exponential_histogram.mapping.errors``
        and are not re-exported from this one.

        Args:
            index: The bucket index to get the lower boundary of.

        Returns:
            The lower boundary of that bucket, which the bucket excludes:
            the bucket holds values above this and up to the lower
            boundary of ``index + 1``.

        Raises:
            MappingUnderflowError: If the whole bucket sits below the
                normal floating point range.
            MappingOverflowError: If the whole bucket sits above it.
        """

    @property
    def scale(self) -> int:
        """
        Returns the parameter that controls the resolution of this mapping.
        See: https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/metrics/datamodel.md#exponential-scale

        Returns:
            The scale the instance was built for. It never changes, since
            ``__new__`` caches one instance per scale, so the aggregation
            builds a different mapping when it needs a different scale.
        """
        return self._scale
