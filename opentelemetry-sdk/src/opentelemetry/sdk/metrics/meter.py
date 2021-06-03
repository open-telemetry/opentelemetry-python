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

from contextlib import contextmanager
from threading import Lock
from typing import Sequence

from opentelemetry.context import attach, detach, set_value
from opentelemetry.metrics.meter import Measurement, Meter, MeterProvider
from opentelemetry.sdk.metrics.export import Record
from opentelemetry.sdk.metrics.instrument import (
    Asynchronous,
    Counter,
    Histogram,
    Instrument,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.sdk.util import get_dict_as_key
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

    def create_counter(self, name, unit=None, description=None) -> Counter:
        return Counter(name, unit=unit, description=description)

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

    @contextmanager
    def get_records(self) -> Sequence[Record]:
        """Gets all the records created with this `Meter` for export.

        Creates checkpoints of the current values in
        each aggregator belonging to the metrics that were created with this
        meter instance.
        """
        # pylint: disable=too-many-branches
        try:
            with self._lock:
                for instrument in self._instruments:
                    if not instrument.enabled:
                        continue
                    if isinstance(instrument, Instrument):
                        to_remove = []
                        for (
                            labels,
                            bound_instrument,
                        ) in instrument.bound_instruments.items():
                            for view_data in bound_instrument.view_datas:
                                self._populate_batch_map(
                                    instrument,
                                    view_data.labels,
                                    view_data.aggregator,
                                )

                            if bound_instrument.ref_count() == 0:
                                to_remove.append(labels)

                        # Remove handles that were released
                        for labels in to_remove:
                            del instrument.bound_instruments[labels]
                    elif isinstance(instrument, Asynchronous):
                        if not instrument.run():
                            continue

                        for (
                            labels,
                            aggregator,
                        ) in instrument.aggregators.items():
                            self._populate_batch_map(
                                instrument, labels, aggregator
                            )

            token = attach(set_value("suppress_instrumentation", True))
            records = []
            # pylint: disable=W0612
            for (
                (instrument, aggregator_type, _, labels),
                aggregator,
            ) in self._batch_map.items():
                records.append(
                    Record(instrument, labels, aggregator, self._resource)
                )

            yield records

        finally:

            detach(token)

            if not self._stateful:
                self._batch_map = {}

    def _populate_batch_map(self, instrument, labels, aggregator) -> None:
        """Stores record information to be ready for exporting."""
        # Checkpoints the current aggregator value to be collected for export
        aggregator.take_checkpoint()

        # The uniqueness of a batch record is defined by a specific metric
        # using an aggregator type with a specific set of labels.
        # If two aggregators are the same but with different configs, they are still two valid unique records
        # (for example, two histogram views with different buckets)
        key = (
            instrument,
            aggregator.__class__,
            get_dict_as_key(aggregator.config),
            labels,
        )

        batch_value = self._batch_map.get(key)

        if batch_value:
            # Update the stored checkpointed value if exists. The call to merge
            # here combines only identical records (same key).
            batch_value.merge(aggregator)
            return

        # create a copy of the aggregator and update
        # it with the current checkpointed value for long-term storage
        aggregator = aggregator.__class__(config=aggregator.config)
        aggregator.merge(aggregator)

        self._batch_map[key] = aggregator


class MeterProvider(MeterProvider):
    def add_pipeline(self):
        pass

    def configure_views(self):
        pass

    def configure_timint(self):
        pass

    def get_meter(
        self,
        name,
        version=None,
        schema_url=None,
    ) -> Meter:
        return Meter()
