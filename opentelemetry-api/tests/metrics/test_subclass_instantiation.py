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
# type: ignore

# NOTE: The tests in this file are intended to test the semver compatibility of the public API.
# Any tests that fail here indicate that the public API has changed in a way that is not backwards compatible.
# Either bump the major version of the API, or make the necessary changes to the API to remain semver compatible.

# pylint: disable=useless-parent-delegation,arguments-differ

from typing import Optional

from opentelemetry.metrics import (
    Asynchronous,
    Counter,
    Histogram,
    Instrument,
    Meter,
    MeterProvider,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    Synchronous,
    UpDownCounter,
    _Gauge,
)


class MeterProviderImplTest(MeterProvider):
    def get_meter(
        self,
        name: str,
        version: Optional[str] = None,
        schema_url: Optional[str] = None,
    ) -> Meter:
        return super().get_meter(name, version, schema_url)


def test_meter_provider_subclass_instantiation():
    meter_provider = MeterProviderImplTest()
    assert isinstance(meter_provider, MeterProvider)


class MeterImplTest(Meter):
    def create_counter(self, name, description, **kwargs):
        pass

    def create_up_down_counter(self, name, description, **kwargs):
        pass

    def create_observable_counter(self, name, description, **kwargs):
        pass

    def create_histogram(self, name, description, **kwargs):
        pass

    def create_observable_gauge(self, name, description, **kwargs):
        pass

    def create_observable_up_down_counter(self, name, description, **kwargs):
        pass


def test_meter_subclass_instantiation():
    meter = MeterImplTest("subclass_test")
    assert isinstance(meter, Meter)


class SynchronousImplTest(Synchronous):
    def __init__(
        self, name: str, unit: str = "", description: str = ""
    ) -> None:
        super().__init__(name, unit, description)


def test_synchronous_subclass_instantiation():
    synchronous = SynchronousImplTest("subclass_test")
    assert isinstance(synchronous, Synchronous)


class AsynchronousImplTest(Asynchronous):
    def __init__(
        self, name: str, unit: str = "", description: str = ""
    ) -> None:
        super().__init__(name, unit, description)


def test_asynchronous_subclass_instantiation():
    asynchronous = AsynchronousImplTest("subclass_test")
    assert isinstance(asynchronous, Asynchronous)


class CounterImplTest(Counter):
    def __init__(
        self, name: str, unit: str = "", description: str = ""
    ) -> None:
        super().__init__(name, unit, description)

    def add(self, amount: int, **kwargs):
        pass


def test_counter_subclass_instantiation():
    counter = CounterImplTest("subclass_test")
    assert isinstance(counter, Counter)


class UpDownCounterImplTest(UpDownCounter):
    def __init__(
        self, name: str, unit: str = "", description: str = ""
    ) -> None:
        super().__init__(name, unit, description)

    def add(self, amount: int, **kwargs):
        pass


def test_up_down_counter_subclass_instantiation():
    up_down_counter = UpDownCounterImplTest("subclass_test")
    assert isinstance(up_down_counter, UpDownCounter)


class ObservableCounterImplTest(ObservableCounter):
    def __init__(
        self, name: str, unit: str = "", description: str = ""
    ) -> None:
        super().__init__(name, unit, description)


def test_observable_counter_subclass_instantiation():
    observable_counter = ObservableCounterImplTest("subclass_test")
    assert isinstance(observable_counter, ObservableCounter)


class HistogramImplTest(Histogram):
    def __init__(
        self, name: str, unit: str = "", description: str = ""
    ) -> None:
        super().__init__(name, unit, description)

    def record(self, amount: int, **kwargs):
        pass


def test_histogram_subclass_instantiation():
    histogram = HistogramImplTest("subclass_test")
    assert isinstance(histogram, Histogram)


class GaugeImplTest(_Gauge):
    def __init__(
        self, name: str, unit: str = "", description: str = ""
    ) -> None:
        super().__init__(name, unit, description)

    def set(self, amount: int, **kwargs):
        pass


def test_gauge_subclass_instantiation():
    gauge = GaugeImplTest("subclass_test")
    assert isinstance(gauge, _Gauge)


class InstrumentImplTest(Instrument):
    def __init__(
        self, name: str, unit: str = "", description: str = ""
    ) -> None:
        super().__init__(name, unit, description)


def test_instrument_subclass_instantiation():
    instrument = InstrumentImplTest("subclass_test")
    assert isinstance(instrument, Instrument)


class ObservableGaugeImplTest(ObservableGauge):
    def __init__(
        self, name: str, unit: str = "", description: str = ""
    ) -> None:
        super().__init__(name, unit, description)


def test_observable_gauge_subclass_instantiation():
    observable_gauge = ObservableGaugeImplTest("subclass_test")
    assert isinstance(observable_gauge, ObservableGauge)


class ObservableUpDownCounterImplTest(ObservableUpDownCounter):
    def __init__(
        self, name: str, unit: str = "", description: str = ""
    ) -> None:
        super().__init__(name, unit, description)


def test_observable_up_down_counter_subclass_instantiation():
    observable_up_down_counter = ObservableUpDownCounterImplTest(
        "subclass_test"
    )
    assert isinstance(observable_up_down_counter, ObservableUpDownCounter)
