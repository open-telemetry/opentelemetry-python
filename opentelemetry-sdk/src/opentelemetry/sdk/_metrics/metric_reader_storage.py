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

from threading import RLock
from typing import Dict, Iterable, List

from opentelemetry._metrics.instrument import Instrument
from opentelemetry.sdk._metrics._view_instrument_match import (
    _ViewInstrumentMatch,
)
from opentelemetry.sdk._metrics.aggregation import AggregationTemporality
from opentelemetry.sdk._metrics.measurement import Measurement
from opentelemetry.sdk._metrics.point import Metric
from opentelemetry.sdk._metrics.sdk_configuration import SdkConfiguration
from opentelemetry.sdk._metrics.view import View

_DEFAULT_VIEW = View(instrument_name="")


class MetricReaderStorage:
    """The SDK's storage for a given reader"""

    def __init__(self, sdk_config: SdkConfiguration) -> None:
        self._lock = RLock()
        self._sdk_config = sdk_config
        self._view_instrument_match: Dict[
            Instrument, List[_ViewInstrumentMatch]
        ] = {}

    def _get_or_init_view_instrument_match(
        self, instrument: Instrument
    ) -> List["_ViewInstrumentMatch"]:
        # Optimistically get the relevant views for the given instrument. Once set for a given
        # instrument, the mapping will never change

        if instrument in self._view_instrument_match:
            return self._view_instrument_match[instrument]

        with self._lock:
            # double check if it was set before we held the lock
            if instrument in self._view_instrument_match:
                return self._view_instrument_match[instrument]

            # not present, hold the lock and add a new mapping
            view_instrument_matches = []
            for view in self._sdk_config.views:
                # pylint: disable=protected-access
                if view._match(instrument):
                    view_instrument_matches.append(
                        _ViewInstrumentMatch(
                            view=view,
                            instrument=instrument,
                            sdk_config=self._sdk_config,
                        )
                    )

            # if no view targeted the instrument, use the default
            if not view_instrument_matches:
                view_instrument_matches.append(
                    _ViewInstrumentMatch(
                        view=_DEFAULT_VIEW,
                        instrument=instrument,
                        sdk_config=self._sdk_config,
                    )
                )
            self._view_instrument_match[instrument] = view_instrument_matches
            return view_instrument_matches

    def consume_measurement(self, measurement: Measurement) -> None:
        for view_instrument_match in self._get_or_init_view_instrument_match(
            measurement.instrument
        ):
            view_instrument_match.consume_measurement(measurement)

    def collect(self, temporality: AggregationTemporality) -> Iterable[Metric]:
        # use a list instead of yielding to prevent a slow reader from holding SDK locks
        metrics: List[Metric] = []

        # While holding the lock, new _ViewInstrumentMatch can't be added from another thread (so we are
        # sure we collect all existing view). However, instruments can still send measurements
        # that will make it into the individual aggregations; collection will acquire those
        # locks iteratively to keep locking as fine-grained as possible. One side effect is
        # that end times can be slightly skewed among the metric streams produced by the SDK,
        # but we still align the output timestamps for a single instrument.
        with self._lock:
            for (
                view_instrument_matches
            ) in self._view_instrument_match.values():
                for view_instrument_match in view_instrument_matches:
                    metrics.extend(view_instrument_match.collect(temporality))

        return metrics
