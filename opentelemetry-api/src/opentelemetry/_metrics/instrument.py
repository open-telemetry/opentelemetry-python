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

# pylint: disable=too-many-ancestors

# type: ignore

from abc import ABC, abstractmethod
from logging import getLogger
from typing import (
    Callable,
    Generator,
    Generic,
    Iterable,
    Optional,
    TypeVar,
    Union,
)

# pylint: disable=unused-import; needed for typing and sphinx
from opentelemetry import _metrics as metrics
from opentelemetry._metrics.observation import Observation

InstrumentT = TypeVar("InstrumentT", bound="Instrument")
CallbackT = Union[
    Callable[[], Iterable[Observation]],
    Generator[Iterable[Observation], None, None],
]


_logger = getLogger(__name__)


class Instrument(ABC):
    """Abstract class that serves as base for all instruments."""

    @abstractmethod
    def __init__(self, name, unit="", description=""):
        pass

        # FIXME check that the instrument name is valid
        # FIXME check that the unit is 63 characters or shorter
        # FIXME check that the unit contains only ASCII characters


class _ProxyInstrument(ABC, Generic[InstrumentT]):
    def __init__(self, name, unit, description) -> None:
        self._name = name
        self._unit = unit
        self._description = description
        self._real_instrument: Optional[InstrumentT] = None

    def on_meter_set(self, meter: "metrics.Meter") -> None:
        """Called when a real meter is set on the creating _ProxyMeter"""

        # We don't need any locking on proxy instruments because it's OK if some
        # measurements get dropped while a real backing instrument is being
        # created.
        self._real_instrument = self._create_real_instrument(meter)

    @abstractmethod
    def _create_real_instrument(self, meter: "metrics.Meter") -> InstrumentT:
        """Create an instance of the real instrument. Implement this."""


class _ProxyAsynchronousInstrument(_ProxyInstrument[InstrumentT]):
    def __init__(self, name, callbacks, unit, description) -> None:
        super().__init__(name, unit, description)
        self._callbacks = callbacks


class Synchronous(Instrument):
    pass


class Asynchronous(Instrument):
    @abstractmethod
    def __init__(
        self,
        name,
        callbacks=None,
        unit="",
        description="",
    ):
        super().__init__(name, unit=unit, description=description)


class _Adding(Instrument):
    pass


class _Grouping(Instrument):
    pass


class _Monotonic(_Adding):
    pass


class _NonMonotonic(_Adding):
    pass


class Counter(_Monotonic, Synchronous):
    """A Counter is a synchronous `Instrument` which supports non-negative increments."""

    @abstractmethod
    def add(self, amount, attributes=None):
        # FIXME check that the amount is non negative
        pass


class NoOpCounter(Counter):
    """No-op implementation of `Counter`."""

    def __init__(self, name, unit="", description=""):
        super().__init__(name, unit=unit, description=description)

    def add(self, amount, attributes=None):
        return super().add(amount, attributes=attributes)


class _ProxyCounter(_ProxyInstrument[Counter], Counter):
    def add(self, amount, attributes=None):
        if self._real_instrument:
            self._real_instrument.add(amount, attributes)

    def _create_real_instrument(self, meter: "metrics.Meter") -> Counter:
        return meter.create_counter(self._name, self._unit, self._description)


class UpDownCounter(_NonMonotonic, Synchronous):
    """An UpDownCounter is a synchronous `Instrument` which supports increments and decrements."""

    @abstractmethod
    def add(self, amount, attributes=None):
        pass


class NoOpUpDownCounter(UpDownCounter):
    """No-op implementation of `UpDownCounter`."""

    def __init__(self, name, unit="", description=""):
        super().__init__(name, unit=unit, description=description)

    def add(self, amount, attributes=None):
        return super().add(amount, attributes=attributes)


class _ProxyUpDownCounter(_ProxyInstrument[UpDownCounter], UpDownCounter):
    def add(self, amount, attributes=None):
        if self._real_instrument:
            self._real_instrument.add(amount, attributes)

    def _create_real_instrument(self, meter: "metrics.Meter") -> UpDownCounter:
        return meter.create_up_down_counter(
            self._name, self._unit, self._description
        )


class ObservableCounter(_Monotonic, Asynchronous):
    """An ObservableCounter is an asynchronous `Instrument` which reports monotonically
    increasing value(s) when the instrument is being observed.
    """


class NoOpObservableCounter(ObservableCounter):
    """No-op implementation of `ObservableCounter`."""

    def __init__(self, name, callbacks=None, unit="", description=""):
        super().__init__(name, callbacks, unit=unit, description=description)


class _ProxyObservableCounter(
    _ProxyAsynchronousInstrument[ObservableCounter], ObservableCounter
):
    def _create_real_instrument(
        self, meter: "metrics.Meter"
    ) -> ObservableCounter:
        return meter.create_observable_counter(
            self._name, self._callbacks, self._unit, self._description
        )


class ObservableUpDownCounter(_NonMonotonic, Asynchronous):
    """An ObservableUpDownCounter is an asynchronous `Instrument` which reports additive value(s) (e.g.
    the process heap size - it makes sense to report the heap size from multiple processes and sum them
    up, so we get the total heap usage) when the instrument is being observed.
    """


class NoOpObservableUpDownCounter(ObservableUpDownCounter):
    """No-op implementation of `ObservableUpDownCounter`."""

    def __init__(self, name, callbacks=None, unit="", description=""):
        super().__init__(name, callbacks, unit=unit, description=description)


class _ProxyObservableUpDownCounter(
    _ProxyAsynchronousInstrument[ObservableUpDownCounter],
    ObservableUpDownCounter,
):
    def _create_real_instrument(
        self, meter: "metrics.Meter"
    ) -> ObservableUpDownCounter:
        return meter.create_observable_up_down_counter(
            self._name, self._callbacks, self._unit, self._description
        )


class Histogram(_Grouping, Synchronous):
    """Histogram is a synchronous `Instrument` which can be used to report arbitrary values
    that are likely to be statistically meaningful. It is intended for statistics such as
    histograms, summaries, and percentile.
    """

    @abstractmethod
    def record(self, amount, attributes=None):
        pass


class NoOpHistogram(Histogram):
    """No-op implementation of `Histogram`."""

    def __init__(self, name, unit="", description=""):
        super().__init__(name, unit=unit, description=description)

    def record(self, amount, attributes=None):
        return super().record(amount, attributes=attributes)


class _ProxyHistogram(_ProxyInstrument[Histogram], Histogram):
    def record(self, amount, attributes=None):
        if self._real_instrument:
            self._real_instrument.record(amount, attributes)

    def _create_real_instrument(self, meter: "metrics.Meter") -> Histogram:
        return meter.create_histogram(
            self._name, self._unit, self._description
        )


class ObservableGauge(_Grouping, Asynchronous):
    """Asynchronous Gauge is an asynchronous `Instrument` which reports non-additive value(s) (e.g.
    the room temperature - it makes no sense to report the temperature value from multiple rooms
    and sum them up) when the instrument is being observed.
    """


class NoOpObservableGauge(ObservableGauge):
    """No-op implementation of `ObservableGauge`."""

    def __init__(self, name, callbacks=None, unit="", description=""):
        super().__init__(name, callbacks, unit=unit, description=description)


class _ProxyObservableGauge(
    _ProxyAsynchronousInstrument[ObservableGauge],
    ObservableGauge,
):
    def _create_real_instrument(
        self, meter: "metrics.Meter"
    ) -> ObservableGauge:
        return meter.create_observable_gauge(
            self._name, self._callbacks, self._unit, self._description
        )
