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
from typing import Iterable, Set

from opentelemetry.sdk._metrics.aggregation import (
    _Aggregation,
    _convert_aggregation_temporality,
)
from opentelemetry.sdk._metrics.measurement import Measurement
from opentelemetry.sdk._metrics.point import AggregationTemporality, Metric
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationInfo

_logger = getLogger(__name__)


class _ViewInstrumentMatch:
    def __init__(
        self,
        name: str,
        unit: str,
        description: str,
        aggregation: _Aggregation,
        instrumentation_info: InstrumentationInfo,
        resource: Resource,
        attribute_keys: Set[str],
    ):
        self._name = name
        self._unit = unit
        self._description = description
        self._aggregation = aggregation
        self._instrumentation_info = instrumentation_info
        self._resource = resource
        self._attribute_keys = attribute_keys
        self._attributes_aggregation = {}
        self._attributes_previous_point = {}
        self._lock = Lock()

    def consume_measurement(self, measurement: Measurement) -> None:

        if self._attribute_keys:

            attributes = {}

            for key, value in measurement.attributes.items():
                if key in self._attribute_keys:
                    attributes[key] = value
        elif measurement.attributes is not None:
            attributes = measurement.attributes
        else:
            attributes = {}

        attributes = frozenset(attributes.items())

        if attributes not in self._attributes_aggregation.keys():
            with self._lock:
                self._attributes_aggregation[attributes] = self._aggregation

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
                        description=self._description,
                        instrumentation_info=self._instrumentation_info,
                        name=self._name,
                        resource=self._resource,
                        unit=self._unit,
                        point=_convert_aggregation_temporality(
                            previous_point,
                            current_point,
                            temporality,
                        ),
                    )
