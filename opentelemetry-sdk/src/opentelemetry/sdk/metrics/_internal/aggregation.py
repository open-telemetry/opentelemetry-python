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

from abc import ABC, abstractmethod
from bisect import bisect_left
from enum import IntEnum
from logging import getLogger
from math import inf
from threading import Lock
from typing import Generic, List, Optional, Sequence, TypeVar

from opentelemetry.metrics import (
    Asynchronous,
    Counter,
    Histogram,
    Instrument,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    Synchronous,
    UpDownCounter,
)
from opentelemetry.sdk.metrics._internal.measurement import Measurement
from opentelemetry.sdk.metrics._internal.point import Gauge
from opentelemetry.sdk.metrics._internal.point import (
    Histogram as HistogramPoint,
)
from opentelemetry.sdk.metrics._internal.point import (
    HistogramDataPoint,
    NumberDataPoint,
    Sum,
)
from opentelemetry.util.types import Attributes

_DataPointVarT = TypeVar("_DataPointVarT", NumberDataPoint, HistogramDataPoint)

_logger = getLogger(__name__)


class AggregationTemporality(IntEnum):
    """
    The temporality to use when aggregating data.

    Can be one of the following values:
    """

    UNSPECIFIED = 0
    DELTA = 1
    CUMULATIVE = 2


class _Aggregation(ABC, Generic[_DataPointVarT]):
    def __init__(self, attributes: Attributes):
        self._lock = Lock()
        self._attributes = attributes
        self._previous_point = None

    @abstractmethod
    def aggregate(self, measurement: Measurement) -> None:
        pass

    @abstractmethod
    def collect(
        self,
        aggregation_temporality: AggregationTemporality,
        collection_start_nano: int,
    ) -> Optional[_DataPointVarT]:
        pass


class _DropAggregation(_Aggregation):
    def aggregate(self, measurement: Measurement) -> None:
        pass

    def collect(
        self,
        aggregation_temporality: AggregationTemporality,
        collection_start_nano: int,
    ) -> Optional[_DataPointVarT]:
        pass


class _SumAggregation(_Aggregation[Sum]):
    def __init__(
        self,
        attributes: Attributes,
        instrument_is_monotonic: bool,
        instrument_temporality: AggregationTemporality,
        start_time_unix_nano: int,
    ):
        super().__init__(attributes)

        self._start_time_unix_nano = start_time_unix_nano
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

    def collect(
        self,
        aggregation_temporality: AggregationTemporality,
        collection_start_nano: int,
    ) -> Optional[NumberDataPoint]:
        """
        Atomically return a point for the current value of the metric and
        reset the aggregation value.
        """
        if self._instrument_temporality is AggregationTemporality.DELTA:

            with self._lock:
                value = self._value
                start_time_unix_nano = self._start_time_unix_nano

                self._value = 0
                self._start_time_unix_nano = collection_start_nano

        else:

            with self._lock:
                if self._value is None:
                    return None
                value = self._value
                self._value = None
                start_time_unix_nano = self._start_time_unix_nano

        current_point = NumberDataPoint(
            attributes=self._attributes,
            start_time_unix_nano=start_time_unix_nano,
            time_unix_nano=collection_start_nano,
            value=value,
        )

        if self._previous_point is None or (
            self._instrument_temporality is aggregation_temporality
        ):
            # Output DELTA for a synchronous instrument
            # Output CUMULATIVE for an asynchronous instrument
            self._previous_point = current_point
            return current_point

        if aggregation_temporality is AggregationTemporality.DELTA:
            # Output temporality DELTA for an asynchronous instrument
            value = current_point.value - self._previous_point.value
            output_start_time_unix_nano = self._previous_point.time_unix_nano

        else:
            # Output CUMULATIVE for a synchronous instrument
            value = current_point.value + self._previous_point.value
            output_start_time_unix_nano = (
                self._previous_point.start_time_unix_nano
            )

        current_point = NumberDataPoint(
            attributes=self._attributes,
            start_time_unix_nano=output_start_time_unix_nano,
            time_unix_nano=current_point.time_unix_nano,
            value=value,
        )

        self._previous_point = current_point
        return current_point


class _LastValueAggregation(_Aggregation[Gauge]):
    def __init__(self, attributes: Attributes):
        super().__init__(attributes)
        self._value = None

    def aggregate(self, measurement: Measurement):
        with self._lock:
            self._value = measurement.value

    def collect(
        self,
        aggregation_temporality: AggregationTemporality,
        collection_start_nano: int,
    ) -> Optional[_DataPointVarT]:
        """
        Atomically return a point for the current value of the metric.
        """
        with self._lock:
            if self._value is None:
                return None
            value = self._value
            self._value = None

        return NumberDataPoint(
            attributes=self._attributes,
            start_time_unix_nano=0,
            time_unix_nano=collection_start_nano,
            value=value,
        )


class _ExplicitBucketHistogramAggregation(_Aggregation[HistogramPoint]):
    def __init__(
        self,
        attributes: Attributes,
        start_time_unix_nano: int,
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
            750.0,
            1000.0,
            2500.0,
            5000.0,
            7500.0,
            10000.0,
        ),
        record_min_max: bool = True,
    ):
        super().__init__(attributes)
        self._boundaries = tuple(boundaries)
        self._bucket_counts = self._get_empty_bucket_counts()
        self._min = inf
        self._max = -inf
        self._sum = 0
        self._record_min_max = record_min_max
        self._start_time_unix_nano = start_time_unix_nano
        # It is assumed that the "natural" aggregation temporality for a
        # Histogram instrument is DELTA, like the "natural" aggregation
        # temporality for a Counter is DELTA and the "natural" aggregation
        # temporality for an ObservableCounter is CUMULATIVE.
        self._instrument_temporality = AggregationTemporality.DELTA

    def _get_empty_bucket_counts(self) -> List[int]:
        return [0] * (len(self._boundaries) + 1)

    def aggregate(self, measurement: Measurement) -> None:

        value = measurement.value

        if self._record_min_max:
            self._min = min(self._min, value)
            self._max = max(self._max, value)

        self._sum += value

        self._bucket_counts[bisect_left(self._boundaries, value)] += 1

    def collect(
        self,
        aggregation_temporality: AggregationTemporality,
        collection_start_nano: int,
    ) -> Optional[_DataPointVarT]:
        """
        Atomically return a point for the current value of the metric.
        """
        with self._lock:
            if not any(self._bucket_counts):
                return None

            bucket_counts = self._bucket_counts
            start_time_unix_nano = self._start_time_unix_nano
            sum_ = self._sum
            max_ = self._max
            min_ = self._min

            self._bucket_counts = self._get_empty_bucket_counts()
            self._start_time_unix_nano = collection_start_nano
            self._sum = 0
            self._min = inf
            self._max = -inf

        current_point = HistogramDataPoint(
            attributes=self._attributes,
            start_time_unix_nano=start_time_unix_nano,
            time_unix_nano=collection_start_nano,
            count=sum(bucket_counts),
            sum=sum_,
            bucket_counts=tuple(bucket_counts),
            explicit_bounds=self._boundaries,
            min=min_,
            max=max_,
        )

        if self._previous_point is None or (
            self._instrument_temporality is aggregation_temporality
        ):
            self._previous_point = current_point
            return current_point

        max_ = current_point.max
        min_ = current_point.min

        if aggregation_temporality is AggregationTemporality.CUMULATIVE:
            start_time_unix_nano = self._previous_point.start_time_unix_nano
            sum_ = current_point.sum + self._previous_point.sum
            # Only update min/max on delta -> cumulative
            max_ = max(current_point.max, self._previous_point.max)
            min_ = min(current_point.min, self._previous_point.min)
            bucket_counts = [
                curr_count + prev_count
                for curr_count, prev_count in zip(
                    current_point.bucket_counts,
                    self._previous_point.bucket_counts,
                )
            ]
        else:
            start_time_unix_nano = self._previous_point.time_unix_nano
            sum_ = current_point.sum - self._previous_point.sum
            bucket_counts = [
                curr_count - prev_count
                for curr_count, prev_count in zip(
                    current_point.bucket_counts,
                    self._previous_point.bucket_counts,
                )
            ]

        current_point = HistogramDataPoint(
            attributes=self._attributes,
            start_time_unix_nano=start_time_unix_nano,
            time_unix_nano=current_point.time_unix_nano,
            count=sum(bucket_counts),
            sum=sum_,
            bucket_counts=tuple(bucket_counts),
            explicit_bounds=current_point.explicit_bounds,
            min=min_,
            max=max_,
        )
        self._previous_point = current_point
        return current_point


class Aggregation(ABC):
    """
    Base class for all aggregation types.
    """

    @abstractmethod
    def _create_aggregation(
        self,
        instrument: Instrument,
        attributes: Attributes,
        start_time_unix_nano: int,
    ) -> _Aggregation:
        """Creates an aggregation"""


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
        instrument: Instrument,
        attributes: Attributes,
        start_time_unix_nano: int,
    ) -> _Aggregation:

        # pylint: disable=too-many-return-statements
        if isinstance(instrument, Counter):
            return _SumAggregation(
                attributes,
                instrument_is_monotonic=True,
                instrument_temporality=AggregationTemporality.DELTA,
                start_time_unix_nano=start_time_unix_nano,
            )
        if isinstance(instrument, UpDownCounter):
            return _SumAggregation(
                attributes,
                instrument_is_monotonic=False,
                instrument_temporality=AggregationTemporality.DELTA,
                start_time_unix_nano=start_time_unix_nano,
            )

        if isinstance(instrument, ObservableCounter):
            return _SumAggregation(
                attributes,
                instrument_is_monotonic=True,
                instrument_temporality=AggregationTemporality.CUMULATIVE,
                start_time_unix_nano=start_time_unix_nano,
            )

        if isinstance(instrument, ObservableUpDownCounter):
            return _SumAggregation(
                attributes,
                instrument_is_monotonic=False,
                instrument_temporality=AggregationTemporality.CUMULATIVE,
                start_time_unix_nano=start_time_unix_nano,
            )

        if isinstance(instrument, Histogram):
            return _ExplicitBucketHistogramAggregation(
                attributes, start_time_unix_nano
            )

        if isinstance(instrument, ObservableGauge):
            return _LastValueAggregation(attributes)

        raise Exception(f"Invalid instrument type {type(instrument)} found")


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
            750.0,
            1000.0,
            2500.0,
            5000.0,
            7500.0,
            10000.0,
        ),
        record_min_max: bool = True,
    ) -> None:
        self._boundaries = boundaries
        self._record_min_max = record_min_max

    def _create_aggregation(
        self,
        instrument: Instrument,
        attributes: Attributes,
        start_time_unix_nano: int,
    ) -> _Aggregation:
        return _ExplicitBucketHistogramAggregation(
            attributes,
            start_time_unix_nano,
            self._boundaries,
            self._record_min_max,
        )


class SumAggregation(Aggregation):
    """This aggregation informs the SDK to collect:

    - The arithmetic sum of Measurement values.
    """

    def _create_aggregation(
        self,
        instrument: Instrument,
        attributes: Attributes,
        start_time_unix_nano: int,
    ) -> _Aggregation:

        temporality = AggregationTemporality.UNSPECIFIED
        if isinstance(instrument, Synchronous):
            temporality = AggregationTemporality.DELTA
        elif isinstance(instrument, Asynchronous):
            temporality = AggregationTemporality.CUMULATIVE

        return _SumAggregation(
            attributes,
            isinstance(instrument, (Counter, ObservableCounter)),
            temporality,
            start_time_unix_nano,
        )


class LastValueAggregation(Aggregation):
    """
    This aggregation informs the SDK to collect:

    - The last Measurement.
    - The timestamp of the last Measurement.
    """

    def _create_aggregation(
        self,
        instrument: Instrument,
        attributes: Attributes,
        start_time_unix_nano: int,
    ) -> _Aggregation:
        return _LastValueAggregation(attributes)


class DropAggregation(Aggregation):
    """Using this aggregation will make all measurements be ignored."""

    def _create_aggregation(
        self,
        instrument: Instrument,
        attributes: Attributes,
        start_time_unix_nano: int,
    ) -> _Aggregation:
        return _DropAggregation(attributes)
