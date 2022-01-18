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

from dataclasses import dataclass
from enum import IntEnum
from typing import Sequence, Union

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationInfo
from opentelemetry.util.types import Attributes


class AggregationTemporality(IntEnum):
    UNSPECIFIED = 0
    DELTA = 1
    CUMULATIVE = 2


@dataclass(frozen=True)
class Sum:
    start_time_unix_nano: int
    time_unix_nano: int
    value: Union[int, float]
    aggregation_temporality: AggregationTemporality
    is_monotonic: bool


@dataclass(frozen=True)
class Gauge:
    time_unix_nano: int
    value: Union[int, float]


@dataclass(frozen=True)
class Histogram:
    start_time_unix_nano: int
    time_unix_nano: int
    bucket_counts: Sequence[int]
    explicit_bounds: Sequence[float]
    aggregation_temporality: AggregationTemporality


PointT = Union[Sum, Gauge, Histogram]


@dataclass(frozen=True)
class Metric:
    """Represents a metric point in the OpenTelemetry data model to be exported

    Concrete metric types contain all the information as in the OTLP proto definitions
    (https://tinyurl.com/7h6yx24v) but are flattened as much as possible.
    """

    # common fields to all metric kinds
    attributes: Attributes
    description: str
    instrumentation_info: InstrumentationInfo
    name: str
    resource: Resource
    unit: str
    point: PointT
    """Contains non-common fields for the given metric"""

    def to_json(self) -> str:
        raise NotImplementedError()
