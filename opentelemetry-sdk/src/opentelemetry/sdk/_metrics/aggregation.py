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
from dataclasses import replace
from logging import getLogger
from math import inf
from threading import Lock
from typing import Generic, List, Optional, Sequence, TypeVar

from opentelemetry.sdk._metrics.measurement import Measurement
from opentelemetry.sdk._metrics.point import (
    AggregationTemporality,
    Gauge,
    Histogram,
    PointT,
    Sum,
)
from opentelemetry.util._time import _time_ns

_PointVarT = TypeVar("_PointVarT", bound=PointT)

_logger = getLogger(__name__)


class _InstrumentMonotonicityAwareAggregation:
    def __init__(self, instrument_is_monotonic: bool):
        self._instrument_is_monotonic = instrument_is_monotonic
        super().__init__()


class Aggregation(ABC, Generic[_PointVarT]):
    def __init__(self):
        self._lock = Lock()

    @abstractmethod
    def aggregate(self, measurement: Measurement) -> None:
        pass

    @abstractmethod
    def collect(self) -> Optional[_PointVarT]:
        pass


class SynchronousSumAggregation(
    _InstrumentMonotonicityAwareAggregation, Aggregation[Sum]
):
    def __init__(self, instrument_is_monotonic: bool):
        super().__init__(instrument_is_monotonic)
        self._value = 0
        self._start_time_unix_nano = _time_ns()

    def aggregate(self, measurement: Measurement) -> None:
        with self._lock:
            self._value = self._value + measurement.value

    def collect(self) -> Optional[Sum]:
        """
        Atomically return a point for the current value of the metric and
        reset the aggregation value.
        """
        now = _time_ns()

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


class AsynchronousSumAggregation(
    _InstrumentMonotonicityAwareAggregation, Aggregation[Sum]
):
    def __init__(self, instrument_is_monotonic: bool):
        super().__init__(instrument_is_monotonic)
        self._value = None
        self._start_time_unix_nano = _time_ns()

    def aggregate(self, measurement: Measurement) -> None:
        with self._lock:
            self._value = measurement.value

    def collect(self) -> Optional[Sum]:
        """
        Atomically return a point for the current value of the metric.
        """
        if self._value is None:
            return None

        return Sum(
            start_time_unix_nano=self._start_time_unix_nano,
            time_unix_nano=_time_ns(),
            value=self._value,
            aggregation_temporality=AggregationTemporality.CUMULATIVE,
            is_monotonic=self._instrument_is_monotonic,
        )


class LastValueAggregation(Aggregation[Gauge]):
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
        if self._value is None:
            return None

        return Gauge(
            time_unix_nano=_time_ns(),
            value=self._value,
        )


class ExplicitBucketHistogramAggregation(Aggregation[Histogram]):
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

    def collect(self) -> Optional[Histogram]:
        """
        Atomically return a point for the current value of the metric.
        """
        now = _time_ns()

        with self._lock:
            value = self._bucket_counts
            start_time_unix_nano = self._start_time_unix_nano

            self._bucket_counts = self._get_empty_bucket_counts()
            self._start_time_unix_nano = now + 1

        return Histogram(
            start_time_unix_nano=start_time_unix_nano,
            time_unix_nano=now,
            bucket_counts=tuple(value),
            explicit_bounds=self._boundaries,
            aggregation_temporality=AggregationTemporality.DELTA,
            sum=self._sum,
        )


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

    if previous_point is not None and type(previous_point) is not type(
        current_point
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

    return None
