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
from typing import Callable, Dict, Iterable, List, Set

from opentelemetry.sdk._metrics.aggregation import (
    Aggregation, _convert_aggregation_temporality
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
        attribute_keys: Set[str] = None,
        aggregation: Aggregation,
        exemplar_reservoir: Callable,
    ):
        self._name = name
        self._unit = unit
        self._description = description
        self._resource = resource
        self._instrumentation_info = instrumentation_info

        if attribute_keys is None:
            self._attribute_keys = set()
        else:
            self._attribute_keys = set(attribute_keys.items())

        self._extra_dimensions = extra_dimensions
        self._aggregation = aggregation
        self._exemplar_reservoir = exemplar_reservoir
        self._attributes_aggregation = {}
        self._attributes_previous_point = {}
        self._lock = Lock()

    def consume_measurement(self, measurement: Measurement) -> None:
        if measurement.attributes is not None:
            measurement_attributes = set()

        else:
            measurement_attributes = set(measurement.attributes.items())

        attributes = frozenset(
            measurement_attributes.intersection(self._attribute_keys)
        )

        # What if attributes == frozenset()?

        if attributes not in self._attributes_aggregation.keys():
            with self._lock:
                self._attributes_aggregation[attributes] = self._aggregation

        self._attributes_aggregation[attributes].aggregate(measurement.value)

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
