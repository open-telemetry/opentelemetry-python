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

from threading import Lock

from opentelemetry.metrics.meter import Measurement, Meter, MeterProvider
from opentelemetry.sdk.metrics.instrument import (
    Counter,
    Histogram,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.util.types import Attributes


class Measurement(Measurement):
    def __init__(self, value, **attributes: Attributes):
        self._value = value
        self._attributes = attributes
        super().__init__(value, **attributes)

    @property
    def value(self):
        return self._value

    @property
    def attributes(self):
        return self._attributes


class Meter(Meter):

    # pylint: disable=no-self-use
    def __init__(self):

        self._batch_map = {}
        self._lock = Lock()
        self._instruments = []
        self._views = []
        self._stateful = False

    # FIXME find a better name for this function
    def get_records(self):

        records = []

        for instrument in self._instruments:

            records.append(
                {
                    attributes: aggregator.value
                    for attributes, aggregator in
                    instrument._attributes_aggregators.items()
                }
            )

            instrument._attributes_aggregators.clear()

        return records

    def create_counter(self, name, unit=None, description=None) -> Counter:

        counter = Counter(name, unit=unit, description=description)
        self._instruments.append(counter)

        return counter

    def create_up_down_counter(
        self, name, unit=None, description=None
    ) -> UpDownCounter:
        return UpDownCounter(name, unit=unit, description=description)

    def create_observable_counter(
        self, name, callback, unit=None, description=None
    ) -> ObservableCounter:
        return ObservableCounter(
            name, callback, unit=unit, description=description
        )

    def create_histogram(self, name, unit=None, description=None) -> Histogram:
        return Histogram(name, unit=unit, description=description)

    def create_observable_gauge(
        self, name, callback, unit=None, description=None
    ) -> ObservableGauge:
        return ObservableGauge(
            name, callback, unit=unit, description=description
        )

    def create_observable_up_down_counter(
        self, name, callback, unit=None, description=None
    ) -> ObservableUpDownCounter:
        return ObservableUpDownCounter(
            name, callback, unit=unit, description=description
        )


class MeterProvider(MeterProvider):

    def get_meter(
        self,
        name,
        version=None,
        schema_url=None,
    ) -> Meter:
        return Meter()

    def register_view(
        self,
        name=None,
        instrument_type=None,
        instrument_name=None,
        meter_name=None,
        meter_version=None,
        meter_schema_url=None,
        metrics_stream_description=None,
        metrics_stream_attribute_keys=None,
        metrics_stream_extra_dimensions=None,
        metrics_stream_aggregation=None
    ):
        pass
