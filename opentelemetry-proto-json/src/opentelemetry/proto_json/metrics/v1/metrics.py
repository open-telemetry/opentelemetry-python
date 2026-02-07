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
        _result: dict[str, Any] = {}
        if self.resource_metrics:
            _result["resourceMetrics"] = _utils.serialize_repeated(self.resource_metrics, lambda _v: _v.to_dict())
        return _result

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
        _args: dict[str, Any] = {}

        if (_value := data.get("resourceMetrics")) is not None:
            _args["resource_metrics"] = _utils.deserialize_repeated(_value, lambda _v: ResourceMetrics.from_dict(_v))

        return cls(**_args)

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
        _result: dict[str, Any] = {}
        if self.resource is not None:
            _result["resource"] = self.resource.to_dict()
        if self.scope_metrics:
            _result["scopeMetrics"] = _utils.serialize_repeated(self.scope_metrics, lambda _v: _v.to_dict())
        if self.schema_url != '':
            _result["schemaUrl"] = self.schema_url
        return _result

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
        _args: dict[str, Any] = {}

        if (_value := data.get("resource")) is not None:
            _args["resource"] = opentelemetry.proto_json.resource.v1.resource.Resource.from_dict(_value)
        if (_value := data.get("scopeMetrics")) is not None:
            _args["scope_metrics"] = _utils.deserialize_repeated(_value, lambda _v: ScopeMetrics.from_dict(_v))
        if (_value := data.get("schemaUrl")) is not None:
            _args["schema_url"] = _value

        return cls(**_args)

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
        _result: dict[str, Any] = {}
        if self.scope is not None:
            _result["scope"] = self.scope.to_dict()
        if self.metrics:
            _result["metrics"] = _utils.serialize_repeated(self.metrics, lambda _v: _v.to_dict())
        if self.schema_url != '':
            _result["schemaUrl"] = self.schema_url
        return _result

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
        _args: dict[str, Any] = {}

        if (_value := data.get("scope")) is not None:
            _args["scope"] = opentelemetry.proto_json.common.v1.common.InstrumentationScope.from_dict(_value)
        if (_value := data.get("metrics")) is not None:
            _args["metrics"] = _utils.deserialize_repeated(_value, lambda _v: Metric.from_dict(_v))
        if (_value := data.get("schemaUrl")) is not None:
            _args["schema_url"] = _value

        return cls(**_args)

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
    gauge: Optional[Gauge] = None
    sum: Optional[Sum] = None
    histogram: Optional[Histogram] = None
    exponential_histogram: Optional[ExponentialHistogram] = None
    summary: Optional[Summary] = None
    metadata: list[opentelemetry.proto_json.common.v1.common.KeyValue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result: dict[str, Any] = {}
        if self.name != '':
            _result["name"] = self.name
        if self.description != '':
            _result["description"] = self.description
        if self.unit != '':
            _result["unit"] = self.unit
        if self.metadata:
            _result["metadata"] = _utils.serialize_repeated(self.metadata, lambda _v: _v.to_dict())
        if self.summary is not None:
            _result["summary"] = self.summary.to_dict()
        elif self.exponential_histogram is not None:
            _result["exponentialHistogram"] = self.exponential_histogram.to_dict()
        elif self.histogram is not None:
            _result["histogram"] = self.histogram.to_dict()
        elif self.sum is not None:
            _result["sum"] = self.sum.to_dict()
        elif self.gauge is not None:
            _result["gauge"] = self.gauge.to_dict()
        return _result

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
        _args: dict[str, Any] = {}

        if (_value := data.get("name")) is not None:
            _args["name"] = _value
        if (_value := data.get("description")) is not None:
            _args["description"] = _value
        if (_value := data.get("unit")) is not None:
            _args["unit"] = _value
        if (_value := data.get("metadata")) is not None:
            _args["metadata"] = _utils.deserialize_repeated(_value, lambda _v: opentelemetry.proto_json.common.v1.common.KeyValue.from_dict(_v))
        if (_value := data.get("summary")) is not None:
            _args["summary"] = Summary.from_dict(_value)
        elif (_value := data.get("exponentialHistogram")) is not None:
            _args["exponential_histogram"] = ExponentialHistogram.from_dict(_value)
        elif (_value := data.get("histogram")) is not None:
            _args["histogram"] = Histogram.from_dict(_value)
        elif (_value := data.get("sum")) is not None:
            _args["sum"] = Sum.from_dict(_value)
        elif (_value := data.get("gauge")) is not None:
            _args["gauge"] = Gauge.from_dict(_value)

        return cls(**_args)

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
        _result: dict[str, Any] = {}
        if self.data_points:
            _result["dataPoints"] = _utils.serialize_repeated(self.data_points, lambda _v: _v.to_dict())
        return _result

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
        _args: dict[str, Any] = {}

        if (_value := data.get("dataPoints")) is not None:
            _args["data_points"] = _utils.deserialize_repeated(_value, lambda _v: NumberDataPoint.from_dict(_v))

        return cls(**_args)

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
        _result: dict[str, Any] = {}
        if self.data_points:
            _result["dataPoints"] = _utils.serialize_repeated(self.data_points, lambda _v: _v.to_dict())
        if self.aggregation_temporality != None:
            _result["aggregationTemporality"] = int(self.aggregation_temporality)
        if self.is_monotonic != False:
            _result["isMonotonic"] = self.is_monotonic
        return _result

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
        _args: dict[str, Any] = {}

        if (_value := data.get("dataPoints")) is not None:
            _args["data_points"] = _utils.deserialize_repeated(_value, lambda _v: NumberDataPoint.from_dict(_v))
        if (_value := data.get("aggregationTemporality")) is not None:
            _args["aggregation_temporality"] = AggregationTemporality(_value)
        if (_value := data.get("isMonotonic")) is not None:
            _args["is_monotonic"] = _value

        return cls(**_args)

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
        _result: dict[str, Any] = {}
        if self.data_points:
            _result["dataPoints"] = _utils.serialize_repeated(self.data_points, lambda _v: _v.to_dict())
        if self.aggregation_temporality != None:
            _result["aggregationTemporality"] = int(self.aggregation_temporality)
        return _result

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
        _args: dict[str, Any] = {}

        if (_value := data.get("dataPoints")) is not None:
            _args["data_points"] = _utils.deserialize_repeated(_value, lambda _v: HistogramDataPoint.from_dict(_v))
        if (_value := data.get("aggregationTemporality")) is not None:
            _args["aggregation_temporality"] = AggregationTemporality(_value)

        return cls(**_args)

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
        _result: dict[str, Any] = {}
        if self.data_points:
            _result["dataPoints"] = _utils.serialize_repeated(self.data_points, lambda _v: _v.to_dict())
        if self.aggregation_temporality != None:
            _result["aggregationTemporality"] = int(self.aggregation_temporality)
        return _result

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
        _args: dict[str, Any] = {}

        if (_value := data.get("dataPoints")) is not None:
            _args["data_points"] = _utils.deserialize_repeated(_value, lambda _v: ExponentialHistogramDataPoint.from_dict(_v))
        if (_value := data.get("aggregationTemporality")) is not None:
            _args["aggregation_temporality"] = AggregationTemporality(_value)

        return cls(**_args)

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
        _result: dict[str, Any] = {}
        if self.data_points:
            _result["dataPoints"] = _utils.serialize_repeated(self.data_points, lambda _v: _v.to_dict())
        return _result

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
        _args: dict[str, Any] = {}

        if (_value := data.get("dataPoints")) is not None:
            _args["data_points"] = _utils.deserialize_repeated(_value, lambda _v: SummaryDataPoint.from_dict(_v))

        return cls(**_args)

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
    as_double: Optional[float] = None
    as_int: Optional[int] = None
    exemplars: list[Exemplar] = field(default_factory=list)
    flags: int = 0

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result: dict[str, Any] = {}
        if self.attributes:
            _result["attributes"] = _utils.serialize_repeated(self.attributes, lambda _v: _v.to_dict())
        if self.start_time_unix_nano != 0:
            _result["startTimeUnixNano"] = _utils.encode_int64(self.start_time_unix_nano)
        if self.time_unix_nano != 0:
            _result["timeUnixNano"] = _utils.encode_int64(self.time_unix_nano)
        if self.exemplars:
            _result["exemplars"] = _utils.serialize_repeated(self.exemplars, lambda _v: _v.to_dict())
        if self.flags != 0:
            _result["flags"] = self.flags
        if self.as_int is not None:
            _result["asInt"] = _utils.encode_int64(self.as_int)
        elif self.as_double is not None:
            _result["asDouble"] = _utils.encode_float(self.as_double)
        return _result

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
        _args: dict[str, Any] = {}

        if (_value := data.get("attributes")) is not None:
            _args["attributes"] = _utils.deserialize_repeated(_value, lambda _v: opentelemetry.proto_json.common.v1.common.KeyValue.from_dict(_v))
        if (_value := data.get("startTimeUnixNano")) is not None:
            _args["start_time_unix_nano"] = _utils.parse_int64(_value)
        if (_value := data.get("timeUnixNano")) is not None:
            _args["time_unix_nano"] = _utils.parse_int64(_value)
        if (_value := data.get("exemplars")) is not None:
            _args["exemplars"] = _utils.deserialize_repeated(_value, lambda _v: Exemplar.from_dict(_v))
        if (_value := data.get("flags")) is not None:
            _args["flags"] = _value
        if (_value := data.get("asInt")) is not None:
            _args["as_int"] = _utils.parse_int64(_value)
        elif (_value := data.get("asDouble")) is not None:
            _args["as_double"] = _utils.parse_float(_value)

        return cls(**_args)

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
        _result: dict[str, Any] = {}
        if self.attributes:
            _result["attributes"] = _utils.serialize_repeated(self.attributes, lambda _v: _v.to_dict())
        if self.start_time_unix_nano != 0:
            _result["startTimeUnixNano"] = _utils.encode_int64(self.start_time_unix_nano)
        if self.time_unix_nano != 0:
            _result["timeUnixNano"] = _utils.encode_int64(self.time_unix_nano)
        if self.count != 0:
            _result["count"] = _utils.encode_int64(self.count)
        if self.sum != 0.0:
            _result["sum"] = _utils.encode_float(self.sum)
        if self.bucket_counts:
            _result["bucketCounts"] = _utils.serialize_repeated(self.bucket_counts, lambda _v: _utils.encode_int64(_v))
        if self.explicit_bounds:
            _result["explicitBounds"] = _utils.serialize_repeated(self.explicit_bounds, lambda _v: _utils.encode_float(_v))
        if self.exemplars:
            _result["exemplars"] = _utils.serialize_repeated(self.exemplars, lambda _v: _v.to_dict())
        if self.flags != 0:
            _result["flags"] = self.flags
        if self.min != 0.0:
            _result["min"] = _utils.encode_float(self.min)
        if self.max != 0.0:
            _result["max"] = _utils.encode_float(self.max)
        return _result

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
        _args: dict[str, Any] = {}

        if (_value := data.get("attributes")) is not None:
            _args["attributes"] = _utils.deserialize_repeated(_value, lambda _v: opentelemetry.proto_json.common.v1.common.KeyValue.from_dict(_v))
        if (_value := data.get("startTimeUnixNano")) is not None:
            _args["start_time_unix_nano"] = _utils.parse_int64(_value)
        if (_value := data.get("timeUnixNano")) is not None:
            _args["time_unix_nano"] = _utils.parse_int64(_value)
        if (_value := data.get("count")) is not None:
            _args["count"] = _utils.parse_int64(_value)
        if (_value := data.get("sum")) is not None:
            _args["sum"] = _utils.parse_float(_value)
        if (_value := data.get("bucketCounts")) is not None:
            _args["bucket_counts"] = _utils.deserialize_repeated(_value, lambda _v: _utils.parse_int64(_v))
        if (_value := data.get("explicitBounds")) is not None:
            _args["explicit_bounds"] = _utils.deserialize_repeated(_value, lambda _v: _utils.parse_float(_v))
        if (_value := data.get("exemplars")) is not None:
            _args["exemplars"] = _utils.deserialize_repeated(_value, lambda _v: Exemplar.from_dict(_v))
        if (_value := data.get("flags")) is not None:
            _args["flags"] = _value
        if (_value := data.get("min")) is not None:
            _args["min"] = _utils.parse_float(_value)
        if (_value := data.get("max")) is not None:
            _args["max"] = _utils.parse_float(_value)

        return cls(**_args)

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
            _result: dict[str, Any] = {}
            if self.offset != 0:
                _result["offset"] = self.offset
            if self.bucket_counts:
                _result["bucketCounts"] = _utils.serialize_repeated(self.bucket_counts, lambda _v: _utils.encode_int64(_v))
            return _result

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
            _args: dict[str, Any] = {}

            if (_value := data.get("offset")) is not None:
                _args["offset"] = _value
            if (_value := data.get("bucketCounts")) is not None:
                _args["bucket_counts"] = _utils.deserialize_repeated(_value, lambda _v: _utils.parse_int64(_v))

            return cls(**_args)

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
        _result: dict[str, Any] = {}
        if self.attributes:
            _result["attributes"] = _utils.serialize_repeated(self.attributes, lambda _v: _v.to_dict())
        if self.start_time_unix_nano != 0:
            _result["startTimeUnixNano"] = _utils.encode_int64(self.start_time_unix_nano)
        if self.time_unix_nano != 0:
            _result["timeUnixNano"] = _utils.encode_int64(self.time_unix_nano)
        if self.count != 0:
            _result["count"] = _utils.encode_int64(self.count)
        if self.sum != 0.0:
            _result["sum"] = _utils.encode_float(self.sum)
        if self.scale != 0:
            _result["scale"] = self.scale
        if self.zero_count != 0:
            _result["zeroCount"] = _utils.encode_int64(self.zero_count)
        if self.positive is not None:
            _result["positive"] = self.positive.to_dict()
        if self.negative is not None:
            _result["negative"] = self.negative.to_dict()
        if self.flags != 0:
            _result["flags"] = self.flags
        if self.exemplars:
            _result["exemplars"] = _utils.serialize_repeated(self.exemplars, lambda _v: _v.to_dict())
        if self.min != 0.0:
            _result["min"] = _utils.encode_float(self.min)
        if self.max != 0.0:
            _result["max"] = _utils.encode_float(self.max)
        if self.zero_threshold != 0.0:
            _result["zeroThreshold"] = _utils.encode_float(self.zero_threshold)
        return _result

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
        _args: dict[str, Any] = {}

        if (_value := data.get("attributes")) is not None:
            _args["attributes"] = _utils.deserialize_repeated(_value, lambda _v: opentelemetry.proto_json.common.v1.common.KeyValue.from_dict(_v))
        if (_value := data.get("startTimeUnixNano")) is not None:
            _args["start_time_unix_nano"] = _utils.parse_int64(_value)
        if (_value := data.get("timeUnixNano")) is not None:
            _args["time_unix_nano"] = _utils.parse_int64(_value)
        if (_value := data.get("count")) is not None:
            _args["count"] = _utils.parse_int64(_value)
        if (_value := data.get("sum")) is not None:
            _args["sum"] = _utils.parse_float(_value)
        if (_value := data.get("scale")) is not None:
            _args["scale"] = _value
        if (_value := data.get("zeroCount")) is not None:
            _args["zero_count"] = _utils.parse_int64(_value)
        if (_value := data.get("positive")) is not None:
            _args["positive"] = ExponentialHistogramDataPoint.Buckets.from_dict(_value)
        if (_value := data.get("negative")) is not None:
            _args["negative"] = ExponentialHistogramDataPoint.Buckets.from_dict(_value)
        if (_value := data.get("flags")) is not None:
            _args["flags"] = _value
        if (_value := data.get("exemplars")) is not None:
            _args["exemplars"] = _utils.deserialize_repeated(_value, lambda _v: Exemplar.from_dict(_v))
        if (_value := data.get("min")) is not None:
            _args["min"] = _utils.parse_float(_value)
        if (_value := data.get("max")) is not None:
            _args["max"] = _utils.parse_float(_value)
        if (_value := data.get("zeroThreshold")) is not None:
            _args["zero_threshold"] = _utils.parse_float(_value)

        return cls(**_args)

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
            _result: dict[str, Any] = {}
            if self.quantile != 0.0:
                _result["quantile"] = _utils.encode_float(self.quantile)
            if self.value != 0.0:
                _result["value"] = _utils.encode_float(self.value)
            return _result

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
            _args: dict[str, Any] = {}

            if (_value := data.get("quantile")) is not None:
                _args["quantile"] = _utils.parse_float(_value)
            if (_value := data.get("value")) is not None:
                _args["value"] = _utils.parse_float(_value)

            return cls(**_args)

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
        _result: dict[str, Any] = {}
        if self.attributes:
            _result["attributes"] = _utils.serialize_repeated(self.attributes, lambda _v: _v.to_dict())
        if self.start_time_unix_nano != 0:
            _result["startTimeUnixNano"] = _utils.encode_int64(self.start_time_unix_nano)
        if self.time_unix_nano != 0:
            _result["timeUnixNano"] = _utils.encode_int64(self.time_unix_nano)
        if self.count != 0:
            _result["count"] = _utils.encode_int64(self.count)
        if self.sum != 0.0:
            _result["sum"] = _utils.encode_float(self.sum)
        if self.quantile_values:
            _result["quantileValues"] = _utils.serialize_repeated(self.quantile_values, lambda _v: _v.to_dict())
        if self.flags != 0:
            _result["flags"] = self.flags
        return _result

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
        _args: dict[str, Any] = {}

        if (_value := data.get("attributes")) is not None:
            _args["attributes"] = _utils.deserialize_repeated(_value, lambda _v: opentelemetry.proto_json.common.v1.common.KeyValue.from_dict(_v))
        if (_value := data.get("startTimeUnixNano")) is not None:
            _args["start_time_unix_nano"] = _utils.parse_int64(_value)
        if (_value := data.get("timeUnixNano")) is not None:
            _args["time_unix_nano"] = _utils.parse_int64(_value)
        if (_value := data.get("count")) is not None:
            _args["count"] = _utils.parse_int64(_value)
        if (_value := data.get("sum")) is not None:
            _args["sum"] = _utils.parse_float(_value)
        if (_value := data.get("quantileValues")) is not None:
            _args["quantile_values"] = _utils.deserialize_repeated(_value, lambda _v: SummaryDataPoint.ValueAtQuantile.from_dict(_v))
        if (_value := data.get("flags")) is not None:
            _args["flags"] = _value

        return cls(**_args)

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
    as_double: Optional[float] = None
    as_int: Optional[int] = None
    span_id: bytes = b''
    trace_id: bytes = b''

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.
        
        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result: dict[str, Any] = {}
        if self.filtered_attributes:
            _result["filteredAttributes"] = _utils.serialize_repeated(self.filtered_attributes, lambda _v: _v.to_dict())
        if self.time_unix_nano != 0:
            _result["timeUnixNano"] = _utils.encode_int64(self.time_unix_nano)
        if self.span_id != b'':
            _result["spanId"] = _utils.encode_hex(self.span_id)
        if self.trace_id != b'':
            _result["traceId"] = _utils.encode_hex(self.trace_id)
        if self.as_int is not None:
            _result["asInt"] = _utils.encode_int64(self.as_int)
        elif self.as_double is not None:
            _result["asDouble"] = _utils.encode_float(self.as_double)
        return _result

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
        _args: dict[str, Any] = {}

        if (_value := data.get("filteredAttributes")) is not None:
            _args["filtered_attributes"] = _utils.deserialize_repeated(_value, lambda _v: opentelemetry.proto_json.common.v1.common.KeyValue.from_dict(_v))
        if (_value := data.get("timeUnixNano")) is not None:
            _args["time_unix_nano"] = _utils.parse_int64(_value)
        if (_value := data.get("spanId")) is not None:
            _args["span_id"] = _utils.decode_hex(_value)
        if (_value := data.get("traceId")) is not None:
            _args["trace_id"] = _utils.decode_hex(_value)
        if (_value := data.get("asInt")) is not None:
            _args["as_int"] = _utils.parse_int64(_value)
        elif (_value := data.get("asDouble")) is not None:
            _args["as_double"] = _utils.parse_float(_value)

        return cls(**_args)

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