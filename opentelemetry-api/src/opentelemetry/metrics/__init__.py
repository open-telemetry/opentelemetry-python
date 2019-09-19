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
from typing import Dict, List, Tuple, Type, Union

from opentelemetry.metrics.handle import (
    CounterHandle,
    GaugeHandle,
    MeasureHandle,
)
from opentelemetry.trace import SpanContext


# pylint: disable=unused-argument
class Meter:
    """An interface to allow the recording of metrics.

    `Metric` s are used for recording pre-defined aggregation (gauge and
    counter), or raw values (measure) in which the aggregation and labels
    for the exported metric are deferred.
    """

    def record_batch(
        self,
        label_tuples: Dict[str, str],
        record_tuples: List[Tuple["Metric", Union[float, int]]],
    ) -> None:
        """Atomically records a batch of `Metric` and value pairs.

        Allows the functionality of acting upon multiple metrics with
        a single API call. Implementations should find handles that match
        the key-value pairs in the label tuples.

        Args:
            label_tuples: A collection of key value pairs that will be matched
                against to record for the metric-handle that has those labels.
            record_tuples: A list of pairs of `Metric` s and the
                corresponding value to record for that metric.
        """


    def create_counter(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: Union[Type[float], Type[int]],
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
        self,
        name: str,
        description: str,
        unit: str,
        value_type: Union[Type[float], Type[int]],
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
        self,
        name: str,
        description: str,
        unit: str,
        value_type: Union[Type[float], Type[int]],
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
    def get_handle(self, label_values: List[str]) -> "object":
        """Gets a handle, used for repeated-use of metrics instruments.

        Handles are useful to reduce the cost of repeatedly recording a metric
        with a pre-defined set of label values. All metric kinds (counter,
        gauge, measure) support declaring a set of required label keys. The
        values corresponding to these keys should be specified in every handle.
        "Unspecified" label values, in cases where a handle is requested but
        a value was not provided are permitted.

        Args:
            label_values: A list of label values that will be associated
                with the return handle.
        """

    def remove_handle(self, label_values: List[str]) -> None:
        """Removes the handle from the Metric, if present.

        The handle with matching label values will be removed.

        args:
            label_values: The list of label values to match against.
        """

    def clear(self) -> None:
        """Removes all handles from the `Metric`."""


class FloatCounter(Metric):
    """A counter type metric that holds float values."""

    def get_handle(self, label_values: List[str]) -> "CounterHandle":
        """Gets a `CounterHandle` with a float value."""


class IntCounter(Metric):
    """A counter type metric that holds int values."""

    def get_handle(self, label_values: List[str]) -> "CounterHandle":
        """Gets a `CounterHandle` with an int value."""


class FloatGauge(Metric):
    """A gauge type metric that holds float values."""

    def get_handle(self, label_values: List[str]) -> "GaugeHandle":
        """Gets a `GaugeHandle` with a float value."""


class IntGauge(Metric):
    """A gauge type metric that holds int values."""

    def get_handle(self, label_values: List[str]) -> "GaugeHandle":
        """Gets a `GaugeHandle` with an int value."""


class FloatMeasure(Metric):
    """A measure type metric that holds float values."""

    def get_handle(self, label_values: List[str]) -> "MeasureHandle":
        """Gets a `MeasureHandle` with a float value."""


class IntMeasure(Metric):
    """A measure type metric that holds int values."""

    def get_handle(self, label_values: List[str]) -> "MeasureHandle":
        """Gets a `MeasureHandle` with an int value."""


class CounterHandle:
    def add(self, value: Union[float, int]) -> None:
        """Adds the given value to the current value.

        The input value cannot be negative if not bidirectional.
        """


class GaugeHandle:
    def set(self, value: Union[float, int]) -> None:
        """Sets the current value to the given value. Can be negative."""


class MeasureHandle:
    def record(self, value: Union[float, int]) -> None:
        """Records the given value to this measure."""
