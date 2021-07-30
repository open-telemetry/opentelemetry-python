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

# pylint: disable=function-redefined,too-many-ancestors

from typing import Generator

from opentelemetry.sdk.metrics.aggregator import (
    Aggregator,
    SumAggregator,
    LastAggregator,
    MinMaxSumCountAggregator,
    MinMaxSumCountLastAggregator,
)
from opentelemetry.metrics.instrument import (
    Adding,
    Asynchronous,
    Counter,
    Grouping,
    Histogram,
    Instrument,
    Monotonic,
    NonMonotonic,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    Synchronous,
    UpDownCounter,
)


class _Instrument(Instrument):
    def __init__(
        self,
        name,
        unit=None,
        description=None,
        aggregator_class=Aggregator,
        *args,
        **kwargs
    ):

        super().__init__(
            name,
            unit=unit,
            description=description,
            *args,
            **kwargs
        )

        self._aggregator = aggregator_class()
        self._name = name
        self._unit = unit
        self._description = description

    @property
    def aggregator_class(self):
        return self._aggregator_class

    @property
    def name(self):
        return self._name

    @property
    def unit(self):
        return self._unit

    @property
    def description(self):
        return self._description


class _Synchronous(Synchronous, _Instrument):
    def __init__(
        self,
        name,
        unit=None,
        description=None,
        aggregator_class=SumAggregator,
        *args,
        **kwargs
    ):
        self._attributes_aggregators = {}
        super().__init__(
            name,
            unit=unit,
            description=description,
            aggregator_class=aggregator_class,
            *args,
            **kwargs
        )

    def add(self, value, **attributes):

        super().add(value, **attributes)

        attributes = frozenset(attributes.items())
        if attributes not in self._attributes_aggregators.keys():

            self._attributes_aggregators[attributes] = self._aggregator_class()
        self._attributes_aggregators[attributes].aggregate(value)


class _Asynchronous(Asynchronous, _Instrument):
    def __init__(
        self,
        name,
        callback: Generator,
        unit=None,
        description=None,
        aggregator_class=LastAggregator,
        *args,
        **kwargs
    ):
        super().__init__(
            name,
            callback,
            unit=unit,
            description=description,
            aggregator_class=aggregator_class,
            *args,
            **kwargs
        )

        self._callback = callback

    def observe(self):
        # FIXME make this limited by a timeout
        value, attributes = super().observe()
        self._aggregator.aggregate(value)


class _Adding(Adding, _Instrument):
    pass


class _Grouping(Grouping, _Instrument):
    pass


class _Monotonic(Monotonic, _Adding):
    pass


class _NonMonotonic(NonMonotonic, _Adding):
    pass


class Counter(Counter, _Monotonic, _Synchronous):
    def add(self, value, **attributes):
        super().add(value, **attributes)


class UpDownCounter(UpDownCounter, _NonMonotonic, _Synchronous):
    def add(self, value, **attributes):
        super().add(value, **attributes)


class ObservableCounter(ObservableCounter, _Monotonic, _Asynchronous):
    pass


class ObservableUpDownCounter(
    ObservableUpDownCounter, _NonMonotonic, _Asynchronous
):
    pass


class Histogram(Histogram, _Grouping, _Synchronous):
    def __init__(
        self,
        name,
        unit=None,
        description=None,
        aggregator_class=MinMaxSumCountAggregator,
        *args,
        **kwargs
    ):
        super().__init__(
            name,
            unit=unit,
            description=description,
            aggregator_class=aggregator_class,
            *args,
            **kwargs
        )

    def record(self, value, **attributes):
        super().add(value, **attributes)


class ObservableGauge(ObservableGauge, _Grouping, _Asynchronous):
    def __init__(
        self,
        name,
        callback,
        unit=None,
        description=None,
        aggregator_class=MinMaxSumCountLastAggregator,
        *args,
        **kwargs
    ):
        super().__init__(
            name,
            callback,
            unit=unit,
            description=description,
            aggregator_class=aggregator_class,
            *args,
            **kwargs
        )
