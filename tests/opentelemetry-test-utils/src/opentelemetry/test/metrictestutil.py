# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Builders for the SDK metric objects an exporter test compares against.

A metrics exporter is tested by handing it a ``Metric`` and checking what it
produces, which means a test needs a ``Metric`` with a known shape. Building one
by hand takes a nested ``Metric``, data and data point construction every time,
so these functions fill in the parts a test does not care about: the timestamps
are fixed constants rather than the current time, except the gauge start
timestamp, which is ``None``; the temporality is cumulative wherever the data
type carries one, which a ``Gauge`` does not; and the description and unit
default to ``"foo"`` and ``"s"``.

Every name here is private, because the exact values are chosen to suit the
exporter tests in this repository and are changed whenever those tests need
different ones.
"""

from opentelemetry.attributes import BoundedAttributes
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    Gauge,
    Histogram,
    HistogramDataPoint,
    Metric,
    NumberDataPoint,
    Sum,
)
from opentelemetry.util.types import Attributes


def _generate_metric(name, data, attributes=None, description=None, unit=None) -> Metric:
    """Wrap already-built metric data in a ``Metric``.

    Args:
        name: The metric name.
        data: The ``Sum``, ``Gauge``, ``Histogram`` or other data object the
            metric carries, already holding its data points. Passing ``None``
            produces a metric with no data, which is what
            ``_generate_unsupported_metric`` relies on.
        attributes: Ignored. Attributes belong to the individual data points
            inside ``data``, so there is nothing for this function to do with
            them. The parameter only keeps the signature uniform with the other
            builders in this module, none of which pass their own ``attributes``
            on to this function.
        description: The metric description. ``None`` means ``"foo"``, so a
            test that does not care about the description gets a non-empty one.
        unit: The metric unit. ``None`` means ``"s"``.

    Returns:
        A ``Metric`` carrying the given name, data, description and unit.
    """
    if description is None:
        description = "foo"
    if unit is None:
        unit = "s"
    return Metric(
        name=name,
        description=description,
        unit=unit,
        data=data,
    )


def _generate_sum(
    name,
    value,
    attributes=None,
    description=None,
    unit=None,
    is_monotonic=True,
) -> Metric:
    """Build a ``Metric`` holding one cumulative ``Sum`` data point.

    Args:
        name: The metric name.
        value: The value of the single data point.
        attributes: Attributes of the data point. ``None`` means
            ``{"a": 1, "b": True}`` wrapped in ``BoundedAttributes``, which is
            what an attribute set that has been through the SDK looks like.
        description: The metric description. ``None`` means ``"foo"``.
        unit: The metric unit. ``None`` means ``"s"``.
        is_monotonic: Whether the sum only ever increases, which is what
            distinguishes a counter from an up-down counter.

    Returns:
        A ``Metric`` whose data is a ``Sum`` with cumulative temporality and
        exactly one ``NumberDataPoint``. Its start and end timestamps are fixed
        constants one second apart, so a test can assert on them.
    """
    if attributes is None:
        attributes = BoundedAttributes(attributes={"a": 1, "b": True})
    return _generate_metric(
        name,
        Sum(
            data_points=[
                NumberDataPoint(
                    attributes=attributes,
                    start_time_unix_nano=1641946015139533244,
                    time_unix_nano=1641946016139533244,
                    value=value,
                )
            ],
            aggregation_temporality=AggregationTemporality.CUMULATIVE,
            is_monotonic=is_monotonic,
        ),
        description=description,
        unit=unit,
    )


def _generate_gauge(name, value, attributes=None, description=None, unit=None) -> Metric:
    """Build a ``Metric`` holding one ``Gauge`` data point.

    Args:
        name: The metric name.
        value: The value of the single data point.
        attributes: Attributes of the data point. ``None`` means
            ``{"a": 1, "b": True}`` wrapped in ``BoundedAttributes``.
        description: The metric description. ``None`` means ``"foo"``.
        unit: The metric unit. ``None`` means ``"s"``.

    Returns:
        A ``Metric`` whose data is a ``Gauge`` with exactly one
        ``NumberDataPoint``. Its start timestamp is ``None``, because a gauge
        reports an instantaneous value and has no interval, which is a case an
        exporter has to encode correctly.
    """
    if attributes is None:
        attributes = BoundedAttributes(attributes={"a": 1, "b": True})
    return _generate_metric(
        name,
        Gauge(
            data_points=[
                NumberDataPoint(
                    attributes=attributes,
                    start_time_unix_nano=None,
                    time_unix_nano=1641946016139533244,
                    value=value,
                )
            ],
        ),
        description=description,
        unit=unit,
    )


def _generate_unsupported_metric(name, attributes=None, description=None, unit=None) -> Metric:
    """Build a ``Metric`` whose data is ``None``.

    No instrument produces such a metric. It exists so a test can check that an
    exporter handed a data type it does not recognise drops the metric and
    reports it, rather than raising.

    Args:
        name: The metric name.
        attributes: Ignored. There are no data points to attach attributes to.
        description: The metric description. ``None`` means ``"foo"``.
        unit: The metric unit. ``None`` means ``"s"``.

    Returns:
        A ``Metric`` whose ``data`` attribute is ``None``.
    """
    return _generate_metric(
        name,
        None,
        description=description,
        unit=unit,
    )


def _generate_histogram(
    name: str,
    attributes: Attributes = None,
    description: str | None = None,
    unit: str | None = None,
) -> Metric:
    """Build a ``Metric`` holding one cumulative ``Histogram`` data point.

    Unlike the other builders here, this one takes no value: the counts, sum,
    bounds and extremes of the data point are fixed. It records 6 measurements
    summing to 579.0, spread over the buckets ``[1, 3, 2]`` with boundaries
    ``[123.0, 456.0]``, a minimum of 1 and a maximum of 457.

    Args:
        name: The metric name.
        attributes: Attributes of the data point. ``None`` means
            ``{"a": 1, "b": True}`` wrapped in ``BoundedAttributes``.
        description: The metric description. ``None`` means ``"foo"``.
        unit: The metric unit. ``None`` means ``"s"``.

    Returns:
        A ``Metric`` whose data is a ``Histogram`` with cumulative temporality
        and exactly one ``HistogramDataPoint``. Its start and end timestamps are
        the same fixed constant, so the data point covers a zero-length
        interval.
    """
    if attributes is None:
        attributes = BoundedAttributes(attributes={"a": 1, "b": True})
    return _generate_metric(
        name,
        Histogram(
            data_points=[
                HistogramDataPoint(
                    attributes=attributes,
                    start_time_unix_nano=1641946016139533244,
                    time_unix_nano=1641946016139533244,
                    count=6,
                    sum=579.0,
                    bucket_counts=[1, 3, 2],
                    explicit_bounds=[123.0, 456.0],
                    min=1,
                    max=457,
                )
            ],
            aggregation_temporality=AggregationTemporality.CUMULATIVE,
        ),
        description=description,
        unit=unit,
    )
