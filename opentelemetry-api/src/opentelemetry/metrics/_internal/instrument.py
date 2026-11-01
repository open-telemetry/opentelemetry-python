# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=too-many-ancestors
# pylint: disable=too-many-lines

"""The instrument types a meter hands out, and their no-op implementations.

An instrument records measurements of one kind. A synchronous instrument is
called at the moment something happens, for example
:meth:`~opentelemetry.metrics.Counter.add`. An asynchronous instrument is
given callbacks instead, and the SDK invokes them when it collects.

Each instrument type here has two implementations beside the abstract one. The
``NoOp`` variant discards every measurement and is what a
:class:`~opentelemetry.metrics.NoOpMeter` returns. The ``_Proxy`` variant is
what a meter returns before a real
:class:`~opentelemetry.metrics.MeterProvider` is set, which is the state with
no SDK installed, and it swaps itself for a real instrument once one is set.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable, Generator, Iterable, Sequence
from dataclasses import dataclass
from logging import getLogger
from re import compile as re_compile
from typing import (
    Generic,
    TypeVar,
)

# pylint: disable=unused-import; needed for typing and sphinx
from opentelemetry import metrics
from opentelemetry.context import Context
from opentelemetry.metrics._internal.observation import Observation
from opentelemetry.util.types import (
    Attributes,
)

_logger = getLogger(__name__)

_name_regex = re_compile(r"[a-zA-Z][-_./a-zA-Z0-9]{0,254}")
_unit_regex = re_compile(r"[\x00-\x7F]{0,63}")


@dataclass(frozen=True)
class _MetricsHistogramAdvisory:
    """A hint to the SDK about how a histogram should bucket its values.

    An advisory is a suggestion rather than a setting. A view configured on
    the SDK overrides it.

    Args:
        explicit_bucket_boundaries: The bucket boundaries the instrument
            suggests, in ascending order. ``None`` leaves the choice to the
            SDK.
    """

    explicit_bucket_boundaries: Sequence[float] | None = None


@dataclass(frozen=True)
class CallbackOptions:
    """Options for the callback

    Args:
        timeout_millis: Timeout for the callback's execution. If the callback does asynchronous
            work (e.g. HTTP requests), it should respect this timeout.
    """

    timeout_millis: float = 10_000


InstrumentT = TypeVar("InstrumentT", bound="Instrument")
# pylint: disable=invalid-name
CallbackT = Callable[[CallbackOptions], Iterable[Observation]] | Generator[Iterable[Observation], CallbackOptions, None]


class Instrument(ABC):
    """Abstract class that serves as base for all instruments.

    Args:
        name: The name of the instrument, which must match
            ``[a-zA-Z][-_./a-zA-Z0-9]{0,254}``.
        unit: The unit of the measurements, as at most 63 ASCII
            characters.
        description: A human-readable description of what the instrument
            measures.
    """

    @abstractmethod
    def __init__(
        self,
        name: str,
        unit: str = "",
        description: str = "",
    ) -> None:
        """Build the instrument.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """

    @staticmethod
    def _check_name_unit_description(name: str, unit: str, description: str) -> dict[str, str | None]:
        """
        Checks the following instrument name, unit and description for
        compliance with the spec.

        Returns a dict with keys "name", "unit" and "description", the
        corresponding values will be the checked strings or `None` if the value
        is invalid. If valid, the checked strings should be used instead of the
        original values.

        Args:
            name: The candidate instrument name.
            unit: The candidate unit. A ``None`` reaching this method despite
                the annotation is treated as the empty string.
            description: The candidate description. A ``None`` reaching this
                method despite the annotation is treated as the empty string.

        Returns:
            A dict with the keys ``"name"``, ``"unit"`` and ``"description"``.
            Each value is the checked string, or ``None`` when that part
            failed validation. The description is never ``None``, since any
            string is accepted.
        """

        result: dict[str, str | None] = {}

        if _name_regex.fullmatch(name) is not None:
            result["name"] = name
        else:
            result["name"] = None

        if unit is None:
            unit = ""
        if _unit_regex.fullmatch(unit) is not None:
            result["unit"] = unit
        else:
            result["unit"] = None

        if description is None:
            result["description"] = ""
        else:
            result["description"] = description

        return result


class _ProxyInstrument(ABC, Generic[InstrumentT]):
    """An instrument that stands in until a real meter provider is set.

    It records nothing of its own. Once a real provider is installed, the
    creating meter calls :meth:`on_meter_set`, and every measurement made after
    that call returns is forwarded to a real instrument built from the stored
    name, unit and description, together with whatever else the subclass stored:
    the callbacks for an asynchronous instrument, the bucket advisory for a
    histogram. A measurement made while the real instrument is being built is
    discarded, since no lock is held across its creation.

    Args:
        name: The name of the instrument, which must match
            ``[a-zA-Z][-_./a-zA-Z0-9]{0,254}``.
        unit: The unit of the measurements, as at most 63 ASCII
            characters.
        description: A human-readable description of what the instrument
            measures.
    """

    def __init__(
        self,
        name: str,
        unit: str = "",
        description: str = "",
    ) -> None:
        """Record what to build the real instrument from, once one is possible.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        self._name = name
        self._unit = unit
        self._description = description
        self._real_instrument: InstrumentT | None = None

    def on_meter_set(self, meter: "metrics.Meter") -> None:
        """Called when a real meter is set on the creating _ProxyMeter

        Args:
            meter: The real meter to build the backing instrument from.
        """

        # We don't need any locking on proxy instruments because it's OK if some
        # measurements get dropped while a real backing instrument is being
        # created.
        self._real_instrument = self._create_real_instrument(meter)

    @abstractmethod
    def _create_real_instrument(self, meter: "metrics.Meter") -> InstrumentT:
        """Create an instance of the real instrument. Implement this.

        Args:
            meter: The real meter to create the instrument from.

        Returns:
            A real instrument of the type this proxy stands in for, carrying
            the name, unit and description the proxy was built with, and
            whatever else the implementing subclass stored.
        """


class _ProxyAsynchronousInstrument(_ProxyInstrument[InstrumentT]):
    """A proxy instrument that also carries callbacks to the real instrument.

    Args:
        name: The name of the instrument, which must match
            ``[a-zA-Z][-_./a-zA-Z0-9]{0,254}``.
        callbacks: The callbacks to invoke on each collection. Each one
            receives a :class:`CallbackOptions` and returns an iterable of
            :class:`~opentelemetry.metrics.Observation`.
        unit: The unit of the measurements, as at most 63 ASCII
            characters.
        description: A human-readable description of what the instrument
            measures.
    """

    def __init__(
        self,
        name: str,
        callbacks: Sequence[CallbackT] | None = None,
        unit: str = "",
        description: str = "",
    ) -> None:
        """Record what to build the real instrument from, including callbacks.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        super().__init__(name, unit, description)
        self._callbacks = callbacks


class Synchronous(Instrument):
    """Base class for all synchronous instruments"""


class Asynchronous(Instrument):
    """Base class for all asynchronous instruments

    Args:
        name: The name of the instrument, which must match
            ``[a-zA-Z][-_./a-zA-Z0-9]{0,254}``.
        callbacks: The callbacks to invoke on each collection. Each one
            receives a :class:`CallbackOptions` and returns an iterable of
            :class:`~opentelemetry.metrics.Observation`.
        unit: The unit of the measurements, as at most 63 ASCII
            characters.
        description: A human-readable description of what the instrument
            measures.
    """

    @abstractmethod
    def __init__(
        self,
        name: str,
        callbacks: Sequence[CallbackT] | None = None,
        unit: str = "",
        description: str = "",
    ) -> None:
        """Build the instrument.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        super().__init__(name, unit=unit, description=description)


class Counter(Synchronous):
    """A Counter is a synchronous `Instrument` which supports non-negative increments."""

    @abstractmethod
    def add(
        self,
        amount: float,
        attributes: Attributes = None,
        context: Context | None = None,
    ) -> None:
        """Records an increment to the counter.

        Args:
            amount: The amount to increment the counter by. Must be non-negative.
            attributes: Optional set of attributes to associate with the measurement.
            context: Optional context to associate with the measurement. If not
                provided, the current context is used.
        """


class NoOpCounter(Counter):
    """No-op implementation of `Counter`.

    Args:
        name: The name of the instrument, which must match
            ``[a-zA-Z][-_./a-zA-Z0-9]{0,254}``.
        unit: The unit of the measurements, as at most 63 ASCII
            characters.
        description: A human-readable description of what the instrument
            measures.
    """

    def __init__(
        self,
        name: str,
        unit: str = "",
        description: str = "",
    ) -> None:
        """Build the no-op instrument.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        super().__init__(name, unit=unit, description=description)

    def add(
        self,
        amount: float,
        attributes: Attributes = None,
        context: Context | None = None,
    ) -> None:
        """Discard the measurement.

        The call reaches the abstract method of the base class, whose body is
        empty, so no argument is read and nothing is recorded anywhere.

        Args:
            amount: Ignored.
            attributes: Ignored.
            context: Ignored.
        """
        return super().add(amount, attributes=attributes, context=context)


class _ProxyCounter(_ProxyInstrument[Counter], Counter):
    """A counter that stands in until a real meter provider is set.

    It records nothing of its own until one is.
    """

    def add(
        self,
        amount: float,
        attributes: Attributes = None,
        context: Context | None = None,
    ) -> None:
        """Forward the measurement to the real instrument, if there is one.

        The measurement is discarded while no real
        :class:`~opentelemetry.metrics.MeterProvider` has been set.

        Args:
            amount: The value to record.
            attributes: Optional set of attributes to associate with the
                measurement.
            context: Optional context to associate with the measurement. If
                not provided, the current context is used.
        """
        if self._real_instrument:
            self._real_instrument.add(amount, attributes, context)

    def _create_real_instrument(self, meter: "metrics.Meter") -> Counter:
        """Create the real counter this proxy stands in for.

        Args:
            meter: The real meter to create the instrument from.

        Returns:
            The instrument returned by
            :meth:`~opentelemetry.metrics.Meter.create_counter`, carrying the name,
            unit and description this proxy was built with.
        """
        return meter.create_counter(
            self._name,
            self._unit,
            self._description,
        )


class UpDownCounter(Synchronous):
    """An UpDownCounter is a synchronous `Instrument` which supports increments and decrements."""

    @abstractmethod
    def add(
        self,
        amount: float,
        attributes: Attributes = None,
        context: Context | None = None,
    ) -> None:
        """Records an increment or decrement to the counter.

        Unlike `Counter`, the ``amount`` may be negative, allowing the
        instrument to track values that go up and down (e.g. number of
        active requests, queue depth).

        Args:
            amount: The amount to add to the counter. May be positive or negative.
            attributes: Optional set of attributes to associate with the measurement.
            context: Optional context to associate with the measurement. If not
                provided, the current context is used.
        """


class NoOpUpDownCounter(UpDownCounter):
    """No-op implementation of `UpDownCounter`.

    Args:
        name: The name of the instrument, which must match
            ``[a-zA-Z][-_./a-zA-Z0-9]{0,254}``.
        unit: The unit of the measurements, as at most 63 ASCII
            characters.
        description: A human-readable description of what the instrument
            measures.
    """

    def __init__(
        self,
        name: str,
        unit: str = "",
        description: str = "",
    ) -> None:
        """Build the no-op instrument.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        super().__init__(name, unit=unit, description=description)

    def add(
        self,
        amount: float,
        attributes: Attributes = None,
        context: Context | None = None,
    ) -> None:
        """Discard the measurement.

        The call reaches the abstract method of the base class, whose body is
        empty, so no argument is read and nothing is recorded anywhere.

        Args:
            amount: Ignored.
            attributes: Ignored.
            context: Ignored.
        """
        return super().add(amount, attributes=attributes, context=context)


class _ProxyUpDownCounter(_ProxyInstrument[UpDownCounter], UpDownCounter):
    """A up-down counter that stands in until a real meter provider is set.

    It records nothing of its own until one is.
    """

    def add(
        self,
        amount: float,
        attributes: Attributes = None,
        context: Context | None = None,
    ) -> None:
        """Forward the measurement to the real instrument, if there is one.

        The measurement is discarded while no real
        :class:`~opentelemetry.metrics.MeterProvider` has been set.

        Args:
            amount: The value to record.
            attributes: Optional set of attributes to associate with the
                measurement.
            context: Optional context to associate with the measurement. If
                not provided, the current context is used.
        """
        if self._real_instrument:
            self._real_instrument.add(amount, attributes, context)

    def _create_real_instrument(self, meter: "metrics.Meter") -> UpDownCounter:
        """Create the real up-down counter this proxy stands in for.

        Args:
            meter: The real meter to create the instrument from.

        Returns:
            The instrument returned by
            :meth:`~opentelemetry.metrics.Meter.create_up_down_counter`,
            carrying the name, unit and description this proxy was built
            with.
        """
        return meter.create_up_down_counter(
            self._name,
            self._unit,
            self._description,
        )


class ObservableCounter(Asynchronous):
    """An ObservableCounter is an asynchronous `Instrument` which reports monotonically
    increasing value(s) when the instrument is being observed.
    """


class NoOpObservableCounter(ObservableCounter):
    """No-op implementation of `ObservableCounter`.

    The callbacks are never invoked.

    Args:
        name: The name of the instrument, which must match
            ``[a-zA-Z][-_./a-zA-Z0-9]{0,254}``.
        callbacks: The callbacks to invoke on each collection. Each one
            receives a :class:`CallbackOptions` and returns an iterable of
            :class:`~opentelemetry.metrics.Observation`.
        unit: The unit of the measurements, as at most 63 ASCII
            characters.
        description: A human-readable description of what the instrument
            measures.
    """

    def __init__(
        self,
        name: str,
        callbacks: Sequence[CallbackT] | None = None,
        unit: str = "",
        description: str = "",
    ) -> None:
        """Build the no-op instrument.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        super().__init__(
            name,
            callbacks,
            unit=unit,
            description=description,
        )


class _ProxyObservableCounter(_ProxyAsynchronousInstrument[ObservableCounter], ObservableCounter):
    """An observable counter that stands in until a real meter provider is set.

    It records nothing of its own until one is.
    """

    def _create_real_instrument(self, meter: "metrics.Meter") -> ObservableCounter:
        """Create the real observable counter this proxy stands in for.

        Args:
            meter: The real meter to create the instrument from.

        Returns:
            The instrument returned by
            :meth:`~opentelemetry.metrics.Meter.create_observable_counter`,
            carrying the name, unit, description and callbacks this proxy was
            built with. The callbacks are handed to the real instrument, so a
            counter created before the SDK was installed starts reporting on
            the first collection after it is.
        """
        return meter.create_observable_counter(
            self._name,
            self._callbacks,
            self._unit,
            self._description,
        )


class ObservableUpDownCounter(Asynchronous):
    """An ObservableUpDownCounter is an asynchronous `Instrument` which reports additive value(s) (e.g.
    the process heap size - it makes sense to report the heap size from multiple processes and sum them
    up, so we get the total heap usage) when the instrument is being observed.
    """


class NoOpObservableUpDownCounter(ObservableUpDownCounter):
    """No-op implementation of `ObservableUpDownCounter`.

    The callbacks are never invoked.

    Args:
        name: The name of the instrument, which must match
            ``[a-zA-Z][-_./a-zA-Z0-9]{0,254}``.
        callbacks: The callbacks to invoke on each collection. Each one
            receives a :class:`CallbackOptions` and returns an iterable of
            :class:`~opentelemetry.metrics.Observation`.
        unit: The unit of the measurements, as at most 63 ASCII
            characters.
        description: A human-readable description of what the instrument
            measures.
    """

    def __init__(
        self,
        name: str,
        callbacks: Sequence[CallbackT] | None = None,
        unit: str = "",
        description: str = "",
    ) -> None:
        """Build the no-op instrument.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        super().__init__(
            name,
            callbacks,
            unit=unit,
            description=description,
        )


class _ProxyObservableUpDownCounter(
    _ProxyAsynchronousInstrument[ObservableUpDownCounter],
    ObservableUpDownCounter,
):
    """An observable up-down counter that stands in until a real meter provider is set.

    It records nothing of its own until one is.
    """

    def _create_real_instrument(self, meter: "metrics.Meter") -> ObservableUpDownCounter:
        """Create the real observable up-down counter this proxy stands in for.

        Args:
            meter: The real meter to create the instrument from.

        Returns:
            The instrument returned by
            :meth:`~opentelemetry.metrics.Meter.create_observable_up_down_counter`,
            carrying the name, unit, description and callbacks this proxy was
            built with. The callbacks are handed to the real instrument, so a
            counter created before the SDK was installed starts reporting on
            the first collection after it is.
        """
        return meter.create_observable_up_down_counter(
            self._name,
            self._callbacks,
            self._unit,
            self._description,
        )


class Histogram(Synchronous):
    """Histogram is a synchronous `Instrument` which can be used to report arbitrary values
    that are likely to be statistically meaningful. It is intended for statistics such as
    histograms, summaries, and percentile.

    Args:
        name: The name of the instrument, which must match
            ``[a-zA-Z][-_./a-zA-Z0-9]{0,254}``.
        unit: The unit of the measurements, as at most 63 ASCII
            characters.
        description: A human-readable description of what the instrument
            measures.
        explicit_bucket_boundaries_advisory: The bucket boundaries the
            instrument suggests to the SDK, in ascending order. ``None``
            leaves the choice to the SDK.
    """

    @abstractmethod
    def __init__(
        self,
        name: str,
        unit: str = "",
        description: str = "",
        explicit_bucket_boundaries_advisory: Sequence[float] | None = None,
    ) -> None:
        """Build the instrument.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """

    @abstractmethod
    def record(
        self,
        amount: float,
        attributes: Attributes = None,
        context: Context | None = None,
    ) -> None:
        """Records a measurement.

        Used to report measurements that are likely to be statistically
        meaningful, such as request durations, payload sizes, or any value
        for which a distribution (e.g. percentiles) is useful.

        Args:
            amount: The measurement to record. Should be non-negative in most
                cases; negative values are only meaningful when the histogram
                is used to track signed deltas.
            attributes: Optional set of attributes to associate with the measurement.
            context: Optional context to associate with the measurement. If not
                provided, the current context is used.
        """


class NoOpHistogram(Histogram):
    """No-op implementation of `Histogram`.

    Args:
        name: The name of the instrument, which must match
            ``[a-zA-Z][-_./a-zA-Z0-9]{0,254}``.
        unit: The unit of the measurements, as at most 63 ASCII
            characters.
        description: A human-readable description of what the instrument
            measures.
        explicit_bucket_boundaries_advisory: The bucket boundaries the
            instrument suggests to the SDK, in ascending order. ``None``
            leaves the choice to the SDK.
    """

    def __init__(
        self,
        name: str,
        unit: str = "",
        description: str = "",
        explicit_bucket_boundaries_advisory: Sequence[float] | None = None,
    ) -> None:
        """Build the no-op instrument.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        super().__init__(
            name,
            unit=unit,
            description=description,
            explicit_bucket_boundaries_advisory=explicit_bucket_boundaries_advisory,
        )

    def record(
        self,
        amount: float,
        attributes: Attributes = None,
        context: Context | None = None,
    ) -> None:
        """Discard the measurement.

        The call reaches the abstract method of the base class, whose body is
        empty, so no argument is read and nothing is recorded anywhere.

        Args:
            amount: Ignored.
            attributes: Ignored.
            context: Ignored.
        """
        return super().record(amount, attributes=attributes, context=context)


class _ProxyHistogram(_ProxyInstrument[Histogram], Histogram):
    """A histogram that stands in until a real meter provider is set.

    It records nothing of its own until one is.

    Args:
        name: The name of the instrument, which must match
            ``[a-zA-Z][-_./a-zA-Z0-9]{0,254}``.
        unit: The unit of the measurements, as at most 63 ASCII
            characters.
        description: A human-readable description of what the instrument
            measures.
        explicit_bucket_boundaries_advisory: The bucket boundaries the
            instrument suggests to the SDK, in ascending order. ``None``
            leaves the choice to the SDK.
    """

    def __init__(
        self,
        name: str,
        unit: str = "",
        description: str = "",
        explicit_bucket_boundaries_advisory: Sequence[float] | None = None,
    ) -> None:
        """Record what to build the real histogram from, once one is possible.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        super().__init__(name, unit=unit, description=description)
        self._explicit_bucket_boundaries_advisory = explicit_bucket_boundaries_advisory

    def record(
        self,
        amount: float,
        attributes: Attributes = None,
        context: Context | None = None,
    ) -> None:
        """Forward the measurement to the real instrument, if there is one.

        The measurement is discarded while no real
        :class:`~opentelemetry.metrics.MeterProvider` has been set.

        Args:
            amount: The value to record.
            attributes: Optional set of attributes to associate with the
                measurement.
            context: Optional context to associate with the measurement. If
                not provided, the current context is used.
        """
        if self._real_instrument:
            self._real_instrument.record(amount, attributes, context)

    def _create_real_instrument(self, meter: "metrics.Meter") -> Histogram:
        """Create the real histogram this proxy stands in for.

        Args:
            meter: The real meter to create the instrument from.

        Returns:
            The instrument returned by
            :meth:`~opentelemetry.metrics.Meter.create_histogram`, carrying the name,
            unit and description this proxy was built with, and the bucket
            advisory as well, so a histogram created before the SDK was
            installed keeps the boundaries it asked for.
        """
        return meter.create_histogram(
            self._name,
            self._unit,
            self._description,
            explicit_bucket_boundaries_advisory=self._explicit_bucket_boundaries_advisory,
        )


class ObservableGauge(Asynchronous):
    """Asynchronous Gauge is an asynchronous `Instrument` which reports non-additive value(s) (e.g.
    the room temperature - it makes no sense to report the temperature value from multiple rooms
    and sum them up) when the instrument is being observed.
    """


class NoOpObservableGauge(ObservableGauge):
    """No-op implementation of `ObservableGauge`.

    The callbacks are never invoked.

    Args:
        name: The name of the instrument, which must match
            ``[a-zA-Z][-_./a-zA-Z0-9]{0,254}``.
        callbacks: The callbacks to invoke on each collection. Each one
            receives a :class:`CallbackOptions` and returns an iterable of
            :class:`~opentelemetry.metrics.Observation`.
        unit: The unit of the measurements, as at most 63 ASCII
            characters.
        description: A human-readable description of what the instrument
            measures.
    """

    def __init__(
        self,
        name: str,
        callbacks: Sequence[CallbackT] | None = None,
        unit: str = "",
        description: str = "",
    ) -> None:
        """Build the no-op instrument.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        super().__init__(
            name,
            callbacks,
            unit=unit,
            description=description,
        )


class _ProxyObservableGauge(
    _ProxyAsynchronousInstrument[ObservableGauge],
    ObservableGauge,
):
    """An observable gauge that stands in until a real meter provider is set.

    It records nothing of its own until one is.
    """

    def _create_real_instrument(self, meter: "metrics.Meter") -> ObservableGauge:
        """Create the real observable gauge this proxy stands in for.

        Args:
            meter: The real meter to create the instrument from.

        Returns:
            The instrument returned by
            :meth:`~opentelemetry.metrics.Meter.create_observable_gauge`,
            carrying the name, unit, description and callbacks this proxy was
            built with. The callbacks are handed to the real instrument, so a
            gauge created before the SDK was installed starts reporting on the
            first collection after it is.
        """
        return meter.create_observable_gauge(
            self._name,
            self._callbacks,
            self._unit,
            self._description,
        )


class Gauge(Synchronous):
    """A Gauge is a synchronous `Instrument` which can be used to record non-additive values as they occur."""

    @abstractmethod
    def set(
        self,
        amount: float,
        attributes: Attributes = None,
        context: Context | None = None,
    ) -> None:
        """Records the current value of the gauge.

        The gauge reports the last recorded value when observed. It is
        intended for non-additive measurements where only the current
        value matters (e.g. CPU utilisation percentage, room temperature).

        Args:
            amount: The current value to record.
            attributes: Optional set of attributes to associate with the measurement.
            context: Optional context to associate with the measurement. If not
                provided, the current context is used.
        """


class NoOpGauge(Gauge):
    """No-op implementation of ``Gauge``.

    Args:
        name: The name of the instrument, which must match
            ``[a-zA-Z][-_./a-zA-Z0-9]{0,254}``.
        unit: The unit of the measurements, as at most 63 ASCII
            characters.
        description: A human-readable description of what the instrument
            measures.
    """

    def __init__(
        self,
        name: str,
        unit: str = "",
        description: str = "",
    ) -> None:
        """Build the no-op instrument.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        super().__init__(name, unit=unit, description=description)

    def set(
        self,
        amount: float,
        attributes: Attributes = None,
        context: Context | None = None,
    ) -> None:
        """Discard the measurement.

        The call reaches the abstract method of the base class, whose body is
        empty, so no argument is read and nothing is recorded anywhere.

        Args:
            amount: Ignored.
            attributes: Ignored.
            context: Ignored.
        """
        return super().set(amount, attributes=attributes, context=context)


class _ProxyGauge(
    _ProxyInstrument[Gauge],
    Gauge,
):
    """A gauge that stands in until a real meter provider is set.

    It records nothing of its own until one is.
    """

    def set(
        self,
        amount: float,
        attributes: Attributes = None,
        context: Context | None = None,
    ) -> None:
        """Forward the measurement to the real instrument, if there is one.

        The measurement is discarded while no real
        :class:`~opentelemetry.metrics.MeterProvider` has been set.

        Args:
            amount: The value to record.
            attributes: Optional set of attributes to associate with the
                measurement.
            context: Optional context to associate with the measurement. If
                not provided, the current context is used.
        """
        if self._real_instrument:
            self._real_instrument.set(amount, attributes, context)

    def _create_real_instrument(self, meter: "metrics.Meter") -> Gauge:
        """Create the real gauge this proxy stands in for.

        Args:
            meter: The real meter to create the instrument from.

        Returns:
            The instrument returned by
            :meth:`~opentelemetry.metrics.Meter.create_gauge`, carrying the name,
            unit and description this proxy was built with.
        """
        return meter.create_gauge(
            self._name,
            self._unit,
            self._description,
        )
