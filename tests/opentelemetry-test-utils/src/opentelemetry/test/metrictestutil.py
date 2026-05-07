# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0


from opentelemetry.attributes import BoundedAttributes
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    DataPointFlags,
    Gauge,
    Histogram,
    HistogramDataPoint,
    Metric,
    NumberDataPoint,
    Sum,
)
from opentelemetry.util.types import Attributes


def _generate_metric(
    name, data, attributes=None, description=None, unit=None
) -> Metric:
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
    flags=None,
) -> Metric:
    if attributes is None:
        attributes = BoundedAttributes(attributes={"a": 1, "b": True})
    if flags is None:
        flags = DataPointFlags.get_default()
    return _generate_metric(
        name,
        Sum(
            data_points=[
                NumberDataPoint(
                    attributes=attributes,
                    start_time_unix_nano=1641946015139533244,
                    time_unix_nano=1641946016139533244,
                    value=value,
                    flags=flags,
                )
            ],
            aggregation_temporality=AggregationTemporality.CUMULATIVE,
            is_monotonic=is_monotonic,
        ),
        description=description,
        unit=unit,
    )


def _generate_gauge(
    name,
    value,
    attributes=None,
    description=None,
    unit=None,
    flags=None,
) -> Metric:
    if attributes is None:
        attributes = BoundedAttributes(attributes={"a": 1, "b": True})
    if flags is None:
        flags = DataPointFlags.get_default()
    return _generate_metric(
        name,
        Gauge(
            data_points=[
                NumberDataPoint(
                    attributes=attributes,
                    start_time_unix_nano=None,
                    time_unix_nano=1641946016139533244,
                    value=value,
                    flags=flags,
                )
            ],
        ),
        description=description,
        unit=unit,
    )


def _generate_unsupported_metric(
    name, attributes=None, description=None, unit=None
) -> Metric:
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
    flags: DataPointFlags | None = None,
) -> Metric:
    if attributes is None:
        attributes = BoundedAttributes(attributes={"a": 1, "b": True})
    if flags is None:
        flags = DataPointFlags.get_default()
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
                    flags=flags,
                )
            ],
            aggregation_temporality=AggregationTemporality.CUMULATIVE,
        ),
        description=description,
        unit=unit,
    )
