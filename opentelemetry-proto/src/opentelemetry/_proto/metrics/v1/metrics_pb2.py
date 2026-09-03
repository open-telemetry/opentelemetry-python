# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# AUTO-GENERATED from "opentelemetry/proto/metrics/v1/metrics.proto"
# DO NOT EDIT MANUALLY
from __future__ import annotations

from enum import IntEnum
from struct import pack

from opentelemetry._proto._pyprotobuf import encode_sfixed64, encode_tag
from opentelemetry._proto._pyprotobuf.fields import WT_64BIT, bool_field, byt, dbl, fix64, msg, opt_dbl, packed_double, packed_fix64, packed_uint64, sint32, string, u64
from opentelemetry._proto._pyprotobuf.message import Message
from opentelemetry._proto.common.v1.common_pb2 import InstrumentationScope
from opentelemetry._proto.common.v1.common_pb2 import KeyValue
from opentelemetry._proto.resource.v1.resource_pb2 import Resource

class AggregationTemporality(IntEnum):
    AGGREGATION_TEMPORALITY_UNSPECIFIED = 0
    AGGREGATION_TEMPORALITY_DELTA = 1
    AGGREGATION_TEMPORALITY_CUMULATIVE = 2


class DataPointFlags(IntEnum):
    DATA_POINT_FLAGS_DO_NOT_USE = 0
    DATA_POINT_FLAGS_NO_RECORDED_VALUE_MASK = 1


class MetricsData(Message):
    def __init__(self, resource_metrics: list[ResourceMetrics] | None = None) -> None:
        self.resource_metrics = list(resource_metrics) if resource_metrics else []

    def SerializeToString(self) -> bytes:
        result = b""
        result += b"".join(msg(1, _v.SerializeToString()) for _v in self.resource_metrics)
        return result


class ResourceMetrics(Message):
    def __init__(self, resource: Resource | None = None, scope_metrics: list[ScopeMetrics] | None = None, schema_url: str | None = "") -> None:
        if isinstance(resource, dict):
            resource = Resource(**resource)
        self.resource = resource
        self.scope_metrics = list(scope_metrics) if scope_metrics else []
        self.schema_url = schema_url

    def SerializeToString(self) -> bytes:
        result = b""
        if self.resource is not None:
            result += msg(1, self.resource.SerializeToString())
        result += b"".join(msg(2, _v.SerializeToString()) for _v in self.scope_metrics)
        result += string(3, self.schema_url)
        return result


class ScopeMetrics(Message):
    def __init__(self, scope: InstrumentationScope | None = None, metrics: list[Metric] | None = None, schema_url: str | None = "") -> None:
        if isinstance(scope, dict):
            scope = InstrumentationScope(**scope)
        self.scope = scope
        self.metrics = list(metrics) if metrics else []
        self.schema_url = schema_url

    def SerializeToString(self) -> bytes:
        result = b""
        if self.scope is not None:
            result += msg(1, self.scope.SerializeToString())
        result += b"".join(msg(2, _v.SerializeToString()) for _v in self.metrics)
        result += string(3, self.schema_url)
        return result


class Metric(Message):
    def __init__(self, name: str | None = "", description: str | None = "", unit: str | None = "", gauge: Gauge | None = None, sum: Sum | None = None, histogram: Histogram | None = None, exponential_histogram: ExponentialHistogram | None = None, summary: Summary | None = None, metadata: list[KeyValue] | None = None) -> None:
        self.name = name
        self.description = description
        self.unit = unit
        self.metadata = list(metadata) if metadata else []
        self._gauge = None
        self._sum = None
        self._histogram = None
        self._exponential_histogram = None
        self._summary = None
        self._which_data = None
        if gauge is not None:
            self.gauge = gauge
        if sum is not None:
            self.sum = sum
        if histogram is not None:
            self.histogram = histogram
        if exponential_histogram is not None:
            self.exponential_histogram = exponential_histogram
        if summary is not None:
            self.summary = summary

    def _select_data(self, name, value) -> None:
        for _f in ("gauge", "sum", "histogram", "exponential_histogram", "summary",):
            setattr(self, f"_{_f}", value if _f == name else None)
        self._which_data = name

    @property
    def gauge(self):
        if self._gauge is None:
            self._select_data("gauge", Gauge())
        return self._gauge

    @gauge.setter
    def gauge(self, value) -> None:
        if value is None:
            self._gauge = None
            if self._which_data == "gauge":
                self._which_data = None
        else:
            if isinstance(value, dict):
                value = Gauge(**value)
            self._select_data("gauge", value)

    @property
    def sum(self):
        if self._sum is None:
            self._select_data("sum", Sum())
        return self._sum

    @sum.setter
    def sum(self, value) -> None:
        if value is None:
            self._sum = None
            if self._which_data == "sum":
                self._which_data = None
        else:
            if isinstance(value, dict):
                value = Sum(**value)
            self._select_data("sum", value)

    @property
    def histogram(self):
        if self._histogram is None:
            self._select_data("histogram", Histogram())
        return self._histogram

    @histogram.setter
    def histogram(self, value) -> None:
        if value is None:
            self._histogram = None
            if self._which_data == "histogram":
                self._which_data = None
        else:
            if isinstance(value, dict):
                value = Histogram(**value)
            self._select_data("histogram", value)

    @property
    def exponential_histogram(self):
        if self._exponential_histogram is None:
            self._select_data("exponential_histogram", ExponentialHistogram())
        return self._exponential_histogram

    @exponential_histogram.setter
    def exponential_histogram(self, value) -> None:
        if value is None:
            self._exponential_histogram = None
            if self._which_data == "exponential_histogram":
                self._which_data = None
        else:
            if isinstance(value, dict):
                value = ExponentialHistogram(**value)
            self._select_data("exponential_histogram", value)

    @property
    def summary(self):
        if self._summary is None:
            self._select_data("summary", Summary())
        return self._summary

    @summary.setter
    def summary(self, value) -> None:
        if value is None:
            self._summary = None
            if self._which_data == "summary":
                self._which_data = None
        else:
            if isinstance(value, dict):
                value = Summary(**value)
            self._select_data("summary", value)

    def WhichOneof(self, oneof_name: str) -> str | None:
        if oneof_name == "data":
            return self._which_data
        return None

    def SerializeToString(self) -> bytes:
        result = b""
        result += string(1, self.name)
        result += string(2, self.description)
        result += string(3, self.unit)
        if self._gauge is not None:
            result += msg(5, self._gauge.SerializeToString())
        if self._sum is not None:
            result += msg(7, self._sum.SerializeToString())
        if self._histogram is not None:
            result += msg(9, self._histogram.SerializeToString())
        if self._exponential_histogram is not None:
            result += msg(10, self._exponential_histogram.SerializeToString())
        if self._summary is not None:
            result += msg(11, self._summary.SerializeToString())
        result += b"".join(msg(12, _v.SerializeToString()) for _v in self.metadata)
        return result


class Gauge(Message):
    def __init__(self, data_points: list[NumberDataPoint] | None = None) -> None:
        self.data_points = list(data_points) if data_points else []

    def SerializeToString(self) -> bytes:
        result = b""
        result += b"".join(msg(1, _v.SerializeToString()) for _v in self.data_points)
        return result


class Sum(Message):
    def __init__(self, data_points: list[NumberDataPoint] | None = None, aggregation_temporality: AggregationTemporality | None = 0, is_monotonic: bool | None = False) -> None:
        self.data_points = list(data_points) if data_points else []
        self.aggregation_temporality = aggregation_temporality
        self.is_monotonic = is_monotonic

    def SerializeToString(self) -> bytes:
        result = b""
        result += b"".join(msg(1, _v.SerializeToString()) for _v in self.data_points)
        result += u64(2, self.aggregation_temporality)
        result += bool_field(3, self.is_monotonic)
        return result


class Histogram(Message):
    def __init__(self, data_points: list[HistogramDataPoint] | None = None, aggregation_temporality: AggregationTemporality | None = 0) -> None:
        self.data_points = list(data_points) if data_points else []
        self.aggregation_temporality = aggregation_temporality

    def SerializeToString(self) -> bytes:
        result = b""
        result += b"".join(msg(1, _v.SerializeToString()) for _v in self.data_points)
        result += u64(2, self.aggregation_temporality)
        return result


class ExponentialHistogram(Message):
    def __init__(self, data_points: list[ExponentialHistogramDataPoint] | None = None, aggregation_temporality: AggregationTemporality | None = 0) -> None:
        self.data_points = list(data_points) if data_points else []
        self.aggregation_temporality = aggregation_temporality

    def SerializeToString(self) -> bytes:
        result = b""
        result += b"".join(msg(1, _v.SerializeToString()) for _v in self.data_points)
        result += u64(2, self.aggregation_temporality)
        return result


class Summary(Message):
    def __init__(self, data_points: list[SummaryDataPoint] | None = None) -> None:
        self.data_points = list(data_points) if data_points else []

    def SerializeToString(self) -> bytes:
        result = b""
        result += b"".join(msg(1, _v.SerializeToString()) for _v in self.data_points)
        return result


class NumberDataPoint(Message):
    def __init__(self, attributes: list[KeyValue] | None = None, start_time_unix_nano: int | None = 0, time_unix_nano: int | None = 0, as_double: float | None = None, as_int: int | None = None, exemplars: list[Exemplar] | None = None, flags: int | None = 0) -> None:
        self.attributes = list(attributes) if attributes else []
        self.start_time_unix_nano = start_time_unix_nano
        self.time_unix_nano = time_unix_nano
        self.exemplars = list(exemplars) if exemplars else []
        self.flags = flags
        self._as_double = None
        self._as_int = None
        self._which_value = None
        if as_double is not None:
            self.as_double = as_double
        if as_int is not None:
            self.as_int = as_int

    def _select_value(self, name, value) -> None:
        for _f in ("as_double", "as_int",):
            setattr(self, f"_{_f}", value if _f == name else None)
        self._which_value = name

    @property
    def as_double(self):
        return self._as_double

    @as_double.setter
    def as_double(self, value) -> None:
        if value is None:
            self._as_double = None
            if self._which_value == "as_double":
                self._which_value = None
        else:
            self._select_value("as_double", value)

    @property
    def as_int(self):
        return self._as_int

    @as_int.setter
    def as_int(self, value) -> None:
        if value is not None and not -9223372036854775808 <= value < 9223372036854775808:
            raise ValueError("Value out of range for as_int: " + repr(value))
        if value is None:
            self._as_int = None
            if self._which_value == "as_int":
                self._which_value = None
        else:
            self._select_value("as_int", value)

    def WhichOneof(self, oneof_name: str) -> str | None:
        if oneof_name == "value":
            return self._which_value
        return None

    def SerializeToString(self) -> bytes:
        result = b""
        result += fix64(2, self.start_time_unix_nano)
        result += fix64(3, self.time_unix_nano)
        if self._as_double is not None:
            result += encode_tag(4, WT_64BIT) + pack("<d", self._as_double)
        result += b"".join(msg(5, _v.SerializeToString()) for _v in self.exemplars)
        if self._as_int is not None:
            result += encode_tag(6, WT_64BIT) + encode_sfixed64(self._as_int)
        result += b"".join(msg(7, _v.SerializeToString()) for _v in self.attributes)
        result += u64(8, self.flags)
        return result


class HistogramDataPoint(Message):
    def __init__(self, attributes: list[KeyValue] | None = None, start_time_unix_nano: int | None = 0, time_unix_nano: int | None = 0, count: int | None = 0, sum: float | None = None, bucket_counts: list[int] | None = None, explicit_bounds: list[float] | None = None, exemplars: list[Exemplar] | None = None, flags: int | None = 0, min: float | None = None, max: float | None = None) -> None:
        self.attributes = list(attributes) if attributes else []
        self.start_time_unix_nano = start_time_unix_nano
        self.time_unix_nano = time_unix_nano
        self.count = count
        self.sum = sum
        self.bucket_counts = list(bucket_counts) if bucket_counts else []
        self.explicit_bounds = list(explicit_bounds) if explicit_bounds else []
        self.exemplars = list(exemplars) if exemplars else []
        self.flags = flags
        self.min = min
        self.max = max

    def SerializeToString(self) -> bytes:
        result = b""
        result += fix64(2, self.start_time_unix_nano)
        result += fix64(3, self.time_unix_nano)
        result += fix64(4, self.count)
        result += opt_dbl(5, self.sum)
        result += packed_fix64(6, self.bucket_counts)
        result += packed_double(7, self.explicit_bounds)
        result += b"".join(msg(8, _v.SerializeToString()) for _v in self.exemplars)
        result += b"".join(msg(9, _v.SerializeToString()) for _v in self.attributes)
        result += u64(10, self.flags)
        result += opt_dbl(11, self.min)
        result += opt_dbl(12, self.max)
        return result


class ExponentialHistogramDataPoint(Message):
    class Buckets(Message):
        def __init__(self, offset: int | None = 0, bucket_counts: list[int] | None = None) -> None:
            self.offset = offset
            self.bucket_counts = list(bucket_counts) if bucket_counts else []

        def SerializeToString(self) -> bytes:
            result = b""
            result += sint32(1, self.offset)
            result += packed_uint64(2, self.bucket_counts)
            return result

    def __init__(self, attributes: list[KeyValue] | None = None, start_time_unix_nano: int | None = 0, time_unix_nano: int | None = 0, count: int | None = 0, sum: float | None = None, scale: int | None = 0, zero_count: int | None = 0, positive: ExponentialHistogramDataPoint.Buckets | None = None, negative: ExponentialHistogramDataPoint.Buckets | None = None, flags: int | None = 0, exemplars: list[Exemplar] | None = None, min: float | None = None, max: float | None = None, zero_threshold: float | None = 0.0) -> None:
        self.attributes = list(attributes) if attributes else []
        self.start_time_unix_nano = start_time_unix_nano
        self.time_unix_nano = time_unix_nano
        self.count = count
        self.sum = sum
        self.scale = scale
        self.zero_count = zero_count
        if isinstance(positive, dict):
            positive = ExponentialHistogramDataPoint.Buckets(**positive)
        self.positive = positive
        if isinstance(negative, dict):
            negative = ExponentialHistogramDataPoint.Buckets(**negative)
        self.negative = negative
        self.flags = flags
        self.exemplars = list(exemplars) if exemplars else []
        self.min = min
        self.max = max
        self.zero_threshold = zero_threshold

    def SerializeToString(self) -> bytes:
        result = b""
        result += b"".join(msg(1, _v.SerializeToString()) for _v in self.attributes)
        result += fix64(2, self.start_time_unix_nano)
        result += fix64(3, self.time_unix_nano)
        result += fix64(4, self.count)
        result += opt_dbl(5, self.sum)
        result += sint32(6, self.scale)
        result += fix64(7, self.zero_count)
        if self.positive is not None:
            result += msg(8, self.positive.SerializeToString())
        if self.negative is not None:
            result += msg(9, self.negative.SerializeToString())
        result += u64(10, self.flags)
        result += b"".join(msg(11, _v.SerializeToString()) for _v in self.exemplars)
        result += opt_dbl(12, self.min)
        result += opt_dbl(13, self.max)
        result += dbl(14, self.zero_threshold)
        return result


class SummaryDataPoint(Message):
    class ValueAtQuantile(Message):
        def __init__(self, quantile: float | None = 0.0, value: float | None = 0.0) -> None:
            self.quantile = quantile
            self.value = value

        def SerializeToString(self) -> bytes:
            result = b""
            result += dbl(1, self.quantile)
            result += dbl(2, self.value)
            return result

    def __init__(self, attributes: list[KeyValue] | None = None, start_time_unix_nano: int | None = 0, time_unix_nano: int | None = 0, count: int | None = 0, sum: float | None = 0.0, quantile_values: list[SummaryDataPoint.ValueAtQuantile] | None = None, flags: int | None = 0) -> None:
        self.attributes = list(attributes) if attributes else []
        self.start_time_unix_nano = start_time_unix_nano
        self.time_unix_nano = time_unix_nano
        self.count = count
        self.sum = sum
        self.quantile_values = list(quantile_values) if quantile_values else []
        self.flags = flags

    def SerializeToString(self) -> bytes:
        result = b""
        result += fix64(2, self.start_time_unix_nano)
        result += fix64(3, self.time_unix_nano)
        result += fix64(4, self.count)
        result += dbl(5, self.sum)
        result += b"".join(msg(6, _v.SerializeToString()) for _v in self.quantile_values)
        result += b"".join(msg(7, _v.SerializeToString()) for _v in self.attributes)
        result += u64(8, self.flags)
        return result


class Exemplar(Message):
    def __init__(self, filtered_attributes: list[KeyValue] | None = None, time_unix_nano: int | None = 0, as_double: float | None = None, as_int: int | None = None, span_id: bytes | None = b"", trace_id: bytes | None = b"") -> None:
        self.filtered_attributes = list(filtered_attributes) if filtered_attributes else []
        self.time_unix_nano = time_unix_nano
        self.span_id = span_id
        self.trace_id = trace_id
        self._as_double = None
        self._as_int = None
        self._which_value = None
        if as_double is not None:
            self.as_double = as_double
        if as_int is not None:
            self.as_int = as_int

    def _select_value(self, name, value) -> None:
        for _f in ("as_double", "as_int",):
            setattr(self, f"_{_f}", value if _f == name else None)
        self._which_value = name

    @property
    def as_double(self):
        return self._as_double

    @as_double.setter
    def as_double(self, value) -> None:
        if value is None:
            self._as_double = None
            if self._which_value == "as_double":
                self._which_value = None
        else:
            self._select_value("as_double", value)

    @property
    def as_int(self):
        return self._as_int

    @as_int.setter
    def as_int(self, value) -> None:
        if value is not None and not -9223372036854775808 <= value < 9223372036854775808:
            raise ValueError("Value out of range for as_int: " + repr(value))
        if value is None:
            self._as_int = None
            if self._which_value == "as_int":
                self._which_value = None
        else:
            self._select_value("as_int", value)

    def WhichOneof(self, oneof_name: str) -> str | None:
        if oneof_name == "value":
            return self._which_value
        return None

    def SerializeToString(self) -> bytes:
        result = b""
        result += fix64(2, self.time_unix_nano)
        if self._as_double is not None:
            result += encode_tag(3, WT_64BIT) + pack("<d", self._as_double)
        result += byt(4, self.span_id)
        result += byt(5, self.trace_id)
        if self._as_int is not None:
            result += encode_tag(6, WT_64BIT) + encode_sfixed64(self._as_int)
        result += b"".join(msg(7, _v.SerializeToString()) for _v in self.filtered_attributes)
        return result
AGGREGATION_TEMPORALITY_UNSPECIFIED = AggregationTemporality.AGGREGATION_TEMPORALITY_UNSPECIFIED
AGGREGATION_TEMPORALITY_DELTA = AggregationTemporality.AGGREGATION_TEMPORALITY_DELTA
AGGREGATION_TEMPORALITY_CUMULATIVE = AggregationTemporality.AGGREGATION_TEMPORALITY_CUMULATIVE

global___AggregationTemporality = AggregationTemporality

DATA_POINT_FLAGS_DO_NOT_USE = DataPointFlags.DATA_POINT_FLAGS_DO_NOT_USE
DATA_POINT_FLAGS_NO_RECORDED_VALUE_MASK = DataPointFlags.DATA_POINT_FLAGS_NO_RECORDED_VALUE_MASK

global___DataPointFlags = DataPointFlags

global___MetricsData = MetricsData
global___ResourceMetrics = ResourceMetrics
global___ScopeMetrics = ScopeMetrics
global___Metric = Metric
global___Gauge = Gauge
global___Sum = Sum
global___Histogram = Histogram
global___ExponentialHistogram = ExponentialHistogram
global___Summary = Summary
global___NumberDataPoint = NumberDataPoint
global___HistogramDataPoint = HistogramDataPoint
global___ExponentialHistogramDataPoint = ExponentialHistogramDataPoint
global___SummaryDataPoint = SummaryDataPoint
global___Exemplar = Exemplar
