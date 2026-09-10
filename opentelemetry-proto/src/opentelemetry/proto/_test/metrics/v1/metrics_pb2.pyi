from opentelemetry.proto._test.common.v1 import common_pb2 as _common_pb2
from opentelemetry.proto._test.resource.v1 import resource_pb2 as _resource_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AggregationTemporality(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    AGGREGATION_TEMPORALITY_UNSPECIFIED: _ClassVar[AggregationTemporality]
    AGGREGATION_TEMPORALITY_DELTA: _ClassVar[AggregationTemporality]
    AGGREGATION_TEMPORALITY_CUMULATIVE: _ClassVar[AggregationTemporality]

class DataPointFlags(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DATA_POINT_FLAGS_DO_NOT_USE: _ClassVar[DataPointFlags]
    DATA_POINT_FLAGS_NO_RECORDED_VALUE_MASK: _ClassVar[DataPointFlags]
AGGREGATION_TEMPORALITY_UNSPECIFIED: AggregationTemporality
AGGREGATION_TEMPORALITY_DELTA: AggregationTemporality
AGGREGATION_TEMPORALITY_CUMULATIVE: AggregationTemporality
DATA_POINT_FLAGS_DO_NOT_USE: DataPointFlags
DATA_POINT_FLAGS_NO_RECORDED_VALUE_MASK: DataPointFlags

class MetricsData(_message.Message):
    __slots__ = ("resource_metrics",)
    RESOURCE_METRICS_FIELD_NUMBER: _ClassVar[int]
    resource_metrics: _containers.RepeatedCompositeFieldContainer[ResourceMetrics]
    def __init__(self, resource_metrics: _Optional[_Iterable[_Union[ResourceMetrics, _Mapping]]] = ...) -> None: ...

class ResourceMetrics(_message.Message):
    __slots__ = ("resource", "scope_metrics", "schema_url")
    RESOURCE_FIELD_NUMBER: _ClassVar[int]
    SCOPE_METRICS_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_URL_FIELD_NUMBER: _ClassVar[int]
    resource: _resource_pb2.Resource
    scope_metrics: _containers.RepeatedCompositeFieldContainer[ScopeMetrics]
    schema_url: str
    def __init__(self, resource: _Optional[_Union[_resource_pb2.Resource, _Mapping]] = ..., scope_metrics: _Optional[_Iterable[_Union[ScopeMetrics, _Mapping]]] = ..., schema_url: _Optional[str] = ...) -> None: ...

class ScopeMetrics(_message.Message):
    __slots__ = ("scope", "metrics", "schema_url")
    SCOPE_FIELD_NUMBER: _ClassVar[int]
    METRICS_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_URL_FIELD_NUMBER: _ClassVar[int]
    scope: _common_pb2.InstrumentationScope
    metrics: _containers.RepeatedCompositeFieldContainer[Metric]
    schema_url: str
    def __init__(self, scope: _Optional[_Union[_common_pb2.InstrumentationScope, _Mapping]] = ..., metrics: _Optional[_Iterable[_Union[Metric, _Mapping]]] = ..., schema_url: _Optional[str] = ...) -> None: ...

class Metric(_message.Message):
    __slots__ = ("name", "description", "unit", "gauge", "sum", "histogram", "exponential_histogram", "summary", "metadata")
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    UNIT_FIELD_NUMBER: _ClassVar[int]
    GAUGE_FIELD_NUMBER: _ClassVar[int]
    SUM_FIELD_NUMBER: _ClassVar[int]
    HISTOGRAM_FIELD_NUMBER: _ClassVar[int]
    EXPONENTIAL_HISTOGRAM_FIELD_NUMBER: _ClassVar[int]
    SUMMARY_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    name: str
    description: str
    unit: str
    gauge: Gauge
    sum: Sum
    histogram: Histogram
    exponential_histogram: ExponentialHistogram
    summary: Summary
    metadata: _containers.RepeatedCompositeFieldContainer[_common_pb2.KeyValue]
    def __init__(self, name: _Optional[str] = ..., description: _Optional[str] = ..., unit: _Optional[str] = ..., gauge: _Optional[_Union[Gauge, _Mapping]] = ..., sum: _Optional[_Union[Sum, _Mapping]] = ..., histogram: _Optional[_Union[Histogram, _Mapping]] = ..., exponential_histogram: _Optional[_Union[ExponentialHistogram, _Mapping]] = ..., summary: _Optional[_Union[Summary, _Mapping]] = ..., metadata: _Optional[_Iterable[_Union[_common_pb2.KeyValue, _Mapping]]] = ...) -> None: ...

class Gauge(_message.Message):
    __slots__ = ("data_points",)
    DATA_POINTS_FIELD_NUMBER: _ClassVar[int]
    data_points: _containers.RepeatedCompositeFieldContainer[NumberDataPoint]
    def __init__(self, data_points: _Optional[_Iterable[_Union[NumberDataPoint, _Mapping]]] = ...) -> None: ...

class Sum(_message.Message):
    __slots__ = ("data_points", "aggregation_temporality", "is_monotonic")
    DATA_POINTS_FIELD_NUMBER: _ClassVar[int]
    AGGREGATION_TEMPORALITY_FIELD_NUMBER: _ClassVar[int]
    IS_MONOTONIC_FIELD_NUMBER: _ClassVar[int]
    data_points: _containers.RepeatedCompositeFieldContainer[NumberDataPoint]
    aggregation_temporality: AggregationTemporality
    is_monotonic: bool
    def __init__(self, data_points: _Optional[_Iterable[_Union[NumberDataPoint, _Mapping]]] = ..., aggregation_temporality: _Optional[_Union[AggregationTemporality, str]] = ..., is_monotonic: bool = ...) -> None: ...

class Histogram(_message.Message):
    __slots__ = ("data_points", "aggregation_temporality")
    DATA_POINTS_FIELD_NUMBER: _ClassVar[int]
    AGGREGATION_TEMPORALITY_FIELD_NUMBER: _ClassVar[int]
    data_points: _containers.RepeatedCompositeFieldContainer[HistogramDataPoint]
    aggregation_temporality: AggregationTemporality
    def __init__(self, data_points: _Optional[_Iterable[_Union[HistogramDataPoint, _Mapping]]] = ..., aggregation_temporality: _Optional[_Union[AggregationTemporality, str]] = ...) -> None: ...

class ExponentialHistogram(_message.Message):
    __slots__ = ("data_points", "aggregation_temporality")
    DATA_POINTS_FIELD_NUMBER: _ClassVar[int]
    AGGREGATION_TEMPORALITY_FIELD_NUMBER: _ClassVar[int]
    data_points: _containers.RepeatedCompositeFieldContainer[ExponentialHistogramDataPoint]
    aggregation_temporality: AggregationTemporality
    def __init__(self, data_points: _Optional[_Iterable[_Union[ExponentialHistogramDataPoint, _Mapping]]] = ..., aggregation_temporality: _Optional[_Union[AggregationTemporality, str]] = ...) -> None: ...

class Summary(_message.Message):
    __slots__ = ("data_points",)
    DATA_POINTS_FIELD_NUMBER: _ClassVar[int]
    data_points: _containers.RepeatedCompositeFieldContainer[SummaryDataPoint]
    def __init__(self, data_points: _Optional[_Iterable[_Union[SummaryDataPoint, _Mapping]]] = ...) -> None: ...

class NumberDataPoint(_message.Message):
    __slots__ = ("attributes", "start_time_unix_nano", "time_unix_nano", "as_double", "as_int", "exemplars", "flags")
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    START_TIME_UNIX_NANO_FIELD_NUMBER: _ClassVar[int]
    TIME_UNIX_NANO_FIELD_NUMBER: _ClassVar[int]
    AS_DOUBLE_FIELD_NUMBER: _ClassVar[int]
    AS_INT_FIELD_NUMBER: _ClassVar[int]
    EXEMPLARS_FIELD_NUMBER: _ClassVar[int]
    FLAGS_FIELD_NUMBER: _ClassVar[int]
    attributes: _containers.RepeatedCompositeFieldContainer[_common_pb2.KeyValue]
    start_time_unix_nano: int
    time_unix_nano: int
    as_double: float
    as_int: int
    exemplars: _containers.RepeatedCompositeFieldContainer[Exemplar]
    flags: int
    def __init__(self, attributes: _Optional[_Iterable[_Union[_common_pb2.KeyValue, _Mapping]]] = ..., start_time_unix_nano: _Optional[int] = ..., time_unix_nano: _Optional[int] = ..., as_double: _Optional[float] = ..., as_int: _Optional[int] = ..., exemplars: _Optional[_Iterable[_Union[Exemplar, _Mapping]]] = ..., flags: _Optional[int] = ...) -> None: ...

class HistogramDataPoint(_message.Message):
    __slots__ = ("attributes", "start_time_unix_nano", "time_unix_nano", "count", "sum", "bucket_counts", "explicit_bounds", "exemplars", "flags", "min", "max")
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    START_TIME_UNIX_NANO_FIELD_NUMBER: _ClassVar[int]
    TIME_UNIX_NANO_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    SUM_FIELD_NUMBER: _ClassVar[int]
    BUCKET_COUNTS_FIELD_NUMBER: _ClassVar[int]
    EXPLICIT_BOUNDS_FIELD_NUMBER: _ClassVar[int]
    EXEMPLARS_FIELD_NUMBER: _ClassVar[int]
    FLAGS_FIELD_NUMBER: _ClassVar[int]
    MIN_FIELD_NUMBER: _ClassVar[int]
    MAX_FIELD_NUMBER: _ClassVar[int]
    attributes: _containers.RepeatedCompositeFieldContainer[_common_pb2.KeyValue]
    start_time_unix_nano: int
    time_unix_nano: int
    count: int
    sum: float
    bucket_counts: _containers.RepeatedScalarFieldContainer[int]
    explicit_bounds: _containers.RepeatedScalarFieldContainer[float]
    exemplars: _containers.RepeatedCompositeFieldContainer[Exemplar]
    flags: int
    min: float
    max: float
    def __init__(self, attributes: _Optional[_Iterable[_Union[_common_pb2.KeyValue, _Mapping]]] = ..., start_time_unix_nano: _Optional[int] = ..., time_unix_nano: _Optional[int] = ..., count: _Optional[int] = ..., sum: _Optional[float] = ..., bucket_counts: _Optional[_Iterable[int]] = ..., explicit_bounds: _Optional[_Iterable[float]] = ..., exemplars: _Optional[_Iterable[_Union[Exemplar, _Mapping]]] = ..., flags: _Optional[int] = ..., min: _Optional[float] = ..., max: _Optional[float] = ...) -> None: ...

class ExponentialHistogramDataPoint(_message.Message):
    __slots__ = ("attributes", "start_time_unix_nano", "time_unix_nano", "count", "sum", "scale", "zero_count", "positive", "negative", "flags", "exemplars", "min", "max", "zero_threshold")
    class Buckets(_message.Message):
        __slots__ = ("offset", "bucket_counts")
        OFFSET_FIELD_NUMBER: _ClassVar[int]
        BUCKET_COUNTS_FIELD_NUMBER: _ClassVar[int]
        offset: int
        bucket_counts: _containers.RepeatedScalarFieldContainer[int]
        def __init__(self, offset: _Optional[int] = ..., bucket_counts: _Optional[_Iterable[int]] = ...) -> None: ...
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    START_TIME_UNIX_NANO_FIELD_NUMBER: _ClassVar[int]
    TIME_UNIX_NANO_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    SUM_FIELD_NUMBER: _ClassVar[int]
    SCALE_FIELD_NUMBER: _ClassVar[int]
    ZERO_COUNT_FIELD_NUMBER: _ClassVar[int]
    POSITIVE_FIELD_NUMBER: _ClassVar[int]
    NEGATIVE_FIELD_NUMBER: _ClassVar[int]
    FLAGS_FIELD_NUMBER: _ClassVar[int]
    EXEMPLARS_FIELD_NUMBER: _ClassVar[int]
    MIN_FIELD_NUMBER: _ClassVar[int]
    MAX_FIELD_NUMBER: _ClassVar[int]
    ZERO_THRESHOLD_FIELD_NUMBER: _ClassVar[int]
    attributes: _containers.RepeatedCompositeFieldContainer[_common_pb2.KeyValue]
    start_time_unix_nano: int
    time_unix_nano: int
    count: int
    sum: float
    scale: int
    zero_count: int
    positive: ExponentialHistogramDataPoint.Buckets
    negative: ExponentialHistogramDataPoint.Buckets
    flags: int
    exemplars: _containers.RepeatedCompositeFieldContainer[Exemplar]
    min: float
    max: float
    zero_threshold: float
    def __init__(self, attributes: _Optional[_Iterable[_Union[_common_pb2.KeyValue, _Mapping]]] = ..., start_time_unix_nano: _Optional[int] = ..., time_unix_nano: _Optional[int] = ..., count: _Optional[int] = ..., sum: _Optional[float] = ..., scale: _Optional[int] = ..., zero_count: _Optional[int] = ..., positive: _Optional[_Union[ExponentialHistogramDataPoint.Buckets, _Mapping]] = ..., negative: _Optional[_Union[ExponentialHistogramDataPoint.Buckets, _Mapping]] = ..., flags: _Optional[int] = ..., exemplars: _Optional[_Iterable[_Union[Exemplar, _Mapping]]] = ..., min: _Optional[float] = ..., max: _Optional[float] = ..., zero_threshold: _Optional[float] = ...) -> None: ...

class SummaryDataPoint(_message.Message):
    __slots__ = ("attributes", "start_time_unix_nano", "time_unix_nano", "count", "sum", "quantile_values", "flags")
    class ValueAtQuantile(_message.Message):
        __slots__ = ("quantile", "value")
        QUANTILE_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        quantile: float
        value: float
        def __init__(self, quantile: _Optional[float] = ..., value: _Optional[float] = ...) -> None: ...
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    START_TIME_UNIX_NANO_FIELD_NUMBER: _ClassVar[int]
    TIME_UNIX_NANO_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    SUM_FIELD_NUMBER: _ClassVar[int]
    QUANTILE_VALUES_FIELD_NUMBER: _ClassVar[int]
    FLAGS_FIELD_NUMBER: _ClassVar[int]
    attributes: _containers.RepeatedCompositeFieldContainer[_common_pb2.KeyValue]
    start_time_unix_nano: int
    time_unix_nano: int
    count: int
    sum: float
    quantile_values: _containers.RepeatedCompositeFieldContainer[SummaryDataPoint.ValueAtQuantile]
    flags: int
    def __init__(self, attributes: _Optional[_Iterable[_Union[_common_pb2.KeyValue, _Mapping]]] = ..., start_time_unix_nano: _Optional[int] = ..., time_unix_nano: _Optional[int] = ..., count: _Optional[int] = ..., sum: _Optional[float] = ..., quantile_values: _Optional[_Iterable[_Union[SummaryDataPoint.ValueAtQuantile, _Mapping]]] = ..., flags: _Optional[int] = ...) -> None: ...

class Exemplar(_message.Message):
    __slots__ = ("filtered_attributes", "time_unix_nano", "as_double", "as_int", "span_id", "trace_id")
    FILTERED_ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    TIME_UNIX_NANO_FIELD_NUMBER: _ClassVar[int]
    AS_DOUBLE_FIELD_NUMBER: _ClassVar[int]
    AS_INT_FIELD_NUMBER: _ClassVar[int]
    SPAN_ID_FIELD_NUMBER: _ClassVar[int]
    TRACE_ID_FIELD_NUMBER: _ClassVar[int]
    filtered_attributes: _containers.RepeatedCompositeFieldContainer[_common_pb2.KeyValue]
    time_unix_nano: int
    as_double: float
    as_int: int
    span_id: bytes
    trace_id: bytes
    def __init__(self, filtered_attributes: _Optional[_Iterable[_Union[_common_pb2.KeyValue, _Mapping]]] = ..., time_unix_nano: _Optional[int] = ..., as_double: _Optional[float] = ..., as_int: _Optional[int] = ..., span_id: _Optional[bytes] = ..., trace_id: _Optional[bytes] = ...) -> None: ...
