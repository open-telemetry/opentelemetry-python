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

"""
.. Explicitly document private _AggregationFactory
.. autoclass:: _AggregationFactory
"""

from abc import ABC, abstractmethod
from bisect import bisect_left
from dataclasses import replace
from logging import getLogger
from math import inf
from threading import Lock
from typing import Generic, List, Optional, Sequence, TypeVar

from opentelemetry._metrics.instrument import (
    Asynchronous,
    Counter,
    Histogram,
    Instrument,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    Synchronous,
    UpDownCounter,
    _Monotonic,
)
from opentelemetry.sdk._metrics.measurement import Measurement
from opentelemetry.sdk._metrics.point import AggregationTemporality, Gauge
from opentelemetry.sdk._metrics.point import Histogram as HistogramPoint
from opentelemetry.sdk._metrics.point import PointT, Sum
from opentelemetry.util._time import _time_ns

_PointVarT = TypeVar("_PointVarT", bound=PointT)

_logger = getLogger(__name__)


class _Aggregation(ABC, Generic[_PointVarT]):
    def __init__(self):
        self._lock = Lock()

    @abstractmethod
    def aggregate(self, measurement: Measurement) -> None:
        pass

    @abstractmethod
    def collect(self) -> Optional[_PointVarT]:
        pass


class _DropAggregation(_Aggregation):
    def aggregate(self, measurement: Measurement) -> None:
        pass

    def collect(self) -> Optional[_PointVarT]:
        pass


class _AggregationFactory(ABC):
    @abstractmethod
    def _create_aggregation(self, instrument: Instrument) -> _Aggregation:
        """Creates an aggregation"""


class DefaultAggregation(_AggregationFactory):
    """
    The default aggregation to be used in a `View`.

    This aggregation will create an actual aggregation depending on the
    instrument type, as specified next:

    ============================================= ====================================
    Instrument                                    Aggregation
    ============================================= ====================================
    `Counter`                                     `SumAggregation`
    `UpDownCounter`                               `SumAggregation`
    `ObservableCounter`                           `SumAggregation`
    `ObservableUpDownCounter`                     `SumAggregation`
    `opentelemetry._metrics.instrument.Histogram` `ExplicitBucketHistogramAggregation`
    `ObservableGauge`                             `LastValueAggregation`
    ============================================= ====================================
    """

    def _create_aggregation(self, instrument: Instrument) -> _Aggregation:

        # pylint: disable=too-many-return-statements
        if isinstance(instrument, Counter):
            return _SumAggregation(
                instrument_is_monotonic=True,
                instrument_temporality=AggregationTemporality.DELTA,
            )
        if isinstance(instrument, UpDownCounter):
            return _SumAggregation(
                instrument_is_monotonic=False,
                instrument_temporality=AggregationTemporality.DELTA,
            )

        if isinstance(instrument, ObservableCounter):
            return _SumAggregation(
                instrument_is_monotonic=True,
                instrument_temporality=AggregationTemporality.CUMULATIVE,
            )

        if isinstance(instrument, ObservableUpDownCounter):
            return _SumAggregation(
                instrument_is_monotonic=False,
                instrument_temporality=AggregationTemporality.CUMULATIVE,
            )

        if isinstance(instrument, Histogram):
            return _ExplicitBucketHistogramAggregation()

        if isinstance(instrument, ObservableGauge):
            return _LastValueAggregation()

        raise Exception(f"Invalid instrument type {type(instrument)} found")


class _SumAggregation(_Aggregation[Sum]):
    def __init__(
        self,
        instrument_is_monotonic: bool,
        instrument_temporality: AggregationTemporality,
    ):
        super().__init__()

        self._start_time_unix_nano = _time_ns()
        self._instrument_temporality = instrument_temporality
        self._instrument_is_monotonic = instrument_is_monotonic

        if self._instrument_temporality is AggregationTemporality.DELTA:
            self._value = 0
        else:
            self._value = None

    def aggregate(self, measurement: Measurement) -> None:
        with self._lock:
            if self._value is None:
                self._value = 0
            self._value = self._value + measurement.value

    def collect(self) -> Optional[Sum]:
        """
        Atomically return a point for the current value of the metric and
        reset the aggregation value.
        """
        now = _time_ns()

        if self._instrument_temporality is AggregationTemporality.DELTA:

            with self._lock:
                value = self._value
                start_time_unix_nano = self._start_time_unix_nano

                self._value = 0
                self._start_time_unix_nano = now + 1

            return Sum(
                aggregation_temporality=AggregationTemporality.DELTA,
                is_monotonic=self._instrument_is_monotonic,
                start_time_unix_nano=start_time_unix_nano,
                time_unix_nano=now,
                value=value,
            )

        with self._lock:
            if self._value is None:
                return None
            value = self._value
            self._value = None

        return Sum(
            aggregation_temporality=AggregationTemporality.CUMULATIVE,
            is_monotonic=self._instrument_is_monotonic,
            start_time_unix_nano=self._start_time_unix_nano,
            time_unix_nano=now,
            value=value,
        )


class _LastValueAggregation(_Aggregation[Gauge]):
    def __init__(self):
        super().__init__()
        self._value = None

    def aggregate(self, measurement: Measurement):
        with self._lock:
            self._value = measurement.value

    def collect(self) -> Optional[Gauge]:
        """
        Atomically return a point for the current value of the metric.
        """
        with self._lock:
            if self._value is None:
                return None
            value = self._value
            self._value = None

        return Gauge(
            time_unix_nano=_time_ns(),
            value=value,
        )


class _ExplicitBucketHistogramAggregation(_Aggregation[HistogramPoint]):
    def __init__(
        self,
        boundaries: Sequence[float] = (
            0.0,
            5.0,
            10.0,
            25.0,
            50.0,
            75.0,
            100.0,
            250.0,
            500.0,
            1000.0,
        ),
        record_min_max: bool = True,
    ):
        super().__init__()
        self._boundaries = tuple(boundaries)
        self._bucket_counts = self._get_empty_bucket_counts()
        self._min = inf
        self._max = -inf
        self._sum = 0
        self._record_min_max = record_min_max
        self._start_time_unix_nano = _time_ns()

    def _get_empty_bucket_counts(self) -> List[int]:
        return [0] * (len(self._boundaries) + 1)

    def aggregate(self, measurement: Measurement) -> None:

        value = measurement.value

        if self._record_min_max:
            self._min = min(self._min, value)
            self._max = max(self._max, value)

        self._sum += value

        self._bucket_counts[bisect_left(self._boundaries, value)] += 1

    def collect(self) -> HistogramPoint:
        """
        Atomically return a point for the current value of the metric.
        """
        now = _time_ns()

        with self._lock:
            value = self._bucket_counts
            start_time_unix_nano = self._start_time_unix_nano
            histogram_sum = self._sum
            histogram_max = self._max
            histogram_min = self._min

            self._bucket_counts = self._get_empty_bucket_counts()
            self._start_time_unix_nano = now + 1
            self._sum = 0
            self._min = inf
            self._max = -inf

        return HistogramPoint(
            aggregation_temporality=AggregationTemporality.DELTA,
            bucket_counts=tuple(value),
            explicit_bounds=self._boundaries,
            max=histogram_max,
            min=histogram_min,
            start_time_unix_nano=start_time_unix_nano,
            sum=histogram_sum,
            time_unix_nano=now,
        )


# pylint: disable=too-many-return-statements,too-many-branches
def _convert_aggregation_temporality(
    previous_point: Optional[_PointVarT],
    current_point: _PointVarT,
    aggregation_temporality: AggregationTemporality,
) -> _PointVarT:
    """Converts `current_point` to the requested `aggregation_temporality`
    given the `previous_point`.

    `previous_point` must have `CUMULATIVE` temporality. `current_point` may
    have `DELTA` or `CUMULATIVE` temporality.

    The output point will have temporality `aggregation_temporality`. Since
    `GAUGE` points have no temporality, they are returned unchanged.
    """

    current_point_type = type(current_point)

    if current_point_type is Gauge:
        return current_point

    if (
        previous_point is not None
        and current_point is not None
        and type(previous_point) is not type(current_point)
    ):
        _logger.warning(
            "convert_aggregation_temporality called with mismatched "
            "point types: %s and %s",
            type(previous_point),
            current_point_type,
        )

        return current_point

    if current_point_type is Sum:
        if previous_point is None:
            # Output CUMULATIVE for a synchronous instrument
            # There is no previous value, return the delta point as a
            # cumulative
            return replace(
                current_point, aggregation_temporality=aggregation_temporality
            )
        if previous_point.aggregation_temporality is not (
            AggregationTemporality.CUMULATIVE
        ):
            raise Exception(
                "previous_point aggregation temporality must be CUMULATIVE"
            )

        if current_point.aggregation_temporality is aggregation_temporality:
            # Output DELTA for a synchronous instrument
            # Output CUMULATIVE for an asynchronous instrument
            return current_point

        if aggregation_temporality is AggregationTemporality.DELTA:
            # Output temporality DELTA for an asynchronous instrument
            value = current_point.value - previous_point.value
            output_start_time_unix_nano = previous_point.time_unix_nano

        else:
            # Output CUMULATIVE for a synchronous instrument
            value = current_point.value + previous_point.value
            output_start_time_unix_nano = previous_point.start_time_unix_nano

        is_monotonic = (
            previous_point.is_monotonic and current_point.is_monotonic
        )

        return Sum(
            start_time_unix_nano=output_start_time_unix_nano,
            time_unix_nano=current_point.time_unix_nano,
            value=value,
            aggregation_temporality=aggregation_temporality,
            is_monotonic=is_monotonic,
        )

    if current_point_type is HistogramPoint:
        if previous_point is None:
            return replace(
                current_point, aggregation_temporality=aggregation_temporality
            )
        if previous_point.aggregation_temporality is not (
            AggregationTemporality.CUMULATIVE
        ):
            raise Exception(
                "previous_point aggregation temporality must be CUMULATIVE"
            )

        if current_point.aggregation_temporality is aggregation_temporality:
            return current_point

        max_ = current_point.max
        min_ = current_point.min

        if aggregation_temporality is AggregationTemporality.CUMULATIVE:
            start_time_unix_nano = previous_point.start_time_unix_nano
            sum_ = current_point.sum + previous_point.sum
            # Only update min/max on delta -> cumulative
            max_ = max(current_point.max, previous_point.max)
            min_ = min(current_point.min, previous_point.min)
            bucket_counts = [
                curr_count + prev_count
                for curr_count, prev_count in zip(
                    current_point.bucket_counts, previous_point.bucket_counts
                )
            ]
        else:
            start_time_unix_nano = previous_point.time_unix_nano
            sum_ = current_point.sum - previous_point.sum
            bucket_counts = [
                curr_count - prev_count
                for curr_count, prev_count in zip(
                    current_point.bucket_counts, previous_point.bucket_counts
                )
            ]

        return HistogramPoint(
            aggregation_temporality=aggregation_temporality,
            bucket_counts=bucket_counts,
            explicit_bounds=current_point.explicit_bounds,
            max=max_,
            min=min_,
            start_time_unix_nano=start_time_unix_nano,
            sum=sum_,
            time_unix_nano=current_point.time_unix_nano,
        )
    return None


class ExplicitBucketHistogramAggregation(_AggregationFactory):
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
        boundaries: Sequence[float] = (
            0.0,
            5.0,
            10.0,
            25.0,
            50.0,
            75.0,
            100.0,
            250.0,
            500.0,
            1000.0,
        ),
        record_min_max: bool = True,
    ) -> None:
        self._boundaries = boundaries
        self._record_min_max = record_min_max

    def _create_aggregation(self, instrument: Instrument) -> _Aggregation:
        return _ExplicitBucketHistogramAggregation(
            boundaries=self._boundaries,
            record_min_max=self._record_min_max,
        )


class SumAggregation(_AggregationFactory):
    """This aggregation informs the SDK to collect:

    - The arithmetic sum of Measurement values.
    """

    def _create_aggregation(self, instrument: Instrument) -> _Aggregation:

        temporality = AggregationTemporality.UNSPECIFIED
        if isinstance(instrument, Synchronous):
            temporality = AggregationTemporality.DELTA
        elif isinstance(instrument, Asynchronous):
            temporality = AggregationTemporality.CUMULATIVE

        return _SumAggregation(
            isinstance(instrument, _Monotonic),
            temporality,
        )


class LastValueAggregation(_AggregationFactory):
    """
    This aggregation informs the SDK to collect:

    - The last Measurement.
    - The timestamp of the last Measurement.
    """

    def _create_aggregation(self, instrument: Instrument) -> _Aggregation:
        return _LastValueAggregation()


class DropAggregation(_AggregationFactory):
    """Using this aggregation will make all measurements be ignored."""

    def _create_aggregation(self, instrument: Instrument) -> _Aggregation:
        return _DropAggregation()
