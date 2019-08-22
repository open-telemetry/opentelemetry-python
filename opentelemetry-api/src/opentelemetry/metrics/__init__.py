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
from typing import Any, Callable, Dict, List

from opentelemetry.metrics.aggregation import Aggregation
from opentelemetry.metrics.time_series import CounterTimeSeries
from opentelemetry.metrics.time_series import GaugeTimeSeries
from opentelemetry.metrics.time_series import MeasureTimeSeries
from opentelemetry.trace import SpanContext

LabelKeys = List['LabelKey']
LabelValues = List['LabelValue']


class Meter:
    """An interface to allow the recording of metrics.

    `Metric` s are used for recording pre-defined aggregation (gauge and
    counter), or raw values (measure) in which the aggregation and labels
    for the exported metric are deferred.
    """

    def create_float_counter(self,
                             name: str,
                             description: str,
                             unit: str,
                             label_keys: LabelKeys,
                             span_context: SpanContext = None
                             ) -> 'CounterFloat':
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

        Returns: A new `CounterFloat`
        """

    def create_int_counter(self,
                           name: str,
                           description: str,
                           unit: str,
                           label_keys: LabelKeys,
                           span_context: SpanContext = None
                           ) -> 'CounterInt':
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
            A new `CounterInt`
        """

    def create_float_gauge(self,
                           name: str,
                           description: str,
                           unit: str,
                           label_keys: LabelKeys,
                           span_context: SpanContext = None
                           ) -> 'GaugeFloat':
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
            A new `GaugeFloat`
        """

    def create_int_gauge(self,
                         name: str,
                         description: str,
                         unit: str,
                         label_keys: LabelKeys,
                         span_context: SpanContext = None
                         ) -> 'GaugeInt':
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
            A new `GaugeInt`
        """

    def create_int_measure(self,
                           name: str,
                           description: str,
                           unit: str,
                           label_keys: LabelKeys,
                           aggregation: 'Aggregation',
                           span_context: SpanContext = None,
                           ) -> 'MeasureInt':
        """Creates a measure used to record raw int values.

        Args:
            name: The name of the measure.
            description: Human readable description of this measure.
            unit: Unit of the measure values.
            label_keys: list of keys for the labels with dynamic values.
                Order of the list is important as the same order MUST be used
                on recording when suppling values for these labels.
            aggregation: The type of aggregation to use for this measure metric.
            span_context: The `SpanContext` that identifies the `Span`
                that the metric is associated with.

        Returns:
            A new `MeasureInt`
        """

    def create_float_measure(self,
                             name: str,
                             description: str,
                             unit: str,
                             label_keys: LabelKeys,
                             aggregation: 'Aggregation',
                             span_context: SpanContext = None,
                             ) -> 'MeasureFloat':
        """Creates a Measure used to record raw float values.

        Args:
            name: the name of the measure
            description: Human readable description of this measure.
            unit: Unit of the measure values.
            label_keys: list of keys for the labels with dynamic values.
                Order of the list is important as the same order MUST be used
                on recording when suppling values for these labels.
            aggregation: The type of aggregation to use for this measure metric.
            span_context: The `SpanContext` that identifies the `Span`
                that the metric is associated with.

        Returns:
            A new `MeasureFloat`
        """


class Metric(ABC):
    """Base class for various types of metrics.

    Metric class that inherit from this class are specialized with the type of
    time series that the metric holds. Metric is constructed from the meter.
    """

    @abstractmethod
    def get_or_create_time_series(self,
                                  label_values: LabelValues
                                  ) -> 'object':
        """Gets and returns a timeseries, a container for a cumulative value.

        If the provided label values are not already associated with this
        metric, a new timeseries is returned, otherwise it returns the existing
        timeseries with the exact label values. The timeseries returned
        contains logic and behaviour specific to the type of metric that
        overrides this function.

        Args:
            label_values: A map of `LabelValue` s that will be associated
                with the return timeseries.
        """

    def remove_time_series(self,
                           label_values: LabelValues) -> None:
        """Removes the timeseries from the Metric, if present.

        The timeseries with matching `LabelValue` s will be removed.

        args:
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
                                  label_values: LabelValues
                                  ) -> 'CounterTimeSeries':
        """Gets a `CounterTimeSeries` with a cumulative float value."""


class CounterInt(Metric):
    """A counter type metric that holds int values.

    Cumulative values can go up or stay the same, but can never go down.
    Cumulative values cannot be negative.
    """

    def get_or_create_time_series(self,
                                  label_values: LabelValues
                                  ) -> 'CounterTimeSeries':
        """Gets a `CounterTimeSeries` with a cumulative int value."""


class GaugeFloat(Metric):
    """A gauge type metric that holds float values.

    Cumulative value can go both up and down. Values can be negative.
    """

    def get_or_create_time_series(self,
                                  label_values: LabelValues
                                  ) -> 'GaugeTimeSeries':
        """Gets a `GaugeTimeSeries` with a cumulative float value."""


class GaugeInt(Metric):
    """A gauge type metric that holds int values.

    Cumulative value can go both up and down. Values can be negative.
    """

    def get_or_create_time_series(self,
                                  label_values: LabelValues
                                  ) -> 'GaugeTimeSeries':
        """Gets a `GaugeTimeSeries` with a cumulative int value."""


class MeasureFloat(Metric):
    """A measure type metric that holds float values.

    Measure metrics represent raw statistics that are recorded.
    """

    def get_or_create_time_series(self,
                                  label_values: LabelValues
                                  ) -> 'MeasureTimeSeries':
        """Gets a `MeasureTimeSeries` with a cumulated float value."""


class MeasureInt(Metric):
    """A measure type metric that holds int values.

    Measure metrics represent raw statistics that are recorded.
    """

    def get_or_create_time_series(self,
                                  label_values: LabelValues
                                  ) -> 'MeasureTimeSeries':
        """Gets a `MeasureTimeSeries` with a cumulated int value."""


class MeasureBatch:

    def record(self, metric_pairs):
        """Records multiple observed values simultaneously.

        Args:
            metric_pairs: A list of tuples containing the `Metric` and value
                to be recorded.
        """


class LabelKey:
    """The label keys associated with the metric.

    :type key: str
    :param key: the key for the label

    :type description: str
    :param description: description of the label
    """
    def __init__(self,
                 key: str,
                 description: str) -> None:
        self.key = key
        self.description = description


class LabelValue:
    """The label values associated with a TimeSeries.

    :type value: str
    :param value: the value for the label
    """
    def __init__(self,
                 value: str) -> None:
        self.value = value