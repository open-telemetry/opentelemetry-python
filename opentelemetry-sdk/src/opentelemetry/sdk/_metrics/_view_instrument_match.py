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

from dataclasses import replace
from logging import getLogger
from threading import Lock
from typing import Callable, Dict, Iterable, List, Optional

from opentelemetry.sdk._metrics.aggregation import Aggregation, _PointVarT
from opentelemetry.sdk._metrics.export import (
    AGGREGATION_TEMPORALITY_CUMULATIVE,
    AGGREGATION_TEMPORALITY_DELTA,
    Gauge,
    Metric,
    Sum,
)
from opentelemetry.sdk._metrics.measurement import Measurement
from opentelemetry.sdk.resources import Resource

_logger = getLogger(__name__)


class _ViewInstrumentMatch:
    def __init__(
        self,
        name: str,
        unit: str,
        description: str,
        attribute_keys: Dict[str, str],
        extra_dimensions: List[str],
        aggregation: Aggregation,
        exemplar_reservoir: Callable,
        resource: Resource,
    ):
        self._name = name
        self._unit = unit
        self._description = description

        if attribute_keys is None:
            self._attribute_keys = set()
        else:
            self._attribute_keys = set(attribute_keys.items())

        self._extra_dimensions = extra_dimensions
        self._aggregation = aggregation
        self._exemplar_reservoir = exemplar_reservoir
        self._attributes_aggregation = {}
        self._attributes_previous_value = {}
        self._lock = Lock()

    def _process(self, measurement: Measurement) -> None:
        if measurement.attributes is None:
            attributes = {}

        else:
            attributes = measurement.attributes

        attributes = frozenset(
            set(attributes).difference(self._attribute_keys)
        )

        if attributes not in self._attributes_aggregation.keys():
            # FIXME how to handle aggregations that support config?
            with self._lock:
                self._attributes_aggregation[attributes] = self._aggregation[
                    attributes
                ]

        self._attributes_aggregation[attributes].aggregate(measurement.amount)

    def _collect(self, temporality: int) -> Iterable[Metric]:
        with self._lock:
            for (
                attributes,
                aggregation,
            ) in self._attributes_aggregation.items():

                previous_point = self._attributes_previous_point.get(
                    attributes
                )

                current_point = aggregation.make_point()

                self._attributes_previous_point[attributes] = (
                    _convert_aggregation_temporality(
                        previous_point,
                        current_point,
                        AGGREGATION_TEMPORALITY_CUMULATIVE,
                    )
                )

                if current_point is not None:

                    yield Metric(
                        attributes=dict(attributes),
                        # FIXME check this is right
                        description=self._description,
                        # FIXME get instrumentation_info from the instrument
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


def _convert_aggregation_temporality(
    previous_point: Optional[_PointVarT],
    current_point: _PointVarT,
    aggregation_temporality: int,
) -> _PointVarT:

    previous_point_type = type(previous_point)
    current_point_type = type(current_point)

    if previous_point is not None and type(previous_point) is not type(
        current_point
    ):
        _logger.warning(
            "convert_aggregation_temporality called with mismatched "
            "point types: %s and %s",
            previous_point_type,
            current_point_type,
        )

        return current_point

    if current_point_type is Sum:
        if previous_point is None:

            return replace(
                current_point, aggregation_temporality=aggregation_temporality
            )

        if current_point.aggregation_temporality is aggregation_temporality:
            return current_point

        if aggregation_temporality == AGGREGATION_TEMPORALITY_DELTA:
            value = current_point.value - previous_point.value

        else:
            value = current_point.value + previous_point.value

        is_monotonic = (
            previous_point.is_monotonic and current_point.is_monotonic
        )

        return Sum(
            aggregation_temporality=aggregation_temporality,
            is_monotonic=is_monotonic,
            start_time_unix_nano=previous_point.start_time_unix_nano,
            time_unix_nano=current_point.time_unix_nano,
            value=value,
        )

    elif current_point_type is Gauge:
        return current_point
