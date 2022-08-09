# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http:  #www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint: disable=unused-import

from dataclasses import asdict, dataclass
from json import dumps, loads
from typing import Optional, Sequence, Union

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

    def to_json(self, indent=4) -> str:
        return dumps(asdict(self), indent=indent)


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

    def to_json(self, indent=4) -> str:
        return dumps(asdict(self), indent=indent)


@dataclass(frozen=True)
class Buckets:
    # Buckets are a set of bucket counts, encoded in a contiguous array
    # of counts.

    # Offset is the bucket index of the first entry in the bucket_counts array.
    #
    # Note: This uses a varint encoding as a simple form of compression.
    offset: int

    # Count is an array of counts, where count[i] carries the count
    # of the bucket at index (offset+i).  count[i] is the count of
    # values greater than base^(offset+i) and less or equal to than
    # base^(offset+i+1).
    #
    # Note: By contrast, the explicit HistogramDataPoint uses
    # fixed64.  This field is expected to have many buckets,
    # especially zeros, so uint64 has been selected to ensure
    # varint encoding.
    bucket_counts: Sequence[int]


@dataclass(frozen=True)
class ExponentialHistogramDataPoint:
    """Single data point in a timeseries whose boundaries are defined by an
    exponential function. This timeseries describes the time-varying scalar
    value of a metric.
    """

    # The set of key/value pairs that uniquely identify the timeseries from
    # where this point belongs. The list may be empty (may contain 0 elements).
    # Attribute keys MUST be unique (it is not allowed to have more than one
    # attribute with the same key).
    attributes: Attributes

    # StartTimeUnixNano is optional but strongly encouraged, see the
    # the detailed comments above Metric.
    #
    # Value is UNIX Epoch time in nanoseconds since 00:00:00 UTC on 1 January
    # 1970.
    start_time_unix_nano: int

    # TimeUnixNano is required, see the detailed comments above Metric.
    #
    # Value is UNIX Epoch time in nanoseconds since 00:00:00 UTC on 1 January
    # 1970.
    time_unix_nano: int

    # count is the number of values in the population. Must be
    # non-negative. This value must be equal to the sum of the "bucket_counts"
    # values in the positive and negative Buckets plus the "zero_count" field.
    count: int

    # sum of the values in the population. If count is zero then this field
    # must be zero.
    #
    # Note: Sum should only be filled out when measuring non-negative discrete
    # events, and is assumed to be monotonic over the values of these events.
    # Negative events *can* be recorded, but sum should not be filled out when
    # doing so.  This is specifically to enforce compatibility w/ OpenMetrics,
    # see: https:  #github.com/OpenObservability/OpenMetrics/blob/main/specification/OpenMetrics.md#histogram
    sum: Union[int, float]

    # scale describes the resolution of the histogram.  Boundaries are
    # located at powers of the base, where:
    #
    #   base = (2^(2^-scale))
    #
    # The histogram bucket identified by `index`, a signed integer,
    # contains values that are greater than (base^index) and
    # less than or equal to (base^(index+1)).
    #
    # The positive and negative ranges of the histogram are expressed
    # separately.  Negative values are mapped by their absolute value
    # into the negative range using the same scale as the positive range.
    #
    # scale is not restricted by the protocol, as the permissible
    # values depend on the range of the data.
    scale: int

    # zero_count is the count of values that are either exactly zero or
    # within the region considered zero by the instrumentation at the
    # tolerated degree of precision.  This bucket stores values that
    # cannot be expressed using the standard exponential formula as
    # well as values that have been rounded to zero.
    #
    # Implementations MAY consider the zero bucket to have probability
    # mass equal to (zero_count / count).
    zero_count: int

    # positive carries the positive range of exponential bucket counts.
    positive: Buckets

    # negative carries the negative range of exponential bucket counts.
    negative: Buckets

    # Flags that apply to this specific data point.  See DataPointFlags
    # for the available flags and their meaning.
    flags: int

    # min is the minimum value over (start_time, end_time].
    min: float

    # max is the maximum value over (start_time, end_time].
    max: float

    def to_json(self, indent=4) -> str:
        return dumps(asdict(self), indent=indent)


@dataclass(frozen=True)
class ExponentialHistogram:
    """Represents the type of a metric that is calculated by aggregating as an
    ExponentialHistogram of all reported measurements over a time interval.
    """

    data_points: Sequence[ExponentialHistogramDataPoint]
    aggregation_temporality: (
        "opentelemetry.sdk.metrics.export.AggregationTemporality"
    )


@dataclass(frozen=True)
class Sum:
    """Represents the type of a scalar metric that is calculated as a sum of
    all reported measurements over a time interval."""

    data_points: Sequence[NumberDataPoint]
    aggregation_temporality: (
        "opentelemetry.sdk.metrics.export.AggregationTemporality"
    )
    is_monotonic: bool

    def to_json(self, indent=4) -> str:
        return dumps(
            {
                "data_points": [
                    loads(data_point.to_json(indent=indent))
                    for data_point in self.data_points
                ],
                "aggregation_temporality": self.aggregation_temporality,
                "is_monotonic": self.is_monotonic,
            },
            indent=indent,
        )


@dataclass(frozen=True)
class Gauge:
    """Represents the type of a scalar metric that always exports the current
    value for every data point. It should be used for an unknown
    aggregation."""

    data_points: Sequence[NumberDataPoint]

    def to_json(self, indent=4) -> str:
        return dumps(
            {
                "data_points": [
                    loads(data_point.to_json(indent=indent))
                    for data_point in self.data_points
                ],
            },
            indent=indent,
        )


@dataclass(frozen=True)
class Histogram:
    """Represents the type of a metric that is calculated by aggregating as a
    histogram of all reported measurements over a time interval."""

    data_points: Sequence[HistogramDataPoint]
    aggregation_temporality: (
        "opentelemetry.sdk.metrics.export.AggregationTemporality"
    )

    def to_json(self, indent=4) -> str:
        return dumps(
            {
                "data_points": [
                    loads(data_point.to_json(indent=indent))
                    for data_point in self.data_points
                ],
                "aggregation_temporality": self.aggregation_temporality,
            },
            indent=indent,
        )


DataT = Union[Sum, Gauge, Histogram]
DataPointT = Union[NumberDataPoint, HistogramDataPoint]


@dataclass(frozen=True)
class Metric:
    """Represents a metric point in the OpenTelemetry data model to be
    exported."""

    name: str
    description: Optional[str]
    unit: Optional[str]
    data: DataT

    def to_json(self, indent=4) -> str:
        return dumps(
            {
                "name": self.name,
                "description": self.description or "",
                "unit": self.unit or "",
                "data": loads(self.data.to_json(indent=indent)),
            },
            indent=indent,
        )


@dataclass(frozen=True)
class ScopeMetrics:
    """A collection of Metrics produced by a scope"""

    scope: InstrumentationScope
    metrics: Sequence[Metric]
    schema_url: str

    def to_json(self, indent=4) -> str:
        return dumps(
            {
                "scope": loads(self.scope.to_json(indent=indent)),
                "metrics": [
                    loads(metric.to_json(indent=indent))
                    for metric in self.metrics
                ],
                "schema_url": self.schema_url,
            },
            indent=indent,
        )


@dataclass(frozen=True)
class ResourceMetrics:
    """A collection of ScopeMetrics from a Resource"""

    resource: Resource
    scope_metrics: Sequence[ScopeMetrics]
    schema_url: str

    def to_json(self, indent=4) -> str:
        return dumps(
            {
                "resource": loads(self.resource.to_json(indent=indent)),
                "scope_metrics": [
                    loads(scope_metrics.to_json(indent=indent))
                    for scope_metrics in self.scope_metrics
                ],
                "schema_url": self.schema_url,
            },
            indent=indent,
        )


@dataclass(frozen=True)
class MetricsData:
    """An array of ResourceMetrics"""

    resource_metrics: Sequence[ResourceMetrics]

    def to_json(self, indent=4) -> str:
        return dumps(
            {
                "resource_metrics": [
                    loads(resource_metrics.to_json(indent=indent))
                    for resource_metrics in self.resource_metrics
                ]
            }
        )
