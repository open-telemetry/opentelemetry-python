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

# pylint: disable=protected-access

from unittest import TestCase
from unittest.mock import Mock, patch

from pytest import fixture

import opentelemetry.metrics._internal as metrics_internal
from opentelemetry import metrics
from opentelemetry.environment_variables import OTEL_PYTHON_METER_PROVIDER
from opentelemetry.metrics import (
    NoOpMeter,
    NoOpMeterProvider,
    get_meter_provider,
    set_meter_provider,
)
from opentelemetry.metrics._internal import _ProxyMeter, _ProxyMeterProvider
from opentelemetry.metrics._internal.instrument import (
    _ProxyCounter,
    _ProxyGauge,
    _ProxyHistogram,
    _ProxyObservableCounter,
    _ProxyObservableGauge,
    _ProxyObservableUpDownCounter,
    _ProxyUpDownCounter,
)
from opentelemetry.test.globals_test import (
    MetricsGlobalsTest,
    reset_metrics_globals,
)

# FIXME Test that the instrument methods can be called concurrently safely.


@fixture
def reset_meter_provider():
    print(f"calling reset_metrics_globals() {reset_metrics_globals}")
    reset_metrics_globals()
    yield
    print("teardown - calling reset_metrics_globals()")
    reset_metrics_globals()


# pylint: disable=redefined-outer-name
def test_set_meter_provider(reset_meter_provider):
    """
    Test that the API provides a way to set a global default MeterProvider
    """

    mock = Mock()

    assert metrics_internal._METER_PROVIDER is None

    set_meter_provider(mock)

    assert metrics_internal._METER_PROVIDER is mock
    assert get_meter_provider() is mock


def test_set_meter_provider_calls_proxy_provider(reset_meter_provider):
    with patch(
        "opentelemetry.metrics._internal._PROXY_METER_PROVIDER"
    ) as mock_proxy_mp:
        assert metrics_internal._PROXY_METER_PROVIDER is mock_proxy_mp
        mock_real_mp = Mock()
        set_meter_provider(mock_real_mp)
        mock_proxy_mp.on_set_meter_provider.assert_called_once_with(
            mock_real_mp
        )


def test_get_meter_provider(reset_meter_provider):
    """
    Test that the API provides a way to get a global default MeterProvider
    """

    assert metrics_internal._METER_PROVIDER is None

    assert isinstance(get_meter_provider(), _ProxyMeterProvider)

    metrics._METER_PROVIDER = None

    with patch.dict(
        "os.environ", {OTEL_PYTHON_METER_PROVIDER: "test_meter_provider"}
    ):

        with patch("opentelemetry.metrics._internal._load_provider", Mock()):
            with patch(
                "opentelemetry.metrics._internal.cast",
                Mock(**{"return_value": "test_meter_provider"}),
            ):
                assert get_meter_provider() == "test_meter_provider"


class TestGetMeter(TestCase):
    def test_get_meter_parameters(self):
        """
        Test that get_meter accepts name, version and schema_url
        """
        try:
            NoOpMeterProvider().get_meter(
                "name", version="version", schema_url="schema_url"
            )
        except Exception as error:  # pylint: disable=broad-exception-caught
            self.fail(f"Unexpected exception raised: {error}")

    def test_invalid_name(self):
        """
        Test that when an invalid name is specified a working meter
        implementation is returned as a fallback.

        Test that the fallback meter name property keeps its original invalid
        value.

        Test that a message is logged reporting the specified value for the
        fallback meter is invalid.
        """
        meter = NoOpMeterProvider().get_meter("")

        self.assertTrue(isinstance(meter, NoOpMeter))

        self.assertEqual(meter.name, "")

        meter = NoOpMeterProvider().get_meter(None)

        self.assertTrue(isinstance(meter, NoOpMeter))

        self.assertEqual(meter.name, None)


class TestProxy(MetricsGlobalsTest, TestCase):
    def test_global_proxy_meter_provider(self):
        # Global get_meter_provider() should initially be a _ProxyMeterProvider
        # singleton

        proxy_meter_provider: _ProxyMeterProvider = get_meter_provider()
        self.assertIsInstance(proxy_meter_provider, _ProxyMeterProvider)
        self.assertIs(get_meter_provider(), proxy_meter_provider)

    def test_proxy_provider(self):
        proxy_meter_provider = _ProxyMeterProvider()

        # Should return a proxy meter when no real MeterProvider is set
        name = "foo"
        version = "1.2"
        schema_url = "schema_url"
        proxy_meter: _ProxyMeter = proxy_meter_provider.get_meter(
            name, version=version, schema_url=schema_url
        )
        self.assertIsInstance(proxy_meter, _ProxyMeter)

        # After setting a real meter provider on the proxy, it should notify
        # it's _ProxyMeters which should create their own real Meters
        mock_real_mp = Mock()
        proxy_meter_provider.on_set_meter_provider(mock_real_mp)
        mock_real_mp.get_meter.assert_called_once_with(
            name, version, schema_url
        )

        # After setting a real meter provider on the proxy, it should now return
        # new meters directly from the set real meter
        another_name = "bar"
        meter2 = proxy_meter_provider.get_meter(another_name)
        self.assertIsInstance(meter2, Mock)
        mock_real_mp.get_meter.assert_called_with(another_name, None, None)

    # pylint: disable=too-many-locals,too-many-statements
    def test_proxy_meter(self):
        meter_name = "foo"
        proxy_meter: _ProxyMeter = _ProxyMeterProvider().get_meter(meter_name)
        self.assertIsInstance(proxy_meter, _ProxyMeter)

        # Should be able to create proxy instruments
        name = "foo"
        unit = "s"
        description = "Foobar"
        callback = Mock()
        proxy_counter = proxy_meter.create_counter(
            name, unit=unit, description=description
        )
        proxy_updowncounter = proxy_meter.create_up_down_counter(
            name, unit=unit, description=description
        )
        proxy_histogram = proxy_meter.create_histogram(
            name, unit=unit, description=description
        )

        proxy_gauge = proxy_meter.create_gauge(
            name, unit=unit, description=description
        )

        proxy_observable_counter = proxy_meter.create_observable_counter(
            name, callbacks=[callback], unit=unit, description=description
        )
        proxy_observable_updowncounter = (
            proxy_meter.create_observable_up_down_counter(
                name, callbacks=[callback], unit=unit, description=description
            )
        )
        proxy_overvable_gauge = proxy_meter.create_observable_gauge(
            name, callbacks=[callback], unit=unit, description=description
        )
        self.assertIsInstance(proxy_counter, _ProxyCounter)
        self.assertIsInstance(proxy_updowncounter, _ProxyUpDownCounter)
        self.assertIsInstance(proxy_histogram, _ProxyHistogram)
        self.assertIsInstance(proxy_gauge, _ProxyGauge)
        self.assertIsInstance(
            proxy_observable_counter, _ProxyObservableCounter
        )
        self.assertIsInstance(
            proxy_observable_updowncounter, _ProxyObservableUpDownCounter
        )
        self.assertIsInstance(proxy_overvable_gauge, _ProxyObservableGauge)

        # Synchronous proxy instruments should be usable
        amount = 12
        attributes = {"foo": "bar"}
        proxy_counter.add(amount, attributes=attributes)
        proxy_updowncounter.add(amount, attributes=attributes)
        proxy_histogram.record(amount, attributes=attributes)
        proxy_gauge.set(amount, attributes=attributes)

        # Calling _ProxyMeterProvider.on_set_meter_provider() should cascade down
        # to the _ProxyInstruments which should create their own real instruments
        # from the real Meter to back their calls
        real_meter_provider = Mock()
        proxy_meter.on_set_meter_provider(real_meter_provider)
        real_meter_provider.get_meter.assert_called_once_with(
            meter_name, None, None
        )

        real_meter: Mock = real_meter_provider.get_meter()
        real_meter.create_counter.assert_called_once_with(
            name, unit, description
        )
        real_meter.create_up_down_counter.assert_called_once_with(
            name, unit, description
        )
        real_meter.create_histogram.assert_called_once_with(
            name, unit, description
        )
        real_meter.create_gauge.assert_called_once_with(
            name, unit, description
        )
        real_meter.create_observable_counter.assert_called_once_with(
            name, [callback], unit, description
        )
        real_meter.create_observable_up_down_counter.assert_called_once_with(
            name, [callback], unit, description
        )
        real_meter.create_observable_gauge.assert_called_once_with(
            name, [callback], unit, description
        )

        # The synchronous instrument measurement methods should call through to
        # the real instruments
        real_counter: Mock = real_meter.create_counter()
        real_updowncounter: Mock = real_meter.create_up_down_counter()
        real_histogram: Mock = real_meter.create_histogram()
        real_gauge: Mock = real_meter.create_gauge()
        real_counter.assert_not_called()
        real_updowncounter.assert_not_called()
        real_histogram.assert_not_called()
        real_gauge.assert_not_called()

        proxy_counter.add(amount, attributes=attributes)
        real_counter.add.assert_called_once_with(amount, attributes)
        proxy_updowncounter.add(amount, attributes=attributes)
        real_updowncounter.add.assert_called_once_with(amount, attributes)
        proxy_histogram.record(amount, attributes=attributes)
        real_histogram.record.assert_called_once_with(amount, attributes)
        proxy_gauge.set(amount, attributes=attributes)
        real_gauge.set.assert_called_once_with(amount, attributes)

    def test_proxy_meter_with_real_meter(self) -> None:
        # Creating new instruments on the _ProxyMeter with a real meter set
        # should create real instruments instead of proxies
        meter_name = "foo"
        proxy_meter: _ProxyMeter = _ProxyMeterProvider().get_meter(meter_name)
        self.assertIsInstance(proxy_meter, _ProxyMeter)

        real_meter_provider = Mock()
        proxy_meter.on_set_meter_provider(real_meter_provider)

        name = "foo"
        unit = "s"
        description = "Foobar"
        callback = Mock()
        counter = proxy_meter.create_counter(
            name, unit=unit, description=description
        )
        updowncounter = proxy_meter.create_up_down_counter(
            name, unit=unit, description=description
        )
        histogram = proxy_meter.create_histogram(
            name, unit=unit, description=description
        )
        gauge = proxy_meter.create_gauge(
            name, unit=unit, description=description
        )
        observable_counter = proxy_meter.create_observable_counter(
            name, callbacks=[callback], unit=unit, description=description
        )
        observable_updowncounter = (
            proxy_meter.create_observable_up_down_counter(
                name, callbacks=[callback], unit=unit, description=description
            )
        )
        observable_gauge = proxy_meter.create_observable_gauge(
            name, callbacks=[callback], unit=unit, description=description
        )

        real_meter: Mock = real_meter_provider.get_meter()
        self.assertIs(counter, real_meter.create_counter())
        self.assertIs(updowncounter, real_meter.create_up_down_counter())
        self.assertIs(histogram, real_meter.create_histogram())
        self.assertIs(gauge, real_meter.create_gauge())
        self.assertIs(
            observable_counter, real_meter.create_observable_counter()
        )
        self.assertIs(
            observable_updowncounter,
            real_meter.create_observable_up_down_counter(),
        )
        self.assertIs(observable_gauge, real_meter.create_observable_gauge())
