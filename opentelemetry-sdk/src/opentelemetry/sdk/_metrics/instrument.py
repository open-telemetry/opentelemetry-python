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

# pylint: disable=function-redefined
# pylint: disable=dangerous-default-value
# Classes in this module use dictionaries as default arguments. This is
# considered dangerous by pylint because the default dictionary is shared by
# all instances. Implementations of these classes must not make any change to
# this default dictionary in __init__.

from opentelemetry._metrics.instrument import (
    Counter,
    Histogram,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.sdk._metrics.aggregation import (
    ExplicitBucketHistogramAggregation,
    LastValueAggregation,
    SumAggregation,
)


class _Instrument:
    def __init__(
        self,
        name,
        unit="",
        description="",
        aggregation=None,
        aggregation_config={},
    ):
        self._attributes_aggregations = {}
        self._aggregation = aggregation
        self._aggregation_config = aggregation_config
        aggregation(**aggregation_config)


class _Synchronous(_Instrument):

    def add(self, amount, attributes=None):

        if attributes is None:
            raise Exception("Missing attributes")

        attributes = frozenset(attributes.items())
        if attributes not in self._attributes_aggregations.keys():

            self._attributes_aggregations[attributes] = (
                self._aggregation(**self._aggregation_config)
            )
        self._attributes_aggregations[attributes].aggregate(amount)


class Counter(_Synchronous, Counter):
    def __init__(
        self,
        name,
        unit="",
        description="",
        aggregation=SumAggregation,
        aggregation_config={},
    ):
        super().__init__(
            name,
            unit=unit,
            description=description,
            aggregation=aggregation,
            aggregation_config=aggregation_config
        )


class UpDownCounter(_Synchronous, UpDownCounter):
    def __init__(
        self,
        name,
        unit="",
        description="",
        aggregation=SumAggregation,
        aggregation_config={},
    ):
        super().__init__(
            name,
            unit=unit,
            description=description,
            aggregation=aggregation,
            aggregation_config=aggregation_config
        )


class ObservableCounter(_Instrument, ObservableCounter):
    def __init__(
        self,
        name,
        callback,
        unit="",
        description="",
        aggregation=SumAggregation,
        aggregation_config={},
    ):
        super().__init__(
            name,
            unit=unit,
            description=description,
            aggregation=aggregation,
            aggregation_config=aggregation_config
        )


class ObservableUpDownCounter(_Instrument, ObservableUpDownCounter):
    def __init__(
        self,
        name,
        callback,
        unit="",
        description="",
        aggregation=SumAggregation,
        aggregation_config={},
    ):
        super().__init__(
            name,
            unit=unit,
            description=description,
            aggregation=aggregation,
            aggregation_config=aggregation_config
        )


class Histogram(_Synchronous, Histogram):
    def __init__(
        self,
        name,
        unit="",
        description="",
        aggregation=ExplicitBucketHistogramAggregation,
        aggregation_config={},
    ):
        super().__init__(
            name,
            unit=unit,
            description=description,
            aggregation=aggregation,
            aggregation_config=aggregation_config
        )


class ObservableGauge(_Instrument, ObservableGauge):
    def __init__(
        self,
        name,
        callback,
        unit="",
        description="",
        aggregation=LastValueAggregation,
        aggregation_config={},
    ):
        super().__init__(
            name,
            unit=unit,
            description=description,
            aggregation=aggregation,
            aggregation_config=aggregation_config
        )
