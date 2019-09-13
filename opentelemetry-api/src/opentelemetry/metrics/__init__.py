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
from typing import List

from opentelemetry.metrics.time_series import (
    CounterTimeSeries,
    GaugeTimeSeries,
    MeasureTimeSeries,
)
from opentelemetry.trace import SpanContext

LabelKeys = List["LabelKey"]
LabelValues = List[str]


class Meter:
    """An interface to allow the recording of metrics.

    `Metric` s are used for recording pre-defined aggregation (gauge and
    counter), or raw values (measure) in which the aggregation and labels
    for the exported metric are deferred.
    """

    def create_float_counter(
        self,
        name: str,
        description: str,
        unit: str,
        label_keys: LabelKeys,
        span_context: SpanContext = None,
    ) -> "FloatCounter":
        """Creates a counter type metric that contains float values.

        Args:
            name: The name of the counter.
            description: Human readable description of the metric.
            unit: Unit of the metric values.
            label_keys: list of keys for the labels with dynamic values.
                Order of the list is important as the same order MUST be used
                on recording when suppling values for these labels.
            span_context: The `SpanContext` that identifies the `Span`
                that the metric is associated with.

        Returns: A new `FloatCounter`
        """

    def create_int_counter(
        self,
        name: str,
        description: str,
        unit: str,
        label_keys: LabelKeys,
        span_context: SpanContext = None,
    ) -> "IntCounter":
        """Creates a counter type metric that contains int values.

        Args:
            name: The name of the counter.
            description: Human readable description of the metric.
            unit: Unit of the metric values.
            label_keys: list of keys for the labels with dynamic values.
                Order of the list is important as the same order MUST be used
                on recording when suppling values for these labels.
            span_context: The `SpanContext` that identifies the `Span`
                that the metric is associated with.

        Returns:
            A new `IntCounter`
        """

    def create_float_gauge(
        self,
        name: str,
        description: str,
        unit: str,
        label_keys: LabelKeys,
        span_context: SpanContext = None,
    ) -> "FloatGauge":
        """Creates a gauge type metric that contains float values.

        Args:
            name: The name of the counter.
            description: Human readable description of the metric.
            unit: Unit of the metric values.
            label_keys: list of keys for the labels with dynamic values.
                Order of the list is important as the same order MUST be used
                on recording when suppling values for these labels.
            span_context: The `SpanContext` that identifies the `Span`
                that the metric is associated with.

        Returns:
            A new `FloatGauge`
        """

    def create_int_gauge(
        self,
        name: str,
        description: str,
        unit: str,
        label_keys: LabelKeys,
        span_context: SpanContext = None,
    ) -> "IntGauge":
        """Creates a gauge type metric that contains int values.

        Args:
            name: The name of the counter.
            description: Human readable description of the metric.
            unit: Unit of the metric values.
            label_keys: list of keys for the labels with dynamic values.
                Order of the list is important as the same order MUST be used
                on recording when suppling values for these labels.
            span_context: The `SpanContext` that identifies the `Span`
                that the metric is associated with.

        Returns:
            A new `IntGauge`
        """

    def create_int_measure(
        self,
        name: str,
        description: str,
        unit: str,
        label_keys: LabelKeys,
        span_context: SpanContext = None,
    ) -> "IntMeasure":
        """Creates a measure used to record raw int values.

        Args:
            name: The name of the measure.
            description: Human readable description of this measure.
            unit: Unit of the measure values.
            label_keys: list of keys for the labels with dynamic values.
                Order of the list is important as the same order MUST be used
                on recording when suppling values for these labels.
            span_context: The `SpanContext` that identifies the `Span`
                that the metric is associated with.

        Returns:
            A new `IntMeasure`
        """

    def create_float_measure(
        self,
        name: str,
        description: str,
        unit: str,
        label_keys: LabelKeys,
        span_context: SpanContext = None,
    ) -> "FloatMeasure":
        """Creates a Measure used to record raw float values.

        Args:
            name: the name of the measure
            description: Human readable description of this measure.
            unit: Unit of the measure values.
            label_keys: list of keys for the labels with dynamic values.
                Order of the list is important as the same order MUST be used
                on recording when suppling values for these labels.
            span_context: The `SpanContext` that identifies the `Span`
                that the metric is associated with.

        Returns:
            A new `FloatMeasure`
        """


class Metric(ABC):
    """Base class for various types of metrics.

    Metric class that inherit from this class are specialized with the type of
    time series that the metric holds. Metric is constructed from the meter.
    """

    @abstractmethod
    def get_or_create_time_series(self, label_values: LabelValues) -> "object":
        """Gets and returns a timeseries, a container for a cumulative value.

        If the provided label values are not already associated with this
        metric, a new timeseries is returned, otherwise it returns the existing
        timeseries with the exact label values. The timeseries returned
        contains logic and behaviour specific to the type of metric that
        overrides this function.

        Args:
            label_values: A list of label values that will be associated
                with the return timeseries.
        """

    def remove_time_series(self, label_values: LabelValues) -> None:
        """Removes the timeseries from the Metric, if present.

        The timeseries with matching label values will be removed.

        args:
            label_values: The list of label values to match against.
        """

    def clear(self) -> None:
        """Removes all timeseries from the `Metric`."""


class FloatCounter(Metric):
    """A counter type metric that holds float values.

    Cumulative values can go up or stay the same, but can never go down.
    Cumulative values cannot be negative.
    """

    def get_or_create_time_series(
        self, label_values: LabelValues
    ) -> "CounterTimeSeries":
        """Gets a `CounterTimeSeries` with a cumulative float value."""


class IntCounter(Metric):
    """A counter type metric that holds int values.

    Cumulative values can go up or stay the same, but can never go down.
    Cumulative values cannot be negative.
    """

    def get_or_create_time_series(
        self, label_values: LabelValues
    ) -> "CounterTimeSeries":
        """Gets a `CounterTimeSeries` with a cumulative int value."""


class FloatGauge(Metric):
    """A gauge type metric that holds float values.

    Cumulative value can go both up and down. Values can be negative.
    """

    def get_or_create_time_series(
        self, label_values: LabelValues
    ) -> "GaugeTimeSeries":
        """Gets a `GaugeTimeSeries` with a cumulative float value."""


class IntGauge(Metric):
    """A gauge type metric that holds int values.

    Cumulative value can go both up and down. Values can be negative.
    """

    def get_or_create_time_series(
        self, label_values: LabelValues
    ) -> "GaugeTimeSeries":
        """Gets a `GaugeTimeSeries` with a cumulative int value."""


class FloatMeasure(Metric):
    """A measure type metric that holds float values.

    Measure metrics represent raw statistics that are recorded.
    """

    def get_or_create_time_series(
        self, label_values: LabelValues
    ) -> "MeasureTimeSeries":
        """Gets a `MeasureTimeSeries` with a cumulated float value."""


class IntMeasure(Metric):
    """A measure type metric that holds int values.

    Measure metrics represent raw statistics that are recorded.
    """

    def get_or_create_time_series(
        self, label_values: LabelValues
    ) -> "MeasureTimeSeries":
        """Gets a `MeasureTimeSeries` with a cumulated int value."""


class LabelKey:
    """The label keys associated with the metric.

    :type key: str
    :param key: the key for the label

    :type description: str
    :param description: description of the label
    """

    def __init__(self, key: str, description: str) -> None:
        self.key = key
        self.description = description
