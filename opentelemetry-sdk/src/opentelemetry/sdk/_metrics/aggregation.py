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
from collections import OrderedDict
from enum import IntEnum
from logging import getLogger
from math import inf
from threading import Lock
from typing import Generic, Optional, Sequence, TypeVar

from opentelemetry.sdk._metrics.measurement import Measurement
from opentelemetry.sdk._metrics.point import Gauge, Histogram, PointT, Sum
from opentelemetry.util._time import _time_ns


class AggregationTemporality(IntEnum):
    UNSPECIFIED = 0
    DELTA = 1
    CUMULATIVE = 2


_PointVarT = TypeVar("_PointVarT", bound=PointT)

_logger = getLogger(__name__)


class _MonotonicitySensitiveAggregation:
    def __init__(self, is_monotonic: bool):
        self._is_monotonic = is_monotonic
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
    _MonotonicitySensitiveAggregation, Aggregation[Sum]
):
    def __init__(self, is_monotonic: bool):
        super().__init__(is_monotonic)
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
            self._value = 0
            self._start_time_unix_nano = now + 1

        return Sum(
            aggregation_temporality=(AggregationTemporality.DELTA),
            is_monotonic=self._is_monotonic,
            start_time_unix_nano=self._start_time_unix_nano,
            time_unix_nano=now,
            value=self._value,
        )


class AsynchronousSumAggregation(
    _MonotonicitySensitiveAggregation, Aggregation[Sum]
):
    def __init__(self, is_monotonic: bool):
        super().__init__(is_monotonic)
        self._value = 0
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
            aggregation_temporality=(AggregationTemporality.CUMULATIVE),
            is_monotonic=self._is_monotonic,
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


class ExplicitBucketHistogramAggregation(
    _MonotonicitySensitiveAggregation, Aggregation[Histogram]
):
    def __init__(
        self,
        is_monotonic: bool,
        boundaries: Sequence[int] = (
            0,
            5,
            10,
            25,
            50,
            75,
            100,
            250,
            500,
            1000,
        ),
        record_min_max: bool = True,
    ):
        super().__init__(is_monotonic)
        self._value = OrderedDict([(key, 0) for key in (*boundaries, inf)])
        self._min = inf
        self._max = -inf
        self._sum = 0
        self._record_min_max = record_min_max
        self._start_time_unix_nano = _time_ns()
        self._boundaries = boundaries

    def aggregate(self, measurement: Measurement) -> None:

        value = measurement.value

        if self._record_min_max:
            self._min = min(self._min, value)
            self._max = max(self._max, value)

        if self._is_monotonic:
            self._sum += value

        for key in self._value.keys():

            if value < key:
                self._value[key] = self._value[key] + 1

                break

    def collect(self) -> Optional[Histogram]:
        """
        Atomically return a point for the current value of the metric.
        """
        now = _time_ns()

        with self._lock:
            self._value = OrderedDict(
                [(key, 0) for key in (*self._boundaries, inf)]
            )
            self._start_time_unix_nano = now + 1

        return Histogram(
            start_time_unix_nano=self._start_time_unix_nano,
            time_unix_nano=now,
            bucket_counts=tuple(self._value.values()),
            explicit_bounds=self._boundaries,
            aggregation_temporality=(AggregationTemporality.DELTA),
        )
