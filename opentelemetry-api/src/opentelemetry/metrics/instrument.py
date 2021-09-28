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
from collections import abc as collections_abc
from logging import getLogger
from re import compile as compile_
from typing import Callable, Generator, Iterable, Union

from opentelemetry.metrics.measurement import Measurement

_TInstrumentCallback = Callable[[], Iterable[Measurement]]
_TInstrumentCallbackGenerator = Generator[Iterable[Measurement], None, None]
TCallback = Union[_TInstrumentCallback, _TInstrumentCallbackGenerator]


_logger = getLogger(__name__)


class Instrument(ABC):

    _name_regex = compile_(r"[a-zA-Z][-.\w]{0,62}")

    @property
    def name(self):
        return self._name

    @property
    def unit(self):
        return self._unit

    @property
    def description(self):
        return self._description

    @abstractmethod
    def __init__(self, name, unit="", description=""):

        if name is None or self._name_regex.fullmatch(name) is None:
            _logger.error("Invalid instrument name %s", name)

        else:
            self._name = name

        if unit is None:
            self._unit = ""
        elif len(unit) > 63:
            _logger.error("unit must be 63 characters or shorter")

        elif any(ord(character) > 127 for character in unit):
            _logger.error("unit must only contain ASCII characters")
        else:
            self._unit = unit

        if description is None:
            description = ""

        self._description = description


class Synchronous(Instrument):
    pass


class Asynchronous(Instrument):
    @abstractmethod
    def __init__(
        self,
        name,
        callback: TCallback,
        *args,
        unit="",
        description="",
        **kwargs
    ):
        super().__init__(
            name, *args, unit=unit, description=description, **kwargs
        )

        if isinstance(callback, collections_abc.Callable):
            self._callback = callback
        elif isinstance(callback, collections_abc.Generator):
            self._callback = self._wrap_generator_callback(callback)
        else:
            _logger.error("callback must be a callable or generator")

    def _wrap_generator_callback(
        self,
        generator_callback: _TInstrumentCallbackGenerator,
    ) -> _TInstrumentCallback:
        """Wraps a generator style callback into a callable one"""
        has_items = True

        def inner() -> Iterable[Measurement]:
            nonlocal has_items
            if not has_items:
                return []

            try:
                return next(generator_callback)
            except StopIteration:
                has_items = False
                _logger.error(
                    "callback generator for instrument %s ran out of measurements",
                    self._name,
                )
                return []

        return inner

    def callback(self):
        measurements = self._callback()
        if not isinstance(measurements, collections_abc.Iterable):
            _logger.error(
                "Callback must return an iterable of Measurement, got %s",
                type(measurements),
            )
            return
        for measurement in measurements:
            if not isinstance(measurement, Measurement):
                _logger.error(
                    "Callback must return an iterable of Measurement, "
                    "iterable contained type %s",
                    type(measurement),
                )
            yield measurement


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
        if amount < 0:
            _logger.error("Amount must be non-negative")


class DefaultCounter(Counter):
    def __init__(self, name, unit="", description=""):
        super().__init__(name, unit=unit, description=description)

    def add(self, amount, attributes=None):
        return super().add(amount, attributes=attributes)


class UpDownCounter(_NonMonotonic, Synchronous):
    @abstractmethod
    def add(self, amount, attributes=None):
        pass


class DefaultUpDownCounter(UpDownCounter):
    def __init__(self, name, unit="", description=""):
        super().__init__(name, unit=unit, description=description)

    def add(self, amount, attributes=None):
        return super().add(amount, attributes=attributes)


class ObservableCounter(_Monotonic, Asynchronous):
    def callback(self):
        measurements = super().callback()

        for measurement in measurements:
            if measurement.value < 0:
                _logger.error("Amount must be non-negative")
            yield measurement


class DefaultObservableCounter(ObservableCounter):
    def __init__(self, name, callback, unit="", description=""):
        super().__init__(name, callback, unit=unit, description=description)


class ObservableUpDownCounter(_NonMonotonic, Asynchronous):

    pass


class DefaultObservableUpDownCounter(ObservableUpDownCounter):
    def __init__(self, name, callback, unit="", description=""):
        super().__init__(name, callback, unit=unit, description=description)


class Histogram(_Grouping, Synchronous):
    @abstractmethod
    def record(self, amount, attributes=None):
        pass


class DefaultHistogram(Histogram):
    def __init__(self, name, unit="", description=""):
        super().__init__(name, unit=unit, description=description)

    def record(self, amount, attributes=None):
        return super().record(amount, attributes=attributes)


class ObservableGauge(_Grouping, Asynchronous):
    pass


class DefaultObservableGauge(ObservableGauge):
    def __init__(self, name, callback, unit="", description=""):
        super().__init__(name, callback, unit=unit, description=description)
