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
from opentelemetry._metrics.measurement import Measurement

InstrumentT = TypeVar("InstrumentT", bound="Instrument")
CallbackT = Union[
    Callable[[], Iterable[Measurement]],
    Generator[Iterable[Measurement], None, None],
]


_logger = getLogger(__name__)


class Instrument(ABC):
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
    def __init__(self, name, callback, unit, description) -> None:
        super().__init__(name, unit, description)
        self._callback = callback


class Synchronous(Instrument):
    pass


class Asynchronous(Instrument):
    @abstractmethod
    def __init__(
        self,
        name,
        callback,
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
    @abstractmethod
    def add(self, amount, attributes=None):
        # FIXME check that the amount is non negative
        pass


class DefaultCounter(Counter):
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
    @abstractmethod
    def add(self, amount, attributes=None):
        pass


class DefaultUpDownCounter(UpDownCounter):
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
    pass


class DefaultObservableCounter(ObservableCounter):
    def __init__(self, name, callback, unit="", description=""):
        super().__init__(name, callback, unit=unit, description=description)


class _ProxyObservableCounter(
    _ProxyAsynchronousInstrument[ObservableCounter], ObservableCounter
):
    def _create_real_instrument(
        self, meter: "metrics.Meter"
    ) -> ObservableCounter:
        return meter.create_observable_counter(
            self._name, self._callback, self._unit, self._description
        )


class ObservableUpDownCounter(_NonMonotonic, Asynchronous):
    pass


class DefaultObservableUpDownCounter(ObservableUpDownCounter):
    def __init__(self, name, callback, unit="", description=""):
        super().__init__(name, callback, unit=unit, description=description)


class _ProxyObservableUpDownCounter(
    _ProxyAsynchronousInstrument[ObservableUpDownCounter],
    ObservableUpDownCounter,
):
    def _create_real_instrument(
        self, meter: "metrics.Meter"
    ) -> ObservableUpDownCounter:
        return meter.create_observable_up_down_counter(
            self._name, self._callback, self._unit, self._description
        )


class Histogram(_Grouping, Synchronous):
    @abstractmethod
    def record(self, amount, attributes=None):
        pass


class DefaultHistogram(Histogram):
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
    pass


class DefaultObservableGauge(ObservableGauge):
    def __init__(self, name, callback, unit="", description=""):
        super().__init__(name, callback, unit=unit, description=description)


class _ProxyObservableGauge(
    _ProxyAsynchronousInstrument[ObservableGauge],
    ObservableGauge,
):
    def _create_real_instrument(
        self, meter: "metrics.Meter"
    ) -> ObservableGauge:
        return meter.create_observable_gauge(
            self._name, self._callback, self._unit, self._description
        )
