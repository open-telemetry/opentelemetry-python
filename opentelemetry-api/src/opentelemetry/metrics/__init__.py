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

from abc import ABC, abstractmethod
from logging import getLogger
from typing import (
    Callable,
    Dict,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from opentelemetry.util import _load_meter_provider

logger = getLogger(__name__)
ValueT = TypeVar("ValueT", int, float)


class Instrument(ABC):
    """
                            Adding                              Grouping
                            Monotonic       Non Monotonic
    Synchronous     Bound   BoundCounter    BoundUpDownCounter  BoundValueRecorder
                    Unbound Counter         UpDownCounter       ValueRecorder
    Asynchronous            SumObserver     UpDownSumObserver   ValueObserver
    """


class Synchronous(Instrument):
    pass


class Bound(Synchronous):
    @abstractmethod
    def unbind(self):
        pass


class Unbound(Synchronous):

    @abstractmethod
    def bind(self, labels: Dict[str, str]) -> Bound:
        """Gets a bound metric instrument.

        Bound metric instruments are useful to reduce the cost of repeatedly
        recording a metric with a pre-defined set of labels.

        Args:
            labels: Labels that the bound instrument will use when its ``add``
                    or ``record`` method will be called.
        """


class Asynchronous(Instrument):

    @abstractmethod
    def observe(self, value: ValueT) -> None:
        pass


class Adding(Instrument):
    pass


class Grouping(Instrument):
    pass


class Monotonic(Adding):

    def _check_value(self, value):
        """
        Checks that the value does not decrease
        """

        if value < 0:
            raise Exception("negative value found {}".format(value))


class NonMonotonic(Adding):
    pass


class Counter(Unbound, Monotonic):

    @abstractmethod
    def add(self, value: ValueT, labels: Dict[str, str]) -> None:
        """Increases the value of the bound counter by ``value``.

        Args:
            value: The value to add to the instrument. Must be positive.
        """
        self._check_value(value)


class BoundCounter(Bound, Monotonic):
    @abstractmethod
    def add(self, value: ValueT) -> None:
        """Increases the value of the counter by ``value``.

        Args:
            value: The value to add to the counter metric. Should be positive
                or zero. For a Counter that can decrease, use
                `UpDownCounter`.
        """
        self._check_value(value)


class UpDownCounter(Unbound, NonMonotonic):

    @abstractmethod
    def add(self, value: ValueT, labels: Dict[str, str]) -> None:
        """Increases the value of the bound counter by ``value``.

        Args:
            value: The value to add to the instrument.
        """


class BoundUpDownCounter(Bound, NonMonotonic):
    @abstractmethod
    def add(self, value: ValueT) -> None:
        """Increases the value of the counter by ``value``.

        Args:
            value: The value to add to the counter instrument
        """


class ValueRecorder(Unbound, Grouping):

    @abstractmethod
    def record(self, value: ValueT, labels: Dict[str, str]) -> None:
        pass


class BoundValueRecorder(Bound, Grouping):
    @abstractmethod
    def record(self, value: ValueT) -> None:
        """Increases the value of the bound counter by ``value``.

        Args:
            value: The value to add to the bound counter. Must be positive.
        """


class SumObserver(Asynchronous, Monotonic):
    @abstractmethod
    def observe(self, value: ValueT) -> None:
        self._check_value(value)


class UpDownSumObserver(Asynchronous, NonMonotonic):
    @abstractmethod
    def observe(self, value: ValueT) -> None:
        pass


class ValueObserver(Asynchronous, Grouping):
    @abstractmethod
    def observe(self, value: ValueT) -> None:
        pass


class DefaultBound(Bound):
    def unbind(self):
        pass


class DefaultCounter(Counter):
    """The default bound counter instrument.

    Used when no bound counter implementation is available.
    """

    def add(self, value: ValueT) -> None:
        super().add(value)

    def bind(self, labels: Dict[str, str]) -> Bound:
        return DefaultBoundCounter()


class DefaultBoundCounter(BoundCounter, DefaultBound):
    """The default bound counter instrument.

    Used when no bound counter implementation is available.
    """

    def add(self, value: ValueT) -> None:
        super().add(value)


class DefaultUpDownCounter(UpDownCounter):
    """The default bound updowncounter instrument.

    Used when no bound updowncounter implementation is available.
    """

    def add(self, value: ValueT) -> None:
        pass

    def bind(self, labels: Dict[str, str]) -> BoundInstrument:
        return DefaultBoundUpDownCounter()


class DefaultBoundUpDownCounter(BoundUpDownCounter, DefaultBoundInstrument):
    """The default bound updowncounter instrument.

    Used when no bound updowncounter implementation is available.
    """

    def add(self, value: ValueT) -> None:
        pass


class DefaultValueRecorder(ValueRecorder, DefaultBoundInstrument):
    def record(self, value: ValueT) -> None:
        pass

    def bind(self, labels: Dict[str, str]) -> BoundInstrument:
        return DefaultBoundValueRecorder()


class DefaultBoundValueRecorder(BoundValueRecorder, DefaultBoundInstrument):
    """The default bound valuerecorder instrument.

    Used when no bound valuerecorder implementation is available.
    """

    def record(self, value: ValueT) -> None:
        pass


class SumObserver(ABC, MonotonicInstrument):
    """Asynchronous instrument used to capture a monotonic sum."""

    @abstractmethod
    def observe(self, value: ValueT, labels: Dict[str, str]) -> None:
        self._check_value(value)


class UpDownSumObserver(ABC):
    @abstractmethod
    def observe(self, value: ValueT, labels: Dict[str, str]) -> None:
        pass


class ValueObserver(ABC):
    @abstractmethod
    def observe(self, value: ValueT, labels: Dict[str, str]) -> None:
        pass


class DefaultSumObserver(SumObserver):
    """No-op implementation of ``SumObserver``."""

    def observe(self, value: ValueT, labels: Dict[str, str]) -> None:
        pass


# pylint: disable=W0223
class UpDownSumObserver(Observer):
    """Asynchronous instrument used to capture a non-monotonic count."""


class DefaultUpDownSumObserver(UpDownSumObserver):
    """No-op implementation of ``UpDownSumObserver``."""

    def observe(self, value: ValueT, labels: Dict[str, str]) -> None:
        pass


# pylint: disable=W0223
class ValueObserver(Observer):
    """Asynchronous instrument used to capture grouping measurements."""


class DefaultValueObserver(ValueObserver):
    """No-op implementation of ``ValueObserver``."""

    def observe(self, value: ValueT, labels: Dict[str, str]) -> None:
        pass


class MeterProvider(ABC):
    @abstractmethod
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
                ``"opentelemetry.instrumentation.requests"``.

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


InstrumentT = TypeVar("InstrumentT", bound=Union[Metric, Observer])
ObserverCallbackT = Callable[[Observer], None]


# pylint: disable=unused-argument
class Meter(ABC):
    """An interface to allow the recording of metrics.

    `Metric` s or metric instruments, are devices used for capturing raw
    measurements. Each metric instrument supports a single method, each with
    fixed interpretation to capture measurements.
    """

    @abstractmethod
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

    @abstractmethod
    def create_counter(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: Type[ValueT],
        enabled: bool = True,
    ) -> "Counter":
        """Creates a `Counter` metric with type ``value_type``.

        Args:
            name: The name of the metric.
            description: Human-readable description of the metric.
            unit: Unit of the metric values following the UCUM convention
                (https://unitsofmeasure.org/ucum.html).
            value_type: The type of values being recorded by the metric.
            enabled: Whether to report the metric by default.
        """

    @abstractmethod
    def create_updowncounter(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: Type[ValueT],
        enabled: bool = True,
    ) -> "UpDownCounter":
        """Creates a `UpDownCounter` metric with type ``value_type``.

        Args:
            name: The name of the metric.
            description: Human-readable description of the metric.
            unit: Unit of the metric values following the UCUM convention
                (https://unitsofmeasure.org/ucum.html).
            value_type: The type of values being recorded by the metric.
            enabled: Whether to report the metric by default.
        """

    @abstractmethod
    def create_valuerecorder(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: Type[ValueT],
        enabled: bool = True,
    ) -> "ValueRecorder":
        """Creates a `ValueRecorder` metric with type ``value_type``.

        Args:
            name: The name of the metric.
            description: Human-readable description of the metric.
            unit: Unit of the metric values following the UCUM convention
                (https://unitsofmeasure.org/ucum.html).
            value_type: The type of values being recorded by the metric.
            enabled: Whether to report the metric by default.
        """

    @abstractmethod
    def register_sumobserver(
        self,
        callback: ObserverCallbackT,
        name: str,
        description: str,
        unit: str,
        value_type: Type[ValueT],
        label_keys: Sequence[str] = (),
        enabled: bool = True,
    ) -> "SumObserver":
        """Registers an ``SumObserver`` metric instrument.

        Args:
            callback: Callback invoked each collection interval with the
                observer as argument.
            name: The name of the metric.
            description: Human-readable description of the metric.
            unit: Unit of the metric values following the UCUM convention
                (https://unitsofmeasure.org/ucum.html).
            value_type: The type of values being recorded by the metric.
            label_keys: The keys for the labels with dynamic values.
            enabled: Whether to report the metric by default.
        Returns: A new ``SumObserver`` metric instrument.
        """

    @abstractmethod
    def register_updownsumobserver(
        self,
        callback: ObserverCallbackT,
        name: str,
        description: str,
        unit: str,
        value_type: Type[ValueT],
        label_keys: Sequence[str] = (),
        enabled: bool = True,
    ) -> "UpDownSumObserver":
        """Registers an ``UpDownSumObserver`` metric instrument.

        Args:
            callback: Callback invoked each collection interval with the
                observer as argument.
            name: The name of the metric.
            description: Human-readable description of the metric.
            unit: Unit of the metric values following the UCUM convention
                (https://unitsofmeasure.org/ucum.html).
            value_type: The type of values being recorded by the metric.
            label_keys: The keys for the labels with dynamic values.
            enabled: Whether to report the metric by default.
        Returns: A new ``UpDownSumObserver`` metric instrument.
        """

    @abstractmethod
    def register_valueobserver(
        self,
        callback: ObserverCallbackT,
        name: str,
        description: str,
        unit: str,
        value_type: Type[ValueT],
        label_keys: Sequence[str] = (),
        enabled: bool = True,
    ) -> "ValueObserver":
        """Registers an ``ValueObserver`` metric instrument.

        Args:
            callback: Callback invoked each collection interval with the
                observer as argument.
            name: The name of the metric.
            description: Human-readable description of the metric.
            unit: Unit of the metric values following the UCUM convention
                (https://unitsofmeasure.org/ucum.html).
            value_type: The type of values being recorded by the metric.
            label_keys: The keys for the labels with dynamic values.
            enabled: Whether to report the metric by default.
        Returns: A new ``ValueObserver`` metric instrument.
        """

    @abstractmethod
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

    def create_counter(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: Type[ValueT],
        enabled: bool = True,
    ) -> "Counter":
        # pylint: disable=no-self-use
        return DefaultCounter()

    def create_updowncounter(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: Type[ValueT],
        enabled: bool = True,
    ) -> "UpDownCounter":
        # pylint: disable=no-self-use
        return DefaultUpDownCounter()

    def create_valuerecorder(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: Type[ValueT],
        enabled: bool = True,
    ) -> "ValueRecorder":
        # pylint: disable=no-self-use
        return DefaultValueRecorder()

    def register_sumobserver(
        self,
        callback: ObserverCallbackT,
        name: str,
        description: str,
        unit: str,
        value_type: Type[ValueT],
        label_keys: Sequence[str] = (),
        enabled: bool = True,
    ) -> "DefaultSumObserver":
        return DefaultSumObserver()

    def register_updownsumobserver(
        self,
        callback: ObserverCallbackT,
        name: str,
        description: str,
        unit: str,
        value_type: Type[ValueT],
        label_keys: Sequence[str] = (),
        enabled: bool = True,
    ) -> "DefaultUpDownSumObserver":
        return DefaultUpDownSumObserver()

    def register_valueobserver(
        self,
        callback: ObserverCallbackT,
        name: str,
        description: str,
        unit: str,
        value_type: Type[ValueT],
        label_keys: Sequence[str] = (),
        enabled: bool = True,
    ) -> "DefaultValueObserver":
        return DefaultValueObserver()

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

    if _METER_PROVIDER is not None:
        logger.warning("Overriding of current MeterProvider is not allowed")
        return

    _METER_PROVIDER = meter_provider


def get_meter_provider() -> MeterProvider:
    """Gets the current global :class:`~.MeterProvider` object."""
    global _METER_PROVIDER  # pylint: disable=global-statement

    if _METER_PROVIDER is None:
        _METER_PROVIDER = _load_meter_provider("meter_provider")

    return _METER_PROVIDER
