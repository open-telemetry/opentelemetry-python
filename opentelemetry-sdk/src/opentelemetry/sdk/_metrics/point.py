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

import json
from dataclasses import asdict, dataclass
from enum import IntEnum
from typing import Sequence, Union

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.util.types import Attributes


class AggregationTemporality(IntEnum):
    UNSPECIFIED = 0
    DELTA = 1
    CUMULATIVE = 2


@dataclass(frozen=True)
class Sum:
    aggregation_temporality: AggregationTemporality
    is_monotonic: bool
    start_time_unix_nano: int
    time_unix_nano: int
    value: Union[int, float]


@dataclass(frozen=True)
class Gauge:
    time_unix_nano: int
    value: Union[int, float]


@dataclass(frozen=True)
class Histogram:
    aggregation_temporality: AggregationTemporality
    bucket_counts: Sequence[int]
    explicit_bounds: Sequence[float]
    max: int
    min: int
    start_time_unix_nano: int
    sum: Union[int, float]
    time_unix_nano: int


PointT = Union[Sum, Gauge, Histogram]


@dataclass(frozen=True)
class Metric:
    """Represents a metric point in the OpenTelemetry data model to be exported

    Concrete metric types contain all the information as in the OTLP proto definitions
    (https://github.com/open-telemetry/opentelemetry-proto/blob/b43e9b18b76abf3ee040164b55b9c355217151f3/opentelemetry/proto/metrics/v1/metrics.proto#L37) but are flattened as much as possible.
    """

    # common fields to all metric kinds
    attributes: Attributes
    description: str
    instrumentation_scope: InstrumentationScope
    name: str
    resource: Resource
    unit: str
    point: PointT
    """Contains non-common fields for the given metric"""

    def to_json(self) -> str:
        return json.dumps(
            {
                "attributes": self.attributes if self.attributes else "",
                "description": self.description if self.description else "",
                "instrumentation_scope": repr(self.instrumentation_scope)
                if self.instrumentation_scope
                else "",
                "name": self.name,
                "resource": repr(self.resource.attributes)
                if self.resource
                else "",
                "unit": self.unit if self.unit else "",
                "point": asdict(self.point) if self.point else "",
            }
        )
