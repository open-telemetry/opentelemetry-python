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
from typing import Callable, Optional, Tuple, Type, Union

from opentelemetry.util import loader


# pylint: disable=unused-argument
class Meter:
    """An interface to allow the recording of metrics.

    `Metric` s are used for recording pre-defined aggregation (gauge and
    counter), or raw values (measure) in which the aggregation and labels
    for the exported metric are deferred.
    """

    def record_batch(
        self,
        label_values: Tuple[str],
        record_tuples: Tuple[Tuple["Metric", Union[float, int]]],
    ) -> None:
        """Atomically records a batch of `Metric` and value pairs.

        Allows the functionality of acting upon multiple metrics with
        a single API call. Implementations should find metric and handles that
        match the key-value pairs in the label tuples.

        Args:
            label_values: The values that will be matched against to record for
            the handles under each metric that has those labels.
            record_tuples: A tuple of pairs of `Metric` s and the
                corresponding value to record for that metric.
        """


    def create_counter(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: Union[Type[float], Type[int]],
        label_keys: Tuple[str] = None,
        enabled: bool = True,
        monotonic: bool = True,
    ) -> Union["FloatCounter", "IntCounter"]:
        """Creates a counter metric with type value_type.

        Counter metric expresses the computation of a sum. By default, counter
        values can only go up (monotonic). Negative inputs will be discarded
        for monotonic counter metrics. Counter metrics that have a monotonic
        option set to False allows negative inputs.

        Args:
            name: The name of the counter.
            description: Human-readable description of the metric.
            unit: Unit of the metric values.
            value_type: The type of values being recorded by the metric.
            label_keys: The keys for the labels with dynamic values.
                Order of the tuple is important as the same order must be used
                on recording when suppling values for these labels.
            enabled: Whether to report the metric by default.
            monotonic: Whether to only allow non-negative values.

        Returns: A new counter metric for values of the given ``value_type``.
        """


    def create_gauge(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: Union[Type[float], Type[int]],
        label_keys: Tuple[str] = None,
        enabled: bool = True,
        monotonic: bool = False,
    ) -> Union["FloatGauge", "IntGauge"]:
        """Creates a gauge metric with type value_type.

        Gauge metrics express a pre-calculated value that is either `Set()`
        by explicit instrumentation or observed through a callback. This kind
        of metric should be used when the metric cannot be expressed as a sum
        or because the measurement interval is arbitrary.

        By default, gauge values can go both up and down (non-monotonic).
        Negative inputs will be discarded for monotonic gauge metrics.

        Args:
            name: The name of the gauge.
            description: Human-readable description of the metric.
            unit: Unit of the metric values.
            value_type: The type of values being recorded by the metric.
            label_keys: The keys for the labels with dynamic values.
                Order of the tuple is important as the same order must be used
                on recording when suppling values for these labels.
            enabled: Whether to report the metric by default.
            monotonic: Whether to only allow non-negative values.

        Returns: A new gauge metric for values of the given ``value_type``.
        """


    def create_measure(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: Union[Type[float], Type[int]],
        label_keys: Tuple[str] = None,
        enabled: bool = True,
        monotonic: bool = False,
    ) -> Union["FloatMeasure", "IntMeasure"]:
        """Creates a measure metric with type value_type.

        Measure metrics represent raw statistics that are recorded. By
        default, measure metrics can accept both positive and negatives.
        Negative inputs will be discarded when monotonic is True.

        Args:
            name: The name of the measure.
            description: Human-readable description of the metric.
            unit: Unit of the metric values.
            value_type: The type of values being recorded by the metric.
            label_keys: The keys for the labels with dynamic values.
                Order of the tuple is important as the same order must be used
                on recording when suppling values for these labels.
            enabled: Whether to report the metric by default.
            monotonic: Whether to only allow non-negative values.

        Returns: A new measure metric for values of the given ``value_type``.
        """

# Once https://github.com/python/mypy/issues/7092 is resolved,
# the following type definition should be replaced with
# from opentelemetry.util.loader import ImplementationFactory
ImplementationFactory = Callable[
    [Type[Meter]], Optional[Meter]
]

_METER = None
_METER_FACTORY = None

def meter() -> Meter:
    """Gets the current global :class:`~.Meter` object.

    If there isn't one set yet, a default will be loaded.
    """
    global _METER, _METER_FACTORY  # pylint:disable=global-statement

    if _METER is None:
        # pylint:disable=protected-access
        _METER = loader._load_impl(Meter, _METER_FACTORY)
        del _METER_FACTORY

    return _METER


def set_preferred_meter_implementation(
    factory: ImplementationFactory
) -> None:
    """Set the factory to be used to create the meter.

    See :mod:`opentelemetry.util.loader` for details.

    This function may not be called after a meter is already loaded.

    Args:
        factory: Callback that should create a new :class:`Meter` instance.
    """
    global _METER, _METER_FACTORY  # pylint:disable=global-statement

    if _METER:
        raise RuntimeError("Meter already loaded.")

    _METER_FACTORY = factory


class Metric(ABC):
    """Base class for various types of metrics.

    Metric class that inherit from this class are specialized with the type of
    time series that the metric holds.
    """

    @abstractmethod
    def get_handle(self, label_values: Tuple[str]) -> "BaseHandle":
        """Gets a handle, used for repeated-use of metrics instruments.

        Handles are useful to reduce the cost of repeatedly recording a metric
        with a pre-defined set of label values. All metric kinds (counter,
        gauge, measure) support declaring a set of required label keys. The
        values corresponding to these keys should be specified in every handle.
        "Unspecified" label values, in cases where a handle is requested but
        a value was not provided are permitted.

        Args:
            label_values: Values to associate with the returned handle.
        """

    def remove_handle(self, label_values: Tuple[str]) -> None:
        """Removes the handle from the Metric, if present.

        The handle with matching label values will be removed.

        args:
            label_values: The label values to match against.
        """

    def clear(self) -> None:
        """Removes all handles from the `Metric`."""


class FloatCounter(Metric):
    """A counter type metric that holds float values."""

    def get_handle(self, label_values: Tuple[str]) -> "CounterHandle":
        """Gets a `CounterHandle` with a float value."""


class IntCounter(Metric):
    """A counter type metric that holds int values."""

    def get_handle(self, label_values: Tuple[str]) -> "CounterHandle":
        """Gets a `CounterHandle` with an int value."""


class FloatGauge(Metric):
    """A gauge type metric that holds float values."""

    def get_handle(self, label_values: Tuple[str]) -> "GaugeHandle":
        """Gets a `GaugeHandle` with a float value."""


class IntGauge(Metric):
    """A gauge type metric that holds int values."""

    def get_handle(self, label_values: Tuple[str]) -> "GaugeHandle":
        """Gets a `GaugeHandle` with an int value."""


class FloatMeasure(Metric):
    """A measure type metric that holds float values."""

    def get_handle(self, label_values: Tuple[str]) -> "MeasureHandle":
        """Gets a `MeasureHandle` with a float value."""


class IntMeasure(Metric):
    """A measure type metric that holds int values."""

    def get_handle(self, label_values: Tuple[str]) -> "MeasureHandle":
        """Gets a `MeasureHandle` with an int value."""


class BaseHandle:
    """An interface for metric handles."""

    @abstractmethod
    def update(self, value: Union[float, int]) -> None:
        """A generic update method to alter the value of the handle.

            Useful for record_batch, where the type of the handle does not
            matter. Implementation should call the appropriate method that
            alters the underlying data for that handle type.
        """ 


class CounterHandle(BaseHandle):
    def update(self, value: Union[float, int]) -> None:
        """Alters the value of the counter handle.
        
            Implementations should call _add().
        """

    def _add(self, value: Union[float, int]) -> None:
        """Adds the given value to the current value."""


class GaugeHandle(BaseHandle):
    def update(self, value: Union[float, int]) -> None:
        """Alters the value of the gauge handle.
        
            Implementations should call _set().
        """
    def _set(self, value: Union[float, int]) -> None:
        """Sets the current value to the given value. Can be negative."""


class MeasureHandle(BaseHandle):
    def update(self, value: Union[float, int]) -> None:
        """Alters the value of the measure handle.
        
            Implementations should call _record().
        """

    def _record(self, value: Union[float, int]) -> None:
        """Records the given value to this measure."""
