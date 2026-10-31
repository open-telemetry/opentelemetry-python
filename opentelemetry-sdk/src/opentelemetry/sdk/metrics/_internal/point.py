# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""The immutable data classes a metric exporter receives.

A metric reader hands an exporter a single ``MetricsData``, which nests
``ResourceMetrics``, ``ScopeMetrics``, ``Metric``, one of the four data types
(``Sum``, ``Gauge``, ``Histogram``, ``ExponentialHistogram``) and finally the
data points. The nesting mirrors the OpenTelemetry protocol message of the
same name, so an OTLP exporter walks this structure field by field.

Every class here is a frozen dataclass and every one of them, except
``Buckets``, has a ``to_json`` method. ``ConsoleMetricExporter`` uses
``MetricsData.to_json`` as its default formatter.

Time fields are named ``*_unix_nano`` and are integers counting nanoseconds
since the Unix epoch.
"""

# pylint: disable=unused-import

from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from json import dumps, loads

# This kind of import is needed to avoid Sphinx errors.
import opentelemetry.sdk.metrics._internal
from opentelemetry.sdk.metrics._internal.exemplar import Exemplar
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.util.types import Attributes


@dataclass(frozen=True)
class NumberDataPoint:
    """Single data point in a timeseries that describes the time-varying scalar
    value of a metric.

    Produced by the sum and last value aggregations.

    Args:
        attributes: The attribute set this point was aggregated under. Two
            measurements of the same instrument land in the same point only
            when their attributes are equal after view filtering.
        start_time_unix_nano: Nanoseconds since the Unix epoch at which the
            interval covered by ``value`` begins. The last value aggregation
            leaves it as ``None``, since a gauge reading covers no interval.
        time_unix_nano: Nanoseconds since the Unix epoch at which the
            collection that produced this point started.
        value: The aggregated value. A delta point carries the change since
            ``start_time_unix_nano``, a cumulative point the running total.
        exemplars: Sample measurements kept by the exemplar reservoir during
            the interval, each one carrying the trace id and span id that were
            active when it was recorded. Empty when no measurement passed the
            exemplar filter.
    """

    attributes: Attributes
    start_time_unix_nano: int
    time_unix_nano: int
    value: int | float
    exemplars: Sequence[Exemplar] = field(default_factory=list)

    def to_json(self, indent: int | None = 4) -> str:
        """Serialise this data point to OTLP-shaped JSON.

        Every field is emitted under its own name, so the result matches the
        ``NumberDataPoint`` message of the OpenTelemetry protocol.

        Args:
            indent: Number of spaces per nesting level. ``None`` produces the
                most compact form, on a single line.

        Returns:
            A JSON object with the attributes, the two timestamps, the value
            and the exemplars of this point.
        """
        return dumps(asdict(self), indent=indent)


@dataclass(frozen=True)
class HistogramDataPoint:
    """Single data point in a timeseries that describes the time-varying scalar
    value of a metric.

    Produced by the explicit bucket histogram aggregation.

    Args:
        attributes: The attribute set this point was aggregated under.
        start_time_unix_nano: Nanoseconds since the Unix epoch at which the
            interval covered by this point begins.
        time_unix_nano: Nanoseconds since the Unix epoch at which the
            collection that produced this point started.
        count: Number of measurements that fell into the interval, equal to
            the sum of ``bucket_counts``.
        sum: Arithmetic sum of those measurements.
        bucket_counts: One count per bucket, in ascending bucket order. It
            holds exactly ``len(explicit_bounds) + 1`` entries: one for every
            bound plus a final one for everything above the last bound.
        explicit_bounds: The strictly increasing bucket boundaries. Bucket
            ``i`` covers the values greater than ``explicit_bounds[i - 1]`` and
            less than or equal to ``explicit_bounds[i]``, so a measurement
            equal to a boundary is counted in the lower of the two buckets
            that boundary separates.
        min: Smallest measurement in the interval, or ``None`` when the
            aggregation was built with ``record_min_max`` set to ``False``.
        max: Largest measurement in the interval, or ``None`` under the same
            condition.
        exemplars: Sample measurements kept by the exemplar reservoir during
            the interval.
    """

    attributes: Attributes
    start_time_unix_nano: int
    time_unix_nano: int
    count: int
    sum: int | float
    bucket_counts: Sequence[int]
    explicit_bounds: Sequence[float]
    min: float | None
    max: float | None
    exemplars: Sequence[Exemplar] = field(default_factory=list)

    def to_json(self, indent: int | None = 4) -> str:
        """Serialise this data point to OTLP-shaped JSON.

        Every field is emitted under its own name, so the result matches the
        ``HistogramDataPoint`` message of the OpenTelemetry protocol.

        Args:
            indent: Number of spaces per nesting level. ``None`` produces the
                most compact form, on a single line.

        Returns:
            A JSON object with the attributes, the timestamps, the count, the
            sum, the buckets, the bounds, the minimum, the maximum and the
            exemplars of this point.
        """
        return dumps(asdict(self), indent=indent)


@dataclass(frozen=True)
class Buckets:
    """One side of an exponential histogram, either positive or negative.

    Args:
        offset: Index of the bucket that ``bucket_counts[0]`` counts. Bucket
            index ``i`` covers the values from ``base ** i`` excluded to
            ``base ** (i + 1)`` included, where ``base`` is
            ``2 ** (2 ** -scale)`` and ``scale`` is read from the data point
            that holds these buckets. The index is signed, since values below
            one map to negative indexes.
        bucket_counts: Counts of the consecutive buckets starting at
            ``offset``, in ascending index order. A side that received no
            measurement is reported as a single bucket holding a count of
            zero, at offset zero.
    """

    offset: int
    bucket_counts: Sequence[int]


@dataclass(frozen=True)
class ExponentialHistogramDataPoint:
    """Single data point in a timeseries whose boundaries are defined by an
    exponential function. This timeseries describes the time-varying scalar
    value of a metric.

    Args:
        attributes: The attribute set this point was aggregated under.
        start_time_unix_nano: Nanoseconds since the Unix epoch at which the
            interval covered by this point begins.
        time_unix_nano: Nanoseconds since the Unix epoch at which the
            collection that produced this point started.
        count: Number of measurements that fell into the interval, zeros
            included.
        sum: Arithmetic sum of those measurements.
        scale: Resolution of the buckets. The bucket base is
            ``2 ** (2 ** -scale)``, so a larger scale means narrower buckets.
            The aggregation lowers it whenever the recorded values stop
            fitting in ``max_size`` buckets, and never raises it, so the scale
            only ever drops while one aggregation object lives. It is not
            monotonic across the points of a stream: a synchronous instrument
            collected with ``DELTA`` temporality discards its aggregation on
            every collection, so the next point starts again at ``max_scale``
            and the reported scale can rise.
        zero_count: Number of measurements that were exactly zero. They are
            counted here and in ``count``, and appear in neither ``positive``
            nor ``negative``.
        positive: Buckets holding the measurements greater than zero.
        negative: Buckets holding the measurements less than zero, indexed by
            their absolute value.
        flags: Data point flags defined by the OpenTelemetry protocol. The SDK
            always emits 0.
        min: Smallest measurement in the interval, or ``None`` when the
            aggregation was built with ``record_min_max`` set to ``False``.
        max: Largest measurement in the interval, or ``None`` under the same
            condition.
        exemplars: Sample measurements kept by the exemplar reservoir during
            the interval.
    """

    attributes: Attributes
    start_time_unix_nano: int
    time_unix_nano: int
    count: int
    sum: int | float
    scale: int
    zero_count: int
    positive: Buckets
    negative: Buckets
    flags: int
    min: float | None
    max: float | None
    exemplars: Sequence[Exemplar] = field(default_factory=list)

    def to_json(self, indent: int | None = 4) -> str:
        """Serialise this data point to OTLP-shaped JSON.

        Every field is emitted under its own name, so the result matches the
        ``ExponentialHistogramDataPoint`` message of the OpenTelemetry
        protocol. The two ``Buckets`` are inlined as nested objects.

        Args:
            indent: Number of spaces per nesting level. ``None`` produces the
                most compact form, on a single line.

        Returns:
            A JSON object with every field of this point, including the
            positive and negative buckets.
        """
        return dumps(asdict(self), indent=indent)


@dataclass(frozen=True)
class ExponentialHistogram:
    """Represents the type of a metric that is calculated by aggregating as an
    ExponentialHistogram of all reported measurements over a time interval.

    Args:
        data_points: One point per attribute set that received a measurement,
            in no particular order.
        aggregation_temporality: Whether each point covers only the interval
            since the previous collection (``DELTA``) or everything since the
            start of the stream (``CUMULATIVE``). The metric reader picks it
            per instrument kind.
    """

    data_points: Sequence[ExponentialHistogramDataPoint]
    aggregation_temporality: "opentelemetry.sdk.metrics.export.AggregationTemporality"

    def to_json(self, indent: int | None = 4) -> str:
        """Serialise this data type to OTLP-shaped JSON.

        Each data point is serialised and parsed back, so the result nests
        real JSON objects rather than strings. The temporality is emitted as
        its integer value.

        Args:
            indent: Number of spaces per nesting level. ``None`` produces the
                most compact form, on a single line.

        Returns:
            A JSON object with ``data_points`` and ``aggregation_temporality``.
        """
        return dumps(
            {
                "data_points": [loads(data_point.to_json(indent=indent)) for data_point in self.data_points],
                "aggregation_temporality": self.aggregation_temporality,
            },
            indent=indent,
        )


@dataclass(frozen=True)
class Sum:
    """Represents the type of a scalar metric that is calculated as a sum of
    all reported measurements over a time interval.

    Args:
        data_points: One point per attribute set that received a measurement,
            in no particular order.
        aggregation_temporality: Whether each point covers only the interval
            since the previous collection (``DELTA``) or everything since the
            start of the stream (``CUMULATIVE``).
        is_monotonic: ``True`` when the instrument behind the stream can only
            increase, which is the case for a counter and an observable
            counter. A backend may rely on this to detect resets.
    """

    data_points: Sequence[NumberDataPoint]
    aggregation_temporality: "opentelemetry.sdk.metrics.export.AggregationTemporality"
    is_monotonic: bool

    def to_json(self, indent: int | None = 4) -> str:
        """Serialise this data type to OTLP-shaped JSON.

        Each data point is serialised and parsed back, so the result nests
        real JSON objects rather than strings. The temporality is emitted as
        its integer value.

        Args:
            indent: Number of spaces per nesting level. ``None`` produces the
                most compact form, on a single line.

        Returns:
            A JSON object with ``data_points``, ``aggregation_temporality``
            and ``is_monotonic``.
        """
        return dumps(
            {
                "data_points": [loads(data_point.to_json(indent=indent)) for data_point in self.data_points],
                "aggregation_temporality": self.aggregation_temporality,
                "is_monotonic": self.is_monotonic,
            },
            indent=indent,
        )


@dataclass(frozen=True)
class Gauge:
    """Represents the type of a scalar metric that always exports the current
    value for every data point. It should be used for an unknown
    aggregation.

    Args:
        data_points: One point per attribute set that received a measurement,
            in no particular order. A gauge point covers no interval, so it
            carries no temporality and its ``start_time_unix_nano`` is
            ``None``.
    """

    data_points: Sequence[NumberDataPoint]

    def to_json(self, indent: int | None = 4) -> str:
        """Serialise this data type to OTLP-shaped JSON.

        Each data point is serialised and parsed back, so the result nests
        real JSON objects rather than strings.

        Args:
            indent: Number of spaces per nesting level. ``None`` produces the
                most compact form, on a single line.

        Returns:
            A JSON object whose only key is ``data_points``.
        """
        return dumps(
            {
                "data_points": [loads(data_point.to_json(indent=indent)) for data_point in self.data_points],
            },
            indent=indent,
        )


@dataclass(frozen=True)
class Histogram:
    """Represents the type of a metric that is calculated by aggregating as a
    histogram of all reported measurements over a time interval.

    Args:
        data_points: One point per attribute set that received a measurement,
            in no particular order. All of them share the same bucket
            boundaries, since the boundaries come from the view or the
            instrument advisory rather than from the data.
        aggregation_temporality: Whether each point covers only the interval
            since the previous collection (``DELTA``) or everything since the
            start of the stream (``CUMULATIVE``).
    """

    data_points: Sequence[HistogramDataPoint]
    aggregation_temporality: "opentelemetry.sdk.metrics.export.AggregationTemporality"

    def to_json(self, indent: int | None = 4) -> str:
        """Serialise this data type to OTLP-shaped JSON.

        Each data point is serialised and parsed back, so the result nests
        real JSON objects rather than strings. The temporality is emitted as
        its integer value.

        Args:
            indent: Number of spaces per nesting level. ``None`` produces the
                most compact form, on a single line.

        Returns:
            A JSON object with ``data_points`` and ``aggregation_temporality``.
        """
        return dumps(
            {
                "data_points": [loads(data_point.to_json(indent=indent)) for data_point in self.data_points],
                "aggregation_temporality": self.aggregation_temporality,
            },
            indent=indent,
        )


# pylint: disable=invalid-name
DataT = Sum | Gauge | Histogram | ExponentialHistogram
DataPointT = NumberDataPoint | HistogramDataPoint | ExponentialHistogramDataPoint


@dataclass(frozen=True)
class Metric:
    """Represents a metric point in the OpenTelemetry data model to be
    exported.

    Args:
        name: Stream name. It is the instrument name unless a view renamed
            it. Nothing stops two streams of one scope from carrying the same
            name: the reader storage logs a warning about conflicting metric
            identities and exports both.
        description: Free text taken from the instrument or the view. ``None``
            is serialised as an empty string.
        unit: Unit of the measured values, as given to the instrument.
            ``None`` is serialised as an empty string.
        data: The aggregated data and the points themselves. Which of the four
            data types appears here follows from the aggregation the view
            selected.
    """

    name: str
    description: str | None
    unit: str | None
    data: DataT

    def to_json(self, indent: int | None = 4) -> str:
        """Serialise this metric to OTLP-shaped JSON.

        A ``description`` or a ``unit`` of ``None`` becomes an empty string,
        which is what the protocol uses for an absent value.

        Args:
            indent: Number of spaces per nesting level. ``None`` produces the
                most compact form, on a single line.

        Returns:
            A JSON object with ``name``, ``description``, ``unit`` and
            ``data``.
        """
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
    """A collection of Metrics produced by a scope.

    Args:
        scope: The instrumentation scope, meaning the name, version and
            attributes of the meter the instruments were created from.
        metrics: The metrics that meter produced during this collection.
        schema_url: URL of the schema the scope declares, as passed to
            ``get_meter``. Empty when the meter declared none.
    """

    scope: InstrumentationScope
    metrics: Sequence[Metric]
    schema_url: str

    def to_json(self, indent: int | None = 4) -> str:
        """Serialise this scope and its metrics to OTLP-shaped JSON.

        Args:
            indent: Number of spaces per nesting level. ``None`` produces the
                most compact form, on a single line.

        Returns:
            A JSON object with ``scope``, ``metrics`` and ``schema_url``.
        """
        return dumps(
            {
                "scope": loads(self.scope.to_json(indent=indent)),
                "metrics": [loads(metric.to_json(indent=indent)) for metric in self.metrics],
                "schema_url": self.schema_url,
            },
            indent=indent,
        )


@dataclass(frozen=True)
class ResourceMetrics:
    """A collection of ScopeMetrics from a Resource.

    Args:
        resource: The resource of the meter provider that produced these
            metrics. Every metric below it is attributed to it.
        scope_metrics: One entry per instrumentation scope that produced
            metrics during this collection.
        schema_url: URL of the schema the resource declares. Empty when the
            resource declared none.
    """

    resource: Resource
    scope_metrics: Sequence[ScopeMetrics]
    schema_url: str

    def to_json(self, indent: int | None = 4) -> str:
        """Serialise this resource and its scopes to OTLP-shaped JSON.

        Args:
            indent: Number of spaces per nesting level. ``None`` produces the
                most compact form, on a single line.

        Returns:
            A JSON object with ``resource``, ``scope_metrics`` and
            ``schema_url``.
        """
        return dumps(
            {
                "resource": loads(self.resource.to_json(indent=indent)),
                "scope_metrics": [loads(scope_metrics.to_json(indent=indent)) for scope_metrics in self.scope_metrics],
                "schema_url": self.schema_url,
            },
            indent=indent,
        )


@dataclass(frozen=True)
class MetricsData:
    """An array of ResourceMetrics.

    This is what a metric reader hands to an exporter, and the outermost
    message of the OpenTelemetry protocol payload.

    Args:
        resource_metrics: One entry per resource. An SDK meter provider has a
            single resource, so a reader of that provider produces exactly one
            entry, or none when no instrument recorded anything.
    """

    resource_metrics: Sequence[ResourceMetrics]

    def to_json(self, indent: int | None = 4) -> str:
        """Serialise the whole collection to OTLP-shaped JSON.

        ``ConsoleMetricExporter`` calls this with the default indent and
        writes one such object per export.

        Args:
            indent: Number of spaces per nesting level. ``None`` produces the
                most compact form, on a single line, which is what a
                line-delimited output wants.

        Returns:
            A JSON object whose only key is ``resource_metrics``.
        """
        return dumps(
            {
                "resource_metrics": [
                    loads(resource_metrics.to_json(indent=indent)) for resource_metrics in self.resource_metrics
                ]
            },
            indent=indent,
        )
