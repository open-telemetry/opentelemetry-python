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

# pylint: disable=too-many-ancestors

from abc import ABC, abstractmethod
from typing import Callable, Dict, Generator, Iterable, Union

from opentelemetry._metrics.instrument import Counter as APICounter
from opentelemetry._metrics.instrument import Histogram as APIHistogram
from opentelemetry._metrics.instrument import (
    ObservableCounter as APIObservableCounter,
)
from opentelemetry._metrics.instrument import (
    ObservableGauge as APIObservableGauge,
)
from opentelemetry._metrics.instrument import (
    ObservableUpDownCounter as APIObservableUpDownCounter,
)
from opentelemetry._metrics.instrument import UpDownCounter as APIUpDownCounter
from opentelemetry.sdk._metrics.aggregation import (
    ExplicitBucketHistogramAggregation,
    LastValueAggregation,
    SumAggregation,
)
from opentelemetry.sdk._metrics.measurement import Measurement
from opentelemetry.sdk.util.instrumentation import InstrumentationInfo

TCallback = Union[
    Callable[[], Iterable[Measurement]],
    Generator[Iterable[Measurement], None, None],
]


class _Instrument(ABC):
    @property
    @abstractmethod
    def _default_aggregation(self):
        pass


class _Synchronous(_Instrument):
    def __init__(
        self,
        instrumentation_info: InstrumentationInfo,
        name: str,
        unit: str = "",
        description: str = "",
    ):
        self._instrumentation_info = instrumentation_info
        super().__init__(name, unit=unit, description=description)


class _Asynchronous(_Instrument):
    def __init__(
        self,
        instrumentation_info: InstrumentationInfo,
        name: str,
        callback: TCallback,
        unit: str = "",
        description: str = "",
    ):

        self._instrumentation_info = instrumentation_info
        super().__init__(name, callback, unit=unit, description=description)

        self._callback = callback

        if isinstance(callback, Generator):

            def inner() -> Iterable[Measurement]:
                return next(callback)

            self._callback = inner

    @property
    def callback(self) -> TCallback:
        return self._callback


class Counter(_Synchronous, APICounter):
    @property
    def _default_aggregation(self):
        return SumAggregation

    def add(
        self, amount: Union[int, float], attributes: Dict[str, str] = None
    ):
        if amount < 0:
            raise Exception("amount must be non negative")


class UpDownCounter(_Synchronous, APIUpDownCounter):
    @property
    def _default_aggregation(self):
        return SumAggregation

    def add(
        self, amount: Union[int, float], attributes: Dict[str, str] = None
    ):
        pass


class ObservableCounter(_Asynchronous, APIObservableCounter):
    @property
    def _default_aggregation(self):
        return SumAggregation


class ObservableUpDownCounter(_Asynchronous, APIObservableUpDownCounter):
    @property
    def _default_aggregation(self):
        return SumAggregation


class Histogram(_Synchronous, APIHistogram):
    @property
    def _default_aggregation(self):
        return ExplicitBucketHistogramAggregation

    def record(self, amount, attributes=None):
        pass


class ObservableGauge(_Asynchronous, APIObservableGauge):
    @property
    def _default_aggregation(self):
        return LastValueAggregation
