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
from typing import Callable, Optional, Sequence, Tuple, Type, TypeVar

from opentelemetry.util import loader

ValueT = TypeVar("ValueT", int, float)


class DefaultMetricHandle:
    """The default MetricHandle.

    Used when no MetricHandle implementation is available.
    """


class CounterHandle:
    def add(self, value: ValueT) -> None:
        """Increases the value of the handle by ``value``.

        Args:
            value: The value to record to the handle.
        """


class GaugeHandle:
    def set(self, value: ValueT) -> None:
        """Sets the current value of the handle to ``value``.

        Args:
            value: The value to record to the handle.
        """


class MeasureHandle:
    def record(self, value: ValueT) -> None:
        """Records the given ``value`` to this handle.

        Args:
            value: The value to record to the handle.
        """


class Metric:
    """Base class for various types of metrics.

    Metric class that inherit from this class are specialized with the type of
    handle that the metric holds.
    """

    def get_handle(self, label_values: Sequence[str]) -> "object":
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


class DefaultMetric(Metric):
    """The default Metric used when no Metric implementation is available."""

    def get_handle(self, label_values: Sequence[str]) -> "DefaultMetricHandle":
        """Gets a `DefaultMetricHandle`.

        Args:
            label_values: The label values associated with the handle.

        Returns:
            A no-op `DefaultMetricHandle`.
        """
        return DefaultMetricHandle()


class Counter(Metric):
    """A counter type metric that expresses the computation of a sum."""

    def get_handle(self, label_values: Sequence[str]) -> "CounterHandle":
        """Gets a `CounterHandle`."""
        return CounterHandle()

    def add(self, label_values: Sequence[str], value: ValueT) -> None:
        """Increases the value of the counter by ``value``.

        Args:
            label_values: The label values associated with the metric.
            value: The value to add to the counter metric.
        """


class Gauge(Metric):
    """A gauge type metric that expresses a pre-calculated value.

    Gauge metrics have a value that is either ``Set`` by explicit
    instrumentation or observed through a callback. This kind of metric
    should be used when the metric cannot be expressed as a sum or because
    the measurement interval is arbitrary.
    """

    def get_handle(self, label_values: Sequence[str]) -> "GaugeHandle":
        """Gets a `GaugeHandle`."""
        return GaugeHandle()

    def set(self, label_values: Sequence[str], value: ValueT) -> None:
        """Sets the value of the gauge to ``value``.

        Args:
            label_values: The label values associated with the metric.
            value: The value to set the gauge metric to.
        """


class Measure(Metric):
    """A measure type metric that represent raw stats that are recorded.

    Measure metrics represent raw statistics that are recorded. By
    default, measure metrics can accept both positive and negatives.
    Negative inputs will be discarded when monotonic is True.
    """

    def get_handle(self, label_values: Sequence[str]) -> "MeasureHandle":
        """Gets a `MeasureHandle` with a float value."""
        return MeasureHandle()

    def record(self, label_values: Sequence[str], value: ValueT) -> None:
        """Records the ``value`` to the measure.

        Args:
            label_values: The label values associated with the metric.
            value: The value to record to this measure metric.
        """


MetricT = TypeVar("MetricT", Counter, Gauge, Measure)


# pylint: disable=unused-argument
class Meter:
    """An interface to allow the recording of metrics.

    `Metric` s are used for recording pre-defined aggregation (gauge and
    counter), or raw values (measure) in which the aggregation and labels
    for the exported metric are deferred.
    """

    def record_batch(
        self,
        label_values: Sequence[str],
        record_tuples: Sequence[Tuple["Metric", ValueT]],
    ) -> None:
        """Atomically records a batch of `Metric` and value pairs.

        Allows the functionality of acting upon multiple metrics with
        a single API call. Implementations should find metric and handles that
        match the key-value pairs in the label tuples.

        Args:
            label_values: The label values associated with all measurements in
                the batch. A measurement is a tuple, representing the `Metric`
                being recorded and the corresponding value to record.
            record_tuples: A sequence of pairs of `Metric` s and the
                corresponding value to record for that metric.
        """

    def create_metric(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: Type[ValueT],
        metric_type: Type[MetricT],
        label_keys: Sequence[str] = None,
        enabled: bool = True,
        monotonic: bool = False,
    ) -> "Metric":
        """Creates a ``metric_kind`` metric with type ``value_type``.

        Args:
            name: The name of the metric.
            description: Human-readable description of the metric.
            unit: Unit of the metric values.
            value_type: The type of values being recorded by the metric.
            metric_type: The type of metric being created.
            label_keys: The keys for the labels with dynamic values.
                Order of the sequence is important as the same order must be
                used on recording when suppling values for these labels.
            enabled: Whether to report the metric by default.
            monotonic: Whether to only allow non-negative values.

        Returns:
            A new ``metric_type`` metric with values of ``value_type``.
        """
        # pylint: disable=no-self-use
        return DefaultMetric()


# Once https://github.com/python/mypy/issues/7092 is resolved,
# the following type definition should be replaced with
# from opentelemetry.util.loader import ImplementationFactory
ImplementationFactory = Callable[[Type[Meter]], Optional[Meter]]

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


def set_preferred_meter_implementation(factory: ImplementationFactory) -> None:
    """Set the factory to be used to create the meter.

    See :mod:`opentelemetry.util.loader` for details.

    This function may not be called after a meter is already loaded.

    Args:
        factory: Callback that should create a new :class:`Meter` instance.

    Raises:
        RuntimeError: if another meter implementation is already loaded.
    """
    global _METER, _METER_FACTORY  # pylint:disable=global-statement

    if _METER:
        raise RuntimeError("Meter already loaded.")

    _METER_FACTORY = factory
