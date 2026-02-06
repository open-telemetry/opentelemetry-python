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

# AUTO-GENERATED from "opentelemetry/proto/metrics/v1/metrics.proto"
# DO NOT EDIT MANUALLY

from __future__ import annotations

import json
from typing import Any, Optional, Union, Self
from dataclasses import dataclass, field
from enum import IntEnum

import opentelemetry.proto_json._otlp_json_utils as _utils
import opentelemetry.proto_json.common.v1.common
import opentelemetry.proto_json.resource.v1.resource

class AggregationTemporality(IntEnum):
    """
    Generated from protobuf enum AggregationTemporality
    """

    AGGREGATION_TEMPORALITY_UNSPECIFIED = 0
    AGGREGATION_TEMPORALITY_DELTA = 1
    AGGREGATION_TEMPORALITY_CUMULATIVE = 2

class DataPointFlags(IntEnum):
    """
    Generated from protobuf enum DataPointFlags
    """

    DATA_POINT_FLAGS_DO_NOT_USE = 0
    DATA_POINT_FLAGS_NO_RECORDED_VALUE_MASK = 1

@dataclass(slots=True)
class MetricsData:
    """
    Generated from protobuf message MetricsData
    """

    resource_metrics: list[ResourceMetrics] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        res: dict[str, Any] = {}
        if self.resource_metrics:
            res["resourceMetrics"] = _utils.serialize_repeated(self.resource_metrics, lambda v: v.to_dict())
        return res

    def to_json(self) -> str:
        """
        Serialize this message to a JSON string.
        
        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """
        Create from a dictionary with lowerCamelCase keys.
        
        Args:
            data: Dictionary representation following OTLP JSON encoding
        
        Returns:
            MetricsData instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("resourceMetrics")) is not None:
            args["resource_metrics"] = _utils.deserialize_repeated(val, lambda v: ResourceMetrics.from_dict(v))
        return cls(**args)

    @classmethod
    def from_json(cls, data: Union[str, bytes]) -> Self:
        """
        Deserialize from a JSON string or bytes.
        
        Args:
            data: JSON string or bytes
        
        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@dataclass(slots=True)
class ResourceMetrics:
    """
    Generated from protobuf message ResourceMetrics
    """

    resource: opentelemetry.proto_json.resource.v1.resource.Resource = None
    scope_metrics: list[ScopeMetrics] = field(default_factory=list)
    schema_url: str = ''

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        res: dict[str, Any] = {}
        if self.resource is not None:
            res["resource"] = self.resource.to_dict()
        if self.scope_metrics:
            res["scopeMetrics"] = _utils.serialize_repeated(self.scope_metrics, lambda v: v.to_dict())
        if self.schema_url != '':
            res["schemaUrl"] = self.schema_url
        return res

    def to_json(self) -> str:
        """
        Serialize this message to a JSON string.
        
        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """
        Create from a dictionary with lowerCamelCase keys.
        
        Args:
            data: Dictionary representation following OTLP JSON encoding
        
        Returns:
            ResourceMetrics instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("resource")) is not None:
            args["resource"] = opentelemetry.proto_json.resource.v1.resource.Resource.from_dict(val)
        if (val := data.get("scopeMetrics")) is not None:
            args["scope_metrics"] = _utils.deserialize_repeated(val, lambda v: ScopeMetrics.from_dict(v))
        if (val := data.get("schemaUrl")) is not None:
            args["schema_url"] = val
        return cls(**args)

    @classmethod
    def from_json(cls, data: Union[str, bytes]) -> Self:
        """
        Deserialize from a JSON string or bytes.
        
        Args:
            data: JSON string or bytes
        
        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@dataclass(slots=True)
class ScopeMetrics:
    """
    Generated from protobuf message ScopeMetrics
    """

    scope: opentelemetry.proto_json.common.v1.common.InstrumentationScope = None
    metrics: list[Metric] = field(default_factory=list)
    schema_url: str = ''

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        res: dict[str, Any] = {}
        if self.scope is not None:
            res["scope"] = self.scope.to_dict()
        if self.metrics:
            res["metrics"] = _utils.serialize_repeated(self.metrics, lambda v: v.to_dict())
        if self.schema_url != '':
            res["schemaUrl"] = self.schema_url
        return res

    def to_json(self) -> str:
        """
        Serialize this message to a JSON string.
        
        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """
        Create from a dictionary with lowerCamelCase keys.
        
        Args:
            data: Dictionary representation following OTLP JSON encoding
        
        Returns:
            ScopeMetrics instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("scope")) is not None:
            args["scope"] = opentelemetry.proto_json.common.v1.common.InstrumentationScope.from_dict(val)
        if (val := data.get("metrics")) is not None:
            args["metrics"] = _utils.deserialize_repeated(val, lambda v: Metric.from_dict(v))
        if (val := data.get("schemaUrl")) is not None:
            args["schema_url"] = val
        return cls(**args)

    @classmethod
    def from_json(cls, data: Union[str, bytes]) -> Self:
        """
        Deserialize from a JSON string or bytes.
        
        Args:
            data: JSON string or bytes
        
        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@dataclass(slots=True)
class Metric:
    """
    Generated from protobuf message Metric
    """

    name: str = ''
    description: str = ''
    unit: str = ''
    gauge: Gauge = None
    sum: Sum = None
    histogram: Histogram = None
    exponential_histogram: ExponentialHistogram = None
    summary: Summary = None
    metadata: list[opentelemetry.proto_json.common.v1.common.KeyValue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        res: dict[str, Any] = {}
        if self.name != '':
            res["name"] = self.name
        if self.description != '':
            res["description"] = self.description
        if self.unit != '':
            res["unit"] = self.unit
        if self.gauge is not None:
            res["gauge"] = self.gauge.to_dict()
        if self.sum is not None:
            res["sum"] = self.sum.to_dict()
        if self.histogram is not None:
            res["histogram"] = self.histogram.to_dict()
        if self.exponential_histogram is not None:
            res["exponentialHistogram"] = self.exponential_histogram.to_dict()
        if self.summary is not None:
            res["summary"] = self.summary.to_dict()
        if self.metadata:
            res["metadata"] = _utils.serialize_repeated(self.metadata, lambda v: v.to_dict())
        return res

    def to_json(self) -> str:
        """
        Serialize this message to a JSON string.
        
        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """
        Create from a dictionary with lowerCamelCase keys.
        
        Args:
            data: Dictionary representation following OTLP JSON encoding
        
        Returns:
            Metric instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("name")) is not None:
            args["name"] = val
        if (val := data.get("description")) is not None:
            args["description"] = val
        if (val := data.get("unit")) is not None:
            args["unit"] = val
        if (val := data.get("gauge")) is not None:
            args["gauge"] = Gauge.from_dict(val)
        if (val := data.get("sum")) is not None:
            args["sum"] = Sum.from_dict(val)
        if (val := data.get("histogram")) is not None:
            args["histogram"] = Histogram.from_dict(val)
        if (val := data.get("exponentialHistogram")) is not None:
            args["exponential_histogram"] = ExponentialHistogram.from_dict(val)
        if (val := data.get("summary")) is not None:
            args["summary"] = Summary.from_dict(val)
        if (val := data.get("metadata")) is not None:
            args["metadata"] = _utils.deserialize_repeated(val, lambda v: opentelemetry.proto_json.common.v1.common.KeyValue.from_dict(v))
        return cls(**args)

    @classmethod
    def from_json(cls, data: Union[str, bytes]) -> Self:
        """
        Deserialize from a JSON string or bytes.
        
        Args:
            data: JSON string or bytes
        
        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@dataclass(slots=True)
class Gauge:
    """
    Generated from protobuf message Gauge
    """

    data_points: list[NumberDataPoint] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        res: dict[str, Any] = {}
        if self.data_points:
            res["dataPoints"] = _utils.serialize_repeated(self.data_points, lambda v: v.to_dict())
        return res

    def to_json(self) -> str:
        """
        Serialize this message to a JSON string.
        
        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """
        Create from a dictionary with lowerCamelCase keys.
        
        Args:
            data: Dictionary representation following OTLP JSON encoding
        
        Returns:
            Gauge instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("dataPoints")) is not None:
            args["data_points"] = _utils.deserialize_repeated(val, lambda v: NumberDataPoint.from_dict(v))
        return cls(**args)

    @classmethod
    def from_json(cls, data: Union[str, bytes]) -> Self:
        """
        Deserialize from a JSON string or bytes.
        
        Args:
            data: JSON string or bytes
        
        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@dataclass(slots=True)
class Sum:
    """
    Generated from protobuf message Sum
    """

    data_points: list[NumberDataPoint] = field(default_factory=list)
    aggregation_temporality: AggregationTemporality = 0
    is_monotonic: bool = False

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        res: dict[str, Any] = {}
        if self.data_points:
            res["dataPoints"] = _utils.serialize_repeated(self.data_points, lambda v: v.to_dict())
        if self.aggregation_temporality != None:
            res["aggregationTemporality"] = int(self.aggregation_temporality)
        if self.is_monotonic != False:
            res["isMonotonic"] = self.is_monotonic
        return res

    def to_json(self) -> str:
        """
        Serialize this message to a JSON string.
        
        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """
        Create from a dictionary with lowerCamelCase keys.
        
        Args:
            data: Dictionary representation following OTLP JSON encoding
        
        Returns:
            Sum instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("dataPoints")) is not None:
            args["data_points"] = _utils.deserialize_repeated(val, lambda v: NumberDataPoint.from_dict(v))
        if (val := data.get("aggregationTemporality")) is not None:
            args["aggregation_temporality"] = AggregationTemporality(val)
        if (val := data.get("isMonotonic")) is not None:
            args["is_monotonic"] = val
        return cls(**args)

    @classmethod
    def from_json(cls, data: Union[str, bytes]) -> Self:
        """
        Deserialize from a JSON string or bytes.
        
        Args:
            data: JSON string or bytes
        
        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@dataclass(slots=True)
class Histogram:
    """
    Generated from protobuf message Histogram
    """

    data_points: list[HistogramDataPoint] = field(default_factory=list)
    aggregation_temporality: AggregationTemporality = 0

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        res: dict[str, Any] = {}
        if self.data_points:
            res["dataPoints"] = _utils.serialize_repeated(self.data_points, lambda v: v.to_dict())
        if self.aggregation_temporality != None:
            res["aggregationTemporality"] = int(self.aggregation_temporality)
        return res

    def to_json(self) -> str:
        """
        Serialize this message to a JSON string.
        
        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """
        Create from a dictionary with lowerCamelCase keys.
        
        Args:
            data: Dictionary representation following OTLP JSON encoding
        
        Returns:
            Histogram instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("dataPoints")) is not None:
            args["data_points"] = _utils.deserialize_repeated(val, lambda v: HistogramDataPoint.from_dict(v))
        if (val := data.get("aggregationTemporality")) is not None:
            args["aggregation_temporality"] = AggregationTemporality(val)
        return cls(**args)

    @classmethod
    def from_json(cls, data: Union[str, bytes]) -> Self:
        """
        Deserialize from a JSON string or bytes.
        
        Args:
            data: JSON string or bytes
        
        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@dataclass(slots=True)
class ExponentialHistogram:
    """
    Generated from protobuf message ExponentialHistogram
    """

    data_points: list[ExponentialHistogramDataPoint] = field(default_factory=list)
    aggregation_temporality: AggregationTemporality = 0

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        res: dict[str, Any] = {}
        if self.data_points:
            res["dataPoints"] = _utils.serialize_repeated(self.data_points, lambda v: v.to_dict())
        if self.aggregation_temporality != None:
            res["aggregationTemporality"] = int(self.aggregation_temporality)
        return res

    def to_json(self) -> str:
        """
        Serialize this message to a JSON string.
        
        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """
        Create from a dictionary with lowerCamelCase keys.
        
        Args:
            data: Dictionary representation following OTLP JSON encoding
        
        Returns:
            ExponentialHistogram instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("dataPoints")) is not None:
            args["data_points"] = _utils.deserialize_repeated(val, lambda v: ExponentialHistogramDataPoint.from_dict(v))
        if (val := data.get("aggregationTemporality")) is not None:
            args["aggregation_temporality"] = AggregationTemporality(val)
        return cls(**args)

    @classmethod
    def from_json(cls, data: Union[str, bytes]) -> Self:
        """
        Deserialize from a JSON string or bytes.
        
        Args:
            data: JSON string or bytes
        
        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@dataclass(slots=True)
class Summary:
    """
    Generated from protobuf message Summary
    """

    data_points: list[SummaryDataPoint] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        res: dict[str, Any] = {}
        if self.data_points:
            res["dataPoints"] = _utils.serialize_repeated(self.data_points, lambda v: v.to_dict())
        return res

    def to_json(self) -> str:
        """
        Serialize this message to a JSON string.
        
        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """
        Create from a dictionary with lowerCamelCase keys.
        
        Args:
            data: Dictionary representation following OTLP JSON encoding
        
        Returns:
            Summary instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("dataPoints")) is not None:
            args["data_points"] = _utils.deserialize_repeated(val, lambda v: SummaryDataPoint.from_dict(v))
        return cls(**args)

    @classmethod
    def from_json(cls, data: Union[str, bytes]) -> Self:
        """
        Deserialize from a JSON string or bytes.
        
        Args:
            data: JSON string or bytes
        
        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@dataclass(slots=True)
class NumberDataPoint:
    """
    Generated from protobuf message NumberDataPoint
    """

    attributes: list[opentelemetry.proto_json.common.v1.common.KeyValue] = field(default_factory=list)
    start_time_unix_nano: int = 0
    time_unix_nano: int = 0
    as_double: float = 0.0
    as_int: int = 0
    exemplars: list[Exemplar] = field(default_factory=list)
    flags: int = 0

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        res: dict[str, Any] = {}
        if self.attributes:
            res["attributes"] = _utils.serialize_repeated(self.attributes, lambda v: v.to_dict())
        if self.start_time_unix_nano != 0:
            res["startTimeUnixNano"] = _utils.encode_int64(self.start_time_unix_nano)
        if self.time_unix_nano != 0:
            res["timeUnixNano"] = _utils.encode_int64(self.time_unix_nano)
        if self.as_double != 0.0:
            res["asDouble"] = _utils.encode_float(self.as_double)
        if self.as_int != 0:
            res["asInt"] = _utils.encode_int64(self.as_int)
        if self.exemplars:
            res["exemplars"] = _utils.serialize_repeated(self.exemplars, lambda v: v.to_dict())
        if self.flags != 0:
            res["flags"] = self.flags
        return res

    def to_json(self) -> str:
        """
        Serialize this message to a JSON string.
        
        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """
        Create from a dictionary with lowerCamelCase keys.
        
        Args:
            data: Dictionary representation following OTLP JSON encoding
        
        Returns:
            NumberDataPoint instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("attributes")) is not None:
            args["attributes"] = _utils.deserialize_repeated(val, lambda v: opentelemetry.proto_json.common.v1.common.KeyValue.from_dict(v))
        if (val := data.get("startTimeUnixNano")) is not None:
            args["start_time_unix_nano"] = _utils.parse_int64(val)
        if (val := data.get("timeUnixNano")) is not None:
            args["time_unix_nano"] = _utils.parse_int64(val)
        if (val := data.get("asDouble")) is not None:
            args["as_double"] = _utils.parse_float(val)
        if (val := data.get("asInt")) is not None:
            args["as_int"] = _utils.parse_int64(val)
        if (val := data.get("exemplars")) is not None:
            args["exemplars"] = _utils.deserialize_repeated(val, lambda v: Exemplar.from_dict(v))
        if (val := data.get("flags")) is not None:
            args["flags"] = val
        return cls(**args)

    @classmethod
    def from_json(cls, data: Union[str, bytes]) -> Self:
        """
        Deserialize from a JSON string or bytes.
        
        Args:
            data: JSON string or bytes
        
        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@dataclass(slots=True)
class HistogramDataPoint:
    """
    Generated from protobuf message HistogramDataPoint
    """

    attributes: list[opentelemetry.proto_json.common.v1.common.KeyValue] = field(default_factory=list)
    start_time_unix_nano: int = 0
    time_unix_nano: int = 0
    count: int = 0
    sum: Optional[float] = None
    bucket_counts: list[int] = field(default_factory=list)
    explicit_bounds: list[float] = field(default_factory=list)
    exemplars: list[Exemplar] = field(default_factory=list)
    flags: int = 0
    min: Optional[float] = None
    max: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        res: dict[str, Any] = {}
        if self.attributes:
            res["attributes"] = _utils.serialize_repeated(self.attributes, lambda v: v.to_dict())
        if self.start_time_unix_nano != 0:
            res["startTimeUnixNano"] = _utils.encode_int64(self.start_time_unix_nano)
        if self.time_unix_nano != 0:
            res["timeUnixNano"] = _utils.encode_int64(self.time_unix_nano)
        if self.count != 0:
            res["count"] = _utils.encode_int64(self.count)
        if self.sum != 0.0:
            res["sum"] = _utils.encode_float(self.sum)
        if self.bucket_counts:
            res["bucketCounts"] = _utils.serialize_repeated(self.bucket_counts, lambda v: _utils.encode_int64(v))
        if self.explicit_bounds:
            res["explicitBounds"] = _utils.serialize_repeated(self.explicit_bounds, lambda v: _utils.encode_float(v))
        if self.exemplars:
            res["exemplars"] = _utils.serialize_repeated(self.exemplars, lambda v: v.to_dict())
        if self.flags != 0:
            res["flags"] = self.flags
        if self.min != 0.0:
            res["min"] = _utils.encode_float(self.min)
        if self.max != 0.0:
            res["max"] = _utils.encode_float(self.max)
        return res

    def to_json(self) -> str:
        """
        Serialize this message to a JSON string.
        
        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """
        Create from a dictionary with lowerCamelCase keys.
        
        Args:
            data: Dictionary representation following OTLP JSON encoding
        
        Returns:
            HistogramDataPoint instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("attributes")) is not None:
            args["attributes"] = _utils.deserialize_repeated(val, lambda v: opentelemetry.proto_json.common.v1.common.KeyValue.from_dict(v))
        if (val := data.get("startTimeUnixNano")) is not None:
            args["start_time_unix_nano"] = _utils.parse_int64(val)
        if (val := data.get("timeUnixNano")) is not None:
            args["time_unix_nano"] = _utils.parse_int64(val)
        if (val := data.get("count")) is not None:
            args["count"] = _utils.parse_int64(val)
        if (val := data.get("sum")) is not None:
            args["sum"] = _utils.parse_float(val)
        if (val := data.get("bucketCounts")) is not None:
            args["bucket_counts"] = _utils.deserialize_repeated(val, lambda v: _utils.parse_int64(v))
        if (val := data.get("explicitBounds")) is not None:
            args["explicit_bounds"] = _utils.deserialize_repeated(val, lambda v: _utils.parse_float(v))
        if (val := data.get("exemplars")) is not None:
            args["exemplars"] = _utils.deserialize_repeated(val, lambda v: Exemplar.from_dict(v))
        if (val := data.get("flags")) is not None:
            args["flags"] = val
        if (val := data.get("min")) is not None:
            args["min"] = _utils.parse_float(val)
        if (val := data.get("max")) is not None:
            args["max"] = _utils.parse_float(val)
        return cls(**args)

    @classmethod
    def from_json(cls, data: Union[str, bytes]) -> Self:
        """
        Deserialize from a JSON string or bytes.
        
        Args:
            data: JSON string or bytes
        
        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@dataclass(slots=True)
class ExponentialHistogramDataPoint:
    """
    Generated from protobuf message ExponentialHistogramDataPoint
    """

    @dataclass(slots=True)
    class Buckets:
        """
        Generated from protobuf message Buckets
        """

        offset: int = 0
        bucket_counts: list[int] = field(default_factory=list)

        def to_dict(self) -> dict[str, Any]:
            """
            Convert this message to a dictionary with lowerCamelCase keys.
            
            Returns:
                Dictionary representation following OTLP JSON encoding
            """
            res: dict[str, Any] = {}
            if self.offset != 0:
                res["offset"] = self.offset
            if self.bucket_counts:
                res["bucketCounts"] = _utils.serialize_repeated(self.bucket_counts, lambda v: _utils.encode_int64(v))
            return res

        def to_json(self) -> str:
            """
            Serialize this message to a JSON string.
            
            Returns:
                JSON string
            """
            return json.dumps(self.to_dict())

        @classmethod
        def from_dict(cls, data: dict[str, Any]) -> Self:
            """
            Create from a dictionary with lowerCamelCase keys.
            
            Args:
                data: Dictionary representation following OTLP JSON encoding
            
            Returns:
                Buckets instance
            """
            args: dict[str, Any] = {}
            if (val := data.get("offset")) is not None:
                args["offset"] = val
            if (val := data.get("bucketCounts")) is not None:
                args["bucket_counts"] = _utils.deserialize_repeated(val, lambda v: _utils.parse_int64(v))
            return cls(**args)

        @classmethod
        def from_json(cls, data: Union[str, bytes]) -> Self:
            """
            Deserialize from a JSON string or bytes.
            
            Args:
                data: JSON string or bytes
            
            Returns:
                Instance of the class
            """
            return cls.from_dict(json.loads(data))

    attributes: list[opentelemetry.proto_json.common.v1.common.KeyValue] = field(default_factory=list)
    start_time_unix_nano: int = 0
    time_unix_nano: int = 0
    count: int = 0
    sum: Optional[float] = None
    scale: int = 0
    zero_count: int = 0
    positive: ExponentialHistogramDataPoint.Buckets = None
    negative: ExponentialHistogramDataPoint.Buckets = None
    flags: int = 0
    exemplars: list[Exemplar] = field(default_factory=list)
    min: Optional[float] = None
    max: Optional[float] = None
    zero_threshold: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        res: dict[str, Any] = {}
        if self.attributes:
            res["attributes"] = _utils.serialize_repeated(self.attributes, lambda v: v.to_dict())
        if self.start_time_unix_nano != 0:
            res["startTimeUnixNano"] = _utils.encode_int64(self.start_time_unix_nano)
        if self.time_unix_nano != 0:
            res["timeUnixNano"] = _utils.encode_int64(self.time_unix_nano)
        if self.count != 0:
            res["count"] = _utils.encode_int64(self.count)
        if self.sum != 0.0:
            res["sum"] = _utils.encode_float(self.sum)
        if self.scale != 0:
            res["scale"] = self.scale
        if self.zero_count != 0:
            res["zeroCount"] = _utils.encode_int64(self.zero_count)
        if self.positive is not None:
            res["positive"] = self.positive.to_dict()
        if self.negative is not None:
            res["negative"] = self.negative.to_dict()
        if self.flags != 0:
            res["flags"] = self.flags
        if self.exemplars:
            res["exemplars"] = _utils.serialize_repeated(self.exemplars, lambda v: v.to_dict())
        if self.min != 0.0:
            res["min"] = _utils.encode_float(self.min)
        if self.max != 0.0:
            res["max"] = _utils.encode_float(self.max)
        if self.zero_threshold != 0.0:
            res["zeroThreshold"] = _utils.encode_float(self.zero_threshold)
        return res

    def to_json(self) -> str:
        """
        Serialize this message to a JSON string.
        
        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """
        Create from a dictionary with lowerCamelCase keys.
        
        Args:
            data: Dictionary representation following OTLP JSON encoding
        
        Returns:
            ExponentialHistogramDataPoint instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("attributes")) is not None:
            args["attributes"] = _utils.deserialize_repeated(val, lambda v: opentelemetry.proto_json.common.v1.common.KeyValue.from_dict(v))
        if (val := data.get("startTimeUnixNano")) is not None:
            args["start_time_unix_nano"] = _utils.parse_int64(val)
        if (val := data.get("timeUnixNano")) is not None:
            args["time_unix_nano"] = _utils.parse_int64(val)
        if (val := data.get("count")) is not None:
            args["count"] = _utils.parse_int64(val)
        if (val := data.get("sum")) is not None:
            args["sum"] = _utils.parse_float(val)
        if (val := data.get("scale")) is not None:
            args["scale"] = val
        if (val := data.get("zeroCount")) is not None:
            args["zero_count"] = _utils.parse_int64(val)
        if (val := data.get("positive")) is not None:
            args["positive"] = ExponentialHistogramDataPoint.Buckets.from_dict(val)
        if (val := data.get("negative")) is not None:
            args["negative"] = ExponentialHistogramDataPoint.Buckets.from_dict(val)
        if (val := data.get("flags")) is not None:
            args["flags"] = val
        if (val := data.get("exemplars")) is not None:
            args["exemplars"] = _utils.deserialize_repeated(val, lambda v: Exemplar.from_dict(v))
        if (val := data.get("min")) is not None:
            args["min"] = _utils.parse_float(val)
        if (val := data.get("max")) is not None:
            args["max"] = _utils.parse_float(val)
        if (val := data.get("zeroThreshold")) is not None:
            args["zero_threshold"] = _utils.parse_float(val)
        return cls(**args)

    @classmethod
    def from_json(cls, data: Union[str, bytes]) -> Self:
        """
        Deserialize from a JSON string or bytes.
        
        Args:
            data: JSON string or bytes
        
        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@dataclass(slots=True)
class SummaryDataPoint:
    """
    Generated from protobuf message SummaryDataPoint
    """

    @dataclass(slots=True)
    class ValueAtQuantile:
        """
        Generated from protobuf message ValueAtQuantile
        """

        quantile: float = 0.0
        value: float = 0.0

        def to_dict(self) -> dict[str, Any]:
            """
            Convert this message to a dictionary with lowerCamelCase keys.
            
            Returns:
                Dictionary representation following OTLP JSON encoding
            """
            res: dict[str, Any] = {}
            if self.quantile != 0.0:
                res["quantile"] = _utils.encode_float(self.quantile)
            if self.value != 0.0:
                res["value"] = _utils.encode_float(self.value)
            return res

        def to_json(self) -> str:
            """
            Serialize this message to a JSON string.
            
            Returns:
                JSON string
            """
            return json.dumps(self.to_dict())

        @classmethod
        def from_dict(cls, data: dict[str, Any]) -> Self:
            """
            Create from a dictionary with lowerCamelCase keys.
            
            Args:
                data: Dictionary representation following OTLP JSON encoding
            
            Returns:
                ValueAtQuantile instance
            """
            args: dict[str, Any] = {}
            if (val := data.get("quantile")) is not None:
                args["quantile"] = _utils.parse_float(val)
            if (val := data.get("value")) is not None:
                args["value"] = _utils.parse_float(val)
            return cls(**args)

        @classmethod
        def from_json(cls, data: Union[str, bytes]) -> Self:
            """
            Deserialize from a JSON string or bytes.
            
            Args:
                data: JSON string or bytes
            
            Returns:
                Instance of the class
            """
            return cls.from_dict(json.loads(data))

    attributes: list[opentelemetry.proto_json.common.v1.common.KeyValue] = field(default_factory=list)
    start_time_unix_nano: int = 0
    time_unix_nano: int = 0
    count: int = 0
    sum: float = 0.0
    quantile_values: list[SummaryDataPoint.ValueAtQuantile] = field(default_factory=list)
    flags: int = 0

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        res: dict[str, Any] = {}
        if self.attributes:
            res["attributes"] = _utils.serialize_repeated(self.attributes, lambda v: v.to_dict())
        if self.start_time_unix_nano != 0:
            res["startTimeUnixNano"] = _utils.encode_int64(self.start_time_unix_nano)
        if self.time_unix_nano != 0:
            res["timeUnixNano"] = _utils.encode_int64(self.time_unix_nano)
        if self.count != 0:
            res["count"] = _utils.encode_int64(self.count)
        if self.sum != 0.0:
            res["sum"] = _utils.encode_float(self.sum)
        if self.quantile_values:
            res["quantileValues"] = _utils.serialize_repeated(self.quantile_values, lambda v: v.to_dict())
        if self.flags != 0:
            res["flags"] = self.flags
        return res

    def to_json(self) -> str:
        """
        Serialize this message to a JSON string.
        
        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """
        Create from a dictionary with lowerCamelCase keys.
        
        Args:
            data: Dictionary representation following OTLP JSON encoding
        
        Returns:
            SummaryDataPoint instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("attributes")) is not None:
            args["attributes"] = _utils.deserialize_repeated(val, lambda v: opentelemetry.proto_json.common.v1.common.KeyValue.from_dict(v))
        if (val := data.get("startTimeUnixNano")) is not None:
            args["start_time_unix_nano"] = _utils.parse_int64(val)
        if (val := data.get("timeUnixNano")) is not None:
            args["time_unix_nano"] = _utils.parse_int64(val)
        if (val := data.get("count")) is not None:
            args["count"] = _utils.parse_int64(val)
        if (val := data.get("sum")) is not None:
            args["sum"] = _utils.parse_float(val)
        if (val := data.get("quantileValues")) is not None:
            args["quantile_values"] = _utils.deserialize_repeated(val, lambda v: SummaryDataPoint.ValueAtQuantile.from_dict(v))
        if (val := data.get("flags")) is not None:
            args["flags"] = val
        return cls(**args)

    @classmethod
    def from_json(cls, data: Union[str, bytes]) -> Self:
        """
        Deserialize from a JSON string or bytes.
        
        Args:
            data: JSON string or bytes
        
        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@dataclass(slots=True)
class Exemplar:
    """
    Generated from protobuf message Exemplar
    """

    filtered_attributes: list[opentelemetry.proto_json.common.v1.common.KeyValue] = field(default_factory=list)
    time_unix_nano: int = 0
    as_double: float = 0.0
    as_int: int = 0
    span_id: bytes = b''
    trace_id: bytes = b''

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        res: dict[str, Any] = {}
        if self.filtered_attributes:
            res["filteredAttributes"] = _utils.serialize_repeated(self.filtered_attributes, lambda v: v.to_dict())
        if self.time_unix_nano != 0:
            res["timeUnixNano"] = _utils.encode_int64(self.time_unix_nano)
        if self.as_double != 0.0:
            res["asDouble"] = _utils.encode_float(self.as_double)
        if self.as_int != 0:
            res["asInt"] = _utils.encode_int64(self.as_int)
        if self.span_id != b'':
            res["spanId"] = _utils.encode_hex(self.span_id)
        if self.trace_id != b'':
            res["traceId"] = _utils.encode_hex(self.trace_id)
        return res

    def to_json(self) -> str:
        """
        Serialize this message to a JSON string.
        
        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """
        Create from a dictionary with lowerCamelCase keys.
        
        Args:
            data: Dictionary representation following OTLP JSON encoding
        
        Returns:
            Exemplar instance
        """
        args: dict[str, Any] = {}
        if (val := data.get("filteredAttributes")) is not None:
            args["filtered_attributes"] = _utils.deserialize_repeated(val, lambda v: opentelemetry.proto_json.common.v1.common.KeyValue.from_dict(v))
        if (val := data.get("timeUnixNano")) is not None:
            args["time_unix_nano"] = _utils.parse_int64(val)
        if (val := data.get("asDouble")) is not None:
            args["as_double"] = _utils.parse_float(val)
        if (val := data.get("asInt")) is not None:
            args["as_int"] = _utils.parse_int64(val)
        if (val := data.get("spanId")) is not None:
            args["span_id"] = _utils.decode_hex(val)
        if (val := data.get("traceId")) is not None:
            args["trace_id"] = _utils.decode_hex(val)
        return cls(**args)

    @classmethod
    def from_json(cls, data: Union[str, bytes]) -> Self:
        """
        Deserialize from a JSON string or bytes.
        
        Args:
            data: JSON string or bytes
        
        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))