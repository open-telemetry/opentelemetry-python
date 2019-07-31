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

import typing

from opentelemetry import loader
from opentelemetry.trace import SpanContext
from opentelemetry.distributedcontext import DistributedContext
from opentelemetry.resources import Resource


class Meter:
    """An interface to allow the recording of measurements and metrics.

    :class:`Measurement`s are used for recording raw values, in which the
    aggregation and labels for the exported metric are defered. This should be
    used to record measurements like "server_latency" or "received_bytes",
    where the value of interest is the recorded value itself.

    :class:`Metric`s are used for recording pre-defined aggregation, or already
    aggregated data. This should be used to report metrics like cpu/memory
    usage, in which the type of aggregation is already defined, or simple
    metrics like "queue_length".

    Initialization of the :class:`Meter` is done through the `meter()` function
    (see below). The meter instance has a singleton implementation.
    """

    def create_double_counter(self,
                              name: str,
                              options: typing.Optional['MetricOptions'] = None
                              ) -> 'CounterDouble':
        """Creates a counter type metric that contains double values.

        Args:
            name: The name of the counter.
            options: An optional :class:`.MetricOptions` used to populate
            details about the counter.

        Returns: A new :class:`.CounterDouble`
        """

    def create_long_counter(self,
                            name: str,
                            options: typing.Optional['MetricOptions'] = None
                            ) -> 'CounterLong':
        """Creates a counter type metric that contains long values.

        Args:
            name: The name of the counter.
            options: An optional :class:`.MetricOptions` used to populate
            details about the counter.

        Returns:
            A new :class:`.CounterLong`
        """

    def create_double_gauge(self,
                            name: str,
                            options: typing.Optional['MetricOptions'] = None
                            ) -> 'GaugeDouble':
        """Creates a gauge type metric that contains double values.

        Args:
            name: The name of the gauge.
            options: An optional :class:`.MetricOptions` used to populate
            details about the gauge.

        Returns:
            A new :class:`.GaugeDouble`
        """

    def create_long_gauge(self,
                          name: str,
                          options: typing.Optional['MetricOptions'] = None
                          ) -> 'GaugeLong':
        """Creates a gauge type metric that contains long values.

        Args:
            name: The name of the gauge.
            options: An optional :class:`.MetricOptions` used to populate
            details about the gauge.

        Returns:
            A new :class:`.GaugeLong`
        """

    def create_measure(self,
                       name: str,
                       options: typing.Optional['MeasureOptions'] = None
                       ) -> 'Measure':
        """Creates a Measure used to record raw :class:`.Measurement`s.

        Args:
            name: the name of the measure
            options: An optional :class:`.MeasureOptions` used to populate
            details about the measure

        Returns:
            A :class:`.Measure`
        """

    def record(self,
               measurements: typing.List['Measurement'],
               options: typing.Optional['RecordOptions'] = None) -> None:
        """A function use to record a set of :class:`.Measurement`s.

        The API is built with the idea that measurement aggregation will occur
        asynchronously. Typical library records multiple measurements at once,
        so this function accepts a collection of measurements so the library
        can batch all of them that need to be recorded.

        Args:
            measurements: The collection of measurements to record. options:
            An optional :class:`.RecordOptions` used to populate details during
            recording.

        Returns: None
        """


_METER: typing.Optional[Meter] = None
_METER_FACTORY: typing.Optional[
    typing.Callable[[typing.Type[Meter]], typing.Optional[Meter]]] = None


def meter() -> Meter:
    """Gets the current global :class:`.Meter` object.

    If there isn't one set yet, a default will be loaded.
    """
    global _METER, _METER_FACTORY  # pylint:disable=global-statement

    if _METER is None:
        # pylint:disable=protected-access
        _METER = loader._load_impl(Meter, _METER_FACTORY)
        del _METER_FACTORY

    return _METER


def set_preferred_meter_implementation(
        factory: typing.Callable[
            [typing.Type[Meter]], typing.Optional[Meter]]
        ) -> None:
    """Set the factory to be used to create the :class:`.Meter`.

    See :mod:`opentelemetry.loader` for details.

    This function may not be called after a meter is already loaded.

    Args:
        factory: Callback that should create a new :class:`.Meter` instance.
    """
    global _METER_FACTORY  # pylint:disable=global-statement

    if _METER:
        raise RuntimeError("Meter already loaded.")

    _METER_FACTORY = factory


class LabelKey:

    def __init__(self,
                 key: str,
                 description: str) -> None:
        self.key = key
        self.description = description


class LabelValue:

    def __init__(self,
                 value: str) -> None:
        self.value = value


class MetricOptions:
    def __init__(self,
                 description: str,
                 unit: str,
                 label_keys: typing.List['LabelKey'],
                 constant_labels: typing.Dict['LabelKey', 'LabelValue'],
                 component: str,
                 resource: 'Resource') -> None:
        """Optional info used when creating a :class:`.Metric`.

        Args:
            description: Human readable description of the metric.
            unit: Unit of the metric values.
            label_keys: list of keys for the labels with dynamic values.
            Order of the list is important as the same order MUST be used
            on recording when suppling values for these labels
            constant_labels: A map of constant labels that will be used for
            all of the TimeSeries created from the Metric.
            component: The name of the component that reports this metric.
            Resource: Sets the :class:`.Resource` associated with this
            Metric.
        """
        self.description = description
        self.unit = unit
        self.label_keys = label_keys
        self.constant_labels = constant_labels
        self.component = component
        self.resource = resource


class MeasureType:
    DOUBLE = 0
    LONG = 1


class MeasureOptions:
    def __init__(self,
                 description: str,
                 unit: str,
                 measure_type: 'MeasureType' = MeasureType.DOUBLE
                 ) -> None:
        """Optional info used when creating a :class:`.Measure`.

        Args:
            description: Human readable description of this measure.
            unit: Unit of the measure values.
            measure_type: Type of the measure. Can be one of two values -
            `LONG` and `DOUBLE`. Default type is `DOUBLE`.
        """
        self.description = description
        self.unit = unit
        self.measure_type = measure_type


class RecordOptions:

    def __init__(self,
                 distributed_context: 'DistributedContext',
                 span_context: 'SpanContext') -> None:
        """Optional info used when recording :class:`.Measurement`s.

        Args:
            distributed_context: Explicit :class:`.DistributedContext` to use
            instead of the current context. Context is used to add dimensions
            for the resulting metric calculated out of the provided
            measurements.
            span_context: the :class:`.SpanContext` that identified the
            :class:`.Span` for which the measurements are associated with.
        """


class Measurement:
    """An empty interface that represents a single value.

    This single value is recorded for the :class:`.Measure` that created
    this measurement.
    """


class Measure:

    def __init__(self,
                 name: str,
                 options: typing.Optional['MeasureOptions'] = None) -> None:
        """Used to create raw :class:`.Measurement`s.

        A contract between the API exposing the raw measurement and SDK
        aggregating these values into the :class:`.Metric`. Measure is
        constructed from the :class:`.Meter` class by providing a set of
        :class:`.MeasureOptions`.
        """
        self.name = name
        if options:
            self.description = options.description
            self.unit = options.unit
            self.measure_type = options.measure_type

    def create_double_measurement(self,
                                  value: float) -> 'Measurement':
        """Creates a measurement that contains double values.

        Args:
            value: The value of the measurement.

        Returns:
            A new :class:`.Measurement`
        """

    def create_long_measurement(self,
                                value: int) -> 'Measurement':
        """Creates a measurement that contains long values.

        Args:
            value: The value of the measurement.

        Returns:
            A new :class:`.Measurement`
        """


class Metric:
    """Base class for various types of metrics.

    Metric class that inherit from this class are specialized with the type of
    time series that the metric holds. Metric is constructed from the
    :class:`.Meter` class, by providing a set of :class:`.MetricOptions`.
    """

    def get_or_create_time_series(self,
                                  label_values: typing.List['LabelValue']
                                  ) -> 'object':
        """Gets and returns a `TimeSeries`, a container for a cumulative value.

        If the provided label values are not already associated with this
        metric, a new timeseries is returned, otherwise it returns the existing
        timeseries with the exact label values. The timeseries returned
        contains logic and behaviour specific to the type of metric that
        overrides this function.

        Args:
            label_values: A map of :class:`.LabelValue`s that will be
            associated with the return timeseries.
        """
        raise NotImplementedError

    def get_default_time_series(self) -> 'object':
        """Returns a `TimeSeries`, a container for a cumulative value.

        The timeseries will have all its labels not set (default).
        """
        raise NotImplementedError

    def set_call_back(self, updater_function: typing.Callable) -> None:
        """Sets a callback that gets executed every time prior to exporting.

        This function MUST set the value of the :class:`.Metric` to the
        value that will be exported.

        args:
            updater_function: The callback function to execute.
        """

    def remove_time_series(self,
                           label_values: typing.List['LabelValue']) -> None:
        """Removes the `TimeSeries` from the :class:`.Metric`, if present.

        The timeseries with matching :class:`.LabelValue`s will be removed.

        args:
            label_values: The list of label values to match against.
        """

    def clear(self) -> None:
        """Removes all `TimeSeries` from the :class:`.Metric`."""


class CounterDouble(Metric):

    def __init__(self,
                 name: str,
                 options: typing.Optional['MetricOptions'] = None
                 ) -> None:
        self.name = name
        if options:
            self.description = options.description
            self.unit = options.unit
            self.label_keys = options.label_keys
            self.constant_labels = options.constant_labels
            self.component = options.component
            self.resource = options.resource

    def get_or_create_time_series(self,
                                  label_values: typing.List['LabelValue']
                                  ) -> 'CounterDouble.TimeSeries':
        """Gets and returns a `TimeSeries`, for a `CounterDouble` metric."""

    def get_default_time_series(self) -> 'CounterDouble.TimeSeries':
        """Returns a `TimeSeries`, for a `CounterDouble` metric."""

    class TimeSeries:

        def add(self, value: float) -> None:
            """Adds the given value to the current value.

            The values cannot be negative.
            """

        def set(self, value: float) -> None:
            """Sets the current value to the given value.

            The given value must be larger than the current recorded value. In
            general should be used in combination with `SetCallback` where the
            recorded value is guaranteed to be monotonically increasing.
            """


class CounterLong(Metric):

    def __init__(self,
                 name: str,
                 options: typing.Optional['MetricOptions'] = None
                 ) -> None:
        self.name = name
        if options:
            self.description = options.description
            self.unit = options.unit
            self.label_keys = options.label_keys
            self.constant_labels = options.constant_labels
            self.component = options.component
            self.resource = options.resource

    def get_or_create_time_series(self,
                                  label_values: typing.List['LabelValue']
                                  ) -> 'CounterLong.TimeSeries':
        """Gets and returns a `TimeSeries`, for a `CounterLong` metric."""

    def get_default_time_series(self) -> 'CounterLong.TimeSeries':
        """Returns a `TimeSeries`, for a `CounterLong` metric."""

    class TimeSeries:

        def add(self, value: float) -> None:
            """Adds the given value to the current value.

            The values cannot be negative.
            """

        def set(self, value: float) -> None:
            """Sets the current value to the given value.

            The given value must be larger than the current recorded value. In
            general should be used in combination with `SetCallback` where the
            recorded value is guaranteed to be monotonically increasing.
            """


class GaugeDouble(Metric):

    def __init__(self,
                 name: str,
                 options: typing.Optional['MetricOptions'] = None
                 ) -> None:
        self.name = name
        if options:
            self.description = options.description
            self.unit = options.unit
            self.label_keys = options.label_keys
            self.constant_labels = options.constant_labels
            self.component = options.component
            self.resource = options.resource

    def get_or_create_time_series(self,
                                  label_values: typing.List['LabelValue']
                                  ) -> 'GaugeDouble.TimeSeries':
        """Gets and returns a `TimeSeries`, for a `GaugeDouble` metric."""

    def get_default_time_series(self) -> 'GaugeDouble.TimeSeries':
        """Returns a `TimeSeries`, for a `GaugeDouble` metric."""

    class TimeSeries:

        def add(self, value: float) -> None:
            """Adds the given value to the current value.

            The values cannot be negative.
            """

        def set(self, value: float) -> None:
            """Sets the current value to the given value.

            The given value must be larger than the current recorded value. In
            general should be used in combination with `SetCallback` where the
            recorded value is guaranteed to be monotonically increasing.
            """


class GaugeLong(Metric):

    def __init__(self,
                 name: str,
                 options: typing.Optional['MetricOptions'] = None
                 ) -> None:
        self.name = name
        if options:
            self.description = options.description
            self.unit = options.unit
            self.label_keys = options.label_keys
            self.constant_labels = options.constant_labels
            self.component = options.component
            self.resource = options.resource

    def get_or_create_time_series(self,
                                  label_values: typing.List['LabelValue']
                                  ) -> 'GaugeLong.TimeSeries':
        """Gets and returns a `TimeSeries`, for a `GaugeLong` metric."""

    def get_default_time_series(self) -> 'GaugeLong.TimeSeries':
        """Returns a `TimeSeries`, for a `GaugeLong` metric."""

    class TimeSeries:

        def add(self, value: float) -> None:
            """Adds the given value to the current value.

            The values cannot be negative.
            """

        def set(self, value: float) -> None:
            """Sets the current value to the given value.

            The given value must be larger than the current recorded value. In
            general should be used in combination with `SetCallback` where the
            recorded value is guaranteed to be monotonically increasing.
            """
