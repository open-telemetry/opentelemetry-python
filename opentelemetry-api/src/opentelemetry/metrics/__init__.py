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

# FIXME enhance the documentation of this module
"""
This module provides abstract and concrete (but noop) classes that can be used
to generate metrics.
"""


from abc import ABC, abstractmethod
from logging import getLogger
from os import environ
from typing import Optional, cast

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

_logger = getLogger(__name__)


class MeterProvider(ABC):
    @abstractmethod
    def get_meter(
        self,
        name,
        version=None,
        schema_url=None,
    ) -> "Meter":
        pass


class _DefaultMeterProvider(MeterProvider):
    def get_meter(
        self,
        name,
        version=None,
        schema_url=None,
    ) -> "Meter":
        super().get_meter(name, version=version, schema_url=schema_url)
        return _DefaultMeter(name, version=version, schema_url=schema_url)


class ProxyMeterProvider(MeterProvider):
    def get_meter(
        self,
        name,
        version=None,
        schema_url=None,
    ) -> "Meter":
        if _METER_PROVIDER:
            return _METER_PROVIDER.get_meter(
                name, version=version, schema_url=schema_url
            )
        return ProxyMeter(name, version=version, schema_url=schema_url)


class Meter(ABC):
    def __init__(self, name, version=None, schema_url=None):
        super().__init__()
        self._name = name
        self._version = version
        self._schema_url = schema_url
        self._instrument_names = set()

    @property
    def name(self):
        return self._name

    @property
    def version(self):
        return self._version

    @property
    def schema_url(self):
        return self._schema_url

    # FIXME check that the instrument name has not been used already

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
        """Creates an observable counter instrument

        An observable counter observes a monotonically increasing count by
        calling a provided callback which returns multiple
        :class:`~opentelemetry.metrics.measurement.Measurement`.

        For example, an observable counter could be used to report system CPU
        time periodically. Here is a basic implementation::

            def cpu_time_callback() -> Iterable[Measurement]:
                measurements = []
                with open("/proc/stat") as procstat:
                    procstat.readline()  # skip the first line
                    for line in procstat:
                        if not line.startswith("cpu"): break
                        cpu, *states = line.split()
                        measurements.append(Measurement(int(states[0]) // 100, {"cpu": cpu, "state": "user"}))
                        measurements.append(Measurement(int(states[1]) // 100, {"cpu": cpu, "state": "nice"}))
                        measurements.append(Measurement(int(states[2]) // 100, {"cpu": cpu, "state": "system"}))
                        # ... other states
                return measurements

            meter.create_observable_counter(
                "system.cpu.time",
                callback=cpu_time_callback,
                unit="s",
                description="CPU time"
            )

        To reduce memory usage, you can use generator callbacks instead of
        building the full list::

            def cpu_time_callback() -> Iterable[Measurement]:
                with open("/proc/stat") as procstat:
                    procstat.readline()  # skip the first line
                    for line in procstat:
                        if not line.startswith("cpu"): break
                        cpu, *states = line.split()
                        yield Measurement(int(states[0]) // 100, {"cpu": cpu, "state": "user"})
                        yield Measurement(int(states[1]) // 100, {"cpu": cpu, "state": "nice"})
                        # ... other states

        Alternatively, you can pass a generator directly instead of a callback,
        which should return iterables of
        :class:`~opentelemetry.metrics.measurement.Measurement`::

            def cpu_time_callback(states_to_include: set[str]) -> Iterable[Iterable[Measurement]]:
                while True:
                    measurements = []
                    with open("/proc/stat") as procstat:
                        procstat.readline()  # skip the first line
                        for line in procstat:
                            if not line.startswith("cpu"): break
                            cpu, *states = line.split()
                            if "user" in states_to_include:
                                measurements.append(Measurement(int(states[0]) // 100, {"cpu": cpu, "state": "user"}))
                            if "nice" in states_to_include:
                                measurements.append(Measurement(int(states[1]) // 100, {"cpu": cpu, "state": "nice"}))
                            # ... other states
                    yield measurements

            meter.create_observable_counter(
                "system.cpu.time",
                callback=cpu_time_callback({"user", "system"}),
                unit="s",
                description="CPU time"
            )

        Args:
            name: The name of the instrument to be created
            callback: A callback that returns an iterable of
                :class:`~opentelemetry.metrics.measurement.Measurement`.
                Alternatively, can be a generator that yields iterables of
                :class:`~opentelemetry.metrics.measurement.Measurement`.
            unit: The unit for measurements this instrument reports. For
                example, ``By`` for bytes. UCUM units are recommended.
            description: A description for this instrument and what it measures.
        """

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


class ProxyMeter(Meter):
    def __init__(
        self,
        name,
        version=None,
        schema_url=None,
    ):
        super().__init__(name, version=version, schema_url=schema_url)
        self._real_meter: Optional[Meter] = None
        self._noop_meter = _DefaultMeter(
            name, version=version, schema_url=schema_url
        )

    @property
    def _meter(self) -> Meter:
        if self._real_meter is not None:
            return self._real_meter

        if _METER_PROVIDER:
            self._real_meter = _METER_PROVIDER.get_meter(
                self._name,
                self._version,
            )
            return self._real_meter
        return self._noop_meter

    def create_counter(self, *args, **kwargs) -> Counter:
        return self._meter.create_counter(*args, **kwargs)

    def create_up_down_counter(self, *args, **kwargs) -> UpDownCounter:
        return self._meter.create_up_down_counter(*args, **kwargs)

    def create_observable_counter(self, *args, **kwargs) -> ObservableCounter:
        return self._meter.create_observable_counter(*args, **kwargs)

    def create_histogram(self, *args, **kwargs) -> Histogram:
        return self._meter.create_histogram(*args, **kwargs)

    def create_observable_gauge(self, *args, **kwargs) -> ObservableGauge:
        return self._meter.create_observable_gauge(*args, **kwargs)

    def create_observable_up_down_counter(
        self, *args, **kwargs
    ) -> ObservableUpDownCounter:
        return self._meter.create_observable_up_down_counter(*args, **kwargs)


class _DefaultMeter(Meter):

    def create_counter(self, name, unit="", description="") -> Counter:
        super().create_counter(name, unit=unit, description=description)
        return DefaultCounter(name, unit=unit, description=description)

    def create_up_down_counter(
        self, name, unit="", description=""
    ) -> UpDownCounter:
        super().create_up_down_counter(
            name, unit=unit, description=description
        )
        return DefaultUpDownCounter(name, unit=unit, description=description)

    def create_observable_counter(
        self, name, callback, unit="", description=""
    ) -> ObservableCounter:
        super().create_observable_counter(
            name, callback, unit=unit, description=description
        )
        return DefaultObservableCounter(
            name,
            callback,
            unit=unit,
            description=description,
        )

    def create_histogram(self, name, unit="", description="") -> Histogram:
        super().create_histogram(name, unit=unit, description=description)
        return DefaultHistogram(name, unit=unit, description=description)

    def create_observable_gauge(
        self, name, callback, unit="", description=""
    ) -> ObservableGauge:
        super().create_observable_gauge(
            name, callback, unit=unit, description=description
        )
        return DefaultObservableGauge(
            name,
            callback,
            unit=unit,
            description=description,
        )

    def create_observable_up_down_counter(
        self, name, callback, unit="", description=""
    ) -> ObservableUpDownCounter:
        super().create_observable_up_down_counter(
            name, callback, unit=unit, description=description
        )
        return DefaultObservableUpDownCounter(
            name,
            callback,
            unit=unit,
            description=description,
        )


_METER_PROVIDER = None
_PROXY_METER_PROVIDER = None


def get_meter(
    name: str,
    version: str = "",
    meter_provider: Optional[MeterProvider] = None,
) -> "Meter":
    """Returns a `Meter` for use by the given instrumentation library.

    This function is a convenience wrapper for
    opentelemetry.trace.MeterProvider.get_meter.

    If meter_provider is omitted the current configured one is used.
    """
    if meter_provider is None:
        meter_provider = get_meter_provider()
    return meter_provider.get_meter(name, version)


def set_meter_provider(meter_provider: MeterProvider) -> None:
    """Sets the current global :class:`~.MeterProvider` object.

    This can only be done once, a warning will be logged if any furter attempt
    is made.
    """
    global _METER_PROVIDER  # pylint: disable=global-statement

    if _METER_PROVIDER is not None:
        _logger.warning("Overriding of current MeterProvider is not allowed")
        return

    _METER_PROVIDER = meter_provider


def get_meter_provider() -> MeterProvider:
    """Gets the current global :class:`~.MeterProvider` object."""
    # pylint: disable=global-statement
    global _METER_PROVIDER
    global _PROXY_METER_PROVIDER

    if _METER_PROVIDER is None:
        if OTEL_PYTHON_METER_PROVIDER not in environ.keys():
            if _PROXY_METER_PROVIDER is None:
                _PROXY_METER_PROVIDER = ProxyMeterProvider()
            return _PROXY_METER_PROVIDER

        _METER_PROVIDER = cast(
            "MeterProvider",
            _load_provider(OTEL_PYTHON_METER_PROVIDER, "meter_provider"),
        )
    return _METER_PROVIDER
