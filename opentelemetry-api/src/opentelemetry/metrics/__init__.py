# Copyright The OpenTelemetry Authors
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

`Meter` s can be obtained via the `MeterProvider`, corresponding to the name
of the instrumenting library and (optionally) a version.

See the `metrics api`_ spec for terminology and context clarification.

.. _metrics api:
    https://github.com/open-telemetry/opentelemetry-specification/blob/master/specification/metrics/api.md
"""
import abc
from logging import getLogger
from typing import Callable, Dict, Optional, Sequence, Tuple, Type, TypeVar

from opentelemetry.util import _load_meter_provider

logger = getLogger(__name__)
ValueT = TypeVar("ValueT", int, float)


class DefaultBoundInstrument:
    """The default bound metric instrument.

    Used when no bound instrument implementation is available.
    """

    def add(self, value: ValueT) -> None:
        """No-op implementation of `BoundCounter` add.

        Args:
            value: The value to add to the bound metric instrument.
        """

    def record(self, value: ValueT) -> None:
        """No-op implementation of `BoundValueRecorder` record.

        Args:
            value: The value to record to the bound metric instrument.
        """

    def release(self) -> None:
        """No-op implementation of release."""


class BoundCounter:
    def add(self, value: ValueT) -> None:
        """Increases the value of the bound counter by ``value``.

        Args:
            value: The value to add to the bound counter. Must be positive.
        """


class BoundUpDownCounter:
    def add(self, value: ValueT) -> None:
        """Increases the value of the bound counter by ``value``.

        Args:
            value: The value to add to the bound counter. Can be positive or
                negative.
        """


class BoundValueRecorder:
    def record(self, value: ValueT) -> None:
        """Records the given ``value`` to this bound valuerecorder.

        Args:
            value: The value to record to the bound valuerecorder.
        """


class Metric(abc.ABC):
    """Base class for various types of metrics.

    Metric class that inherit from this class are specialized with the type of
    bound metric instrument that the metric holds.
    """

    @abc.abstractmethod
    def bind(self, labels: Dict[str, str]) -> "object":
        """Gets a bound metric instrument.

        Bound metric instruments are useful to reduce the cost of repeatedly
        recording a metric with a pre-defined set of label values.

        Args:
            labels: Labels to associate with the bound instrument.
        """


class DefaultMetric(Metric):
    """The default Metric used when no Metric implementation is available."""

    def bind(self, labels: Dict[str, str]) -> "DefaultBoundInstrument":
        """Gets a `DefaultBoundInstrument`.

        Args:
            labels: Labels to associate with the bound instrument.
        """
        return DefaultBoundInstrument()

    def add(self, value: ValueT, labels: Dict[str, str]) -> None:
        """No-op implementation of `Counter` add.

        Args:
            value: The value to add to the counter metric.
            labels: Labels to associate with the bound instrument.
        """

    def record(self, value: ValueT, labels: Dict[str, str]) -> None:
        """No-op implementation of `ValueRecorder` record.

        Args:
            value: The value to record to this valuerecorder metric.
            labels: Labels to associate with the bound instrument.
        """


class Counter(Metric):
    """A counter type metric that expresses the computation of a sum."""

    def bind(self, labels: Dict[str, str]) -> "BoundCounter":
        """Gets a `BoundCounter`."""
        return BoundCounter()

    def add(self, value: ValueT, labels: Dict[str, str]) -> None:
        """Increases the value of the counter by ``value``.

        Args:
            value: The value to add to the counter metric. Should be positive
                or zero. For a Counter that can decrease, use
                `UpDownCounter`.
            labels: Labels to associate with the bound instrument.
        """


class UpDownCounter(Metric):
    """A counter type metric that expresses the computation of a sum,
    allowing negative increments."""

    def bind(self, labels: Dict[str, str]) -> "BoundUpDownCounter":
        """Gets a `BoundUpDownCounter`."""
        return BoundUpDownCounter()

    def add(self, value: ValueT, labels: Dict[str, str]) -> None:
        """Increases the value of the counter by ``value``.

        Args:
            value: The value to add to the counter metric. Can be positive or
                negative. For a Counter that is never decreasing, use
                `Counter`.
            labels: Labels to associate with the bound instrument.
        """


class ValueRecorder(Metric):
    """A valuerecorder type metric that represent raw stats."""

    def bind(self, labels: Dict[str, str]) -> "BoundValueRecorder":
        """Gets a `BoundValueRecorder`."""
        return BoundValueRecorder()

    def record(self, value: ValueT, labels: Dict[str, str]) -> None:
        """Records the ``value`` to the valuerecorder.

        Args:
            value: The value to record to this valuerecorder metric.
            labels: Labels to associate with the bound instrument.
        """


class Observer(abc.ABC):
    """An observer type metric instrument used to capture a current set of
    values.

    Observer instruments are asynchronous, a callback is invoked with the
    observer instrument as argument allowing the user to capture multiple
    values per collection interval.
    """

    @abc.abstractmethod
    def observe(self, value: ValueT, labels: Dict[str, str]) -> None:
        """Captures ``value`` to the observer.

        Args:
            value: The value to capture to this observer metric.
            labels: Labels associated to ``value``.
        """


class DefaultObserver(Observer):
    """No-op implementation of ``Observer``."""

    def observe(self, value: ValueT, labels: Dict[str, str]) -> None:
        """Captures ``value`` to the observer.

        Args:
            value: The value to capture to this observer metric.
            labels: Labels associated to ``value``.
        """


class SumObserver(Observer):
    """No-op implementation of ``SumObserver``."""

    def observe(self, value: ValueT, labels: Dict[str, str]) -> None:
        """Captures ``value`` to the sumobserver.

        Args:
            value: The value to capture to this sumobserver metric.
            labels: Labels associated to ``value``.
        """


class UpDownSumObserver(Observer):
    """No-op implementation of ``UpDownSumObserver``."""

    def observe(self, value: ValueT, labels: Dict[str, str]) -> None:
        """Captures ``value`` to the updownsumobserver.

        Args:
            value: The value to capture to this updownsumobserver metric.
            labels: Labels associated to ``value``.
        """


class ValueObserver(Observer):
    """No-op implementation of ``ValueObserver``."""

    def observe(self, value: ValueT, labels: Dict[str, str]) -> None:
        """Captures ``value`` to the valueobserver.

        Args:
            value: The value to capture to this valueobserver metric.
            labels: Labels associated to ``value``.
        """


class MeterProvider(abc.ABC):
    @abc.abstractmethod
    def get_meter(
        self,
        instrumenting_module_name: str,
        instrumenting_library_version: str = "",
    ) -> "Meter":
        """Returns a `Meter` for use by the given instrumentation library.

        This function may return different `Meter` types (e.g. a no-op meter
        vs. a functional meter).

        Args:
            instrumenting_module_name: The name of the instrumenting module
                (usually just ``__name__``).

                This should *not* be the name of the module that is
                instrumented but the name of the module doing the instrumentation.
                E.g., instead of ``"requests"``, use
                ``"opentelemetry.ext.requests"``.

            instrumenting_library_version: Optional. The version string of the
                instrumenting library.  Usually this should be the same as
                ``pkg_resources.get_distribution(instrumenting_library_name).version``.
        """


class DefaultMeterProvider(MeterProvider):
    """The default MeterProvider, used when no implementation is available.

    All operations are no-op.
    """

    def get_meter(
        self,
        instrumenting_module_name: str,
        instrumenting_library_version: str = "",
    ) -> "Meter":
        # pylint:disable=no-self-use,unused-argument
        return DefaultMeter()


MetricT = TypeVar("MetricT", Counter, ValueRecorder)
InstrumentT = TypeVar(
    "InstrumentT", Counter, UpDownCounter, Observer, ValueRecorder
)
ObserverT = TypeVar("ObserverT", bound=Observer)
ObserverCallbackT = Callable[[Observer], None]


# pylint: disable=unused-argument
class Meter(abc.ABC):
    """An interface to allow the recording of metrics.

    `Metric` s or metric instruments, are devices used for capturing raw
    measurements. Each metric instrument supports a single method, each with
    fixed interpretation to capture measurements.
    """

    @abc.abstractmethod
    def record_batch(
        self,
        labels: Dict[str, str],
        record_tuples: Sequence[Tuple["Metric", ValueT]],
    ) -> None:
        """Atomically records a batch of `Metric` and value pairs.

        Allows the functionality of acting upon multiple metrics with a single
        API call. Implementations should find bound metric instruments that
        match the key-value pairs in the labels.

        Args:
            labels: Labels associated with all measurements in the
                batch.
            record_tuples: A sequence of pairs of `Metric` s and the
                corresponding value to record for that metric.
        """

    @abc.abstractmethod
    def create_metric(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: Type[ValueT],
        metric_type: Type[MetricT],
        label_keys: Sequence[str] = (),
        enabled: bool = True,
    ) -> "Metric":
        """Creates a ``metric_kind`` metric with type ``value_type``.

        Args:
            name: The name of the metric.
            description: Human-readable description of the metric.
            unit: Unit of the metric values following the UCUM convention
                (https://unitsofmeasure.org/ucum.html).
            value_type: The type of values being recorded by the metric.
            metric_type: The type of metric being created.
            label_keys: The keys for the labels with dynamic values.
            enabled: Whether to report the metric by default.
        Returns: A new ``metric_type`` metric with values of ``value_type``.
        """

    @abc.abstractmethod
    def register_observer(
        self,
        callback: ObserverCallbackT,
        name: str,
        description: str,
        unit: str,
        value_type: Type[ValueT],
        observer_type: Type[ObserverT],
        label_keys: Sequence[str] = (),
        enabled: bool = True,
    ) -> "Observer":
        """Registers an ``Observer`` metric instrument.

        Args:
            callback: Callback invoked each collection interval with the
                observer as argument.
            name: The name of the metric.
            description: Human-readable description of the metric.
            unit: Unit of the metric values following the UCUM convention
                (https://unitsofmeasure.org/ucum.html).
            value_type: The type of values being recorded by the metric.
            observer_type: The type of observer being registered.
            label_keys: The keys for the labels with dynamic values.
            enabled: Whether to report the metric by default.
        Returns: A new ``Observer`` metric instrument.
        """

    @abc.abstractmethod
    def unregister_observer(self, observer: "Observer") -> None:
        """Unregisters an ``Observer`` metric instrument.

        Args:
            observer: The observer to unregister.
        """


class DefaultMeter(Meter):
    """The default Meter used when no Meter implementation is available."""

    def record_batch(
        self,
        labels: Dict[str, str],
        record_tuples: Sequence[Tuple["Metric", ValueT]],
    ) -> None:
        pass

    def create_metric(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: Type[ValueT],
        metric_type: Type[MetricT],
        label_keys: Sequence[str] = (),
        enabled: bool = True,
    ) -> "Metric":
        # pylint: disable=no-self-use
        return DefaultMetric()

    def register_observer(
        self,
        callback: ObserverCallbackT,
        name: str,
        description: str,
        unit: str,
        value_type: Type[ValueT],
        observer_type: Type[ObserverT],
        label_keys: Sequence[str] = (),
        enabled: bool = True,
    ) -> "Observer":
        return DefaultObserver()

    def unregister_observer(self, observer: "Observer") -> None:
        pass


_METER_PROVIDER = None


def get_meter(
    instrumenting_module_name: str,
    instrumenting_library_version: str = "",
    meter_provider: Optional[MeterProvider] = None,
) -> "Meter":
    """Returns a `Meter` for use by the given instrumentation library.
    This function is a convenience wrapper for
    opentelemetry.metrics.get_meter_provider().get_meter

    If meter_provider is omitted the current configured one is used.
    """
    if meter_provider is None:
        meter_provider = get_meter_provider()
    return meter_provider.get_meter(
        instrumenting_module_name, instrumenting_library_version
    )


def set_meter_provider(meter_provider: MeterProvider) -> None:
    """Sets the current global :class:`~.MeterProvider` object."""
    global _METER_PROVIDER  # pylint: disable=global-statement
    _METER_PROVIDER = meter_provider


def get_meter_provider() -> MeterProvider:
    """Gets the current global :class:`~.MeterProvider` object."""
    global _METER_PROVIDER  # pylint: disable=global-statement

    if _METER_PROVIDER is None:
        _METER_PROVIDER = _load_meter_provider("meter_provider")

    return _METER_PROVIDER
