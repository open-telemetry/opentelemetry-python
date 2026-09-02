"""Pure-Python equivalents of opentelemetry/proto/metrics/v1/metrics_pb2.py.

Field numbers:
    Exemplar            filtered_attributes=7  time_unix_nano=2
                        as_double=3(wire_64bit)  as_int=6(sfixed64)
                        span_id=4  trace_id=5
    NumberDataPoint     attributes=7  start_time_unix_nano=2  time_unix_nano=3
                        as_double=4(wire_64bit)  as_int=6(sfixed64)
                        exemplars=5  flags=8
    HistogramDataPoint  attributes=9  start_time_unix_nano=2  time_unix_nano=3
                        count=4(fixed64)  sum=5(opt_dbl)
                        bucket_counts=6(packed_fix64)
                        explicit_bounds=7(packed_dbl)  exemplars=8
                        flags=10  min=11(opt_dbl)  max=12(opt_dbl)
    ExponentialHistogramDataPoint
                        attributes=1  start_time_unix_nano=2  time_unix_nano=3
                        count=4(fixed64)  sum=5(opt_dbl)  scale=6(sint32)
                        zero_count=7(fixed64)  positive=8  negative=9
                        flags=10  exemplars=11  min=12(opt_dbl)
                        max=13(opt_dbl)  zero_threshold=14(dbl)
    ExponentialHistogramDataPoint.Buckets
                        offset=1(sint32)  bucket_counts=2(packed_uint64)
    SummaryDataPoint    attributes=7  start_time_unix_nano=2  time_unix_nano=3
                        count=4(fixed64)  sum=5(dbl)  quantile_values=6  flags=8
    SummaryDataPoint.ValueAtQuantile  quantile=1(dbl)  value=2(dbl)
    Gauge               data_points=1
    Sum                 data_points=1  aggregation_temporality=2  is_monotonic=3
    Histogram           data_points=1  aggregation_temporality=2
    ExponentialHistogram data_points=1  aggregation_temporality=2
    Summary             data_points=1
    Metric              name=1  description=2  unit=3
                        oneof data: gauge=5 sum=7 histogram=9
                                    exponential_histogram=10 summary=11
    ScopeMetrics        scope=1  metrics=2  schema_url=3
    ResourceMetrics     resource=1  scope_metrics=2  schema_url=3
"""

from __future__ import annotations

from struct import pack

from opentelemetry._proto.common.v1.common_pb2 import (
    InstrumentationScope,
    KeyValue,
)
from opentelemetry._proto.resource.v1.resource_pb2 import Resource
from opentelemetry._proto._pyprotobuf.fields import (
    byt,
    bool_field,
    dbl,
    fix64,
    msg,
    opt_dbl,
    packed_double,
    packed_fix64,
    packed_uint64,
    sint32,
    string,
    u64,
    WT_64BIT,
)
from opentelemetry._proto._pyprotobuf import encode_tag


def _sfixed64(field: int, value: int) -> bytes:
    """sfixed64 field (little-endian signed 64-bit int)."""
    if value == 0:
        return b""
    return encode_tag(field, WT_64BIT) + pack("<q", int(value))


def _as_double(field: int, value: float) -> bytes:
    """Oneof as_double: always write, even if 0.0."""
    return encode_tag(field, WT_64BIT) + pack("<d", value)


def _as_int(field: int, value: int) -> bytes:
    """Oneof as_int: always write, even if 0."""
    return encode_tag(field, WT_64BIT) + pack("<q", int(value))


from opentelemetry._proto._pyprotobuf.message import Message


class _ValueOneof:
    """Mixin for messages with a ``value`` oneof of ``as_double``/``as_int``.

    Protobuf lets callers assign the oneof members as plain attributes
    (``point.as_int = 5``); doing so selects that member and clears the other.
    These properties reproduce that so the unchanged OTLP encoders keep working.
    """

    @property
    def as_double(self) -> float | None:
        return self._as_double

    @as_double.setter
    def as_double(self, value: float | None) -> None:
        self._as_double = value
        self._as_int = None
        self._which = "as_double" if value is not None else None

    @property
    def as_int(self) -> int | None:
        return self._as_int

    @as_int.setter
    def as_int(self, value: int | None) -> None:
        if value is not None and not -(2**63) <= value < 2**63:
            # protobuf raises ValueError when a value does not fit the signed
            # 64-bit field; reproduce that so callers see the same failure.
            raise ValueError(f"Value out of range for sfixed64: {value}")
        self._as_int = value
        self._as_double = None
        self._which = "as_int" if value is not None else None


class Exemplar(_ValueOneof, Message):
    def __init__(
        self,
        filtered_attributes: list[KeyValue] | None = None,
        time_unix_nano: int = 0,
        as_double: float | None = None,
        as_int: int | None = None,
        span_id: bytes = b"",
        trace_id: bytes = b"",
    ):
        self.filtered_attributes: list[KeyValue] = (
            list(filtered_attributes) if filtered_attributes else []
        )
        self.time_unix_nano = time_unix_nano
        self._as_double = as_double
        self._as_int = as_int
        self.span_id = span_id
        self.trace_id = trace_id
        self._which = (
            "as_double" if as_double is not None else
            "as_int" if as_int is not None else None
        )

    def WhichOneof(self, oneof_name: str) -> str | None:
        if oneof_name == "value":
            return self._which
        return None

    def SerializeToString(self) -> bytes:
        result = fix64(2, self.time_unix_nano)
        if self._which == "as_double":
            result += _as_double(3, self._as_double)  # type: ignore[arg-type]
        result += byt(4, self.span_id) + byt(5, self.trace_id)
        if self._which == "as_int":
            result += _as_int(6, self._as_int)  # type: ignore[arg-type]
        result += b"".join(
            msg(7, kv.SerializeToString()) for kv in self.filtered_attributes
        )
        return result


class NumberDataPoint(_ValueOneof, Message):
    def __init__(
        self,
        attributes: list[KeyValue] | None = None,
        start_time_unix_nano: int = 0,
        time_unix_nano: int = 0,
        as_double: float | None = None,
        as_int: int | None = None,
        exemplars: list[Exemplar] | None = None,
        flags: int = 0,
    ):
        self.attributes: list[KeyValue] = list(attributes) if attributes else []
        self.start_time_unix_nano = start_time_unix_nano
        self.time_unix_nano = time_unix_nano
        self._as_double = as_double
        self._as_int = as_int
        self.exemplars: list[Exemplar] = list(exemplars) if exemplars else []
        self.flags = flags
        self._which = (
            "as_double" if as_double is not None else
            "as_int" if as_int is not None else None
        )

    def WhichOneof(self, oneof_name: str) -> str | None:
        if oneof_name == "value":
            return self._which
        return None

    def SerializeToString(self) -> bytes:
        result = fix64(2, self.start_time_unix_nano) + fix64(3, self.time_unix_nano)
        if self._which == "as_double":
            result += _as_double(4, self._as_double)  # type: ignore[arg-type]
        result += b"".join(msg(5, ex.SerializeToString()) for ex in self.exemplars)
        if self._which == "as_int":
            result += _as_int(6, self._as_int)  # type: ignore[arg-type]
        result += b"".join(msg(7, kv.SerializeToString()) for kv in self.attributes)
        result += u64(8, self.flags)
        return result


class HistogramDataPoint(Message):
    def __init__(
        self,
        attributes: list[KeyValue] | None = None,
        start_time_unix_nano: int = 0,
        time_unix_nano: int = 0,
        count: int = 0,
        sum: float | None = None,
        bucket_counts: list[int] | None = None,
        explicit_bounds: list[float] | None = None,
        exemplars: list[Exemplar] | None = None,
        flags: int = 0,
        min: float | None = None,
        max: float | None = None,
    ):
        self.attributes: list[KeyValue] = list(attributes) if attributes else []
        self.start_time_unix_nano = start_time_unix_nano
        self.time_unix_nano = time_unix_nano
        self.count = count
        self.sum = sum
        self.bucket_counts: list[int] = list(bucket_counts) if bucket_counts else []
        self.explicit_bounds: list[float] = (
            list(explicit_bounds) if explicit_bounds else []
        )
        self.exemplars: list[Exemplar] = list(exemplars) if exemplars else []
        self.flags = flags
        self.min = min
        self.max = max

    def SerializeToString(self) -> bytes:
        return (
            fix64(2, self.start_time_unix_nano)
            + fix64(3, self.time_unix_nano)
            + fix64(4, self.count)
            + opt_dbl(5, self.sum)
            + packed_fix64(6, self.bucket_counts)
            + packed_double(7, self.explicit_bounds)
            + b"".join(msg(8, ex.SerializeToString()) for ex in self.exemplars)
            + b"".join(msg(9, kv.SerializeToString()) for kv in self.attributes)
            + u64(10, self.flags)
            + opt_dbl(11, self.min)
            + opt_dbl(12, self.max)
        )


class ExponentialHistogramDataPoint(Message):
    class Buckets(Message):
        def __init__(
            self,
            offset: int = 0,
            bucket_counts: list[int] | None = None,
        ):
            self.offset = offset
            self.bucket_counts: list[int] = (
                list(bucket_counts) if bucket_counts else []
            )

        def SerializeToString(self) -> bytes:
            return (
                sint32(1, self.offset)
                + packed_uint64(2, self.bucket_counts)
            )

    def __init__(
        self,
        attributes: list[KeyValue] | None = None,
        start_time_unix_nano: int = 0,
        time_unix_nano: int = 0,
        count: int = 0,
        sum: float | None = None,
        scale: int = 0,
        zero_count: int = 0,
        positive: "ExponentialHistogramDataPoint.Buckets | None" = None,
        negative: "ExponentialHistogramDataPoint.Buckets | None" = None,
        flags: int = 0,
        exemplars: list[Exemplar] | None = None,
        min: float | None = None,
        max: float | None = None,
        zero_threshold: float = 0.0,
    ):
        self.attributes: list[KeyValue] = list(attributes) if attributes else []
        self.start_time_unix_nano = start_time_unix_nano
        self.time_unix_nano = time_unix_nano
        self.count = count
        self.sum = sum
        self.scale = scale
        self.zero_count = zero_count
        self.positive = positive
        self.negative = negative
        self.flags = flags
        self.exemplars: list[Exemplar] = list(exemplars) if exemplars else []
        self.min = min
        self.max = max
        self.zero_threshold = zero_threshold

    def SerializeToString(self) -> bytes:
        result = b"".join(msg(1, kv.SerializeToString()) for kv in self.attributes)
        result += (
            fix64(2, self.start_time_unix_nano)
            + fix64(3, self.time_unix_nano)
            + fix64(4, self.count)
            + opt_dbl(5, self.sum)
            + sint32(6, self.scale)
            + fix64(7, self.zero_count)
        )
        if self.positive is not None:
            result += msg(8, self.positive.SerializeToString())
        if self.negative is not None:
            result += msg(9, self.negative.SerializeToString())
        result += (
            u64(10, self.flags)
            + b"".join(msg(11, ex.SerializeToString()) for ex in self.exemplars)
            + opt_dbl(12, self.min)
            + opt_dbl(13, self.max)
            + dbl(14, self.zero_threshold)
        )
        return result


class SummaryDataPoint(Message):
    class ValueAtQuantile(Message):
        def __init__(self, quantile: float = 0.0, value: float = 0.0):
            self.quantile = quantile
            self.value = value

        def SerializeToString(self) -> bytes:
            return dbl(1, self.quantile) + dbl(2, self.value)

    def __init__(
        self,
        attributes: list[KeyValue] | None = None,
        start_time_unix_nano: int = 0,
        time_unix_nano: int = 0,
        count: int = 0,
        sum: float = 0.0,
        quantile_values: list["SummaryDataPoint.ValueAtQuantile"] | None = None,
        flags: int = 0,
    ):
        self.attributes: list[KeyValue] = list(attributes) if attributes else []
        self.start_time_unix_nano = start_time_unix_nano
        self.time_unix_nano = time_unix_nano
        self.count = count
        self.sum = sum
        self.quantile_values: list[SummaryDataPoint.ValueAtQuantile] = (
            list(quantile_values) if quantile_values else []
        )
        self.flags = flags

    def SerializeToString(self) -> bytes:
        return (
            fix64(2, self.start_time_unix_nano)
            + fix64(3, self.time_unix_nano)
            + fix64(4, self.count)
            + dbl(5, self.sum)
            + b"".join(msg(6, qv.SerializeToString()) for qv in self.quantile_values)
            + b"".join(msg(7, kv.SerializeToString()) for kv in self.attributes)
            + u64(8, self.flags)
        )


class Gauge(Message):
    def __init__(self, data_points: list[NumberDataPoint] | None = None):
        self.data_points: list[NumberDataPoint] = (
            list(data_points) if data_points else []
        )

    def SerializeToString(self) -> bytes:
        return b"".join(msg(1, dp.SerializeToString()) for dp in self.data_points)


class Sum(Message):
    def __init__(
        self,
        data_points: list[NumberDataPoint] | None = None,
        aggregation_temporality: int = 0,
        is_monotonic: bool = False,
    ):
        self.data_points: list[NumberDataPoint] = (
            list(data_points) if data_points else []
        )
        self.aggregation_temporality = aggregation_temporality
        self.is_monotonic = is_monotonic

    def SerializeToString(self) -> bytes:
        temp = self.aggregation_temporality
        temp_int = temp.value if hasattr(temp, "value") else int(temp)
        return (
            b"".join(msg(1, dp.SerializeToString()) for dp in self.data_points)
            + u64(2, temp_int)
            + bool_field(3, self.is_monotonic)
        )


class Histogram(Message):
    def __init__(
        self,
        data_points: list[HistogramDataPoint] | None = None,
        aggregation_temporality: int = 0,
    ):
        self.data_points: list[HistogramDataPoint] = (
            list(data_points) if data_points else []
        )
        self.aggregation_temporality = aggregation_temporality

    def SerializeToString(self) -> bytes:
        temp = self.aggregation_temporality
        temp_int = temp.value if hasattr(temp, "value") else int(temp)
        return (
            b"".join(msg(1, dp.SerializeToString()) for dp in self.data_points)
            + u64(2, temp_int)
        )


class ExponentialHistogram(Message):
    def __init__(
        self,
        data_points: list[ExponentialHistogramDataPoint] | None = None,
        aggregation_temporality: int = 0,
    ):
        self.data_points: list[ExponentialHistogramDataPoint] = (
            list(data_points) if data_points else []
        )
        self.aggregation_temporality = aggregation_temporality

    def SerializeToString(self) -> bytes:
        temp = self.aggregation_temporality
        temp_int = temp.value if hasattr(temp, "value") else int(temp)
        return (
            b"".join(msg(1, dp.SerializeToString()) for dp in self.data_points)
            + u64(2, temp_int)
        )


class Summary(Message):
    def __init__(self, data_points: list[SummaryDataPoint] | None = None):
        self.data_points: list[SummaryDataPoint] = (
            list(data_points) if data_points else []
        )

    def SerializeToString(self) -> bytes:
        return b"".join(msg(1, dp.SerializeToString()) for dp in self.data_points)


_METRIC_DATA_FIELDS = (
    "gauge",
    "sum",
    "histogram",
    "exponential_histogram",
    "summary",
)


def _oneof_message_property(name: str, message_type: type):
    """Build a property for one member of Metric's ``data`` oneof.

    Reading an unset member auto-creates it, reproducing protobuf's mutable
    message behaviour so ``metric.sum.aggregation_temporality = x`` works on a
    freshly built Metric. Assigning a member selects it and clears the others.
    """

    def getter(self):
        if getattr(self, f"_{name}") is None:
            self._select_data(name, message_type())
        return getattr(self, f"_{name}")

    def setter(self, value):
        if value is None:
            setattr(self, f"_{name}", None)
            if self._which_data == name:
                self._which_data = None
        else:
            self._select_data(name, value)

    return property(getter, setter)


class Metric(Message):
    def __init__(
        self,
        name: str = "",
        description: str = "",
        unit: str = "",
        gauge: Gauge | None = None,
        sum: Sum | None = None,
        histogram: Histogram | None = None,
        exponential_histogram: ExponentialHistogram | None = None,
        summary: Summary | None = None,
    ):
        self.name = name
        self.description = description
        self.unit = unit
        self._gauge = None
        self._sum = None
        self._histogram = None
        self._exponential_histogram = None
        self._summary = None
        self._which_data = None
        for field_name, value in (
            ("gauge", gauge),
            ("sum", sum),
            ("histogram", histogram),
            ("exponential_histogram", exponential_histogram),
            ("summary", summary),
        ):
            if value is not None:
                self._select_data(field_name, value)

    def _select_data(self, name: str, value) -> None:
        for field_name in _METRIC_DATA_FIELDS:
            setattr(self, f"_{field_name}", value if field_name == name else None)
        self._which_data = name

    gauge = _oneof_message_property("gauge", Gauge)
    sum = _oneof_message_property("sum", Sum)
    histogram = _oneof_message_property("histogram", Histogram)
    exponential_histogram = _oneof_message_property(
        "exponential_histogram", ExponentialHistogram
    )
    summary = _oneof_message_property("summary", Summary)

    def WhichOneof(self, oneof_name: str) -> str | None:
        if oneof_name == "data":
            return self._which_data
        return None

    def SerializeToString(self) -> bytes:
        result = string(1, self.name) + string(2, self.description) + string(3, self.unit)
        if self._gauge is not None:
            result += msg(5, self._gauge.SerializeToString())
        elif self._sum is not None:
            result += msg(7, self._sum.SerializeToString())
        elif self._histogram is not None:
            result += msg(9, self._histogram.SerializeToString())
        elif self._exponential_histogram is not None:
            result += msg(10, self._exponential_histogram.SerializeToString())
        elif self._summary is not None:
            result += msg(11, self._summary.SerializeToString())
        return result


class ScopeMetrics(Message):
    def __init__(
        self,
        scope: InstrumentationScope | None = None,
        metrics: list[Metric] | None = None,
        schema_url: str = "",
    ):
        self.scope = scope
        self.metrics: list[Metric] = list(metrics) if metrics else []
        self.schema_url = schema_url

    def SerializeToString(self) -> bytes:
        result = b""
        if self.scope is not None:
            result += msg(1, self.scope.SerializeToString())
        result += b"".join(msg(2, m.SerializeToString()) for m in self.metrics)
        result += string(3, self.schema_url)
        return result


class ResourceMetrics(Message):
    def __init__(
        self,
        resource: Resource | None = None,
        scope_metrics: list[ScopeMetrics] | None = None,
        schema_url: str = "",
    ):
        # protobuf accepts a mapping for a message field and coerces it.
        if isinstance(resource, dict):
            resource = Resource(**resource)
        self.resource = resource
        self.scope_metrics: list[ScopeMetrics] = (
            list(scope_metrics) if scope_metrics else []
        )
        self.schema_url = schema_url

    def SerializeToString(self) -> bytes:
        result = b""
        if self.resource is not None:
            result += msg(1, self.resource.SerializeToString())
        result += b"".join(msg(2, sm.SerializeToString()) for sm in self.scope_metrics)
        result += string(3, self.schema_url)
        return result
