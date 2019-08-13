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

The `Meter` class is used to construct `Measure` s to
record raw measurements and `Metric` s to record metrics with
predefined aggregation.

See the `metrics api`_ spec for terminology and context clarification.

.. _metrics api:
    https://github.com/open-telemetry/opentelemetry-specification/blob/master/specification/api-metrics.md


"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List

from opentelemetry import types
from opentelemetry.metrics.time_series import CounterTimeSeries
from opentelemetry.metrics.time_series import GaugeTimeSeries
from opentelemetry.resources import Resource
from opentelemetry.trace import SpanContext


class Meter:
    """An interface to allow the recording of measurements and metrics.

    `Measurement` s are used for recording raw values, in which the
    aggregation and labels for the exported metric are defered. This should be
    used to record measurements like "server_latency" or "received_bytes",
    where the value of interest is the recorded value itself.

    `Metric` s are used for recording pre-defined aggregation, or
    already aggregated data. This should be used to report metrics like
    cpu/memory usage, in which the type of aggregation is already defined, or
    simple metrics like "queue_length".
    """

    def create_float_counter(self,
                             name: str,
                             description: str,
                             unit: str,
                             label_keys: 'types.LabelKeys',
                             constant_labels: 'types.LabelMap' = None,
                             component: str = None,
                             resource: 'Resource' = None
                             ) -> 'CounterFloat':
        """Creates a counter type metric that contains float values.

        Args:
            name: The name of the counter.
            description: Human readable description of the metric.
            unit: Unit of the metric values.
            label_keys: List of keys for the labels with dynamic values.
                Order of the list is important as the same order MUST be
                used on recording when suppling values for these labels.
            constant_labels: A map of constant labels that will be used for
                all of the TimeSeries created from the Metric.
            component: The name of the component that reports this metric.
            resource: Sets the `Resource` associated with this metric.

        Returns: A new `CounterFloat`
        """

    def create_int_counter(self,
                           name: str,
                           description: str,
                           unit: str,
                           label_keys: 'types.LabelKeys',
                           constant_labels: 'types.LabelMap' = None,
                           component: str = None,
                           resource: 'Resource' = None
                           ) -> 'CounterInt':
        """Creates a counter type metric that contains int values.

        Args:
            name: The name of the counter.
            description: Human readable description of the metric.
            unit: Unit of the metric values.
            label_keys: List of keys for the labels with dynamic values.
                Order of the list is important as the same order MUST be
                used on recording when suppling values for these labels.
            constant_labels: A map of constant labels that will be used for
                all of the TimeSeries created from the Metric.
            component: The name of the component that reports this metric.
            resource: Sets the `Resource` associated with this metric.

        Returns:
            A new `CounterInt`
        """

    def create_float_gauge(self,
                           name: str,
                           description: str,
                           unit: str,
                           label_keys: 'types.LabelKeys',
                           constant_labels: 'types.LabelMap' = None,
                           component: str = None,
                           resource: 'Resource' = None
                           ) -> 'GaugeFloat':
        """Creates a gauge type metric that contains float values.

        Args:
            name: The name of the counter.
            description: Human readable description of the metric.
            unit: Unit of the metric values.
            label_keys: List of keys for the labels with dynamic values.
                Order of the list is important as the same order MUST be
                used on recording when suppling values for these labels.
            constant_labels: A map of constant labels that will be used for
                all of the TimeSeries created from the Metric.
            component: The name of the component that reports this metric.
            resource: Sets the `Resource` associated with this metric.

        Returns:
            A new `GaugeFloat`
        """

    def create_int_gauge(self,
                         name: str,
                         description: str,
                         unit: str,
                         label_keys: 'types.LabelKeys',
                         constant_labels: 'types.LabelMap' = None,
                         component: str = None,
                         resource: 'Resource' = None
                         ) -> 'GaugeInt':
        """Creates a gauge type metric that contains int values.

        Args:
            name: The name of the counter.
            description: Human readable description of the metric.
            unit: Unit of the metric values.
            label_keys: List of keys for the labels with dynamic values.
                Order of the list is important as the same order MUST be
                used on recording when suppling values for these labels.
            constant_labels: A map of constant labels that will be used for
                all of the TimeSeries created from the Metric.
            component: The name of the component that reports this metric.
            resource: Sets the `Resource` associated with this metric.

        Returns:
            A new `GaugeInt`
        """

    def create_int_measure(self,
                           name: str,
                           description: str,
                           unit: str
                           ) -> 'IntMeasure':
        """Creates a measure used to record raw `Measurement` s.
        The measurements created from this measure will have type int.

        Args:
            name: The name of the measure.
            description: Human readable description of this measure.
            unit: Unit of the measure values.

        Returns:
            A `IntMeasure`
        """

    def create_float_measure(self,
                             name: str,
                             description: str,
                             unit: str
                             ) -> 'FloatMeasure':
        """Creates a Measure used to record raw `Measurement` s.
        The measurements created from this measure will have type float.

        Args:
            name: The name of the measure.
            description: Human readable description of this measure.
            unit: Unit of the measure values.

        Returns:
            A `FloatMeasure`
        """

    def record(self,
               measurements: List['Measurement'],
               span_context: 'SpanContext' = None
               ) -> None:
        """Records a set of `Measurement` s.

        The API is built with the idea that measurement aggregation will occur
        asynchronously. Typical library records multiple measurements at once,
        so this function accepts a collection of measurements so the library
        can batch all of them that need to be recorded.

        Args:
            measurements: The collection of measurements to record.
            span_context: The `SpanContext` that identified the `Span`
                for which the measurements are associated with.
            TODO: DistributedContext

        Returns: None
        """


class Measurement:
    """An empty interface that represents a single value.

    This single value is recorded for the `Measure` that created
    this measurement.
    """


class FloatMeasurement(Measurement):
    """A `Measurement` with an float value."""


class IntMeasurement(Measurement):
    """A `Measurement` with an int value."""


class Measure(ABC):
    """Used to create raw `Measurement` s.

    A contract between the API exposing the raw measurement and SDK
    aggregating these values into the `Metric`. Measure is
    constructed from the `Meter` class.
    """
    @abstractmethod
    def create_measurement(self,
                           value: Any
                           ) -> 'Measurement':
        """Creates a measurement.

        The type of the value in the measurement will correspond to the type
        of measure that overrides this method.

        Args:
            value: The value of the measurement.

        Returns:
            A new `Measurement`
        """

class FloatMeasure(Measure):
    """Used to create raw `FloatMeasurement` s."""

    def create_measurement(self,
                           value: float,
                           ) -> 'FloatMeasurement':
        """Creates a measurement with a float type.

        Args:
            value: The value of the measurement.

        Returns:
            A new `FloatMeasurement`
        """

class IntMeasure(Measure):
    """Used to create raw `IntMeasurement` s."""

    def create_measurement(self,
                           value: int,
                           ) -> 'IntMeasurement':
        """Creates a measurement with an int type.

        Args:
            value: The value of the measurement.

        Returns:
            A new `IntMeasurement`
        """


class Metric(ABC):
    """Base class for various types of metrics.

    Metric class that inherit from this class are specialized with the type of
    time series that the metric holds. Metric is constructed from the
    `Meter` class.
    """

    @abstractmethod
    def get_or_create_time_series(self,
                                  label_values: 'types.LabelValues'
                                  ) -> 'object':
        """Gets and returns a timeseries, a container for a cumulative value.

        If the provided label values are not already associated with this
        metric, a new timeseries is returned, otherwise it returns the existing
        timeseries with the exact label values. The timeseries returned
        contains logic and behaviour specific to the type of metric that
        overrides this function.

        Args:
            label_values: A list of `LabelValue` s that will be associated
                with the returned timeseries.
        """

    @abstractmethod
    def get_default_time_series(self) -> 'object':
        """Returns a timeseries, a container for a cumulative value.

        The timeseries will have all its labels not set (default).
        """

    def set_call_back(self,
                      updater_function: Callable[..., None]
                      ) -> None:
        """Sets a callback that gets executed every time prior to exporting.

        This function MUST set the value of the `Metric` to the
        value that will be exported.

        Args:
            updater_function: The callback function to execute.
        """

    def remove_time_series(self,
                           label_values: 'types.LabelValues') -> None:
        """Removes the timeseries from the `Metric`, if present.

        The timeseries with matching `LabelValue` s will be removed.

        Args:
            label_values: The list of label values to match against.
        """

    def clear(self) -> None:
        """Removes all timeseries from the `Metric`."""


class CounterFloat(Metric):
    """A counter type metric that holds float values.

    Cumulative values can go up or stay the same, but can never go down.
    Cumulative values cannot be negative.
    """

    def get_or_create_time_series(self,
                                  label_values: 'types.LabelValues'
                                  ) -> 'CounterTimeSeries':
        """Gets a `CounterTimeSeries` with a cumulated float value.
        
        Args:
            label_values: A list of `LabelValue` s that will be associated
                with the returned timeseries.
        """

    def get_default_time_series(self) -> 'CounterTimeSeries':
        """Returns a `CounterTimeSeries` with a float value."""


class CounterInt(Metric):
    """A counter type metric that holds int values.

    Cumulative values can go up or stay the same, but can never go down.
    Cumulative values cannot be negative.
    """

    def get_or_create_time_series(self,
                                  label_values: 'types.LabelValues'
                                  ) -> 'CounterTimeSeries':
        """Gets a `CounterTimeSeries` with a cumulated int value.

        Args:
            label_values: A list of `LabelValue` s that will be associated
                with the returned timeseries.
        """

    def get_default_time_series(self) -> 'CounterTimeSeries':
        """Returns a `CounterTimeSeries` with a cumulated int value."""

class GaugeFloat(Metric):
    """A gauge type metric that holds float values.

    Cumulative value can go both up and down. Values can be negative.
    """

    def get_or_create_time_series(self,
                                  label_values: 'types.LabelValues'
                                  ) -> 'GaugeTimeSeries':
        """Gets a `GaugeTimeSeries` with a cumulated float value.
                
        Args:
            label_values: A list of `LabelValue` s that will be associated
                with the returned timeseries.
        """

    def get_default_time_series(self) -> 'GaugeTimeSeries':
        """Returns a `GaugeTimeSeries` with a cumulated float value."""


class GaugeInt(Metric):
    """A gauge type metric that holds int values.

    Cumulative value can go both up and down. Values can be negative.
    """

    def get_or_create_time_series(self,
                                  label_values: 'types.LabelValues'
                                  ) -> 'GaugeTimeSeries':
        """Gets a `GaugeTimeSeries` with a cumulated int value.
                
        Args:
            label_values: A list of `LabelValue` s that will be associated
                with the returned timeseries.
        """

    def get_default_time_series(self) -> 'GaugeTimeSeries':
        """Returns a `GaugeTimeSeries` with a cumulated int value."""

class LabelKey:
    """The label keys associated with the metric.

    :type key: str
    :param key: The key for the label.

    :type description: str
    :param description: The description of the label.
    """
    def __init__(self,
                 key: str,
                 description: str) -> None:
        self.key = key
        self.description = description

class LabelValue:
    """The label values associated with a TimeSeries.

    :type value: str
    :param value: The value for the label.
    """
    def __init__(self,
                 value: str) -> None:
        self.value = value
