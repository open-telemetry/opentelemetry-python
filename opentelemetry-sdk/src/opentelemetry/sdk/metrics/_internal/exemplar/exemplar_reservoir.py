# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""The reservoirs that hold exemplars between collections.

A reservoir receives the measurements an exemplar filter let through and
keeps a bounded number of them until a metric reader collects. Each
aggregation owns one, built by the factory in
``opentelemetry.sdk.metrics._internal.view``. Two implementations are
provided: ``SimpleFixedSizeExemplarReservoir``, which samples uniformly,
and ``AlignedHistogramBucketExemplarReservoir``, which keeps one
measurement per explicit histogram bucket.
"""

from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from random import randrange
from threading import Lock
from typing import (
    Any,
)

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.trace.span import INVALID_SPAN
from opentelemetry.util.types import Attributes

from .exemplar import Exemplar


class ExemplarReservoir(ABC):
    """ExemplarReservoir provide a method to offer measurements to the reservoir
    and another to collect accumulated Exemplars.

    Note:
        The constructor MUST accept ``**kwargs`` that may be set from aggregation
        parameters.

    Note:
        All methods MUST be safe to call concurrently. Measurements are offered
        from application threads while a metric reader collects from its own
        thread.

    Reference:
        https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/metrics/sdk.md#exemplarreservoir
    """

    @abstractmethod
    def offer(
        self,
        value: float,
        time_unix_nano: int,
        attributes: Attributes,
        context: Context,
    ) -> None:
        """Offers a measurement to be sampled.

        Args:
            value: Measured value
            time_unix_nano: Measurement instant
            attributes: Measurement attributes
            context: Measurement context
        """
        raise NotImplementedError("ExemplarReservoir.offer is not implemented")

    @abstractmethod
    def collect(self, point_attributes: Attributes) -> list[Exemplar]:
        """Returns accumulated Exemplars and also resets the reservoir for the next
        sampling period

        Args:
            point_attributes: The attributes associated with metric point.

        Returns:
            a list of ``opentelemetry.sdk.metrics._internal.exemplar.exemplar.Exemplar`` s. Returned
            exemplars contain the attributes that were filtered out by the aggregator,
            but recorded alongside the original measurement.
        """
        raise NotImplementedError("ExemplarReservoir.collect is not implemented")


class ExemplarBucket:
    """One cell of a reservoir, holding at most one measurement.

    A cell keeps the last measurement offered to it. The span id and trace
    id are read out of the context only when a span is current, and are
    never cleared, so after an offer made outside any span the cell still
    carries the ids of the last offer that was made inside one. The
    reservoir decides which cell a measurement goes to, so overwriting is
    how a cell is reused rather than a loss to be avoided. ``collect``
    turns what the cell holds into an ``Exemplar`` and empties the cell, so
    a cell offered nothing during a collection cycle contributes nothing.
    """

    def __init__(self) -> None:
        """Build an empty cell, which collects nothing until it is offered."""
        self.__value: int | float = 0
        self.__attributes: Attributes = None
        self.__time_unix_nano: int = 0
        self.__span_id: int | None = None
        self.__trace_id: int | None = None
        self.__offered: bool = False

    def offer(
        self,
        value: float,
        time_unix_nano: int,
        attributes: Attributes,
        context: Context,
    ) -> None:
        """Offers a measurement to be sampled.

        Args:
            value: Measured value
            time_unix_nano: Measurement instant
            attributes: Measurement attributes
            context: Measurement context
        """
        self.__value = value
        self.__time_unix_nano = time_unix_nano
        self.__attributes = attributes
        span = trace.get_current_span(context)
        if span != INVALID_SPAN:
            span_context = span.get_span_context()
            self.__span_id = span_context.span_id
            self.__trace_id = span_context.trace_id

        self.__offered = True

    def collect(self, point_attributes: Attributes) -> Exemplar | None:
        """May return an Exemplar and resets the bucket for the next sampling period.

        Args:
            point_attributes: The attributes of the metric point the
                exemplar will hang off. Any attribute of the measurement
                that also appears here is left out of the exemplar, since
                the point already carries it.

        Returns:
            An ``Exemplar`` holding the value, the timestamp, the
            attributes that survived the filtering above and the span id
            and trace id captured by ``offer``, or ``None`` when nothing
            has been offered since the last collection. Those two are the
            ids of the most recent offer that was made inside a span since
            the last collection, which is not necessarily the offer whose
            value is reported. They are ``None`` only when no offer since
            the last collection had a span current.
        """
        if not self.__offered:
            return None

        # filters out attributes from the measurement that are already included in the metric data point
        # See the specification for more details:
        # https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/metrics/sdk.md#exemplar
        filtered_attributes = (
            {k: v for k, v in self.__attributes.items() if k not in point_attributes} if self.__attributes else None
        )

        exemplar = Exemplar(
            filtered_attributes,
            self.__value,
            self.__time_unix_nano,
            self.__span_id,
            self.__trace_id,
        )
        self.__reset()
        return exemplar

    def __reset(self) -> None:
        """Reset the bucket state after a collection cycle."""
        self.__value = 0
        self.__attributes = {}
        self.__time_unix_nano = 0
        self.__span_id = None
        self.__trace_id = None
        self.__offered = False


class BucketIndexError(ValueError):
    """An exception raised when the bucket index cannot be found."""


class FixedSizeExemplarReservoirABC(ExemplarReservoir):
    """Abstract class for a reservoir with fixed size.

    The reservoir holds at most ``size`` cells, each an
    ``ExemplarBucket``, created on first use by a ``defaultdict``.
    ``offer`` asks ``_find_bucket_index`` which cell a measurement belongs
    in and a subclass answers that; a subclass that wants to drop the
    measurement raises ``BucketIndexError``, which ``offer`` swallows. One
    lock guards both ``offer`` and ``collect``, since measurements arrive
    on application threads while a metric reader collects on its own.

    Args:
        size: How many cells the reservoir has, which is the largest
            number of exemplars one collection can produce.
        kwargs: Further aggregation parameters. They are handed to the
            parent class, which defines no ``__init__``, so a parameter
            that no class in the chain consumes ends up at
            ``object.__init__`` and raises ``TypeError``. The reservoirs
            in this module are built with none.
    """

    def __init__(self, size: int, **kwargs) -> None:
        """Build the reservoir.

        Every parameter is documented on the class itself, since that is
        the form the API reference renders.
        """
        super().__init__(**kwargs)
        self._size: int = size
        self._reservoir_storage: Mapping[int, ExemplarBucket] = defaultdict(ExemplarBucket)
        self._lock = Lock()

    def collect(self, point_attributes: Attributes) -> list[Exemplar]:
        """Returns accumulated Exemplars and also resets the reservoir for the next
        sampling period

        Args:
            point_attributes: The attributes associated with metric point.

        Returns:
            a list of ``opentelemetry.sdk.metrics._internal.exemplar.exemplar.Exemplar`` s. Returned
            exemplars contain the attributes that were filtered out by the aggregator,
            but recorded alongside the original measurement.
        """
        with self._lock:
            exemplars = [
                e
                for e in (bucket.collect(point_attributes) for _, bucket in sorted(self._reservoir_storage.items()))
                if e is not None
            ]
            self._reset()
        return exemplars

    def offer(
        self,
        value: float,
        time_unix_nano: int,
        attributes: Attributes,
        context: Context,
    ) -> None:
        """Offers a measurement to be sampled.

        Args:
            value: Measured value
            time_unix_nano: Measurement instant
            attributes: Measurement attributes
            context: Measurement context
        """
        with self._lock:
            try:
                index = self._find_bucket_index(value, time_unix_nano, attributes, context)

                self._reservoir_storage[index].offer(value, time_unix_nano, attributes, context)
            except BucketIndexError:
                # Ignore invalid bucket index
                pass

    @abstractmethod
    def _find_bucket_index(
        self,
        value: float,
        time_unix_nano: int,
        attributes: Attributes,
        context: Context,
    ) -> int:
        """Determines the bucket index for the given measurement.

        It should be implemented by subclasses based on specific strategies.

        Args:
            value: Measured value
            time_unix_nano: Measurement instant
            attributes: Measurement attributes
            context: Measurement context

        Returns:
            The bucket index

        Raises:
            BucketIndexError: If no bucket index can be found.
        """

    def _reset(self) -> None:
        """Reset the reservoir by resetting any stateful logic after a collection cycle.

        This implementation does nothing, because the cells have already
        been emptied by ``collect`` before it is called. A subclass that
        keeps state of its own beyond the cells overrides it. ``collect``
        calls it while holding the lock.
        """


class SimpleFixedSizeExemplarReservoir(FixedSizeExemplarReservoirABC):
    """This reservoir uses an uniformly-weighted sampling algorithm based on the number
    of samples the reservoir has seen so far to determine if the offered measurements
    should be sampled.

    The count of measurements seen is kept per collection cycle and
    cleared by ``_reset``, so the sampling starts over after each
    collection rather than letting early measurements of the process
    crowd out later ones.

    Args:
        size: How many cells the reservoir has, which is the largest
            number of exemplars one collection can produce. One cell by
            default, which is what the specification asks for on a
            non-histogram aggregation.
        kwargs: Further aggregation parameters, handed on to
            ``FixedSizeExemplarReservoirABC``.

    Reference:
        https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/metrics/sdk.md#simplefixedsizeexemplarreservoir
    """

    def __init__(self, size: int = 1, **kwargs) -> None:
        """Build the reservoir.

        Every parameter is documented on the class itself, since that is
        the form the API reference renders.
        """
        super().__init__(size, **kwargs)
        self._measurements_seen: int = 0

    def _reset(self) -> None:
        """Clear the measurement count along with the cell contents.

        ``collect`` calls this once it has emptied the cells, so the next
        collection cycle samples from scratch.
        """
        super()._reset()
        self._measurements_seen = 0

    def _find_bucket_index(
        self,
        value: float,
        time_unix_nano: int,
        attributes: Attributes,
        context: Context,
    ) -> int:
        """Pick the cell for a measurement, giving each one equal odds.

        The first ``size`` measurements of a collection cycle fill the
        cells in order. Every measurement after that is placed in a cell
        drawn uniformly from the range ``0`` to ``m - 1``, where ``m``
        counts every measurement the cycle has seen including this one, and
        is dropped when the draw lands outside the cells. The ``m``-th
        measurement is therefore kept with probability ``size / m``, which
        leaves every measurement of the cycle with the same chance of being
        one of the kept ones.

        Args:
            value: Measured value. The choice does not depend on it.
            time_unix_nano: Measurement instant, unused here.
            attributes: Measurement attributes, unused here.
            context: Measurement context, unused here.

        Returns:
            The index of the cell to store the measurement in, between 0
            and ``size - 1``.

        Raises:
            BucketIndexError: If the draw landed outside the cells, which
                means this measurement is dropped. ``offer`` catches it.
        """
        if self._measurements_seen < self._size:
            self._measurements_seen += 1
            return self._measurements_seen - 1

        self._measurements_seen += 1
        index = randrange(0, self._measurements_seen)
        if index < self._size:
            return index

        raise BucketIndexError("Unable to find the bucket index.")


class AlignedHistogramBucketExemplarReservoir(FixedSizeExemplarReservoirABC):
    """This Exemplar reservoir takes a configuration parameter that is the
    configuration of a Histogram. This implementation keeps the last seen measurement
    that falls within a histogram bucket.

    There is one cell per histogram bucket, so the reservoir size is one
    more than the number of boundaries. Nothing is ever dropped: every
    measurement that reaches the reservoir overwrites the cell of its
    bucket.

    Args:
        boundaries: The explicit bucket boundaries of the histogram, in
            ascending order. They come from the aggregation, which binds
            them to the reservoir class with ``functools.partial`` before
            the reservoir is built.
        kwargs: Further aggregation parameters, handed on to
            ``FixedSizeExemplarReservoirABC``.

    Reference:
        https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/metrics/sdk.md#alignedhistogrambucketexemplarreservoir
    """

    def __init__(self, boundaries: Sequence[float], **kwargs) -> None:
        """Build the reservoir.

        Every parameter is documented on the class itself, since that is
        the form the API reference renders.
        """
        super().__init__(len(boundaries) + 1, **kwargs)
        self._boundaries: Sequence[float] = boundaries

    def _find_bucket_index(
        self,
        value: float,
        time_unix_nano: int,
        attributes: Attributes,
        context: Context,
    ) -> int:
        """Pick the cell that matches the histogram bucket of the value.

        The boundaries are scanned in ascending order and the first one
        that ``value`` does not exceed decides the cell, which lands on
        the same bucket the explicit bucket histogram aggregation counts
        the measurement in. Since the cell is overwritten on every offer,
        what survives a collection cycle is the last measurement that fell
        in each bucket.

        Args:
            value: Measured value, compared against the boundaries.
            time_unix_nano: Measurement instant, unused here.
            attributes: Measurement attributes, unused here.
            context: Measurement context, unused here.

        Returns:
            The position of the first boundary that is at least ``value``,
            or the number of boundaries when ``value`` is above all of
            them. ``BucketIndexError`` is never raised here, so no
            measurement is dropped.
        """
        for index, boundary in enumerate(self._boundaries):
            if value <= boundary:
                return index
        return len(self._boundaries)


# ExemplarReservoirBuilder: A callable that takes Aggregation parameters
# (e.g. boundaries for _ExplicitBucketHistogramAggregation) and returns
# an ExemplarReservoir instance.
ExemplarReservoirBuilder = Callable[[dict[str, Any]], ExemplarReservoir]
