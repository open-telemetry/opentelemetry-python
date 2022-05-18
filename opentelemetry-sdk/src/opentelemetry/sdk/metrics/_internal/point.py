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

# pylint: disable=unused-import

from dataclasses import asdict, dataclass
from json import dumps
from typing import Sequence, Union

# This kind of import is needed to avoid Sphinx errors.
import opentelemetry.sdk.metrics._internal
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.util.types import Attributes


@dataclass(frozen=True)
class NumberDataPoint:
    """Single data point in a timeseries that describes the time-varying scalar
    value of a metric.
    """

    attributes: Attributes
    start_time_unix_nano: int
    time_unix_nano: int
    value: Union[int, float]


@dataclass(frozen=True)
class Sum:
    """Represents the type of a scalar metric that is calculated as a sum of
    all reported measurements over a time interval."""

    data_points: Sequence[NumberDataPoint]
    aggregation_temporality: (
        "opentelemetry.sdk.metrics.export.AggregationTemporality"
    )
    is_monotonic: bool

    def to_json(self) -> str:
        return dumps(
            {
                "data_points": dumps(
                    [asdict(data_point) for data_point in self.data_points]
                ),
                "aggregation_temporality": self.aggregation_temporality,
                "is_monotonic": self.is_monotonic,
            }
        )


@dataclass(frozen=True)
class Gauge:
    """Represents the type of a scalar metric that always exports the current
    value for every data point. It should be used for an unknown
    aggregation."""

    data_points: Sequence[NumberDataPoint]

    def to_json(self) -> str:
        return dumps(
            {
                "data_points": dumps(
                    [asdict(data_point) for data_point in self.data_points]
                )
            }
        )


@dataclass(frozen=True)
class HistogramDataPoint:
    """Single data point in a timeseries that describes the time-varying scalar
    value of a metric.
    """

    attributes: Attributes
    start_time_unix_nano: int
    time_unix_nano: int
    count: int
    sum: Union[int, float]
    bucket_counts: Sequence[int]
    explicit_bounds: Sequence[float]
    min: float
    max: float


@dataclass(frozen=True)
class Histogram:
    """Represents the type of a metric that is calculated by aggregating as a
    histogram of all reported measurements over a time interval."""

    data_points: Sequence[HistogramDataPoint]
    aggregation_temporality: (
        "opentelemetry.sdk.metrics.export.AggregationTemporality"
    )

    def to_json(self) -> str:
        return dumps(
            {
                "data_points": dumps(
                    [asdict(data_point) for data_point in self.data_points]
                ),
                "aggregation_temporality": self.aggregation_temporality,
            }
        )


DataT = Union[Sum, Gauge, Histogram]
DataPointT = Union[NumberDataPoint, HistogramDataPoint]


@dataclass(frozen=True)
class Metric:
    """Represents a metric point in the OpenTelemetry data model to be
    exported."""

    name: str
    description: str
    unit: str
    data: DataT

    def to_json(self) -> str:
        return dumps(
            {
                "name": self.name,
                "description": self.description if self.description else "",
                "unit": self.unit if self.unit else "",
                "data": self.data.to_json(),
            }
        )


@dataclass(frozen=True)
class ScopeMetrics:
    """A collection of Metrics produced by a scope"""

    scope: InstrumentationScope
    metrics: Sequence[Metric]
    schema_url: str


@dataclass(frozen=True)
class ResourceMetrics:
    """A collection of ScopeMetrics from a Resource"""

    resource: Resource
    scope_metrics: Sequence[ScopeMetrics]
    schema_url: str


@dataclass(frozen=True)
class MetricsData:
    """An array of ResourceMetrics"""

    resource_metrics: Sequence[ResourceMetrics]
