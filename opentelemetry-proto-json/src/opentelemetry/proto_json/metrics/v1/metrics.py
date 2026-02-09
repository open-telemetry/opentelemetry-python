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

import builtins
import dataclasses
import enum
import functools
import json
import sys
import typing

if sys.version_info >= (3, 10):
    _dataclass = functools.partial(dataclasses.dataclass, slots=True)
else:
    _dataclass = dataclasses.dataclass

import opentelemetry.proto_json._otlp_json_utils as _utils
import opentelemetry.proto_json.common.v1.common
import opentelemetry.proto_json.resource.v1.resource


@typing.final
class AggregationTemporality(enum.IntEnum):
    """
    Generated from protobuf enum AggregationTemporality
    """

    AGGREGATION_TEMPORALITY_UNSPECIFIED = 0
    AGGREGATION_TEMPORALITY_DELTA = 1
    AGGREGATION_TEMPORALITY_CUMULATIVE = 2

@typing.final
class DataPointFlags(enum.IntEnum):
    """
    Generated from protobuf enum DataPointFlags
    """

    DATA_POINT_FLAGS_DO_NOT_USE = 0
    DATA_POINT_FLAGS_NO_RECORDED_VALUE_MASK = 1

@typing.final
@_dataclass
class MetricsData:
    """
    Generated from protobuf message MetricsData
    """

    resource_metrics: builtins.list[ResourceMetrics] = dataclasses.field(default_factory=builtins.list)

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.resource_metrics:
            _result["resourceMetrics"] = _utils.serialize_repeated(self.resource_metrics, lambda _v: _v.to_dict())
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "MetricsData":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            MetricsData instance
        """
        _utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("resourceMetrics")) is not None:
            _args["resource_metrics"] = _utils.deserialize_repeated(_value, lambda _v: ResourceMetrics.from_dict(_v), "resource_metrics")

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "MetricsData":
        """
        Deserialize from a JSON string or bytes.

        Args:
            data: JSON string or bytes

        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@typing.final
@_dataclass
class ResourceMetrics:
    """
    Generated from protobuf message ResourceMetrics
    """

    resource: typing.Optional[opentelemetry.proto_json.resource.v1.resource.Resource] = None
    scope_metrics: builtins.list[ScopeMetrics] = dataclasses.field(default_factory=builtins.list)
    schema_url: typing.Optional[builtins.str] = ""

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.resource:
            _result["resource"] = self.resource.to_dict()
        if self.scope_metrics:
            _result["scopeMetrics"] = _utils.serialize_repeated(self.scope_metrics, lambda _v: _v.to_dict())
        if self.schema_url:
            _result["schemaUrl"] = self.schema_url
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "ResourceMetrics":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            ResourceMetrics instance
        """
        _utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("resource")) is not None:
            _args["resource"] = opentelemetry.proto_json.resource.v1.resource.Resource.from_dict(_value)
        if (_value := data.get("scopeMetrics")) is not None:
            _args["scope_metrics"] = _utils.deserialize_repeated(_value, lambda _v: ScopeMetrics.from_dict(_v), "scope_metrics")
        if (_value := data.get("schemaUrl")) is not None:
            _utils.validate_type(_value, builtins.str, "schema_url")
            _args["schema_url"] = _value

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "ResourceMetrics":
        """
        Deserialize from a JSON string or bytes.

        Args:
            data: JSON string or bytes

        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@typing.final
@_dataclass
class ScopeMetrics:
    """
    Generated from protobuf message ScopeMetrics
    """

    scope: typing.Optional[opentelemetry.proto_json.common.v1.common.InstrumentationScope] = None
    metrics: builtins.list[Metric] = dataclasses.field(default_factory=builtins.list)
    schema_url: typing.Optional[builtins.str] = ""

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.scope:
            _result["scope"] = self.scope.to_dict()
        if self.metrics:
            _result["metrics"] = _utils.serialize_repeated(self.metrics, lambda _v: _v.to_dict())
        if self.schema_url:
            _result["schemaUrl"] = self.schema_url
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "ScopeMetrics":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            ScopeMetrics instance
        """
        _utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("scope")) is not None:
            _args["scope"] = opentelemetry.proto_json.common.v1.common.InstrumentationScope.from_dict(_value)
        if (_value := data.get("metrics")) is not None:
            _args["metrics"] = _utils.deserialize_repeated(_value, lambda _v: Metric.from_dict(_v), "metrics")
        if (_value := data.get("schemaUrl")) is not None:
            _utils.validate_type(_value, builtins.str, "schema_url")
            _args["schema_url"] = _value

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "ScopeMetrics":
        """
        Deserialize from a JSON string or bytes.

        Args:
            data: JSON string or bytes

        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@typing.final
@_dataclass
class Metric:
    """
    Generated from protobuf message Metric
    """

    name: typing.Optional[builtins.str] = ""
    description: typing.Optional[builtins.str] = ""
    unit: typing.Optional[builtins.str] = ""
    gauge: typing.Optional[Gauge] = None
    sum: typing.Optional[Sum] = None
    histogram: typing.Optional[Histogram] = None
    exponential_histogram: typing.Optional[ExponentialHistogram] = None
    summary: typing.Optional[Summary] = None
    metadata: builtins.list[opentelemetry.proto_json.common.v1.common.KeyValue] = dataclasses.field(default_factory=builtins.list)

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.name:
            _result["name"] = self.name
        if self.description:
            _result["description"] = self.description
        if self.unit:
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

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "Metric":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            Metric instance
        """
        _utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("name")) is not None:
            _utils.validate_type(_value, builtins.str, "name")
            _args["name"] = _value
        if (_value := data.get("description")) is not None:
            _utils.validate_type(_value, builtins.str, "description")
            _args["description"] = _value
        if (_value := data.get("unit")) is not None:
            _utils.validate_type(_value, builtins.str, "unit")
            _args["unit"] = _value
        if (_value := data.get("metadata")) is not None:
            _args["metadata"] = _utils.deserialize_repeated(_value, lambda _v: opentelemetry.proto_json.common.v1.common.KeyValue.from_dict(_v), "metadata")
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

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "Metric":
        """
        Deserialize from a JSON string or bytes.

        Args:
            data: JSON string or bytes

        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@typing.final
@_dataclass
class Gauge:
    """
    Generated from protobuf message Gauge
    """

    data_points: builtins.list[NumberDataPoint] = dataclasses.field(default_factory=builtins.list)

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.data_points:
            _result["dataPoints"] = _utils.serialize_repeated(self.data_points, lambda _v: _v.to_dict())
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "Gauge":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            Gauge instance
        """
        _utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("dataPoints")) is not None:
            _args["data_points"] = _utils.deserialize_repeated(_value, lambda _v: NumberDataPoint.from_dict(_v), "data_points")

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "Gauge":
        """
        Deserialize from a JSON string or bytes.

        Args:
            data: JSON string or bytes

        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@typing.final
@_dataclass
class Sum:
    """
    Generated from protobuf message Sum
    """

    data_points: builtins.list[NumberDataPoint] = dataclasses.field(default_factory=builtins.list)
    aggregation_temporality: typing.Union[AggregationTemporality, builtins.int, None] = 0
    is_monotonic: typing.Optional[builtins.bool] = False

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.data_points:
            _result["dataPoints"] = _utils.serialize_repeated(self.data_points, lambda _v: _v.to_dict())
        if self.aggregation_temporality:
            _result["aggregationTemporality"] = builtins.int(self.aggregation_temporality)
        if self.is_monotonic:
            _result["isMonotonic"] = self.is_monotonic
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "Sum":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            Sum instance
        """
        _utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("dataPoints")) is not None:
            _args["data_points"] = _utils.deserialize_repeated(_value, lambda _v: NumberDataPoint.from_dict(_v), "data_points")
        if (_value := data.get("aggregationTemporality")) is not None:
            _utils.validate_type(_value, builtins.int, "aggregation_temporality")
            _args["aggregation_temporality"] = AggregationTemporality(_value)
        if (_value := data.get("isMonotonic")) is not None:
            _utils.validate_type(_value, builtins.bool, "is_monotonic")
            _args["is_monotonic"] = _value

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "Sum":
        """
        Deserialize from a JSON string or bytes.

        Args:
            data: JSON string or bytes

        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@typing.final
@_dataclass
class Histogram:
    """
    Generated from protobuf message Histogram
    """

    data_points: builtins.list[HistogramDataPoint] = dataclasses.field(default_factory=builtins.list)
    aggregation_temporality: typing.Union[AggregationTemporality, builtins.int, None] = 0

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.data_points:
            _result["dataPoints"] = _utils.serialize_repeated(self.data_points, lambda _v: _v.to_dict())
        if self.aggregation_temporality:
            _result["aggregationTemporality"] = builtins.int(self.aggregation_temporality)
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "Histogram":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            Histogram instance
        """
        _utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("dataPoints")) is not None:
            _args["data_points"] = _utils.deserialize_repeated(_value, lambda _v: HistogramDataPoint.from_dict(_v), "data_points")
        if (_value := data.get("aggregationTemporality")) is not None:
            _utils.validate_type(_value, builtins.int, "aggregation_temporality")
            _args["aggregation_temporality"] = AggregationTemporality(_value)

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "Histogram":
        """
        Deserialize from a JSON string or bytes.

        Args:
            data: JSON string or bytes

        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@typing.final
@_dataclass
class ExponentialHistogram:
    """
    Generated from protobuf message ExponentialHistogram
    """

    data_points: builtins.list[ExponentialHistogramDataPoint] = dataclasses.field(default_factory=builtins.list)
    aggregation_temporality: typing.Union[AggregationTemporality, builtins.int, None] = 0

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.data_points:
            _result["dataPoints"] = _utils.serialize_repeated(self.data_points, lambda _v: _v.to_dict())
        if self.aggregation_temporality:
            _result["aggregationTemporality"] = builtins.int(self.aggregation_temporality)
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "ExponentialHistogram":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            ExponentialHistogram instance
        """
        _utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("dataPoints")) is not None:
            _args["data_points"] = _utils.deserialize_repeated(_value, lambda _v: ExponentialHistogramDataPoint.from_dict(_v), "data_points")
        if (_value := data.get("aggregationTemporality")) is not None:
            _utils.validate_type(_value, builtins.int, "aggregation_temporality")
            _args["aggregation_temporality"] = AggregationTemporality(_value)

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "ExponentialHistogram":
        """
        Deserialize from a JSON string or bytes.

        Args:
            data: JSON string or bytes

        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@typing.final
@_dataclass
class Summary:
    """
    Generated from protobuf message Summary
    """

    data_points: builtins.list[SummaryDataPoint] = dataclasses.field(default_factory=builtins.list)

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.data_points:
            _result["dataPoints"] = _utils.serialize_repeated(self.data_points, lambda _v: _v.to_dict())
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "Summary":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            Summary instance
        """
        _utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("dataPoints")) is not None:
            _args["data_points"] = _utils.deserialize_repeated(_value, lambda _v: SummaryDataPoint.from_dict(_v), "data_points")

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "Summary":
        """
        Deserialize from a JSON string or bytes.

        Args:
            data: JSON string or bytes

        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@typing.final
@_dataclass
class NumberDataPoint:
    """
    Generated from protobuf message NumberDataPoint
    """

    attributes: builtins.list[opentelemetry.proto_json.common.v1.common.KeyValue] = dataclasses.field(default_factory=builtins.list)
    start_time_unix_nano: typing.Optional[builtins.int] = 0
    time_unix_nano: typing.Optional[builtins.int] = 0
    as_double: typing.Optional[builtins.float] = None
    as_int: typing.Optional[builtins.int] = None
    exemplars: builtins.list[Exemplar] = dataclasses.field(default_factory=builtins.list)
    flags: typing.Optional[builtins.int] = 0

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.attributes:
            _result["attributes"] = _utils.serialize_repeated(self.attributes, lambda _v: _v.to_dict())
        if self.start_time_unix_nano:
            _result["startTimeUnixNano"] = _utils.encode_int64(self.start_time_unix_nano)
        if self.time_unix_nano:
            _result["timeUnixNano"] = _utils.encode_int64(self.time_unix_nano)
        if self.exemplars:
            _result["exemplars"] = _utils.serialize_repeated(self.exemplars, lambda _v: _v.to_dict())
        if self.flags:
            _result["flags"] = self.flags
        if self.as_int is not None:
            _result["asInt"] = _utils.encode_int64(self.as_int)
        elif self.as_double is not None:
            _result["asDouble"] = _utils.encode_float(self.as_double)
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "NumberDataPoint":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            NumberDataPoint instance
        """
        _utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("attributes")) is not None:
            _args["attributes"] = _utils.deserialize_repeated(_value, lambda _v: opentelemetry.proto_json.common.v1.common.KeyValue.from_dict(_v), "attributes")
        if (_value := data.get("startTimeUnixNano")) is not None:
            _args["start_time_unix_nano"] = _utils.parse_int64(_value, "start_time_unix_nano")
        if (_value := data.get("timeUnixNano")) is not None:
            _args["time_unix_nano"] = _utils.parse_int64(_value, "time_unix_nano")
        if (_value := data.get("exemplars")) is not None:
            _args["exemplars"] = _utils.deserialize_repeated(_value, lambda _v: Exemplar.from_dict(_v), "exemplars")
        if (_value := data.get("flags")) is not None:
            _utils.validate_type(_value, builtins.int, "flags")
            _args["flags"] = _value
        if (_value := data.get("asInt")) is not None:
            _args["as_int"] = _utils.parse_int64(_value, "as_int")
        elif (_value := data.get("asDouble")) is not None:
            _args["as_double"] = _utils.parse_float(_value, "as_double")

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "NumberDataPoint":
        """
        Deserialize from a JSON string or bytes.

        Args:
            data: JSON string or bytes

        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@typing.final
@_dataclass
class HistogramDataPoint:
    """
    Generated from protobuf message HistogramDataPoint
    """

    attributes: builtins.list[opentelemetry.proto_json.common.v1.common.KeyValue] = dataclasses.field(default_factory=builtins.list)
    start_time_unix_nano: typing.Optional[builtins.int] = 0
    time_unix_nano: typing.Optional[builtins.int] = 0
    count: typing.Optional[builtins.int] = 0
    sum: typing.Optional[builtins.float] = None
    bucket_counts: builtins.list[builtins.int] = dataclasses.field(default_factory=builtins.list)
    explicit_bounds: builtins.list[builtins.float] = dataclasses.field(default_factory=builtins.list)
    exemplars: builtins.list[Exemplar] = dataclasses.field(default_factory=builtins.list)
    flags: typing.Optional[builtins.int] = 0
    min: typing.Optional[builtins.float] = None
    max: typing.Optional[builtins.float] = None

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.attributes:
            _result["attributes"] = _utils.serialize_repeated(self.attributes, lambda _v: _v.to_dict())
        if self.start_time_unix_nano:
            _result["startTimeUnixNano"] = _utils.encode_int64(self.start_time_unix_nano)
        if self.time_unix_nano:
            _result["timeUnixNano"] = _utils.encode_int64(self.time_unix_nano)
        if self.count:
            _result["count"] = _utils.encode_int64(self.count)
        if self.sum:
            _result["sum"] = _utils.encode_float(self.sum)
        if self.bucket_counts:
            _result["bucketCounts"] = _utils.serialize_repeated(self.bucket_counts, lambda _v: _utils.encode_int64(_v))
        if self.explicit_bounds:
            _result["explicitBounds"] = _utils.serialize_repeated(self.explicit_bounds, lambda _v: _utils.encode_float(_v))
        if self.exemplars:
            _result["exemplars"] = _utils.serialize_repeated(self.exemplars, lambda _v: _v.to_dict())
        if self.flags:
            _result["flags"] = self.flags
        if self.min:
            _result["min"] = _utils.encode_float(self.min)
        if self.max:
            _result["max"] = _utils.encode_float(self.max)
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "HistogramDataPoint":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            HistogramDataPoint instance
        """
        _utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("attributes")) is not None:
            _args["attributes"] = _utils.deserialize_repeated(_value, lambda _v: opentelemetry.proto_json.common.v1.common.KeyValue.from_dict(_v), "attributes")
        if (_value := data.get("startTimeUnixNano")) is not None:
            _args["start_time_unix_nano"] = _utils.parse_int64(_value, "start_time_unix_nano")
        if (_value := data.get("timeUnixNano")) is not None:
            _args["time_unix_nano"] = _utils.parse_int64(_value, "time_unix_nano")
        if (_value := data.get("count")) is not None:
            _args["count"] = _utils.parse_int64(_value, "count")
        if (_value := data.get("sum")) is not None:
            _args["sum"] = _utils.parse_float(_value, "sum")
        if (_value := data.get("bucketCounts")) is not None:
            _args["bucket_counts"] = _utils.deserialize_repeated(_value, lambda _v: _utils.parse_int64(_v, "bucket_counts"), "bucket_counts")
        if (_value := data.get("explicitBounds")) is not None:
            _args["explicit_bounds"] = _utils.deserialize_repeated(_value, lambda _v: _utils.parse_float(_v, "explicit_bounds"), "explicit_bounds")
        if (_value := data.get("exemplars")) is not None:
            _args["exemplars"] = _utils.deserialize_repeated(_value, lambda _v: Exemplar.from_dict(_v), "exemplars")
        if (_value := data.get("flags")) is not None:
            _utils.validate_type(_value, builtins.int, "flags")
            _args["flags"] = _value
        if (_value := data.get("min")) is not None:
            _args["min"] = _utils.parse_float(_value, "min")
        if (_value := data.get("max")) is not None:
            _args["max"] = _utils.parse_float(_value, "max")

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "HistogramDataPoint":
        """
        Deserialize from a JSON string or bytes.

        Args:
            data: JSON string or bytes

        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@typing.final
@_dataclass
class ExponentialHistogramDataPoint:
    """
    Generated from protobuf message ExponentialHistogramDataPoint
    """

    @typing.final
    @_dataclass
    class Buckets:
        """
        Generated from protobuf message Buckets
        """

        offset: typing.Optional[builtins.int] = 0
        bucket_counts: builtins.list[builtins.int] = dataclasses.field(default_factory=builtins.list)

        def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
            """
            Convert this message to a dictionary with lowerCamelCase keys.

            Returns:
                Dictionary representation following OTLP JSON encoding
            """
            _result = {}
            if self.offset:
                _result["offset"] = self.offset
            if self.bucket_counts:
                _result["bucketCounts"] = _utils.serialize_repeated(self.bucket_counts, lambda _v: _utils.encode_int64(_v))
            return _result

        def to_json(self) -> builtins.str:
            """
            Serialize this message to a JSON string.

            Returns:
                JSON string
            """
            return json.dumps(self.to_dict())

        @builtins.classmethod
        def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "ExponentialHistogramDataPoint.Buckets":
            """
            Create from a dictionary with lowerCamelCase keys.

            Args:
                data: Dictionary representation following OTLP JSON encoding

            Returns:
                Buckets instance
            """
            _utils.validate_type(data, builtins.dict, "data")
            _args = {}

            if (_value := data.get("offset")) is not None:
                _utils.validate_type(_value, builtins.int, "offset")
                _args["offset"] = _value
            if (_value := data.get("bucketCounts")) is not None:
                _args["bucket_counts"] = _utils.deserialize_repeated(_value, lambda _v: _utils.parse_int64(_v, "bucket_counts"), "bucket_counts")

            return cls(**_args)

        @builtins.classmethod
        def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "ExponentialHistogramDataPoint.Buckets":
            """
            Deserialize from a JSON string or bytes.

            Args:
                data: JSON string or bytes

            Returns:
                Instance of the class
            """
            return cls.from_dict(json.loads(data))

    attributes: builtins.list[opentelemetry.proto_json.common.v1.common.KeyValue] = dataclasses.field(default_factory=builtins.list)
    start_time_unix_nano: typing.Optional[builtins.int] = 0
    time_unix_nano: typing.Optional[builtins.int] = 0
    count: typing.Optional[builtins.int] = 0
    sum: typing.Optional[builtins.float] = None
    scale: typing.Optional[builtins.int] = 0
    zero_count: typing.Optional[builtins.int] = 0
    positive: typing.Optional[ExponentialHistogramDataPoint.Buckets] = None
    negative: typing.Optional[ExponentialHistogramDataPoint.Buckets] = None
    flags: typing.Optional[builtins.int] = 0
    exemplars: builtins.list[Exemplar] = dataclasses.field(default_factory=builtins.list)
    min: typing.Optional[builtins.float] = None
    max: typing.Optional[builtins.float] = None
    zero_threshold: typing.Optional[builtins.float] = 0.0

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.attributes:
            _result["attributes"] = _utils.serialize_repeated(self.attributes, lambda _v: _v.to_dict())
        if self.start_time_unix_nano:
            _result["startTimeUnixNano"] = _utils.encode_int64(self.start_time_unix_nano)
        if self.time_unix_nano:
            _result["timeUnixNano"] = _utils.encode_int64(self.time_unix_nano)
        if self.count:
            _result["count"] = _utils.encode_int64(self.count)
        if self.sum:
            _result["sum"] = _utils.encode_float(self.sum)
        if self.scale:
            _result["scale"] = self.scale
        if self.zero_count:
            _result["zeroCount"] = _utils.encode_int64(self.zero_count)
        if self.positive:
            _result["positive"] = self.positive.to_dict()
        if self.negative:
            _result["negative"] = self.negative.to_dict()
        if self.flags:
            _result["flags"] = self.flags
        if self.exemplars:
            _result["exemplars"] = _utils.serialize_repeated(self.exemplars, lambda _v: _v.to_dict())
        if self.min:
            _result["min"] = _utils.encode_float(self.min)
        if self.max:
            _result["max"] = _utils.encode_float(self.max)
        if self.zero_threshold:
            _result["zeroThreshold"] = _utils.encode_float(self.zero_threshold)
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "ExponentialHistogramDataPoint":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            ExponentialHistogramDataPoint instance
        """
        _utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("attributes")) is not None:
            _args["attributes"] = _utils.deserialize_repeated(_value, lambda _v: opentelemetry.proto_json.common.v1.common.KeyValue.from_dict(_v), "attributes")
        if (_value := data.get("startTimeUnixNano")) is not None:
            _args["start_time_unix_nano"] = _utils.parse_int64(_value, "start_time_unix_nano")
        if (_value := data.get("timeUnixNano")) is not None:
            _args["time_unix_nano"] = _utils.parse_int64(_value, "time_unix_nano")
        if (_value := data.get("count")) is not None:
            _args["count"] = _utils.parse_int64(_value, "count")
        if (_value := data.get("sum")) is not None:
            _args["sum"] = _utils.parse_float(_value, "sum")
        if (_value := data.get("scale")) is not None:
            _utils.validate_type(_value, builtins.int, "scale")
            _args["scale"] = _value
        if (_value := data.get("zeroCount")) is not None:
            _args["zero_count"] = _utils.parse_int64(_value, "zero_count")
        if (_value := data.get("positive")) is not None:
            _args["positive"] = ExponentialHistogramDataPoint.Buckets.from_dict(_value)
        if (_value := data.get("negative")) is not None:
            _args["negative"] = ExponentialHistogramDataPoint.Buckets.from_dict(_value)
        if (_value := data.get("flags")) is not None:
            _utils.validate_type(_value, builtins.int, "flags")
            _args["flags"] = _value
        if (_value := data.get("exemplars")) is not None:
            _args["exemplars"] = _utils.deserialize_repeated(_value, lambda _v: Exemplar.from_dict(_v), "exemplars")
        if (_value := data.get("min")) is not None:
            _args["min"] = _utils.parse_float(_value, "min")
        if (_value := data.get("max")) is not None:
            _args["max"] = _utils.parse_float(_value, "max")
        if (_value := data.get("zeroThreshold")) is not None:
            _args["zero_threshold"] = _utils.parse_float(_value, "zero_threshold")

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "ExponentialHistogramDataPoint":
        """
        Deserialize from a JSON string or bytes.

        Args:
            data: JSON string or bytes

        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@typing.final
@_dataclass
class SummaryDataPoint:
    """
    Generated from protobuf message SummaryDataPoint
    """

    @typing.final
    @_dataclass
    class ValueAtQuantile:
        """
        Generated from protobuf message ValueAtQuantile
        """

        quantile: typing.Optional[builtins.float] = 0.0
        value: typing.Optional[builtins.float] = 0.0

        def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
            """
            Convert this message to a dictionary with lowerCamelCase keys.

            Returns:
                Dictionary representation following OTLP JSON encoding
            """
            _result = {}
            if self.quantile:
                _result["quantile"] = _utils.encode_float(self.quantile)
            if self.value:
                _result["value"] = _utils.encode_float(self.value)
            return _result

        def to_json(self) -> builtins.str:
            """
            Serialize this message to a JSON string.

            Returns:
                JSON string
            """
            return json.dumps(self.to_dict())

        @builtins.classmethod
        def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "SummaryDataPoint.ValueAtQuantile":
            """
            Create from a dictionary with lowerCamelCase keys.

            Args:
                data: Dictionary representation following OTLP JSON encoding

            Returns:
                ValueAtQuantile instance
            """
            _utils.validate_type(data, builtins.dict, "data")
            _args = {}

            if (_value := data.get("quantile")) is not None:
                _args["quantile"] = _utils.parse_float(_value, "quantile")
            if (_value := data.get("value")) is not None:
                _args["value"] = _utils.parse_float(_value, "value")

            return cls(**_args)

        @builtins.classmethod
        def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "SummaryDataPoint.ValueAtQuantile":
            """
            Deserialize from a JSON string or bytes.

            Args:
                data: JSON string or bytes

            Returns:
                Instance of the class
            """
            return cls.from_dict(json.loads(data))

    attributes: builtins.list[opentelemetry.proto_json.common.v1.common.KeyValue] = dataclasses.field(default_factory=builtins.list)
    start_time_unix_nano: typing.Optional[builtins.int] = 0
    time_unix_nano: typing.Optional[builtins.int] = 0
    count: typing.Optional[builtins.int] = 0
    sum: typing.Optional[builtins.float] = 0.0
    quantile_values: builtins.list[SummaryDataPoint.ValueAtQuantile] = dataclasses.field(default_factory=builtins.list)
    flags: typing.Optional[builtins.int] = 0

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.attributes:
            _result["attributes"] = _utils.serialize_repeated(self.attributes, lambda _v: _v.to_dict())
        if self.start_time_unix_nano:
            _result["startTimeUnixNano"] = _utils.encode_int64(self.start_time_unix_nano)
        if self.time_unix_nano:
            _result["timeUnixNano"] = _utils.encode_int64(self.time_unix_nano)
        if self.count:
            _result["count"] = _utils.encode_int64(self.count)
        if self.sum:
            _result["sum"] = _utils.encode_float(self.sum)
        if self.quantile_values:
            _result["quantileValues"] = _utils.serialize_repeated(self.quantile_values, lambda _v: _v.to_dict())
        if self.flags:
            _result["flags"] = self.flags
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "SummaryDataPoint":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            SummaryDataPoint instance
        """
        _utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("attributes")) is not None:
            _args["attributes"] = _utils.deserialize_repeated(_value, lambda _v: opentelemetry.proto_json.common.v1.common.KeyValue.from_dict(_v), "attributes")
        if (_value := data.get("startTimeUnixNano")) is not None:
            _args["start_time_unix_nano"] = _utils.parse_int64(_value, "start_time_unix_nano")
        if (_value := data.get("timeUnixNano")) is not None:
            _args["time_unix_nano"] = _utils.parse_int64(_value, "time_unix_nano")
        if (_value := data.get("count")) is not None:
            _args["count"] = _utils.parse_int64(_value, "count")
        if (_value := data.get("sum")) is not None:
            _args["sum"] = _utils.parse_float(_value, "sum")
        if (_value := data.get("quantileValues")) is not None:
            _args["quantile_values"] = _utils.deserialize_repeated(_value, lambda _v: SummaryDataPoint.ValueAtQuantile.from_dict(_v), "quantile_values")
        if (_value := data.get("flags")) is not None:
            _utils.validate_type(_value, builtins.int, "flags")
            _args["flags"] = _value

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "SummaryDataPoint":
        """
        Deserialize from a JSON string or bytes.

        Args:
            data: JSON string or bytes

        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))


@typing.final
@_dataclass
class Exemplar:
    """
    Generated from protobuf message Exemplar
    """

    filtered_attributes: builtins.list[opentelemetry.proto_json.common.v1.common.KeyValue] = dataclasses.field(default_factory=builtins.list)
    time_unix_nano: typing.Optional[builtins.int] = 0
    as_double: typing.Optional[builtins.float] = None
    as_int: typing.Optional[builtins.int] = None
    span_id: typing.Optional[builtins.bytes] = b""
    trace_id: typing.Optional[builtins.bytes] = b""

    def to_dict(self) -> builtins.dict[builtins.str, typing.Any]:
        """
        Convert this message to a dictionary with lowerCamelCase keys.

        Returns:
            Dictionary representation following OTLP JSON encoding
        """
        _result = {}
        if self.filtered_attributes:
            _result["filteredAttributes"] = _utils.serialize_repeated(self.filtered_attributes, lambda _v: _v.to_dict())
        if self.time_unix_nano:
            _result["timeUnixNano"] = _utils.encode_int64(self.time_unix_nano)
        if self.span_id:
            _result["spanId"] = _utils.encode_hex(self.span_id)
        if self.trace_id:
            _result["traceId"] = _utils.encode_hex(self.trace_id)
        if self.as_int is not None:
            _result["asInt"] = _utils.encode_int64(self.as_int)
        elif self.as_double is not None:
            _result["asDouble"] = _utils.encode_float(self.as_double)
        return _result

    def to_json(self) -> builtins.str:
        """
        Serialize this message to a JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @builtins.classmethod
    def from_dict(cls, data: builtins.dict[builtins.str, typing.Any]) -> "Exemplar":
        """
        Create from a dictionary with lowerCamelCase keys.

        Args:
            data: Dictionary representation following OTLP JSON encoding

        Returns:
            Exemplar instance
        """
        _utils.validate_type(data, builtins.dict, "data")
        _args = {}

        if (_value := data.get("filteredAttributes")) is not None:
            _args["filtered_attributes"] = _utils.deserialize_repeated(_value, lambda _v: opentelemetry.proto_json.common.v1.common.KeyValue.from_dict(_v), "filtered_attributes")
        if (_value := data.get("timeUnixNano")) is not None:
            _args["time_unix_nano"] = _utils.parse_int64(_value, "time_unix_nano")
        if (_value := data.get("spanId")) is not None:
            _args["span_id"] = _utils.decode_hex(_value, "span_id")
        if (_value := data.get("traceId")) is not None:
            _args["trace_id"] = _utils.decode_hex(_value, "trace_id")
        if (_value := data.get("asInt")) is not None:
            _args["as_int"] = _utils.parse_int64(_value, "as_int")
        elif (_value := data.get("asDouble")) is not None:
            _args["as_double"] = _utils.parse_float(_value, "as_double")

        return cls(**_args)

    @builtins.classmethod
    def from_json(cls, data: typing.Union[builtins.str, builtins.bytes]) -> "Exemplar":
        """
        Deserialize from a JSON string or bytes.

        Args:
            data: JSON string or bytes

        Returns:
            Instance of the class
        """
        return cls.from_dict(json.loads(data))
