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

from logging import getLogger
from threading import Lock, RLock
from typing import Dict, Iterable, List

from opentelemetry._metrics import MeterProvider
from opentelemetry._metrics.instrument import Instrument, Synchronous
from opentelemetry.sdk._metrics._view_instrument_match import (
    _ViewInstrumentMatch,
)
from opentelemetry.sdk._metrics.export import (
    AGGREGATION_TEMPORALITY_CUMULATIVE,
    Metric,
)
from opentelemetry.sdk._metrics.measurement import Measurement

_logger = getLogger(__name__)


class MetricReader:
    def __init__(
        self, aggregation_temporality: int = AGGREGATION_TEMPORALITY_CUMULATIVE
    ) -> None:

        self._meter_provider = None
        self._rlock = RLock()
        self._lock = Lock()
        self._aggregation_temporality = aggregation_temporality
        self._instrument_view_instrument_matches: Dict[
            Instrument, List[_ViewInstrumentMatch]
        ] = {}

    def _register_meter_provider(self, meter_provider: MeterProvider):

        self._meter_provider = meter_provider

    def _process(
        self, instrument: Instrument, measurement: Measurement
    ) -> List[_ViewInstrumentMatch]:

        # pylint: disable=consider-iterating-dictionary
        if instrument in self._instrument_view_instrument_matches.keys():
            view_instrument_matches = self._instrument_view_instrument_matches[
                instrument
            ]

        else:

            with self._rlock:

                if instrument in (
                    # pylint: disable=consider-iterating-dictionary
                    self._instrument_view_instrument_matches.keys()
                ):
                    view_instrument_matches = (
                        self._instrument_view_instrument_matches[instrument]
                    )

                else:

                    view_instrument_matches = []

                    # pylint: disable=protected-access
                    for view in self._meter_provider._views:

                        if view._matches(instrument):
                            view_instrument_matches.append(
                                _ViewInstrumentMatch(
                                    view._name or instrument._name,
                                    view._unit or instrument._unit,
                                    (
                                        view._description
                                        or instrument._description
                                    ),
                                    view._attribute_keys or {},
                                    (
                                        view._extra_dimensions
                                        if isinstance(instrument, Synchronous)
                                        else None
                                    ),
                                    (
                                        view._aggregation
                                        or instrument._default_aggregation
                                    ),
                                    view._exemplar_reservoir,
                                    self._meter_provider._resource,
                                )
                            )

        self._instrument_view_instrument_matches[
            instrument
        ] = view_instrument_matches

        for view_instrument_match in view_instrument_matches:

            # pylint: disable=protected-access
            view_instrument_match._process(measurement)

    def collect(self) -> Iterable[Metric]:
        if self._meter_provider is None:
            _logger.warning(
                "Can't call collect on a MetricReader "
                "until it is registered on a MeterProvider"
            )

            return []

        # pylint: disable=protected-access
        for (
            asynchronous_instrument
        ) in self._meter_provider._asynchronous_instrument:
            for measurement in asynchronous_instrument.callback():
                self._process(asynchronous_instrument, measurement)

        metrics: List[Metric] = []

        for (
            view_instrument_matches
        ) in self._instrument_view_instrument_matches.values():
            for view_instrument_match in view_instrument_matches:
                with self._lock:
                    metrics.extend(
                        view_instrument_match.collect(
                            self._aggregation_temporality
                        )
                    )

        return metrics

    def shutdown(self) -> None:
        pass
