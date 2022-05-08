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
from threading import RLock
from typing import Dict, Iterable, List

from opentelemetry._metrics import Asynchronous, Instrument
from opentelemetry.sdk._metrics._internal._view_instrument_match import (
    _ViewInstrumentMatch,
)
from opentelemetry.sdk._metrics._internal.aggregation import (
    Aggregation,
    ExplicitBucketHistogramAggregation,
)
from opentelemetry.sdk._metrics._internal.export import AggregationTemporality
from opentelemetry.sdk._metrics._internal.measurement import Measurement
from opentelemetry.sdk._metrics._internal.point import Metric
from opentelemetry.sdk._metrics._internal.sdk_configuration import (
    SdkConfiguration,
)
from opentelemetry.sdk._metrics._internal.view import View

_logger = getLogger(__name__)

_DEFAULT_VIEW = View(instrument_name="")


class MetricReaderStorage:
    """The SDK's storage for a given reader"""

    def __init__(
        self,
        sdk_config: SdkConfiguration,
        instrument_class_aggregation: Dict[type, Aggregation],
    ) -> None:
        self._lock = RLock()
        self._sdk_config = sdk_config
        self._instrument_view_instrument_matches: Dict[
            Instrument, List[_ViewInstrumentMatch]
        ] = {}
        self._instrument_class_aggregation = instrument_class_aggregation

    def _get_or_init_view_instrument_match(
        self, instrument: Instrument
    ) -> List[_ViewInstrumentMatch]:
        # Optimistically get the relevant views for the given instrument. Once set for a given
        # instrument, the mapping will never change

        if instrument in self._instrument_view_instrument_matches:
            return self._instrument_view_instrument_matches[instrument]

        with self._lock:
            # double check if it was set before we held the lock
            if instrument in self._instrument_view_instrument_matches:
                return self._instrument_view_instrument_matches[instrument]

            # not present, hold the lock and add a new mapping
            view_instrument_matches = []

            self._handle_view_instrument_match(
                instrument, view_instrument_matches
            )

            # if no view targeted the instrument, use the default
            if not view_instrument_matches:
                view_instrument_matches.append(
                    _ViewInstrumentMatch(
                        view=_DEFAULT_VIEW,
                        instrument=instrument,
                        sdk_config=self._sdk_config,
                        instrument_class_aggregation=(
                            self._instrument_class_aggregation
                        ),
                    )
                )
            self._instrument_view_instrument_matches[
                instrument
            ] = view_instrument_matches

            return view_instrument_matches

    def consume_measurement(self, measurement: Measurement) -> None:
        for view_instrument_match in self._get_or_init_view_instrument_match(
            measurement.instrument
        ):
            view_instrument_match.consume_measurement(measurement)

    def collect(
        self, instrument_type_temporality: Dict[type, AggregationTemporality]
    ) -> Iterable[Metric]:
        # Use a list instead of yielding to prevent a slow reader from holding
        # SDK locks
        metrics: List[Metric] = []

        # While holding the lock, new _ViewInstrumentMatch can't be added from
        # another thread (so we are sure we collect all existing view).
        # However, instruments can still send measurements that will make it
        # into the individual aggregations; collection will acquire those locks
        # iteratively to keep locking as fine-grained as possible. One side
        # effect is that end times can be slightly skewed among the metric
        # streams produced by the SDK, but we still align the output timestamps
        # for a single instrument.
        with self._lock:
            for (
                view_instrument_matches
            ) in self._instrument_view_instrument_matches.values():
                for view_instrument_match in view_instrument_matches:
                    metrics.extend(
                        view_instrument_match.collect(
                            instrument_type_temporality
                        )
                    )

        return metrics

    def _handle_view_instrument_match(
        self,
        instrument: Instrument,
        view_instrument_matches: List["_ViewInstrumentMatch"],
    ) -> None:
        for view in self._sdk_config.views:
            # pylint: disable=protected-access
            if not view._match(instrument):
                continue

            if not self._check_view_instrument_compatibility(view, instrument):
                continue

            new_view_instrument_match = _ViewInstrumentMatch(
                view=view,
                instrument=instrument,
                sdk_config=self._sdk_config,
                instrument_class_aggregation=(
                    self._instrument_class_aggregation
                ),
            )

            for (
                existing_view_instrument_matches
            ) in self._instrument_view_instrument_matches.values():
                for (
                    existing_view_instrument_match
                ) in existing_view_instrument_matches:
                    if existing_view_instrument_match.conflicts(
                        new_view_instrument_match
                    ):

                        _logger.warning(
                            "Views %s and %s will cause conflicting "
                            "metrics identities",
                            existing_view_instrument_match._view,
                            new_view_instrument_match._view,
                        )

            view_instrument_matches.append(new_view_instrument_match)

    @staticmethod
    def _check_view_instrument_compatibility(
        view: View, instrument: Instrument
    ) -> bool:
        """
        Checks if a view and an instrument are compatible.

        Returns `true` if they are compatible and a `_ViewInstrumentMatch`
        object should be created, `false` otherwise.
        """

        result = True

        # pylint: disable=protected-access
        if isinstance(instrument, Asynchronous) and isinstance(
            view._aggregation, ExplicitBucketHistogramAggregation
        ):
            _logger.warning(
                "View %s and instrument %s will produce "
                "semantic errors when matched, the view "
                "has not been applied.",
                view,
                instrument,
            )
            result = False

        return result
