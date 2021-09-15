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

# pylint: disable=abstract-class-instantiated
# pylint: disable=too-many-ancestors
# pylint: disable=useless-super-delegation

# type: ignore


from abc import ABC, abstractmethod
from logging import getLogger
from re import compile as compile_
from typing import Callable

_logger = getLogger(__name__)


class Instrument(ABC):

    _name_regex = compile_(r"[a-zA-Z][-.\w]{0,62}")

    @abstractmethod
    def __init__(self, name, *args, unit="", description="", **kwargs):

        if self._name_regex.fullmatch(name) is None:
            raise Exception("Invalid instrument name {}".format(name))

        if len(unit) > 63:
            raise Exception("unit must be 63 characters or shorter")

        if any(ord(character) > 127 for character in unit):
            raise Exception("unit must only contain ASCII characters")


class Synchronous(Instrument):
    pass


class Asynchronous(Instrument):
    @abstractmethod
    def __init__(
        self, name, callback, *args, unit="", description="", **kwargs
    ):

        if not isinstance(callback, Callable):
            raise Exception("callback must be callable")

        super().__init__(
            name, unit=unit, description=description, *args, **kwargs
        )

    def observe(self):
        return next(self._callback)  # pylint: disable=no-member


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
            raise Exception("Amount must be non-negative")

        super().add(amount, attributes=attributes)  # pylint: disable=no-member


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
    pass


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
