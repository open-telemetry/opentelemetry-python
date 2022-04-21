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
from threading import Lock
from typing import TYPE_CHECKING, Dict, Iterable

from opentelemetry.sdk._metrics.aggregation import (
    _Aggregation,
    _convert_aggregation_temporality,
    _PointVarT,
)
from opentelemetry.sdk._metrics.measurement import Measurement
from opentelemetry.sdk._metrics.point import AggregationTemporality, Metric
from opentelemetry.sdk._metrics.sdk_configuration import SdkConfiguration
from opentelemetry.sdk._metrics.view import View

if TYPE_CHECKING:
    from opentelemetry.sdk._metrics.instrument import _Instrument

_logger = getLogger(__name__)


class _ViewInstrumentMatch:
    def __init__(
        self,
        view: View,
        instrument: "_Instrument",
        sdk_config: SdkConfiguration,
    ):
        self._view = view
        self._instrument = instrument
        self._sdk_config = sdk_config
        self._attributes_aggregation: Dict[frozenset, _Aggregation] = {}
        self._attributes_previous_point: Dict[frozenset, _PointVarT] = {}
        self._lock = Lock()

    # pylint: disable=protected-access
    def consume_measurement(self, measurement: Measurement) -> None:

        if self._view._attribute_keys is not None:

            attributes = {}

            for key, value in (measurement.attributes or {}).items():
                if key in self._view._attribute_keys:
                    attributes[key] = value
        elif measurement.attributes is not None:
            attributes = measurement.attributes
        else:
            attributes = {}

        attributes = frozenset(attributes.items())

        if attributes not in self._attributes_aggregation:
            with self._lock:
                if attributes not in self._attributes_aggregation:
                    self._attributes_aggregation[
                        attributes
                    ] = self._view._aggregation._create_aggregation(
                        self._instrument
                    )

        self._attributes_aggregation[attributes].aggregate(measurement)

    def collect(self, temporality: int) -> Iterable[Metric]:

        with self._lock:
            for (
                attributes,
                aggregation,
            ) in self._attributes_aggregation.items():

                previous_point = self._attributes_previous_point.get(
                    attributes
                )

                current_point = aggregation.collect()

                # pylint: disable=assignment-from-none
                self._attributes_previous_point[
                    attributes
                ] = _convert_aggregation_temporality(
                    previous_point,
                    current_point,
                    AggregationTemporality.CUMULATIVE,
                )

                if current_point is not None:

                    yield Metric(
                        attributes=dict(attributes),
                        description=(
                            self._view._description
                            or self._instrument.description
                        ),
                        instrumentation_scope=self._instrument.instrumentation_scope,
                        name=self._view._name or self._instrument.name,
                        resource=self._sdk_config.resource,
                        unit=self._instrument.unit,
                        point=_convert_aggregation_temporality(
                            previous_point,
                            current_point,
                            temporality,
                        ),
                    )
