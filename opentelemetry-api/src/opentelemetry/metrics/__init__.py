# Copyright 2019, OpenTelemetry Authors
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

"""
The OpenTelemetry metrics API describes the classes used to report raw
measurements, as well as metrics with known aggregation and labels.

The `Meter` class is used to construct `Metric` s to record raw statistics
as well as metrics with predefined aggregation.

See the `metrics api`_ spec for terminology and context clarification.

.. _metrics api:
    https://github.com/open-telemetry/opentelemetry-specification/blob/master/specification/api-metrics.md


"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Union

from opentelemetry.metrics.time_series import (
    CounterTimeSeries,
    GaugeTimeSeries,
    MeasureTimeSeries,
)
from opentelemetry.trace import SpanContext


# pylint: disable=unused-argument
class Meter:
    """An interface to allow the recording of metrics.

    `Metric` s are used for recording pre-defined aggregation (gauge and
    counter), or raw values (measure) in which the aggregation and labels
    for the exported metric are deferred.
    """

    # TODO: RecordBatch


class ValueType(Enum):
    FLOAT = 0
    INT = 1


def create_counter(
    name: str,
    description: str,
    unit: str,
    value_type: "ValueType",
    is_bidirectional: bool = False,
    label_keys: List[str] = None,
    span_context: SpanContext = None,
) -> Union["FloatCounter", "IntCounter"]:
    """Creates a counter metric with type value_type.

    By default, counter values can only go up (unidirectional). The API
    should reject negative inputs to unidirectional counter metrics.
    Counter metrics have a bidirectional option to allow for negative
    inputs.

    Args:
        name: The name of the counter.
        description: Human readable description of the metric.
        unit: Unit of the metric values.
        value_type: The type of values being recorded by the metric.
        is_bidirectional: Set to true to allow negative inputs.
        label_keys: list of keys for the labels with dynamic values.
            Order of the list is important as the same order must be used
            on recording when suppling values for these labels.
        span_context: The `SpanContext` that identifies the `Span`
            that the metric is associated with.

    Returns: A new counter metric for values of the given value_type.
    """


def create_gauge(
    name: str,
    description: str,
    unit: str,
    value_type: "ValueType",
    is_unidirectional: bool = False,
    label_keys: List[str] = None,
    span_context: SpanContext = None,
) -> Union["FloatGauge", "IntGauge"]:
    """Creates a gauge metric with type value_type.

    By default, gauge values can go both up and down (bidirectional). The API
    allows for an optional unidirectional flag, in which when set will reject
    descending update values.

    Args:
        name: The name of the gauge.
        description: Human readable description of the metric.
        unit: Unit of the metric values.
        value_type: The type of values being recorded by the metric.
        is_unidirectional: Set to true to reject negative inputs.
        label_keys: list of keys for the labels with dynamic values.
            Order of the list is important as the same order must be used
            on recording when suppling values for these labels.
        span_context: The `SpanContext` that identifies the `Span`
            that the metric is associated with.

    Returns: A new gauge metric for values of the given value_type.
    """


def create_measure(
    name: str,
    description: str,
    unit: str,
    value_type: "ValueType",
    is_non_negative: bool = False,
    label_keys: List[str] = None,
    span_context: SpanContext = None,
) -> Union["FloatMeasure", "IntMeasure"]:
    """Creates a measure metric with type value_type.

    Measure metrics represent raw statistics that are recorded. As an option,
    measure metrics can be declared as non-negative. The API will reject
    negative metric events for non-negative measures.

    Args:
        name: The name of the measure.
        description: Human readable description of the metric.
        unit: Unit of the metric values.
        value_type: The type of values being recorded by the metric.
        is_non_negative: Set to true to reject negative inputs.
        label_keys: list of keys for the labels with dynamic values.
            Order of the list is important as the same order must be used
            on recording when suppling values for these labels.
        span_context: The `SpanContext` that identifies the `Span`
            that the metric is associated with.

    Returns: A new measure metric for values of the given value_type.
    """


class Metric(ABC):
    """Base class for various types of metrics.

    Metric class that inherit from this class are specialized with the type of
    time series that the metric holds.
    """

    @abstractmethod
    def get_or_create_time_series(self, label_values: List[str]) -> "object":
        """Gets a timeseries, used for repeated-use of metrics instruments.

        If the provided label values are not already associated with this
        metric, a new timeseries is returned, otherwise it returns the existing
        timeseries with the exact label values. The timeseries returned
        contains logic and behaviour specific to the type of metric that
        overrides this function.

        Args:
            label_values: A list of label values that will be associated
                with the return timeseries.
        """

    def remove_time_series(self, label_values: List[str]) -> None:
        """Removes the timeseries from the Metric, if present.

        The timeseries with matching label values will be removed.

        args:
            label_values: The list of label values to match against.
        """

    def clear(self) -> None:
        """Removes all timeseries from the `Metric`."""


class FloatCounter(Metric):
    """A counter type metric that holds float values."""

    def get_or_create_time_series(
        self, label_values: List[str]
    ) -> "CounterTimeSeries":
        """Gets a `CounterTimeSeries` with a float value."""


class IntCounter(Metric):
    """A counter type metric that holds int values."""

    def get_or_create_time_series(
        self, label_values: List[str]
    ) -> "CounterTimeSeries":
        """Gets a `CounterTimeSeries` with an int value."""


class FloatGauge(Metric):
    """A gauge type metric that holds float values."""

    def get_or_create_time_series(
        self, label_values: List[str]
    ) -> "GaugeTimeSeries":
        """Gets a `GaugeTimeSeries` with a float value."""


class IntGauge(Metric):
    """A gauge type metric that holds int values."""

    def get_or_create_time_series(
        self, label_values: List[str]
    ) -> "GaugeTimeSeries":
        """Gets a `GaugeTimeSeries` with an int value."""


class FloatMeasure(Metric):
    """A measure type metric that holds float values."""

    def get_or_create_time_series(
        self, label_values: List[str]
    ) -> "MeasureTimeSeries":
        """Gets a `MeasureTimeSeries` with a float value."""


class IntMeasure(Metric):
    """A measure type metric that holds int values."""

    def get_or_create_time_series(
        self, label_values: List[str]
    ) -> "MeasureTimeSeries":
        """Gets a `MeasureTimeSeries` with an int value."""
