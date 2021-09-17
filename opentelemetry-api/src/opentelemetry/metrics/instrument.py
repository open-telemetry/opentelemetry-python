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
from re import compile as compile_
from threading import RLock
from types import GeneratorType

from opentelemetry.metrics.measurement import Measurement

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
    def __init__(self, name, *args, unit="", description="", **kwargs):
        self._lock = RLock()

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
        self, name, callback, *args, unit="", description="", **kwargs
    ):
        super().__init__(name, *args, unit=unit, description="", **kwargs)
        with self._lock:

            if not isinstance(callback, GeneratorType):
                _logger.error("callback must be a generator")

            else:
                super().__init__(
                    name, unit=unit, description=description, *args, **kwargs
                )
                self._callback = callback

    def observe(self):
        # FIXME this needs a timeout mechanism.
        with self._lock:
            measurement = next(self._callback)
            if not isinstance(measurement, Measurement):
                _logger.error("Result of observing must be a Measurement")
                return None
            return measurement


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
        with self._lock:
            if amount < 0:
                _logger.error("Amount must be non-negative")


class DefaultCounter(Counter):
    def __init__(self, name, unit="", description=""):
        super().__init__(name, unit=unit, description=description)

    def add(self, amount, attributes=None):
        with self._lock:
            return super().add(amount, attributes=attributes)


class UpDownCounter(_NonMonotonic, Synchronous):
    @abstractmethod
    def add(self, amount, attributes=None):
        with self._lock:
            pass


class DefaultUpDownCounter(UpDownCounter):
    def __init__(self, name, unit="", description=""):
        super().__init__(name, unit=unit, description=description)

    def add(self, amount, attributes=None):
        with self._lock:
            return super().add(amount, attributes=attributes)


class ObservableCounter(_Monotonic, Asynchronous):
    def observe(self):
        with self._lock:
            measurement = super().observe()

            if isinstance(measurement, Measurement):

                if measurement.value < 0:
                    _logger.error("Amount must be non-negative")
                    return None
                return measurement
            return None


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
        with self._lock:
            pass


class DefaultHistogram(Histogram):
    def __init__(self, name, unit="", description=""):
        super().__init__(name, unit=unit, description=description)

    def record(self, amount, attributes=None):
        with self._lock:
            return super().record(amount, attributes=attributes)


class ObservableGauge(_Grouping, Asynchronous):
    pass


class DefaultObservableGauge(ObservableGauge):
    def __init__(self, name, callback, unit="", description=""):
        super().__init__(name, callback, unit=unit, description=description)
