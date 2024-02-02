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
import typing
from dataclasses import dataclass
from json import dumps
from typing import Optional, Sequence, Union

# This kind of import is needed to avoid Sphinx errors.
import opentelemetry.sdk.metrics._internal
from opentelemetry.sdk.resources import Resource, ResourceDict
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.util.types import Attributes


class NumberDataPointDict(typing.TypedDict):
    """Dictionary representation of a NumberDataPoint."""

    attributes: Attributes
    start_time_unix_nano: int
    time_unix_nano: int
    value: Union[int, float]


@dataclass(frozen=True)
class NumberDataPoint:
    """Single data point in a timeseries that describes the time-varying scalar
    value of a metric.
    """

    attributes: Attributes
    start_time_unix_nano: int
    time_unix_nano: int
    value: Union[int, float]

    def to_dict(self) -> NumberDataPointDict:
        return {
            "attributes": dict(self.attributes),
            "start_time_unix_nano": self.start_time_unix_nano,
            "time_unix_nano": self.time_unix_nano,
            "value": self.value,
        }

    def to_json(self, indent=4) -> str:
        return dumps(self.to_dict(), indent=indent)


class HistogramDataPointDict(typing.TypedDict):
    """Dictionary representation of a HistogramDataPoint."""

    attributes: Attributes
    start_time_unix_nano: int
    time_unix_nano: int
    count: int
    sum: Union[int, float]
    bucket_counts: typing.List[int]
    explicit_bounds: typing.List[float]
    min: float
    max: float


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

    def to_dict(self) -> HistogramDataPointDict:
        return {
            "attributes": dict(self.attributes),
            "start_time_unix_nano": self.start_time_unix_nano,
            "time_unix_nano": self.time_unix_nano,
            "count": self.count,
            "sum": self.sum,
            "bucket_counts": list(self.bucket_counts),
            "explicit_bounds": list(self.explicit_bounds),
            "min": self.min,
            "max": self.max,
        }

    def to_json(self, indent=4) -> str:
        return dumps(self.to_dict(), indent=indent)


class BucketsDict(typing.TypedDict):
    """Dictionary representation of a Buckets object."""

    offset: int
    bucket_counts: typing.List[int]


@dataclass(frozen=True)
class Buckets:
    offset: int
    bucket_counts: Sequence[int]

    def to_dict(self) -> BucketsDict:
        return {
            "offset": self.offset,
            "bucket_counts": list(self.bucket_counts),
        }


class ExponentialHistogramDataPointDict(typing.TypedDict):
    """Dictionary representation of an ExponentialHistogramDataPoint."""

    attributes: Attributes
    start_time_unix_nano: int
    time_unix_nano: int
    count: int
    sum: Union[int, float]
    scale: int
    zero_count: int
    positive: BucketsDict
    negative: BucketsDict
    flags: int
    min: float
    max: float


@dataclass(frozen=True)
class ExponentialHistogramDataPoint:
    """Single data point in a timeseries whose boundaries are defined by an
    exponential function. This timeseries describes the time-varying scalar
    value of a metric.
    """

    attributes: Attributes
    start_time_unix_nano: int
    time_unix_nano: int
    count: int
    sum: Union[int, float]
    scale: int
    zero_count: int
    positive: Buckets
    negative: Buckets
    flags: int
    min: float
    max: float

    def to_dict(self) -> ExponentialHistogramDataPointDict:
        return {
            "attributes": dict(self.attributes),
            "start_time_unix_nano": self.start_time_unix_nano,
            "time_unix_nano": self.time_unix_nano,
            "count": self.count,
            "sum": self.sum,
            "scale": self.scale,
            "zero_count": self.zero_count,
            "positive": self.positive.to_dict(),
            "negative": self.negative.to_dict(),
            "flags": self.flags,
            "min": self.min,
            "max": self.max,
        }

    def to_json(self, indent=4) -> str:
        return dumps(self.to_dict(), indent=indent)


class ExponentialHistogramDict(typing.TypedDict):
    """Dictionary representation of an ExponentialHistogram."""

    data_points: typing.List[ExponentialHistogramDataPointDict]
    aggregation_temporality: int


@dataclass(frozen=True)
class ExponentialHistogram:
    """Represents the type of a metric that is calculated by aggregating as an
    ExponentialHistogram of all reported measurements over a time interval.
    """

    data_points: Sequence[ExponentialHistogramDataPoint]
    aggregation_temporality: (
        "opentelemetry.sdk.metrics.export.AggregationTemporality"
    )

    def to_dict(self) -> ExponentialHistogramDict:
        return {
            "data_points": [
                data_point.to_dict() for data_point in self.data_points
            ],
            "aggregation_temporality": self.aggregation_temporality.value,
        }


class SumDict(typing.TypedDict):
    """Dictionary representation of a Sum."""

    data_points: typing.List[NumberDataPointDict]
    aggregation_temporality: int
    is_monotonic: bool


@dataclass(frozen=True)
class Sum:
    """Represents the type of a scalar metric that is calculated as a sum of
    all reported measurements over a time interval."""

    data_points: Sequence[NumberDataPoint]
    aggregation_temporality: (
        "opentelemetry.sdk.metrics.export.AggregationTemporality"
    )
    is_monotonic: bool

    def to_dict(self) -> SumDict:
        return {
            "data_points": [
                data_point.to_dict() for data_point in self.data_points
            ],
            "aggregation_temporality": self.aggregation_temporality.value,
            "is_monotonic": self.is_monotonic,
        }

    def to_json(self, indent=4) -> str:
        return dumps(self.to_dict(), indent=indent)


class GaugeDict(typing.TypedDict):
    """Dictionary representation of a Gauge."""

    data_points: typing.List[NumberDataPointDict]


@dataclass(frozen=True)
class Gauge:
    """Represents the type of a scalar metric that always exports the current
    value for every data point. It should be used for an unknown
    aggregation."""

    data_points: Sequence[NumberDataPoint]

    def to_dict(self) -> GaugeDict:
        return {
            "data_points": [
                data_point.to_dict() for data_point in self.data_points
            ],
        }

    def to_json(self, indent=4) -> str:
        return dumps(self.to_dict(), indent=indent)


class HistogramDict(typing.TypedDict):
    """Dictionary representation of a Histogram."""

    data_points: typing.List[HistogramDataPointDict]
    aggregation_temporality: int


@dataclass(frozen=True)
class Histogram:
    """Represents the type of a metric that is calculated by aggregating as a
    histogram of all reported measurements over a time interval."""

    data_points: Sequence[HistogramDataPoint]
    aggregation_temporality: (
        "opentelemetry.sdk.metrics.export.AggregationTemporality"
    )

    def to_dict(self) -> HistogramDict:
        return {
            "data_points": [
                data_point.to_dict() for data_point in self.data_points
            ],
            "aggregation_temporality": self.aggregation_temporality.value,
        }

    def to_json(self, indent=4) -> str:
        return dumps(self.to_dict(), indent=indent)


# pylint: disable=invalid-name
DataT = Union[Sum, Gauge, Histogram, ExponentialHistogram]
DataPointT = Union[
    NumberDataPoint, HistogramDataPoint, ExponentialHistogramDataPoint
]


class MetricDict(typing.TypedDict):
    """Dictionary representation of a Metric."""

    name: str
    description: str
    unit: str
    data: typing.Union[
        SumDict, GaugeDict, HistogramDict, ExponentialHistogramDict
    ]


@dataclass(frozen=True)
class Metric:
    """Represents a metric point in the OpenTelemetry data model to be
    exported."""

    name: str
    description: Optional[str]
    unit: Optional[str]
    data: DataT

    def to_dict(self) -> MetricDict:
        return {
            "name": self.name,
            "description": self.description or "",
            "unit": self.unit or "",
            "data": self.data.to_dict(),
        }

    def to_json(self, indent=4) -> str:
        return dumps(self.to_dict(), indent=indent)


class ScopeMetricsDict(typing.TypedDict):
    """Dictionary representation of a ScopeMetrics object."""

    scope: typing.Any
    metrics: typing.List[typing.Any]
    schema_url: str


@dataclass(frozen=True)
class ScopeMetrics:
    """A collection of Metrics produced by a scope"""

    scope: InstrumentationScope
    metrics: Sequence[Metric]
    schema_url: str

    def to_dict(self) -> ScopeMetricsDict:
        return {
            "scope": self.scope.to_dict(),
            "metrics": [metric.to_dict() for metric in self.metrics],
            "schema_url": self.schema_url,
        }

    def to_json(self, indent=4) -> str:
        return dumps(self.to_dict(), indent=indent)


class ResourceMetricsDict(typing.TypedDict):
    """Dictionary representation of a ResourceMetrics object."""

    resource: ResourceDict
    scope_metrics: typing.List[ScopeMetricsDict]
    schema_url: str


@dataclass(frozen=True)
class ResourceMetrics:
    """A collection of ScopeMetrics from a Resource"""

    resource: Resource
    scope_metrics: Sequence[ScopeMetrics]
    schema_url: str

    def to_dict(self) -> ResourceMetricsDict:
        return {
            "resource": self.resource.to_dict(),
            "scope_metrics": [
                scope_metrics.to_dict() for scope_metrics in self.scope_metrics
            ],
            "schema_url": self.schema_url,
        }

    def to_json(self, indent=4) -> str:
        return dumps(self.to_dict(), indent=indent)


class MetricsDataDict(typing.TypedDict):
    """Dictionary representation of a MetricsData object."""

    resource_metrics: typing.List[ResourceMetricsDict]


@dataclass(frozen=True)
class MetricsData:
    """An array of ResourceMetrics"""

    resource_metrics: Sequence[ResourceMetrics]

    def to_dict(self) -> MetricsDataDict:
        return {
            "resource_metrics": [
                resource_metrics.to_dict()
                for resource_metrics in self.resource_metrics
            ]
        }

    def to_json(self, indent=4) -> str:
        return dumps(self.to_dict(), indent=indent)
