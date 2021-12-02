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


from collections.abc import Callable, Generator
from typing import Iterable, Union

from opentelemetry._metrics.instrument import Asynchronous
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
from opentelemetry._metrics.instrument import Synchronous
from opentelemetry._metrics.instrument import UpDownCounter as APIUpDownCounter
from opentelemetry.sdk._metrics.aggregation import (
    ExplicitBucketHistogramAggregation,
    LastValueAggregation,
    SynchronousSumAggregation,
)
from opentelemetry.sdk._metrics.measurement import Measurement


class _Synchronous(Synchronous):
    def __init__(
        self,
        meter_provider,
        name,
        unit="",
        description="",
    ):

        self._meter_provider = meter_provider

        super().__init__(name, unit=unit, description=description)


class _Asynchronous(Asynchronous):
    def __init__(
        self,
        meter_provider,
        name,
        callback: Union[Callable, Generator],
        unit="",
        description="",
    ):
        self._meter_provider = meter_provider

        super().__init__(name, callback, unit=unit, description=description)

        self._callback = callback

        if isinstance(callback, Generator):

            def inner() -> Iterable[Measurement]:
                return next(callback)

            self._callback = inner

    @property
    def callback(self) -> Union[Callable, Generator]:
        return self._callback


class Counter(_Synchronous, APICounter):

    _default_aggregation = SynchronousSumAggregation

    def add(self, amount, attributes=None):
        if amount < 0:
            raise Exception("amount must be non negative")

        # pylint: disable=protected-access
        self._meter_provider._measurement_processor.process(
            self, Measurement(amount, attributes=attributes)
        )


class UpDownCounter(_Synchronous, APIUpDownCounter):

    _default_aggregation = SynchronousSumAggregation

    def add(self, amount, attributes=None):
        # pylint: disable=protected-access
        self._meter_provider._measurement_processor.process(
            self, Measurement(amount, attributes=attributes)
        )


class ObservableCounter(_Asynchronous, APIObservableCounter):

    _default_aggregation = SynchronousSumAggregation


class ObservableUpDownCounter(_Asynchronous, APIObservableUpDownCounter):

    _default_aggregation = SynchronousSumAggregation


class Histogram(_Synchronous, APIHistogram):

    _default_aggregation = ExplicitBucketHistogramAggregation

    def record(self, amount, attributes=None):
        # pylint: disable=protected-access
        self._meter_provider._measurement_processor.process(
            self, Measurement(amount, attributes=attributes)
        )


class ObservableGauge(_Asynchronous, APIObservableGauge):

    _default_aggregation = LastValueAggregation
