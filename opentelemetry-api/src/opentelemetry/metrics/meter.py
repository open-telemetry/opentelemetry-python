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
# type:ignore


from abc import ABC, abstractmethod
from functools import wraps
from logging import getLogger
from typing import cast

from opentelemetry.environment_variables import OTEL_PYTHON_METER_PROVIDER
from opentelemetry.metrics.instrument import (
    Counter,
    DefaultCounter,
    DefaultHistogram,
    DefaultObservableCounter,
    DefaultObservableGauge,
    DefaultObservableUpDownCounter,
    DefaultUpDownCounter,
    Histogram,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.util._providers import _load_provider
from opentelemetry.util.types import Attributes

_logger = getLogger(__name__)


class Measurement(ABC):
    @abstractmethod
    def __init__(self, value, **attributes: Attributes):
        pass


class DefaultMeasurement(Measurement):
    def __init__(self, value, **attributes: Attributes):
        super().__init__(value, **attributes)


class Meter(ABC):

    # FIXME make unit and description be "" if unit or description are None
    @abstractmethod
    def create_counter(self, name, unit="", description="") -> Counter:
        pass

    @abstractmethod
    def create_up_down_counter(
        self, name, unit="", description=""
    ) -> UpDownCounter:
        pass

    @abstractmethod
    def create_observable_counter(
        self, name, callback, unit="", description=""
    ) -> ObservableCounter:
        pass

    @abstractmethod
    def create_histogram(self, name, unit="", description="") -> Histogram:
        pass

    @abstractmethod
    def create_observable_gauge(
        self, name, callback, unit="", description=""
    ) -> ObservableGauge:
        pass

    @abstractmethod
    def create_observable_up_down_counter(
        self, name, callback, unit="", description=""
    ) -> ObservableUpDownCounter:
        pass

    @staticmethod
    def check_unique_name(checker):
        def wrapper_0(method):
            @wraps(method)
            def wrapper_1(self, name, unit="", description=""):
                checker(self, name)
                return method(self, name, unit=unit, description=description)

            return wrapper_1

        return wrapper_0


class DefaultMeter(Meter):
    def __init__(self):
        self._instrument_names = set()

    def _instrument_name_checker(self, name):

        if name in self._instrument_names:
            raise Exception("Instrument name {} has been used already")

        self._instrument_names.add(name)

    @Meter.check_unique_name(_instrument_name_checker)
    def create_counter(self, name, unit="", description="") -> Counter:
        return DefaultCounter(name, unit=unit, description=description)

    @Meter.check_unique_name(_instrument_name_checker)
    def create_up_down_counter(
        self, name, unit="", description=""
    ) -> UpDownCounter:
        return DefaultUpDownCounter(name, unit=unit, description=description)

    @Meter.check_unique_name(_instrument_name_checker)
    def create_observable_counter(
        self, name, callback, unit="", description=""
    ) -> ObservableCounter:
        return DefaultObservableCounter(
            name,
            callback,
            unit=unit,
            description=description,
        )

    @Meter.check_unique_name(_instrument_name_checker)
    def create_histogram(self, name, unit="", description="") -> Histogram:
        return DefaultHistogram(name, unit=unit, description=description)

    @Meter.check_unique_name(_instrument_name_checker)
    def create_observable_gauge(
        self, name, callback, unit="", description=""
    ) -> ObservableGauge:
        return DefaultObservableGauge(  # pylint: disable=abstract-class-instantiated
            name,
            callback,
            unit=unit,
            description=description,
        )

    @Meter.check_unique_name(_instrument_name_checker)
    def create_observable_up_down_counter(
        self, name, callback, unit="", description=""
    ) -> ObservableUpDownCounter:
        return DefaultObservableUpDownCounter(  # pylint: disable=abstract-class-instantiated
            name,
            callback,
            unit=unit,
            description=description,
        )


class MeterProvider(ABC):
    @abstractmethod
    def get_meter(
        self,
        name,
        version=None,
        schema_url=None,
    ) -> Meter:
        pass


class DefaultMeterProvider(MeterProvider):
    def get_meter(
        self,
        name,
        version=None,
        schema_url=None,
    ) -> Meter:
        return DefaultMeter()


_METER_PROVIDER = None


def set_meter_provider(meter_provider: MeterProvider) -> None:
    """Sets the current global :class:`~.MeterProvider` object."""
    global _METER_PROVIDER  # pylint: disable=global-statement

    if _METER_PROVIDER is not None:
        _logger.warning("Overriding of current MeterProvider is not allowed")
        return

    _METER_PROVIDER = meter_provider


def get_meter_provider() -> MeterProvider:
    """Gets the current global :class:`~.MeterProvider` object."""
    global _METER_PROVIDER  # pylint: disable=global-statement

    if _METER_PROVIDER is None:
        _METER_PROVIDER = cast(
            "MeterProvider",
            _load_provider(OTEL_PYTHON_METER_PROVIDER, "meter_provider"),
        )

    return _METER_PROVIDER
