# @generated by generate_proto_mypy_stubs.py.  Do not edit!
import sys
from google.protobuf.descriptor import (
    Descriptor as google___protobuf___descriptor___Descriptor,
    EnumDescriptor as google___protobuf___descriptor___EnumDescriptor,
    FileDescriptor as google___protobuf___descriptor___FileDescriptor,
)

from google.protobuf.internal.containers import (
    RepeatedCompositeFieldContainer as google___protobuf___internal___containers___RepeatedCompositeFieldContainer,
    RepeatedScalarFieldContainer as google___protobuf___internal___containers___RepeatedScalarFieldContainer,
)

from google.protobuf.message import (
    Message as google___protobuf___message___Message,
)

from opentelemetry.proto.common.v1.common_pb2 import (
    InstrumentationLibrary as opentelemetry___proto___common___v1___common_pb2___InstrumentationLibrary,
    StringKeyValue as opentelemetry___proto___common___v1___common_pb2___StringKeyValue,
)

from opentelemetry.proto.resource.v1.resource_pb2 import (
    Resource as opentelemetry___proto___resource___v1___resource_pb2___Resource,
)

from typing import (
    Iterable as typing___Iterable,
    List as typing___List,
    NewType as typing___NewType,
    Optional as typing___Optional,
    Text as typing___Text,
    Tuple as typing___Tuple,
    Union as typing___Union,
    cast as typing___cast,
)

from typing_extensions import (
    Literal as typing_extensions___Literal,
)


builtin___bool = bool
builtin___bytes = bytes
builtin___float = float
builtin___int = int
builtin___str = str
if sys.version_info < (3,):
    builtin___buffer = buffer
    builtin___unicode = unicode


DESCRIPTOR: google___protobuf___descriptor___FileDescriptor = ...

class ResourceMetrics(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...

    @property
    def resource(self) -> opentelemetry___proto___resource___v1___resource_pb2___Resource: ...

    @property
    def instrumentation_library_metrics(self) -> google___protobuf___internal___containers___RepeatedCompositeFieldContainer[type___InstrumentationLibraryMetrics]: ...

    def __init__(self,
        *,
        resource : typing___Optional[opentelemetry___proto___resource___v1___resource_pb2___Resource] = None,
        instrumentation_library_metrics : typing___Optional[typing___Iterable[type___InstrumentationLibraryMetrics]] = None,
        ) -> None: ...
    if sys.version_info >= (3,):
        @classmethod
        def FromString(cls, s: builtin___bytes) -> ResourceMetrics: ...
    else:
        @classmethod
        def FromString(cls, s: typing___Union[builtin___bytes, builtin___buffer, builtin___unicode]) -> ResourceMetrics: ...
    def HasField(self, field_name: typing_extensions___Literal[u"resource",b"resource"]) -> builtin___bool: ...
    def ClearField(self, field_name: typing_extensions___Literal[u"instrumentation_library_metrics",b"instrumentation_library_metrics",u"resource",b"resource"]) -> None: ...
type___ResourceMetrics = ResourceMetrics

class InstrumentationLibraryMetrics(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...

    @property
    def instrumentation_library(self) -> opentelemetry___proto___common___v1___common_pb2___InstrumentationLibrary: ...

    @property
    def metrics(self) -> google___protobuf___internal___containers___RepeatedCompositeFieldContainer[type___Metric]: ...

    def __init__(self,
        *,
        instrumentation_library : typing___Optional[opentelemetry___proto___common___v1___common_pb2___InstrumentationLibrary] = None,
        metrics : typing___Optional[typing___Iterable[type___Metric]] = None,
        ) -> None: ...
    if sys.version_info >= (3,):
        @classmethod
        def FromString(cls, s: builtin___bytes) -> InstrumentationLibraryMetrics: ...
    else:
        @classmethod
        def FromString(cls, s: typing___Union[builtin___bytes, builtin___buffer, builtin___unicode]) -> InstrumentationLibraryMetrics: ...
    def HasField(self, field_name: typing_extensions___Literal[u"instrumentation_library",b"instrumentation_library"]) -> builtin___bool: ...
    def ClearField(self, field_name: typing_extensions___Literal[u"instrumentation_library",b"instrumentation_library",u"metrics",b"metrics"]) -> None: ...
type___InstrumentationLibraryMetrics = InstrumentationLibraryMetrics

class Metric(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...

    @property
    def metric_descriptor(self) -> type___MetricDescriptor: ...

    @property
    def int64_data_points(self) -> google___protobuf___internal___containers___RepeatedCompositeFieldContainer[type___Int64DataPoint]: ...

    @property
    def double_data_points(self) -> google___protobuf___internal___containers___RepeatedCompositeFieldContainer[type___DoubleDataPoint]: ...

    @property
    def histogram_data_points(self) -> google___protobuf___internal___containers___RepeatedCompositeFieldContainer[type___HistogramDataPoint]: ...

    @property
    def summary_data_points(self) -> google___protobuf___internal___containers___RepeatedCompositeFieldContainer[type___SummaryDataPoint]: ...

    def __init__(self,
        *,
        metric_descriptor : typing___Optional[type___MetricDescriptor] = None,
        int64_data_points : typing___Optional[typing___Iterable[type___Int64DataPoint]] = None,
        double_data_points : typing___Optional[typing___Iterable[type___DoubleDataPoint]] = None,
        histogram_data_points : typing___Optional[typing___Iterable[type___HistogramDataPoint]] = None,
        summary_data_points : typing___Optional[typing___Iterable[type___SummaryDataPoint]] = None,
        ) -> None: ...
    if sys.version_info >= (3,):
        @classmethod
        def FromString(cls, s: builtin___bytes) -> Metric: ...
    else:
        @classmethod
        def FromString(cls, s: typing___Union[builtin___bytes, builtin___buffer, builtin___unicode]) -> Metric: ...
    def HasField(self, field_name: typing_extensions___Literal[u"metric_descriptor",b"metric_descriptor"]) -> builtin___bool: ...
    def ClearField(self, field_name: typing_extensions___Literal[u"double_data_points",b"double_data_points",u"histogram_data_points",b"histogram_data_points",u"int64_data_points",b"int64_data_points",u"metric_descriptor",b"metric_descriptor",u"summary_data_points",b"summary_data_points"]) -> None: ...
type___Metric = Metric

class MetricDescriptor(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    TypeValue = typing___NewType('TypeValue', builtin___int)
    type___TypeValue = TypeValue
    class Type(object):
        DESCRIPTOR: google___protobuf___descriptor___EnumDescriptor = ...
        @classmethod
        def Name(cls, number: builtin___int) -> builtin___str: ...
        @classmethod
        def Value(cls, name: builtin___str) -> MetricDescriptor.TypeValue: ...
        @classmethod
        def keys(cls) -> typing___List[builtin___str]: ...
        @classmethod
        def values(cls) -> typing___List[MetricDescriptor.TypeValue]: ...
        @classmethod
        def items(cls) -> typing___List[typing___Tuple[builtin___str, MetricDescriptor.TypeValue]]: ...
        INVALID_TYPE = typing___cast(MetricDescriptor.TypeValue, 0)
        INT64 = typing___cast(MetricDescriptor.TypeValue, 1)
        MONOTONIC_INT64 = typing___cast(MetricDescriptor.TypeValue, 2)
        DOUBLE = typing___cast(MetricDescriptor.TypeValue, 3)
        MONOTONIC_DOUBLE = typing___cast(MetricDescriptor.TypeValue, 4)
        HISTOGRAM = typing___cast(MetricDescriptor.TypeValue, 5)
        SUMMARY = typing___cast(MetricDescriptor.TypeValue, 6)
    INVALID_TYPE = typing___cast(MetricDescriptor.TypeValue, 0)
    INT64 = typing___cast(MetricDescriptor.TypeValue, 1)
    MONOTONIC_INT64 = typing___cast(MetricDescriptor.TypeValue, 2)
    DOUBLE = typing___cast(MetricDescriptor.TypeValue, 3)
    MONOTONIC_DOUBLE = typing___cast(MetricDescriptor.TypeValue, 4)
    HISTOGRAM = typing___cast(MetricDescriptor.TypeValue, 5)
    SUMMARY = typing___cast(MetricDescriptor.TypeValue, 6)
    type___Type = Type

    TemporalityValue = typing___NewType('TemporalityValue', builtin___int)
    type___TemporalityValue = TemporalityValue
    class Temporality(object):
        DESCRIPTOR: google___protobuf___descriptor___EnumDescriptor = ...
        @classmethod
        def Name(cls, number: builtin___int) -> builtin___str: ...
        @classmethod
        def Value(cls, name: builtin___str) -> MetricDescriptor.TemporalityValue: ...
        @classmethod
        def keys(cls) -> typing___List[builtin___str]: ...
        @classmethod
        def values(cls) -> typing___List[MetricDescriptor.TemporalityValue]: ...
        @classmethod
        def items(cls) -> typing___List[typing___Tuple[builtin___str, MetricDescriptor.TemporalityValue]]: ...
        INVALID_TEMPORALITY = typing___cast(MetricDescriptor.TemporalityValue, 0)
        INSTANTANEOUS = typing___cast(MetricDescriptor.TemporalityValue, 1)
        DELTA = typing___cast(MetricDescriptor.TemporalityValue, 2)
        CUMULATIVE = typing___cast(MetricDescriptor.TemporalityValue, 3)
    INVALID_TEMPORALITY = typing___cast(MetricDescriptor.TemporalityValue, 0)
    INSTANTANEOUS = typing___cast(MetricDescriptor.TemporalityValue, 1)
    DELTA = typing___cast(MetricDescriptor.TemporalityValue, 2)
    CUMULATIVE = typing___cast(MetricDescriptor.TemporalityValue, 3)
    type___Temporality = Temporality

    name: typing___Text = ...
    description: typing___Text = ...
    unit: typing___Text = ...
    type: type___MetricDescriptor.TypeValue = ...
    temporality: type___MetricDescriptor.TemporalityValue = ...

    def __init__(self,
        *,
        name : typing___Optional[typing___Text] = None,
        description : typing___Optional[typing___Text] = None,
        unit : typing___Optional[typing___Text] = None,
        type : typing___Optional[type___MetricDescriptor.TypeValue] = None,
        temporality : typing___Optional[type___MetricDescriptor.TemporalityValue] = None,
        ) -> None: ...
    if sys.version_info >= (3,):
        @classmethod
        def FromString(cls, s: builtin___bytes) -> MetricDescriptor: ...
    else:
        @classmethod
        def FromString(cls, s: typing___Union[builtin___bytes, builtin___buffer, builtin___unicode]) -> MetricDescriptor: ...
    def ClearField(self, field_name: typing_extensions___Literal[u"description",b"description",u"name",b"name",u"temporality",b"temporality",u"type",b"type",u"unit",b"unit"]) -> None: ...
type___MetricDescriptor = MetricDescriptor

class Int64DataPoint(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    start_time_unix_nano: builtin___int = ...
    time_unix_nano: builtin___int = ...
    value: builtin___int = ...

    @property
    def labels(self) -> google___protobuf___internal___containers___RepeatedCompositeFieldContainer[opentelemetry___proto___common___v1___common_pb2___StringKeyValue]: ...

    def __init__(self,
        *,
        labels : typing___Optional[typing___Iterable[opentelemetry___proto___common___v1___common_pb2___StringKeyValue]] = None,
        start_time_unix_nano : typing___Optional[builtin___int] = None,
        time_unix_nano : typing___Optional[builtin___int] = None,
        value : typing___Optional[builtin___int] = None,
        ) -> None: ...
    if sys.version_info >= (3,):
        @classmethod
        def FromString(cls, s: builtin___bytes) -> Int64DataPoint: ...
    else:
        @classmethod
        def FromString(cls, s: typing___Union[builtin___bytes, builtin___buffer, builtin___unicode]) -> Int64DataPoint: ...
    def ClearField(self, field_name: typing_extensions___Literal[u"labels",b"labels",u"start_time_unix_nano",b"start_time_unix_nano",u"time_unix_nano",b"time_unix_nano",u"value",b"value"]) -> None: ...
type___Int64DataPoint = Int64DataPoint

class DoubleDataPoint(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    start_time_unix_nano: builtin___int = ...
    time_unix_nano: builtin___int = ...
    value: builtin___float = ...

    @property
    def labels(self) -> google___protobuf___internal___containers___RepeatedCompositeFieldContainer[opentelemetry___proto___common___v1___common_pb2___StringKeyValue]: ...

    def __init__(self,
        *,
        labels : typing___Optional[typing___Iterable[opentelemetry___proto___common___v1___common_pb2___StringKeyValue]] = None,
        start_time_unix_nano : typing___Optional[builtin___int] = None,
        time_unix_nano : typing___Optional[builtin___int] = None,
        value : typing___Optional[builtin___float] = None,
        ) -> None: ...
    if sys.version_info >= (3,):
        @classmethod
        def FromString(cls, s: builtin___bytes) -> DoubleDataPoint: ...
    else:
        @classmethod
        def FromString(cls, s: typing___Union[builtin___bytes, builtin___buffer, builtin___unicode]) -> DoubleDataPoint: ...
    def ClearField(self, field_name: typing_extensions___Literal[u"labels",b"labels",u"start_time_unix_nano",b"start_time_unix_nano",u"time_unix_nano",b"time_unix_nano",u"value",b"value"]) -> None: ...
type___DoubleDataPoint = DoubleDataPoint

class HistogramDataPoint(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    class Bucket(google___protobuf___message___Message):
        DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
        class Exemplar(google___protobuf___message___Message):
            DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
            value: builtin___float = ...
            time_unix_nano: builtin___int = ...

            @property
            def attachments(self) -> google___protobuf___internal___containers___RepeatedCompositeFieldContainer[opentelemetry___proto___common___v1___common_pb2___StringKeyValue]: ...

            def __init__(self,
                *,
                value : typing___Optional[builtin___float] = None,
                time_unix_nano : typing___Optional[builtin___int] = None,
                attachments : typing___Optional[typing___Iterable[opentelemetry___proto___common___v1___common_pb2___StringKeyValue]] = None,
                ) -> None: ...
            if sys.version_info >= (3,):
                @classmethod
                def FromString(cls, s: builtin___bytes) -> HistogramDataPoint.Bucket.Exemplar: ...
            else:
                @classmethod
                def FromString(cls, s: typing___Union[builtin___bytes, builtin___buffer, builtin___unicode]) -> HistogramDataPoint.Bucket.Exemplar: ...
            def ClearField(self, field_name: typing_extensions___Literal[u"attachments",b"attachments",u"time_unix_nano",b"time_unix_nano",u"value",b"value"]) -> None: ...
        type___Exemplar = Exemplar

        count: builtin___int = ...

        @property
        def exemplar(self) -> type___HistogramDataPoint.Bucket.Exemplar: ...

        def __init__(self,
            *,
            count : typing___Optional[builtin___int] = None,
            exemplar : typing___Optional[type___HistogramDataPoint.Bucket.Exemplar] = None,
            ) -> None: ...
        if sys.version_info >= (3,):
            @classmethod
            def FromString(cls, s: builtin___bytes) -> HistogramDataPoint.Bucket: ...
        else:
            @classmethod
            def FromString(cls, s: typing___Union[builtin___bytes, builtin___buffer, builtin___unicode]) -> HistogramDataPoint.Bucket: ...
        def HasField(self, field_name: typing_extensions___Literal[u"exemplar",b"exemplar"]) -> builtin___bool: ...
        def ClearField(self, field_name: typing_extensions___Literal[u"count",b"count",u"exemplar",b"exemplar"]) -> None: ...
    type___Bucket = Bucket

    start_time_unix_nano: builtin___int = ...
    time_unix_nano: builtin___int = ...
    count: builtin___int = ...
    sum: builtin___float = ...
    explicit_bounds: google___protobuf___internal___containers___RepeatedScalarFieldContainer[builtin___float] = ...

    @property
    def labels(self) -> google___protobuf___internal___containers___RepeatedCompositeFieldContainer[opentelemetry___proto___common___v1___common_pb2___StringKeyValue]: ...

    @property
    def buckets(self) -> google___protobuf___internal___containers___RepeatedCompositeFieldContainer[type___HistogramDataPoint.Bucket]: ...

    def __init__(self,
        *,
        labels : typing___Optional[typing___Iterable[opentelemetry___proto___common___v1___common_pb2___StringKeyValue]] = None,
        start_time_unix_nano : typing___Optional[builtin___int] = None,
        time_unix_nano : typing___Optional[builtin___int] = None,
        count : typing___Optional[builtin___int] = None,
        sum : typing___Optional[builtin___float] = None,
        buckets : typing___Optional[typing___Iterable[type___HistogramDataPoint.Bucket]] = None,
        explicit_bounds : typing___Optional[typing___Iterable[builtin___float]] = None,
        ) -> None: ...
    if sys.version_info >= (3,):
        @classmethod
        def FromString(cls, s: builtin___bytes) -> HistogramDataPoint: ...
    else:
        @classmethod
        def FromString(cls, s: typing___Union[builtin___bytes, builtin___buffer, builtin___unicode]) -> HistogramDataPoint: ...
    def ClearField(self, field_name: typing_extensions___Literal[u"buckets",b"buckets",u"count",b"count",u"explicit_bounds",b"explicit_bounds",u"labels",b"labels",u"start_time_unix_nano",b"start_time_unix_nano",u"sum",b"sum",u"time_unix_nano",b"time_unix_nano"]) -> None: ...
type___HistogramDataPoint = HistogramDataPoint

class SummaryDataPoint(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    class ValueAtPercentile(google___protobuf___message___Message):
        DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
        percentile: builtin___float = ...
        value: builtin___float = ...

        def __init__(self,
            *,
            percentile : typing___Optional[builtin___float] = None,
            value : typing___Optional[builtin___float] = None,
            ) -> None: ...
        if sys.version_info >= (3,):
            @classmethod
            def FromString(cls, s: builtin___bytes) -> SummaryDataPoint.ValueAtPercentile: ...
        else:
            @classmethod
            def FromString(cls, s: typing___Union[builtin___bytes, builtin___buffer, builtin___unicode]) -> SummaryDataPoint.ValueAtPercentile: ...
        def ClearField(self, field_name: typing_extensions___Literal[u"percentile",b"percentile",u"value",b"value"]) -> None: ...
    type___ValueAtPercentile = ValueAtPercentile

    start_time_unix_nano: builtin___int = ...
    time_unix_nano: builtin___int = ...
    count: builtin___int = ...
    sum: builtin___float = ...

    @property
    def labels(self) -> google___protobuf___internal___containers___RepeatedCompositeFieldContainer[opentelemetry___proto___common___v1___common_pb2___StringKeyValue]: ...

    @property
    def percentile_values(self) -> google___protobuf___internal___containers___RepeatedCompositeFieldContainer[type___SummaryDataPoint.ValueAtPercentile]: ...

    def __init__(self,
        *,
        labels : typing___Optional[typing___Iterable[opentelemetry___proto___common___v1___common_pb2___StringKeyValue]] = None,
        start_time_unix_nano : typing___Optional[builtin___int] = None,
        time_unix_nano : typing___Optional[builtin___int] = None,
        count : typing___Optional[builtin___int] = None,
        sum : typing___Optional[builtin___float] = None,
        percentile_values : typing___Optional[typing___Iterable[type___SummaryDataPoint.ValueAtPercentile]] = None,
        ) -> None: ...
    if sys.version_info >= (3,):
        @classmethod
        def FromString(cls, s: builtin___bytes) -> SummaryDataPoint: ...
    else:
        @classmethod
        def FromString(cls, s: typing___Union[builtin___bytes, builtin___buffer, builtin___unicode]) -> SummaryDataPoint: ...
    def ClearField(self, field_name: typing_extensions___Literal[u"count",b"count",u"labels",b"labels",u"percentile_values",b"percentile_values",u"start_time_unix_nano",b"start_time_unix_nano",u"sum",b"sum",u"time_unix_nano",b"time_unix_nano"]) -> None: ...
type___SummaryDataPoint = SummaryDataPoint
