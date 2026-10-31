# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=too-many-lines

"""Aggregations: how recorded measurements become exported data points.

There are two families of classes in this module and they are easy to confuse.

The public ones, ``Aggregation`` and its subclasses (``SumAggregation``,
``LastValueAggregation``, ``ExplicitBucketHistogramAggregation``,
``ExponentialBucketHistogramAggregation``, ``DropAggregation`` and
``DefaultAggregation``), are factories. A ``View`` holds one of them, it holds
no measurement state, and the same instance is shared by every stream the view
produces. Its ``_create_aggregation`` method builds one object of the second
family.

The private ones, ``_Aggregation`` and its subclasses, hold the state. One of
them exists per attribute set per stream. ``aggregate`` folds a measurement
into that state and ``collect`` turns the state into a data point.

Two temporalities are involved in a collection and they are independent. The
instrument aggregation temporality is fixed by the instrument kind: a
synchronous instrument reports increments, so it is ``DELTA``, while an
asynchronous instrument reports running totals, so it is ``CUMULATIVE``. The
collection aggregation temporality is chosen by the metric reader and passed
to ``collect``, which converts between the two when they differ.
"""

import math
from abc import ABC, abstractmethod
from bisect import bisect_left
from collections.abc import Callable, Sequence
from enum import IntEnum
from functools import partial
from logging import getLogger
from threading import Lock
from typing import (
    Generic,
    TypeVar,
    cast,
)

from opentelemetry.metrics import (
    Asynchronous,
    Counter,
    Histogram,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    Synchronous,
    UpDownCounter,
    _Gauge,
)
from opentelemetry.sdk.metrics._internal.exemplar import (
    Exemplar,
    ExemplarReservoirBuilder,
)
from opentelemetry.sdk.metrics._internal.exponential_histogram.buckets import (
    Buckets,
)
from opentelemetry.sdk.metrics._internal.exponential_histogram.mapping import (
    Mapping,
)
from opentelemetry.sdk.metrics._internal.exponential_histogram.mapping.exponent_mapping import (
    ExponentMapping,
)
from opentelemetry.sdk.metrics._internal.exponential_histogram.mapping.logarithm_mapping import (
    LogarithmMapping,
)
from opentelemetry.sdk.metrics._internal.instrument import _Instrument
from opentelemetry.sdk.metrics._internal.measurement import Measurement
from opentelemetry.sdk.metrics._internal.point import Buckets as BucketsPoint
from opentelemetry.sdk.metrics._internal.point import (
    ExponentialHistogramDataPoint,
    HistogramDataPoint,
    NumberDataPoint,
    Sum,
)
from opentelemetry.sdk.metrics._internal.point import Gauge as GaugePoint
from opentelemetry.sdk.metrics._internal.point import (
    Histogram as HistogramPoint,
)
from opentelemetry.util.types import Attributes

_DataPointVarT = TypeVar("_DataPointVarT", NumberDataPoint, HistogramDataPoint)

_logger = getLogger(__name__)


class AggregationTemporality(IntEnum):
    """
    The temporality to use when aggregating data.

    Can be one of the following values:

    ``UNSPECIFIED`` is the zero value. A factory assigns it when the
    instrument is neither synchronous nor asynchronous, which no instrument
    shipped with the SDK is.

    ``DELTA`` means a point covers only what happened since the previous
    collection, so the start time of each point is the time of the previous
    collection.

    ``CUMULATIVE`` means a point covers everything since the stream started,
    so the start time of each point is the time the aggregation was created.

    The integer values match the ``AggregationTemporality`` enumeration of the
    OpenTelemetry protocol, and that is what ``to_json`` emits.
    """

    UNSPECIFIED = 0
    DELTA = 1
    CUMULATIVE = 2


class _Aggregation(ABC, Generic[_DataPointVarT]):
    """Holds the aggregated state of one attribute set of one stream.

    An instance is created by the ``_create_aggregation`` method of an
    ``Aggregation`` factory, the first time a measurement carrying this
    attribute set is seen. From then on it receives every further measurement
    with those attributes through ``aggregate``, and every collection cycle
    asks it for a point through ``collect``.

    Subclasses guard their mutable state with ``self._lock``, because
    ``aggregate`` is called from application threads while ``collect`` is
    called from the thread of a metric reader.

    Args:
        attributes: The attribute set this instance aggregates, after the
            view has dropped whatever it filters out. It is copied into every
            point ``collect`` returns, and it is also what
            ``_collect_exemplars`` subtracts from the exemplar attributes.
        reservoir_builder: Called once, here, with no positional arguments, to
            build the exemplar reservoir. The factories bind the
            aggregation-specific keyword arguments (bucket boundaries, size)
            into it beforehand with ``partial``.
    """

    def __init__(
        self,
        attributes: Attributes,
        reservoir_builder: ExemplarReservoirBuilder,
    ):
        """Build the instance.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        self._lock = Lock()
        self._attributes = attributes
        self._reservoir = reservoir_builder()
        self._previous_point = None

    @abstractmethod
    def aggregate(self, measurement: Measurement, should_sample_exemplar: bool = True) -> None:
        """Aggregate a measurement.

        Args:
            measurement: Measurement to aggregate
            should_sample_exemplar: Whether the measurement should be sampled by the exemplars reservoir or not.
        """

    @abstractmethod
    def collect(
        self,
        collection_aggregation_temporality: AggregationTemporality,
        collection_start_nano: int,
    ) -> _DataPointVarT | None:
        """Turn the state accumulated so far into a data point.

        Implementations take ``self._lock`` while they read and reset their
        state, so a measurement recorded concurrently lands either wholly in
        this point or wholly in the next one.

        Args:
            collection_aggregation_temporality: The temporality the metric
                reader asked for. When it differs from the temporality of the
                instrument, the implementation converts, which is what the
                ``_previous_*`` attributes of the subclasses are kept for.
            collection_start_nano: Nanoseconds since the Unix epoch at which
                this collection cycle started. Every point produced by one
                cycle carries the same value as its ``time_unix_nano``.

        Returns:
            The point, or ``None`` when there is nothing to report, which
            happens when no measurement arrived since the previous collection
            or when the requested conversion is not supported.
        """

    def _collect_exemplars(self) -> Sequence[Exemplar]:
        """Returns the collected exemplars.

        Calling this drains the reservoir and resets it for the next sampling
        period, so it is called exactly once per point that ``collect``
        returns. A ``collect`` that returns ``None`` leaves the reservoir
        untouched, and those exemplars then appear in the next point.

        Returns:
            The exemplars collected by the reservoir, with the attributes of
            this aggregation removed from each of them, so only the attributes
            the view dropped remain. Empty when nothing was sampled.
        """
        return self._reservoir.collect(self._attributes)

    def _sample_exemplar(self, measurement: Measurement, should_sample_exemplar: bool) -> None:
        """Offer the measurement to the exemplar reservoir for sampling.

        It should be called within the each :ref:`aggregate` call.

        Args:
            measurement: The new measurement
            should_sample_exemplar: Whether the measurement should be sampled by the exemplars reservoir or not.
        """
        if should_sample_exemplar:
            self._reservoir.offer(
                measurement.value,
                measurement.time_unix_nano,
                measurement.attributes,
                measurement.context,
            )


class _DropAggregation(_Aggregation):
    """Keeps no state and produces no point.

    This is what a stream gets when its view selects ``DropAggregation``. The
    measurements still reach it, so the instrument and the view keep working,
    but nothing is stored and nothing is ever exported for the stream. The
    constructor is the one inherited from ``_Aggregation``, and the exemplar
    reservoir it builds is never offered anything.
    """

    def aggregate(self, measurement: Measurement, should_sample_exemplar: bool = True) -> None:
        """Discard the measurement.

        Args:
            measurement: Ignored.
            should_sample_exemplar: Ignored. No measurement is offered to the
                exemplar reservoir, whatever the exemplar filter decided.
        """

    def collect(
        self,
        collection_aggregation_temporality: AggregationTemporality,
        collection_start_nano: int,
    ) -> _DataPointVarT | None:
        """Report nothing.

        Args:
            collection_aggregation_temporality: Ignored.
            collection_start_nano: Ignored.

        Returns:
            ``None``, always, so the stream contributes no data point to any
            collection.
        """


class _SumAggregation(_Aggregation[Sum]):
    """Adds up the measurements of one attribute set.

    The running value starts at ``None`` rather than at zero, which is how an
    interval that received no measurement is told apart from one that received
    measurements adding up to zero. A negative measurement is added like any
    other: this class never rejects one, and an instrument that is declared
    monotonic but is handed a negative value will report a decreasing sum.

    Args:
        attributes: The attribute set this instance aggregates.
        instrument_is_monotonic: Whether the instrument can only increase. It
            changes nothing about how the value is computed, and is only read
            when two streams are checked for a naming conflict. The
            ``is_monotonic`` field of the exported ``Sum`` is derived from the
            instrument type instead, by the metric reader storage.
        instrument_aggregation_temporality: ``DELTA`` for a synchronous
            instrument, whose measurements are increments, and ``CUMULATIVE``
            for an asynchronous one, whose measurements are running totals.
        start_time_unix_nano: Nanoseconds since the Unix epoch at which this
            stream started. It is the start time of every cumulative point,
            and the start time of the first delta point.
        reservoir_builder: Builds the exemplar reservoir, as on
            ``_Aggregation``.
    """

    def __init__(
        self,
        attributes: Attributes,
        instrument_is_monotonic: bool,
        instrument_aggregation_temporality: AggregationTemporality,
        start_time_unix_nano: int,
        reservoir_builder: ExemplarReservoirBuilder,
    ):
        """Build the instance.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        super().__init__(attributes, reservoir_builder)

        self._start_time_unix_nano = start_time_unix_nano
        self._instrument_aggregation_temporality = instrument_aggregation_temporality
        self._instrument_is_monotonic = instrument_is_monotonic

        self._value = None

        self._previous_collection_start_nano = self._start_time_unix_nano
        self._previous_value = 0

    def aggregate(self, measurement: Measurement, should_sample_exemplar: bool = True) -> None:
        """Add the measured value to the running value.

        For a synchronous instrument the value is an increment and this
        accumulates it. For an asynchronous one the value is a running total
        reported by a callback, and since a callback runs once per collection
        the addition happens once per cycle, so the running value ends up
        being the reported total.

        Args:
            measurement: The measurement to fold in. Its value may be
                negative, and is then subtracted from the running value.
            should_sample_exemplar: Whether the measurement may be offered to
                the exemplar reservoir. It comes from the exemplar filter and
                is passed on unchanged. Offering happens outside the lock,
                after the value has been updated.
        """
        with self._lock:
            if self._value is None:
                self._value = 0

            self._value = self._value + measurement.value

        self._sample_exemplar(measurement, should_sample_exemplar)

    def collect(
        self,
        collection_aggregation_temporality: AggregationTemporality,
        collection_start_nano: int,
    ) -> NumberDataPoint | None:
        """
        Atomically return a point for the current value of the metric and
        reset the aggregation value.

        Synchronous instruments have a method which is called directly with
        increments for a given quantity:

        For example, an instrument that counts the amount of passengers in
        every vehicle that crosses a certain point in a highway:

        synchronous_instrument.add(2)
        collect(...)  # 2 passengers are counted
        synchronous_instrument.add(3)
        collect(...)  # 3 passengers are counted
        synchronous_instrument.add(1)
        collect(...)  # 1 passenger is counted

        In this case the instrument aggregation temporality is DELTA because
        every value represents an increment to the count,

        Asynchronous instruments have a callback which returns the total value
        of a given quantity:

        For example, an instrument that measures the amount of bytes written to
        a certain hard drive:

        callback() -> 1352
        collect(...) # 1352 bytes have been written so far
        callback() -> 2324
        collect(...) # 2324 bytes have been written so far
        callback() -> 4542
        collect(...) # 4542 bytes have been written so far

        In this case the instrument aggregation temporality is CUMULATIVE
        because every value represents the total of the measurement.

        There is also the collection aggregation temporality, which is passed
        to this method. The collection aggregation temporality defines the
        nature of the returned value by this aggregation.

        When the collection aggregation temporality matches the
        instrument aggregation temporality, then this method returns the
        current value directly:

        synchronous_instrument.add(2)
        collect(DELTA) -> 2
        synchronous_instrument.add(3)
        collect(DELTA) -> 3
        synchronous_instrument.add(1)
        collect(DELTA) -> 1

        callback() -> 1352
        collect(CUMULATIVE) -> 1352
        callback() -> 2324
        collect(CUMULATIVE) -> 2324
        callback() -> 4542
        collect(CUMULATIVE) -> 4542

        When the collection aggregation temporality does not match the
        instrument aggregation temporality, then a conversion is made. For this
        purpose, this aggregation keeps a private attribute,
        self._previous_value.

        When the instrument is synchronous:

        self._previous_value is the sum of every previously
        collected (delta) value. In this case, the returned (cumulative) value
        will be:

        self._previous_value + value

        synchronous_instrument.add(2)
        collect(CUMULATIVE) -> 2
        synchronous_instrument.add(3)
        collect(CUMULATIVE) -> 5
        synchronous_instrument.add(1)
        collect(CUMULATIVE) -> 6

        Also, as a diagram:

        time ->

        self._previous_value
        |-------------|

        value (delta)
                      |----|

        returned value (cumulative)
        |------------------|

        When the instrument is asynchronous:

        self._previous_value is the value of the previously
        collected (cumulative) value. In this case, the returned (delta) value
        will be:

        value - self._previous_value

        callback() -> 1352
        collect(DELTA) -> 1352
        callback() -> 2324
        collect(DELTA) -> 972
        callback() -> 4542
        collect(DELTA) -> 2218

        Also, as a diagram:

        time ->

        self._previous_value
        |-------------|

        value (cumulative)
        |------------------|

        returned value (delta)
                      |----|

        The running value is reset to ``None`` on every call, whichever
        branch is taken.

        Args:
            collection_aggregation_temporality: The temporality the metric
                reader asked for, which selects one of the four branches
                described above.
            collection_start_nano: Nanoseconds since the Unix epoch at which
                this collection cycle started. It becomes the
                ``time_unix_nano`` of the returned point, and it is also
                remembered as the start of the next delta interval.

        Returns:
            A ``NumberDataPoint``, or ``None``. ``None`` is returned when a
            delta point is asked for and no measurement arrived since the
            previous collection, and also when the instrument is asynchronous
            and its callback produced nothing. A cumulative point is returned
            even for an empty interval, since the total is still meaningful.
            The start time of a delta point is the time of the previous
            collection, falling back to ``start_time_unix_nano`` for the first
            one; the start time of a cumulative point is always
            ``start_time_unix_nano``.
        """

        with self._lock:
            value = self._value
            self._value = None

            if self._instrument_aggregation_temporality is AggregationTemporality.DELTA:
                # This happens when the corresponding instrument for this
                # aggregation is synchronous.
                if collection_aggregation_temporality is AggregationTemporality.DELTA:
                    previous_collection_start_nano = self._previous_collection_start_nano
                    self._previous_collection_start_nano = collection_start_nano

                    if value is None:
                        return None

                    return NumberDataPoint(
                        attributes=self._attributes,
                        exemplars=self._collect_exemplars(),
                        start_time_unix_nano=previous_collection_start_nano,
                        time_unix_nano=collection_start_nano,
                        value=value,
                    )

                if value is None:
                    value = 0

                self._previous_value = value + self._previous_value

                return NumberDataPoint(
                    attributes=self._attributes,
                    exemplars=self._collect_exemplars(),
                    start_time_unix_nano=self._start_time_unix_nano,
                    time_unix_nano=collection_start_nano,
                    value=self._previous_value,
                )

            # This happens when the corresponding instrument for this
            # aggregation is asynchronous.

            if value is None:
                # This happens when the corresponding instrument callback
                # does not produce measurements.
                return None

            if collection_aggregation_temporality is AggregationTemporality.DELTA:
                result_value = value - self._previous_value

                self._previous_value = value

                previous_collection_start_nano = self._previous_collection_start_nano
                self._previous_collection_start_nano = collection_start_nano

                return NumberDataPoint(
                    attributes=self._attributes,
                    exemplars=self._collect_exemplars(),
                    start_time_unix_nano=previous_collection_start_nano,
                    time_unix_nano=collection_start_nano,
                    value=result_value,
                )

            return NumberDataPoint(
                attributes=self._attributes,
                exemplars=self._collect_exemplars(),
                start_time_unix_nano=self._start_time_unix_nano,
                time_unix_nano=collection_start_nano,
                value=value,
            )


class _LastValueAggregation(_Aggregation[GaugePoint]):
    """Keeps only the most recent measurement of one attribute set.

    Nothing is summed and no history is kept, so a measurement is lost as soon
    as the next one arrives. The points this produces carry no start time,
    because a gauge reading describes an instant rather than an interval.

    Args:
        attributes: The attribute set this instance aggregates.
        reservoir_builder: Builds the exemplar reservoir, as on
            ``_Aggregation``.
        instrument_is_synchronous: Whether the instrument is a synchronous
            gauge, as opposed to an observable gauge. It decides whether the
            stored value survives a cumulative collection, which is what lets
            a synchronous gauge keep reporting its last reading when no new
            measurement was recorded.
    """

    def __init__(
        self,
        attributes: Attributes,
        reservoir_builder: ExemplarReservoirBuilder,
        instrument_is_synchronous: bool,
    ):
        """Build the instance.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        super().__init__(attributes, reservoir_builder)
        self._instrument_is_synchronous = instrument_is_synchronous
        self._value = None

    def aggregate(self, measurement: Measurement, should_sample_exemplar: bool = True):
        """Replace the stored value with the measured one.

        Args:
            measurement: The measurement to store. Its timestamp is not kept:
                the point produced later is stamped with the time of the
                collection instead.
            should_sample_exemplar: Whether the measurement may be offered to
                the exemplar reservoir. It comes from the exemplar filter and
                is passed on unchanged.
        """
        with self._lock:
            self._value = measurement.value

        self._sample_exemplar(measurement, should_sample_exemplar)

    def collect(
        self,
        collection_aggregation_temporality: AggregationTemporality,
        collection_start_nano: int,
    ) -> _DataPointVarT | None:
        """
        Atomically return a point for the current value of the metric.

        The stored value is cleared afterwards, so a later collection that
        saw no new measurement reports nothing. There is one exception: a
        synchronous gauge collected cumulatively keeps its value, and
        therefore repeats the same reading in every cycle until a new
        measurement replaces it.

        Args:
            collection_aggregation_temporality: The temporality the metric
                reader asked for. It does not change the value reported, only
                whether the value is kept for the next cycle.
            collection_start_nano: Nanoseconds since the Unix epoch at which
                this collection cycle started. It becomes the
                ``time_unix_nano`` of the returned point.

        Returns:
            A ``NumberDataPoint`` whose ``start_time_unix_nano`` is ``None``,
            or ``None`` when no measurement has been recorded since the value
            was last cleared.
        """
        with self._lock:
            if self._value is None:
                return None
            value = self._value
            if not (
                self._instrument_is_synchronous
                and collection_aggregation_temporality is AggregationTemporality.CUMULATIVE
            ):
                self._value = None

        exemplars = self._collect_exemplars()

        return NumberDataPoint(
            attributes=self._attributes,
            exemplars=exemplars,
            start_time_unix_nano=None,
            time_unix_nano=collection_start_nano,
            value=value,
        )


_DEFAULT_EXPLICIT_BUCKET_HISTOGRAM_AGGREGATION_BOUNDARIES: Sequence[float] = (
    0.0,
    5.0,
    10.0,
    25.0,
    50.0,
    75.0,
    100.0,
    250.0,
    500.0,
    750.0,
    1000.0,
    2500.0,
    5000.0,
    7500.0,
    10000.0,
)


class _ExplicitBucketHistogramAggregation(_Aggregation[HistogramPoint]):
    """Counts measurements into buckets whose boundaries are fixed up front.

    The number of buckets is ``len(boundaries) + 1`` and never changes. Bucket
    ``i`` counts the values greater than ``boundaries[i - 1]`` and less than or
    equal to ``boundaries[i]``, so a value equal to a boundary falls in the
    lower of the two buckets that boundary separates. The last bucket counts
    everything above the last boundary, and the first counts everything at or
    below the first one, negative values included.

    A negative measurement is accepted. It lands in the first bucket (with the
    default boundaries, whose first entry is ``0.0``) and it is subtracted
    from the running sum, which is why the specification advises against a
    histogram over an instrument that records negative values.

    Args:
        attributes: The attribute set this instance aggregates.
        instrument_aggregation_temporality: ``DELTA`` for a synchronous
            instrument and ``CUMULATIVE`` for an asynchronous one. Only
            ``DELTA`` produces points: see ``collect``.
        start_time_unix_nano: Nanoseconds since the Unix epoch at which this
            stream started. It is the start time of every cumulative point.
        reservoir_builder: Builds the exemplar reservoir. The boundaries are
            bound into it, so the default reservoir keeps one exemplar per
            bucket.
        boundaries: Strictly increasing, finite bucket boundaries. ``None``
            selects the default set, which runs from ``0.0`` to ``10000.0``.
            An empty sequence is accepted and gives a single bucket holding
            every value.
        record_min_max: Whether to track the smallest and largest measurement.
            When ``False``, the points report ``None`` for both, and the
            running extremes are not updated.

    Raises:
        ValueError: If a boundary is infinite or ``NaN``, or if the
            boundaries are not strictly increasing.
    """

    def __init__(
        self,
        attributes: Attributes,
        instrument_aggregation_temporality: AggregationTemporality,
        start_time_unix_nano: int,
        reservoir_builder: ExemplarReservoirBuilder,
        boundaries: Sequence[float] | None = None,
        record_min_max: bool = True,
    ):
        """Build the instance.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.

        Raises:
            ValueError: If a boundary is infinite or ``NaN``, or if the
                boundaries are not strictly increasing.
        """
        if boundaries is None:
            boundaries = _DEFAULT_EXPLICIT_BUCKET_HISTOGRAM_AGGREGATION_BOUNDARIES
        if boundaries:
            for idx, bound in enumerate(boundaries):
                if not math.isfinite(bound):
                    raise ValueError(f"invalid boundary: {bound!r}")
                if idx and boundaries[idx - 1] >= bound:
                    raise ValueError("boundaries must be strictly increasing")
        super().__init__(
            attributes,
            reservoir_builder=partial(reservoir_builder, boundaries=boundaries),
        )

        self._instrument_aggregation_temporality = instrument_aggregation_temporality
        self._start_time_unix_nano = start_time_unix_nano
        self._boundaries = tuple(boundaries)
        self._record_min_max = record_min_max

        self._value = None
        self._min = math.inf
        self._max = -math.inf
        self._sum = 0

        self._previous_value = None
        self._previous_min = math.inf
        self._previous_max = -math.inf
        self._previous_sum = 0

        self._previous_collection_start_nano = self._start_time_unix_nano

    def _get_empty_bucket_counts(self) -> list[int]:
        """Build a fresh counter list sized for the configured boundaries.

        Returns:
            A new list of ``len(self._boundaries) + 1`` zeros. It is a new
            list on every call, so the caller may store it and mutate it.
        """
        return [0] * (len(self._boundaries) + 1)

    def aggregate(self, measurement: Measurement, should_sample_exemplar: bool = True) -> None:
        """Count the measurement into its bucket.

        The bucket is found by a binary search over the boundaries, the sum is
        updated, and the extremes are updated when ``record_min_max`` is
        ``True``. Every value is counted, however large or small, since the
        first and last buckets are unbounded.

        Args:
            measurement: The measurement to count.
            should_sample_exemplar: Whether the measurement may be offered to
                the exemplar reservoir. It comes from the exemplar filter and
                is passed on unchanged.
        """
        with self._lock:
            if self._value is None:
                self._value = self._get_empty_bucket_counts()

            measurement_value = measurement.value

            self._sum += measurement_value

            if self._record_min_max:
                self._min = min(self._min, measurement_value)
                self._max = max(self._max, measurement_value)

            self._value[bisect_left(self._boundaries, measurement_value)] += 1

        self._sample_exemplar(measurement, should_sample_exemplar)

    def collect(
        self,
        collection_aggregation_temporality: AggregationTemporality,
        collection_start_nano: int,
    ) -> _DataPointVarT | None:
        """
        Atomically return a point for the current value of the metric.

        The bucket counts, the sum and the extremes are read and reset under
        the lock. When a cumulative point is asked for, the counts just read
        are added element by element into the running cumulative counts, the
        sums are added and the extremes are widened, and the running totals
        are what gets reported.

        Args:
            collection_aggregation_temporality: The temporality the metric
                reader asked for.
            collection_start_nano: Nanoseconds since the Unix epoch at which
                this collection cycle started. It becomes the
                ``time_unix_nano`` of the returned point, and the start of the
                next delta interval.

        Returns:
            A ``HistogramDataPoint``, or ``None``. ``None`` is returned when a
            delta point is asked for and no measurement arrived since the
            previous collection, and also whenever the instrument temporality
            is ``CUMULATIVE``, which means an asynchronous instrument with
            this aggregation never reports anything. The start time of a delta
            point is the time of the previous collection, falling back to
            ``start_time_unix_nano`` for the first one; the start time of a
            cumulative point is always ``start_time_unix_nano``. A cumulative
            point produced before any measurement reports ``inf`` as its
            minimum and ``-inf`` as its maximum.
        """

        with self._lock:
            value = self._value
            sum_ = self._sum
            min_ = self._min
            max_ = self._max

            self._value = None
            self._sum = 0
            self._min = math.inf
            self._max = -math.inf

            if self._instrument_aggregation_temporality is AggregationTemporality.DELTA:
                # This happens when the corresponding instrument for this
                # aggregation is synchronous.
                if collection_aggregation_temporality is AggregationTemporality.DELTA:
                    previous_collection_start_nano = self._previous_collection_start_nano
                    self._previous_collection_start_nano = collection_start_nano

                    if value is None:
                        return None

                    return HistogramDataPoint(
                        attributes=self._attributes,
                        exemplars=self._collect_exemplars(),
                        start_time_unix_nano=previous_collection_start_nano,
                        time_unix_nano=collection_start_nano,
                        count=sum(value),
                        sum=sum_,
                        bucket_counts=tuple(value),
                        explicit_bounds=self._boundaries,
                        min=min_ if self._record_min_max else None,
                        max=max_ if self._record_min_max else None,
                    )

                if value is None:
                    value = self._get_empty_bucket_counts()

                if self._previous_value is None:
                    self._previous_value = self._get_empty_bucket_counts()

                self._previous_value = [
                    value_element + previous_value_element
                    for (
                        value_element,
                        previous_value_element,
                    ) in zip(value, self._previous_value)
                ]
                self._previous_min = min(min_, self._previous_min)
                self._previous_max = max(max_, self._previous_max)
                self._previous_sum = sum_ + self._previous_sum

                return HistogramDataPoint(
                    attributes=self._attributes,
                    exemplars=self._collect_exemplars(),
                    start_time_unix_nano=self._start_time_unix_nano,
                    time_unix_nano=collection_start_nano,
                    count=sum(self._previous_value),
                    sum=self._previous_sum,
                    bucket_counts=tuple(self._previous_value),
                    explicit_bounds=self._boundaries,
                    min=self._previous_min if self._record_min_max else None,
                    max=self._previous_max if self._record_min_max else None,
                )

            return None


# pylint: disable=protected-access
class _ExponentialBucketHistogramAggregation(_Aggregation[HistogramPoint]):
    """Counts measurements into buckets whose boundaries follow a power law.

    Bucket ``i`` covers the values from ``base ** i`` excluded to
    ``base ** (i + 1)`` included, where ``base`` is ``2 ** (2 ** -scale)``.
    The scale is therefore a resolution: raising it by one halves the width of
    every bucket. The index is signed, so values below one get negative
    indexes. Positive and negative measurements are counted in two separate
    sets of buckets, the negative ones by their absolute value, and a
    measurement of exactly zero is counted in neither and tallied in a
    dedicated zero count.

    Unlike the explicit bucket histogram, the buckets here are chosen from the
    data. The aggregation starts at ``max_scale`` and lowers the scale
    whenever a new measurement would need a span of more than ``max_size``
    buckets: the existing buckets are collapsed in pairs, each halving of the
    resolution costing one unit of scale, and the mapping is rebuilt at the
    new scale. The scale thus only ever decreases while one instance lives,
    and the number of buckets on either side never exceeds ``max_size``. The
    scale reported for a stream is not monotonic, because a synchronous
    instrument collected with ``DELTA`` temporality discards this object on
    every collection and the next one starts again at ``max_scale``.

    Args:
        attributes: The attribute set this instance aggregates.
        reservoir_builder: Builds the exemplar reservoir. A size of
            ``min(20, max_size)`` is bound into it.
        instrument_aggregation_temporality: ``DELTA`` for a synchronous
            instrument and ``CUMULATIVE`` for an asynchronous one. Only
            ``DELTA`` produces points: see ``collect``.
        start_time_unix_nano: Nanoseconds since the Unix epoch at which this
            stream started. It is the start time of every cumulative point.
        max_size: Largest number of buckets allowed on each side, positive and
            negative, not counting the zero count. Lowering it makes
            downscaling happen sooner and so costs resolution. The default of
            160 comes from the specification.
        max_scale: Scale the aggregation starts at, and therefore the finest
            resolution it will ever use. A value above 20 is accepted with a
            warning, since at a higher scale the mapping loses accuracy.
        record_min_max: Whether to track the smallest and largest measurement.
            When ``False``, the points report ``None`` for both.

    Raises:
        ValueError: If ``max_size`` is below 2 or above 16384.
    """

    # _min_max_size and _max_max_size are the smallest and largest values
    # the max_size parameter may have, respectively.

    # _min_max_size is is the smallest reasonable value which is small enough
    # to contain the entire normal floating point range at the minimum scale.
    _min_max_size = 2

    # _max_max_size is an arbitrary limit meant to limit accidental creation of
    # giant exponential bucket histograms.
    _max_max_size = 16384

    def __init__(
        self,
        attributes: Attributes,
        reservoir_builder: ExemplarReservoirBuilder,
        instrument_aggregation_temporality: AggregationTemporality,
        start_time_unix_nano: int,
        # This is the default maximum number of buckets per positive or
        # negative number range.  The value 160 is specified by OpenTelemetry.
        # See the derivation here:
        # https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/metrics/sdk.md#exponential-bucket-histogram-aggregation)
        max_size: int = 160,
        max_scale: int = 20,
        record_min_max: bool = True,
    ):
        """Build the instance.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.

        Raises:
            ValueError: If ``max_size`` is below 2 or above 16384.
        """
        # max_size is the maximum capacity of the positive and negative
        # buckets.
        # _sum is the sum of all the values aggregated by this aggregator.
        # _count is the count of all calls to aggregate.
        # _zero_count is the count of all the calls to aggregate when the value
        # to be aggregated is exactly 0.
        # _min is the smallest value aggregated by this aggregator.
        # _max is the smallest value aggregated by this aggregator.
        # _positive holds the positive values.
        # _negative holds the negative values by their absolute value.
        if max_size < self._min_max_size:
            raise ValueError(f"Buckets max size {max_size} is smaller than minimum max size {self._min_max_size}")

        if max_size > self._max_max_size:
            raise ValueError(f"Buckets max size {max_size} is larger than maximum max size {self._max_max_size}")
        if max_scale > 20:
            _logger.warning(
                "max_scale is set to %s which is larger than the recommended value of 20",
                max_scale,
            )

        # This aggregation is analogous to _ExplicitBucketHistogramAggregation,
        # the only difference is that with every call to aggregate, the size
        # and amount of buckets can change (in
        # _ExplicitBucketHistogramAggregation both size and amount of buckets
        # remain constant once it is instantiated).

        super().__init__(
            attributes,
            reservoir_builder=partial(reservoir_builder, size=min(20, max_size)),
        )

        self._instrument_aggregation_temporality = instrument_aggregation_temporality
        self._start_time_unix_nano = start_time_unix_nano
        self._max_size = max_size
        self._max_scale = max_scale
        self._record_min_max = record_min_max

        self._value_positive = None
        self._value_negative = None
        self._min = math.inf
        self._max = -math.inf
        self._sum = 0
        self._count = 0
        self._zero_count = 0
        self._scale = None

        self._previous_value_positive = None
        self._previous_value_negative = None
        self._previous_min = math.inf
        self._previous_max = -math.inf
        self._previous_sum = 0
        self._previous_count = 0
        self._previous_zero_count = 0
        self._previous_scale = None

        self._previous_collection_start_nano = self._start_time_unix_nano

        self._mapping = self._new_mapping(self._max_scale)

    def aggregate(self, measurement: Measurement, should_sample_exemplar: bool = True) -> None:
        """Count the measurement, rescaling the buckets if it does not fit.

        The sum, the count and, when ``record_min_max`` is ``True``, the
        extremes are updated first, for every measurement including zero. A
        measurement of exactly zero then increments the zero count and
        returns, touching no bucket; while every measurement so far has been
        zero the scale is reported as 0, since no mapping has been exercised.

        A non-zero measurement is mapped to a bucket index at the current
        scale. If that index would stretch the used range of the side it
        belongs to, positive or negative, to more than ``max_size`` buckets,
        the scale is lowered by as much as it takes for the range to fit,
        both sides are collapsed together so that one scale keeps describing
        the whole histogram, the mapping is rebuilt and the value is mapped
        again at the new scale. The bucket array is
        then grown if needed, to a power of two capped at ``max_size``, and
        the bucket is incremented.

        Args:
            measurement: The measurement to count. A negative value is
                counted in the negative buckets by its absolute value, and is
                still subtracted from the running sum.
            should_sample_exemplar: Whether the measurement may be offered to
                the exemplar reservoir. It comes from the exemplar filter and
                is passed on unchanged. A zero measurement returns before the
                reservoir is offered anything.
        """
        # pylint: disable=too-many-branches,too-many-statements, too-many-locals

        with self._lock:
            if self._value_positive is None:
                self._value_positive = Buckets()
            if self._value_negative is None:
                self._value_negative = Buckets()

            measurement_value = measurement.value

            self._sum += measurement_value

            if self._record_min_max:
                self._min = min(self._min, measurement_value)
                self._max = max(self._max, measurement_value)

            self._count += 1

            if measurement_value == 0:
                self._zero_count += 1

                if self._count == self._zero_count:
                    self._scale = 0

                return

            if measurement_value > 0:
                value = self._value_positive

            else:
                measurement_value = -measurement_value
                value = self._value_negative

            # The following code finds out if it is necessary to change the
            # buckets to hold the incoming measurement_value, changes them if
            # necessary. This process does not exist in
            # _ExplicitBucketHistogram aggregation because the buckets there
            # are constant in size and amount.
            index = self._mapping.map_to_index(measurement_value)

            is_rescaling_needed = False
            low, high = 0, 0

            if len(value) == 0:
                value.index_start = index
                value.index_end = index
                value.index_base = index

            elif index < value.index_start and (value.index_end - index) >= self._max_size:
                is_rescaling_needed = True
                low = index
                high = value.index_end

            elif index > value.index_end and (index - value.index_start) >= self._max_size:
                is_rescaling_needed = True
                low = value.index_start
                high = index

            if is_rescaling_needed:
                scale_change = self._get_scale_change(low, high)
                self._downscale(
                    scale_change,
                    self._value_positive,
                    self._value_negative,
                )
                self._mapping = self._new_mapping(self._mapping.scale - scale_change)

                index = self._mapping.map_to_index(measurement_value)

            self._scale = self._mapping.scale

            if index < value.index_start:
                span = value.index_end - index

                if span >= len(value.counts):
                    value.grow(span + 1, self._max_size)

                value.index_start = index

            elif index > value.index_end:
                span = index - value.index_start

                if span >= len(value.counts):
                    value.grow(span + 1, self._max_size)

                value.index_end = index

            bucket_index = index - value.index_base

            if bucket_index < 0:
                bucket_index += len(value.counts)

            # Now the buckets have been changed if needed and bucket_index will
            # be used to increment the counter of the bucket that needs to be
            # incremented.

            # This is analogous to
            # self._value[bisect_left(self._boundaries, measurement_value)] += 1
            # in _ExplicitBucketHistogramAggregation.aggregate
            value.increment_bucket(bucket_index)

        self._sample_exemplar(measurement, should_sample_exemplar)

    def collect(
        self,
        collection_aggregation_temporality: AggregationTemporality,
        collection_start_nano: int,
    ) -> _DataPointVarT | None:
        """
        Atomically return a point for the current value of the metric.

        Producing a cumulative point is more involved than for the explicit
        bucket histogram, because the buckets just collected and the running
        cumulative buckets may be at different scales. Both are first brought
        down to a common scale, lowering it further if the merged range would
        not fit in ``max_size`` buckets, and only then are the counts added
        into the cumulative buckets. The scale reported is that common scale,
        so it can be lower than the scale of either side on its own.

        Args:
            collection_aggregation_temporality: The temporality the metric
                reader asked for.
            collection_start_nano: Nanoseconds since the Unix epoch at which
                this collection cycle started. It becomes the
                ``time_unix_nano`` of the returned point, and the start of the
                next delta interval.

        Returns:
            An ``ExponentialHistogramDataPoint``, or ``None``. ``None`` is
            returned when a delta point is asked for and no measurement
            arrived since the previous collection, and also whenever the
            instrument temporality is ``CUMULATIVE``, which means an
            asynchronous instrument with this aggregation never reports
            anything. The start time of a delta point is the time of the
            previous collection, falling back to ``start_time_unix_nano`` for
            the first one; the start time of a cumulative point is always
            ``start_time_unix_nano``. The ``flags`` field of the point is
            always 0.
        """

        # pylint: disable=too-many-statements, too-many-locals
        with self._lock:
            value_positive = self._value_positive
            value_negative = self._value_negative
            sum_ = self._sum
            min_ = self._min
            max_ = self._max
            count = self._count
            zero_count = self._zero_count
            scale = self._scale

            self._value_positive = None
            self._value_negative = None
            self._sum = 0
            self._min = math.inf
            self._max = -math.inf
            self._count = 0
            self._zero_count = 0
            self._scale = None

            if self._instrument_aggregation_temporality is AggregationTemporality.DELTA:
                # This happens when the corresponding instrument for this
                # aggregation is synchronous.
                if collection_aggregation_temporality is AggregationTemporality.DELTA:
                    previous_collection_start_nano = self._previous_collection_start_nano
                    self._previous_collection_start_nano = collection_start_nano

                    if value_positive is None and value_negative is None:
                        return None

                    return ExponentialHistogramDataPoint(
                        attributes=self._attributes,
                        exemplars=self._collect_exemplars(),
                        start_time_unix_nano=previous_collection_start_nano,
                        time_unix_nano=collection_start_nano,
                        count=count,
                        sum=sum_,
                        scale=scale,
                        zero_count=zero_count,
                        positive=BucketsPoint(
                            offset=value_positive.offset,
                            bucket_counts=(value_positive.get_offset_counts()),
                        ),
                        negative=BucketsPoint(
                            offset=value_negative.offset,
                            bucket_counts=(value_negative.get_offset_counts()),
                        ),
                        # FIXME: Find the right value for flags
                        flags=0,
                        min=min_ if self._record_min_max else None,
                        max=max_ if self._record_min_max else None,
                    )

                # Here collection_temporality is CUMULATIVE.
                # instrument_temporality is always DELTA for the time being.
                # Here we need to handle the case where:
                # collect is called after at least one other call to collect
                # (there is data in previous buckets, a call to merge is needed
                # to handle possible differences in bucket sizes).
                # collect is called without another call previous call to
                # collect was made (there is no previous buckets, previous,
                # empty buckets that are the same scale of the current buckets
                # need to be made so that they can be cumulatively aggregated
                # to the current buckets).

                if value_positive is None and self._previous_value_positive is None:
                    # This happens if collect is called for the first time
                    # and aggregate has not yet been called.
                    value_positive = Buckets()
                    self._previous_value_positive = value_positive.copy_empty()
                if value_negative is None and self._previous_value_negative is None:
                    value_negative = Buckets()
                    self._previous_value_negative = value_negative.copy_empty()
                if scale is None and self._previous_scale is None:
                    scale = self._mapping.scale
                    self._previous_scale = scale

                if value_positive is not None and self._previous_value_positive is None:
                    # This happens when collect is called the very first time
                    # and aggregate has been called before.

                    # We need previous buckets to add them to the current ones.
                    # When collect is called for the first time, there are no
                    # previous buckets, so we need to create empty buckets to
                    # add them to the current ones. The addition of empty
                    # buckets to the current ones will result in the current
                    # ones unchanged.

                    # The way the previous buckets are generated here is
                    # different from the explicit bucket histogram where
                    # the size and amount of the buckets does not change once
                    # they are instantiated. Here, the size and amount of the
                    # buckets can change with every call to aggregate. In order
                    # to get empty buckets that can be added to the current
                    # ones resulting in the current ones unchanged we need to
                    # generate empty buckets that have the same size and amount
                    # as the current ones, this is what copy_empty does.
                    self._previous_value_positive = value_positive.copy_empty()
                if value_negative is not None and self._previous_value_negative is None:
                    self._previous_value_negative = value_negative.copy_empty()
                if scale is not None and self._previous_scale is None:
                    self._previous_scale = scale

                if value_positive is None and self._previous_value_positive is not None:
                    value_positive = self._previous_value_positive.copy_empty()
                if value_negative is None and self._previous_value_negative is not None:
                    value_negative = self._previous_value_negative.copy_empty()
                if scale is None and self._previous_scale is not None:
                    scale = self._previous_scale

                # here self._previous_value_negative and self._previous_value_positive are not Optional anymore
                self._previous_value_negative = cast(Buckets, self._previous_value_negative)
                self._previous_value_positive = cast(Buckets, self._previous_value_positive)

                min_scale = min(self._previous_scale, scale)

                low_positive, high_positive = self._get_low_high_previous_current(
                    self._previous_value_positive,
                    value_positive,
                    scale,
                    min_scale,
                )
                low_negative, high_negative = self._get_low_high_previous_current(
                    self._previous_value_negative,
                    value_negative,
                    scale,
                    min_scale,
                )

                min_scale = min(
                    min_scale - self._get_scale_change(low_positive, high_positive),
                    min_scale - self._get_scale_change(low_negative, high_negative),
                )

                self._downscale(
                    self._previous_scale - min_scale,
                    self._previous_value_positive,
                    self._previous_value_negative,
                )

                # self._merge adds the values from value to
                # self._previous_value, this is analogous to
                # self._previous_value = [
                #     value_element + previous_value_element
                #     for (
                #         value_element,
                #         previous_value_element,
                #     ) in zip(value, self._previous_value)
                # ]
                # in _ExplicitBucketHistogramAggregation.collect.
                self._merge(
                    self._previous_value_positive,
                    value_positive,
                    scale,
                    min_scale,
                    collection_aggregation_temporality,
                )
                self._merge(
                    self._previous_value_negative,
                    value_negative,
                    scale,
                    min_scale,
                    collection_aggregation_temporality,
                )

                self._previous_min = min(min_, self._previous_min)
                self._previous_max = max(max_, self._previous_max)
                self._previous_sum = sum_ + self._previous_sum
                self._previous_count = count + self._previous_count
                self._previous_zero_count = zero_count + self._previous_zero_count
                self._previous_scale = min_scale

                return ExponentialHistogramDataPoint(
                    attributes=self._attributes,
                    exemplars=self._collect_exemplars(),
                    start_time_unix_nano=self._start_time_unix_nano,
                    time_unix_nano=collection_start_nano,
                    count=self._previous_count,
                    sum=self._previous_sum,
                    scale=self._previous_scale,
                    zero_count=self._previous_zero_count,
                    positive=BucketsPoint(
                        offset=self._previous_value_positive.offset,
                        bucket_counts=(self._previous_value_positive.get_offset_counts()),
                    ),
                    negative=BucketsPoint(
                        offset=self._previous_value_negative.offset,
                        bucket_counts=(self._previous_value_negative.get_offset_counts()),
                    ),
                    # FIXME: Find the right value for flags
                    flags=0,
                    min=self._previous_min if self._record_min_max else None,
                    max=self._previous_max if self._record_min_max else None,
                )

            return None

    def _get_low_high_previous_current(
        self,
        previous_point_buckets,
        current_point_buckets,
        current_scale,
        min_scale,
    ):
        """Find the index range that the two sets of buckets span together.

        Both ranges are expressed at ``min_scale`` before being combined, so
        that they can be compared. A set that is empty, which
        ``_get_low_high`` reports as the inverted range ``(0, -1)``, is left
        out of the combination, and if both are empty the inverted range is
        returned unchanged.

        Args:
            previous_point_buckets: The running cumulative buckets. They are
                read at ``self._previous_scale``.
            current_point_buckets: The buckets just collected.
            current_scale: Scale that ``current_point_buckets`` are at.
            min_scale: Scale both ranges are shifted down to.

        Returns:
            The lowest and the highest bucket index of the union, as a pair,
            both at ``min_scale``.
        """
        (previous_point_low, previous_point_high) = self._get_low_high(
            previous_point_buckets, self._previous_scale, min_scale
        )
        (current_point_low, current_point_high) = self._get_low_high(current_point_buckets, current_scale, min_scale)

        if current_point_low > current_point_high:
            low = previous_point_low
            high = previous_point_high

        elif previous_point_low > previous_point_high:
            low = current_point_low
            high = current_point_high

        else:
            low = min(previous_point_low, current_point_low)
            high = max(previous_point_high, current_point_high)

        return low, high

    @staticmethod
    def _get_low_high(buckets, scale, min_scale):
        """Express the index range of one set of buckets at a lower scale.

        Lowering the scale by one halves the number of buckets, so an index
        is shifted right by the difference between the two scales.

        Args:
            buckets: The buckets whose range is wanted.
            scale: Scale the buckets are at.
            min_scale: Scale the range is wanted at. It is never above
                ``scale``, so the shift is never negative.

        Returns:
            The lowest and the highest bucket index, as a pair, at
            ``min_scale``. A set of buckets that holds nothing is reported as
            ``(0, -1)``, an inverted range, which callers read as empty.
        """
        if buckets.counts == [0]:
            return 0, -1

        shift = scale - min_scale

        return buckets.index_start >> shift, buckets.index_end >> shift

    @staticmethod
    def _new_mapping(scale: int) -> Mapping:
        """Build the object that maps a value to a bucket index at ``scale``.

        Args:
            scale: The scale the mapping works at.

        Returns:
            A ``LogarithmMapping`` for a positive scale, where buckets are
            narrower than a power of two and a logarithm is needed, and an
            ``ExponentMapping`` for a scale of zero or below, where a bucket
            covers one or more binary exponents and the index can be read off
            the floating point representation.
        """
        if scale <= 0:
            return ExponentMapping(scale)
        return LogarithmMapping(scale)

    def _get_scale_change(self, low, high):
        """Count how far the scale must drop for a range to fit.

        The range is halved repeatedly until it spans no more than
        ``max_size`` buckets, and the number of halvings is the answer, since
        one halving of the bucket count is one unit of scale.

        Args:
            low: Lowest bucket index of the range.
            high: Highest bucket index of the range.

        Returns:
            The number of units the scale has to be lowered by, which is 0
            when the range already fits.
        """
        change = 0

        while high - low >= self._max_size:
            high = high >> 1
            low = low >> 1

            change += 1

        return change

    @staticmethod
    def _downscale(change: int, positive, negative):
        """Collapse both sides of the histogram by ``change`` units of scale.

        Each unit merges neighbouring buckets in pairs, so the counts are
        preserved and the resolution drops. Both sides are always collapsed
        together, so that one scale keeps describing the whole histogram.

        Args:
            change: How many units to lower the scale by. A change of 0 does
                nothing and returns immediately.
            positive: Buckets holding the positive measurements.
            negative: Buckets holding the negative measurements.

        Raises:
            Exception: If ``change`` is negative, which would mean raising the
                scale. The buckets carry no information to split, so this is
                a programming error rather than a recoverable condition.
        """
        if change == 0:
            return

        if change < 0:
            # pylint: disable=broad-exception-raised
            raise Exception("Invalid change of scale")

        positive.downscale(change)
        negative.downscale(change)

    def _merge(
        self,
        previous_buckets: Buckets,
        current_buckets: Buckets,
        current_scale,
        min_scale,
        aggregation_temporality,
    ):
        """Add the counts of one set of buckets into another, in place.

        Each non-empty bucket of ``current_buckets`` is mapped down to
        ``min_scale``, ``previous_buckets`` is extended if the index falls
        outside the range it already covers, and the count is added there.
        This is the exponential counterpart of adding two fixed bucket count
        lists element by element.

        Args:
            previous_buckets: The running cumulative buckets. They are
                modified in place and may be grown.
            current_buckets: The buckets just collected. They are only read.
            current_scale: Scale that ``current_buckets`` are at.
            min_scale: Scale ``previous_buckets`` are at, and the scale the
                indexes of ``current_buckets`` are shifted down to.
            aggregation_temporality: When it is ``DELTA``, each count is
                negated before being added, which subtracts the current
                buckets from the previous ones instead of adding them.

        Raises:
            Exception: If an index would stretch ``previous_buckets`` to more
                than ``max_size`` buckets, meaning the common scale was
                computed wrongly by the caller.
        """
        current_change = current_scale - min_scale

        for current_bucket_index, current_bucket in enumerate(current_buckets.counts):
            if current_bucket == 0:
                continue

            # Not considering the case where len(previous_buckets) == 0. This
            # would not happen because self._previous_point is only assigned to
            # an ExponentialHistogramDataPoint object if self._count != 0.

            current_index = current_buckets.index_base + current_bucket_index
            if current_index > current_buckets.index_end:
                current_index -= len(current_buckets.counts)

            index = current_index >> current_change

            if index < previous_buckets.index_start:
                span = previous_buckets.index_end - index

                if span >= self._max_size:
                    # pylint: disable=broad-exception-raised
                    raise Exception("Incorrect merge scale")

                if span >= len(previous_buckets.counts):
                    previous_buckets.grow(span + 1, self._max_size)

                previous_buckets.index_start = index

            if index > previous_buckets.index_end:
                span = index - previous_buckets.index_start

                if span >= self._max_size:
                    # pylint: disable=broad-exception-raised
                    raise Exception("Incorrect merge scale")

                if span >= len(previous_buckets.counts):
                    previous_buckets.grow(span + 1, self._max_size)

                previous_buckets.index_end = index

            bucket_index = index - previous_buckets.index_base

            if bucket_index < 0:
                bucket_index += len(previous_buckets.counts)

            if aggregation_temporality is AggregationTemporality.DELTA:
                current_bucket = -current_bucket

            previous_buckets.increment_bucket(bucket_index, increment=current_bucket)


class Aggregation(ABC):
    """
    Base class for all aggregation types.

    A subclass is a factory and holds no measurement state. A ``View`` is
    given one instance, and that instance is asked for a new ``_Aggregation``
    every time the stream sees an attribute set it has not seen before. The
    subclasses that take parameters (``ExplicitBucketHistogramAggregation``,
    ``ExponentialBucketHistogramAggregation``) hold them and pass them to
    every object they build, which is why one instance can be shared.
    """

    @abstractmethod
    def _create_aggregation(
        self,
        instrument: _Instrument,
        attributes: Attributes,
        reservoir_factory: Callable[[type[_Aggregation]], ExemplarReservoirBuilder],
        start_time_unix_nano: int,
    ) -> _Aggregation:
        """Creates an aggregation

        Args:
            instrument: The instrument the stream was created from. Most
                implementations read its kind, to decide whether measurements
                are increments or running totals.
            attributes: The attribute set the new object will aggregate.
            reservoir_factory: Called with the class of the ``_Aggregation``
                about to be built, and returns the builder for the exemplar
                reservoir that suits it.
            start_time_unix_nano: Nanoseconds since the Unix epoch to record
                as the start of the stream.

        Returns:
            A new ``_Aggregation`` holding no measurements yet.
        """


class DefaultAggregation(Aggregation):
    """
    The default aggregation to be used in a `View`.

    This aggregation will create an actual aggregation depending on the
    instrument type, as specified next:

    ==================================================== ====================================
    Instrument                                           Aggregation
    ==================================================== ====================================
    `opentelemetry.sdk.metrics.Counter`                  `SumAggregation`
    `opentelemetry.sdk.metrics.UpDownCounter`            `SumAggregation`
    `opentelemetry.sdk.metrics.ObservableCounter`        `SumAggregation`
    `opentelemetry.sdk.metrics.ObservableUpDownCounter`  `SumAggregation`
    `opentelemetry.sdk.metrics.Histogram`                `ExplicitBucketHistogramAggregation`
    `opentelemetry.sdk.metrics.ObservableGauge`          `LastValueAggregation`
    ==================================================== ====================================
    """

    def _create_aggregation(
        self,
        instrument: _Instrument,
        attributes: Attributes,
        reservoir_factory: Callable[[type[_Aggregation]], ExemplarReservoirBuilder],
        start_time_unix_nano: int,
    ) -> _Aggregation:
        """Build the aggregation that suits the instrument kind.

        The instrument type is tested against the API classes in the order of
        the table above, and that choice also fixes the instrument
        temporality: ``DELTA`` for the synchronous instruments, ``CUMULATIVE``
        for the observable ones. A histogram takes its bucket boundaries from
        the advisory the instrument was created with.

        Args:
            instrument: The instrument the stream was created from.
            attributes: The attribute set the new object will aggregate.
            reservoir_factory: Builds the exemplar reservoir builder for the
                aggregation class that was chosen.
            start_time_unix_nano: Nanoseconds since the Unix epoch to record
                as the start of the stream.

        Returns:
            A ``_SumAggregation``, a ``_ExplicitBucketHistogramAggregation``
            or a ``_LastValueAggregation``, according to the table above. A
            synchronous gauge, which the table omits, also gets a
            ``_LastValueAggregation``, built with
            ``instrument_is_synchronous`` set to ``True``.

        Raises:
            Exception: If the instrument is of none of the known kinds, which
                can only happen with an instrument implemented outside this
                SDK.
        """
        # pylint: disable=too-many-return-statements
        if isinstance(instrument, Counter):
            return _SumAggregation(
                attributes,
                reservoir_builder=reservoir_factory(_SumAggregation),
                instrument_is_monotonic=True,
                instrument_aggregation_temporality=(AggregationTemporality.DELTA),
                start_time_unix_nano=start_time_unix_nano,
            )
        if isinstance(instrument, UpDownCounter):
            return _SumAggregation(
                attributes,
                reservoir_builder=reservoir_factory(_SumAggregation),
                instrument_is_monotonic=False,
                instrument_aggregation_temporality=(AggregationTemporality.DELTA),
                start_time_unix_nano=start_time_unix_nano,
            )

        if isinstance(instrument, ObservableCounter):
            return _SumAggregation(
                attributes,
                reservoir_builder=reservoir_factory(_SumAggregation),
                instrument_is_monotonic=True,
                instrument_aggregation_temporality=(AggregationTemporality.CUMULATIVE),
                start_time_unix_nano=start_time_unix_nano,
            )

        if isinstance(instrument, ObservableUpDownCounter):
            return _SumAggregation(
                attributes,
                reservoir_builder=reservoir_factory(_SumAggregation),
                instrument_is_monotonic=False,
                instrument_aggregation_temporality=(AggregationTemporality.CUMULATIVE),
                start_time_unix_nano=start_time_unix_nano,
            )

        if isinstance(instrument, Histogram):
            boundaries = instrument._advisory.explicit_bucket_boundaries
            return _ExplicitBucketHistogramAggregation(
                attributes,
                reservoir_builder=reservoir_factory(_ExplicitBucketHistogramAggregation),
                instrument_aggregation_temporality=(AggregationTemporality.DELTA),
                boundaries=boundaries,
                start_time_unix_nano=start_time_unix_nano,
            )

        if isinstance(instrument, ObservableGauge):
            return _LastValueAggregation(
                attributes,
                reservoir_builder=reservoir_factory(_LastValueAggregation),
                instrument_is_synchronous=False,
            )

        if isinstance(instrument, _Gauge):
            return _LastValueAggregation(
                attributes,
                reservoir_builder=reservoir_factory(_LastValueAggregation),
                instrument_is_synchronous=True,
            )

        # pylint: disable=broad-exception-raised
        raise Exception(f"Invalid instrument type {type(instrument)} found")


class ExponentialBucketHistogramAggregation(Aggregation):
    """This aggregation informs the SDK to collect:

    - Count of Measurement values falling using a base-2 exponential formula.
    - Arithmetic sum of Measurement values in population. This SHOULD NOT be collected when used with instruments that record negative measurements, e.g. UpDownCounter or ObservableGauge.
    - Min (optional) Measurement value in population.
    - Max (optional) Measurement value in population.

    Args:
        max_size: Maximum number of buckets in each of the positive and negative ranges, not counting the special zero bucket.
        max_scale: Maximum scale factor.
        record_min_max: Whether to record min and max.
    """

    def __init__(
        self,
        max_size: int = 160,
        max_scale: int = 20,
        record_min_max: bool = True,
    ):
        """Build the factory.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders. Nothing is validated here: a
        ``max_size`` outside the allowed range is only rejected when the
        first stream is created.
        """
        self._max_size = max_size
        self._max_scale = max_scale
        self._record_min_max = record_min_max

    def _create_aggregation(
        self,
        instrument: _Instrument,
        attributes: Attributes,
        reservoir_factory: Callable[[type[_Aggregation]], ExemplarReservoirBuilder],
        start_time_unix_nano: int,
    ) -> _Aggregation:
        """Build an exponential bucket histogram for one attribute set.

        The three parameters held by this factory are passed on unchanged, so
        every stream the view produces shares the same limits.

        Args:
            instrument: The instrument the stream was created from. A
                synchronous one gives an instrument temporality of ``DELTA``,
                an asynchronous one ``CUMULATIVE``, and anything else
                ``UNSPECIFIED``, which produces no points at all.
            attributes: The attribute set the new object will aggregate.
            reservoir_factory: Builds the exemplar reservoir builder.
            start_time_unix_nano: Nanoseconds since the Unix epoch to record
                as the start of the stream.

        Returns:
            A new ``_ExponentialBucketHistogramAggregation``.
        """
        instrument_aggregation_temporality = AggregationTemporality.UNSPECIFIED
        if isinstance(instrument, Synchronous):
            instrument_aggregation_temporality = AggregationTemporality.DELTA
        elif isinstance(instrument, Asynchronous):
            instrument_aggregation_temporality = AggregationTemporality.CUMULATIVE

        return _ExponentialBucketHistogramAggregation(
            attributes,
            reservoir_factory(_ExponentialBucketHistogramAggregation),
            instrument_aggregation_temporality,
            start_time_unix_nano,
            max_size=self._max_size,
            max_scale=self._max_scale,
            record_min_max=self._record_min_max,
        )


class ExplicitBucketHistogramAggregation(Aggregation):
    """This aggregation informs the SDK to collect:

    - Count of Measurement values falling within explicit bucket boundaries.
    - Arithmetic sum of Measurement values in population. This SHOULD NOT be collected when used with instruments that record negative measurements, e.g. UpDownCounter or ObservableGauge.
    - Min (optional) Measurement value in population.
    - Max (optional) Measurement value in population.


    Args:
        boundaries: Array of increasing values representing explicit bucket boundary values.
        record_min_max: Whether to record min and max.
    """

    def __init__(
        self,
        boundaries: Sequence[float] | None = None,
        record_min_max: bool = True,
    ) -> None:
        """Build the factory.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders. The boundaries are not validated
        here: a malformed sequence is only rejected when the first stream is
        created.
        """
        self._boundaries = boundaries
        self._record_min_max = record_min_max

    def _create_aggregation(
        self,
        instrument: _Instrument,
        attributes: Attributes,
        reservoir_factory: Callable[[type[_Aggregation]], ExemplarReservoirBuilder],
        start_time_unix_nano: int,
    ) -> _Aggregation:
        """Build an explicit bucket histogram for one attribute set.

        The boundaries given to this factory win. When it was given ``None``,
        the boundaries come from the advisory of the instrument, and when the
        instrument carries no advisory they stay ``None``, which makes the
        aggregation fall back to its own default set.

        Args:
            instrument: The instrument the stream was created from. A
                synchronous one gives an instrument temporality of ``DELTA``,
                an asynchronous one ``CUMULATIVE``, and anything else
                ``UNSPECIFIED``, which produces no points at all.
            attributes: The attribute set the new object will aggregate.
            reservoir_factory: Builds the exemplar reservoir builder.
            start_time_unix_nano: Nanoseconds since the Unix epoch to record
                as the start of the stream.

        Returns:
            A new ``_ExplicitBucketHistogramAggregation``.

        Raises:
            ValueError: If the boundaries that end up being used are not
                finite and strictly increasing.
        """
        instrument_aggregation_temporality = AggregationTemporality.UNSPECIFIED
        if isinstance(instrument, Synchronous):
            instrument_aggregation_temporality = AggregationTemporality.DELTA
        elif isinstance(instrument, Asynchronous):
            instrument_aggregation_temporality = AggregationTemporality.CUMULATIVE

        if self._boundaries is not None:
            boundaries = self._boundaries
        else:
            # guard for usage with instruments without advisory
            advisory = getattr(instrument, "_advisory", None)
            boundaries = advisory.explicit_bucket_boundaries if advisory is not None else None

        return _ExplicitBucketHistogramAggregation(
            attributes,
            instrument_aggregation_temporality,
            start_time_unix_nano,
            reservoir_factory(_ExplicitBucketHistogramAggregation),
            boundaries,
            self._record_min_max,
        )


class SumAggregation(Aggregation):
    """This aggregation informs the SDK to collect:

    - The arithmetic sum of Measurement values.
    """

    def _create_aggregation(
        self,
        instrument: _Instrument,
        attributes: Attributes,
        reservoir_factory: Callable[[type[_Aggregation]], ExemplarReservoirBuilder],
        start_time_unix_nano: int,
    ) -> _Aggregation:
        """Build a sum aggregation for one attribute set.

        Selecting this aggregation in a view is how a histogram instrument
        can be reduced to a plain sum.

        Args:
            instrument: The instrument the stream was created from. A counter
                or an observable counter is reported as monotonic, anything
                else as non-monotonic. A synchronous instrument gives an
                instrument temporality of ``DELTA``, an asynchronous one
                ``CUMULATIVE``, and anything else ``UNSPECIFIED``.
            attributes: The attribute set the new object will aggregate.
            reservoir_factory: Builds the exemplar reservoir builder.
            start_time_unix_nano: Nanoseconds since the Unix epoch to record
                as the start of the stream.

        Returns:
            A new ``_SumAggregation``.
        """
        instrument_aggregation_temporality = AggregationTemporality.UNSPECIFIED
        if isinstance(instrument, Synchronous):
            instrument_aggregation_temporality = AggregationTemporality.DELTA
        elif isinstance(instrument, Asynchronous):
            instrument_aggregation_temporality = AggregationTemporality.CUMULATIVE

        return _SumAggregation(
            attributes,
            isinstance(instrument, (Counter, ObservableCounter)),
            instrument_aggregation_temporality,
            start_time_unix_nano,
            reservoir_factory(_SumAggregation),
        )


class LastValueAggregation(Aggregation):
    """
    This aggregation informs the SDK to collect:

    - The last Measurement.
    - The timestamp of the last Measurement.
    """

    def _create_aggregation(
        self,
        instrument: _Instrument,
        attributes: Attributes,
        reservoir_factory: Callable[[type[_Aggregation]], ExemplarReservoirBuilder],
        start_time_unix_nano: int,
    ) -> _Aggregation:
        """Build a last value aggregation for one attribute set.

        Args:
            instrument: The instrument the stream was created from. Only
                whether it is synchronous matters here, and it decides
                whether the stored reading survives a cumulative collection.
            attributes: The attribute set the new object will aggregate.
            reservoir_factory: Builds the exemplar reservoir builder.
            start_time_unix_nano: Ignored. The points this aggregation
                produces carry no start time.

        Returns:
            A new ``_LastValueAggregation``.
        """
        return _LastValueAggregation(
            attributes,
            reservoir_builder=reservoir_factory(_LastValueAggregation),
            instrument_is_synchronous=isinstance(instrument, Synchronous),
        )


class DropAggregation(Aggregation):
    """Using this aggregation will make all measurements be ignored."""

    def _create_aggregation(
        self,
        instrument: _Instrument,
        attributes: Attributes,
        reservoir_factory: Callable[[type[_Aggregation]], ExemplarReservoirBuilder],
        start_time_unix_nano: int,
    ) -> _Aggregation:
        """Build the aggregation that discards everything.

        Args:
            instrument: Ignored. The behaviour does not depend on the
                instrument kind.
            attributes: The attribute set the new object would aggregate. It
                is stored and never used, since no point is produced.
            reservoir_factory: Builds the exemplar reservoir builder. The
                reservoir is created and never offered anything.
            start_time_unix_nano: Ignored.

        Returns:
            A new ``_DropAggregation``.
        """
        return _DropAggregation(attributes, reservoir_factory(_DropAggregation))
