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
        )
