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


class _Instrument:
    def __init__(self, name, unit="", description=""):

        super().__init__(name, unit=unit, description=description)

        self._view_instruments = []

    def _instrument(self, amount, attributes):

        for view_instrument in self._view_instruments:

            view_instrument.instrument(amount, attributes)


class _ViewInstrument:
    def __init__(
        self,
        name,
        unit,
        description,
        attribute_keys,
        extra_dimensions,
        aggregation,
        exemplar_reservoir,
    ):

        self._name = name
        self._unit = unit
        self._description = description
        if attribute_keys is None:
            self._attribute_keys = set()
        else:
            self._attribute_keys = set(attribute_keys)
        if extra_dimensions is not None:
            self._extra_dimensions = extra_dimensions
        self._aggregation = aggregation
        self._exemplar_reservoir = exemplar_reservoir

        self._attributes_aggregation = {}

    def instrument(self, amount, attributes):

        attributes = frozenset(
            set(attributes).difference(self._attribute_keys)
        )

        if attributes not in self._attributes_aggregation.keys():
            self._attributes_aggregation[attributes] = self._aggregation()

        self._attributes_aggregation[attributes].aggregate(amount)


class Counter(_Instrument, APICounter):

    _default_aggregation = SumAggregation

    def add(self, amount, attributes={}):
        if amount < 0:
            raise Exception("amount must be positive")

        self._instrument(amount, attributes)


class UpDownCounter(_Instrument, APIUpDownCounter):

    _default_aggregation = SumAggregation

    def add(self, amount, attributes={}):
        self._instrument(amount, attributes)


class ObservableCounter(_Instrument, APIObservableCounter):

    _default_aggregation = SumAggregation


class ObservableUpDownCounter(_Instrument, APIObservableUpDownCounter):

    _default_aggregation = SumAggregation


class Histogram(_Instrument, APIHistogram):

    _default_aggregation = ExplicitBucketHistogramAggregation

    def record(self, amount, attributes={}):
        self._instrument(amount, attributes)


class ObservableGauge(_Instrument, APIObservableGauge):

    _default_aggregation = LastValueAggregation
