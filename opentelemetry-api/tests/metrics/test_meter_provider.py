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

from logging import WARNING
from unittest import TestCase
from unittest.mock import Mock, patch

from pytest import fixture

from opentelemetry import metrics
from opentelemetry.environment_variables import OTEL_PYTHON_METER_PROVIDER
from opentelemetry.metrics import (
    ProxyMeter,
    ProxyMeterProvider,
    _DefaultMeter,
    _DefaultMeterProvider,
    get_meter_provider,
    set_meter_provider,
)
from opentelemetry.metrics.instrument import (
    DefaultCounter,
    DefaultHistogram,
    DefaultObservableCounter,
    DefaultObservableGauge,
    DefaultObservableUpDownCounter,
    DefaultUpDownCounter,
)


# FIXME Test that the instrument methods can be called concurrently safely.

@fixture
def reset_meter_provider():
    original_meter_provider_value = metrics._METER_PROVIDER

    yield

    metrics._METER_PROVIDER = original_meter_provider_value


def test_set_meter_provider(reset_meter_provider):
    """
    Test that the API provides a way to set a global default MeterProvider
    """

    mock = Mock()

    assert metrics._METER_PROVIDER is None

    set_meter_provider(mock)

    assert metrics._METER_PROVIDER is mock


def test_get_meter_provider(reset_meter_provider):
    """
    Test that the API provides a way to get a global default MeterProvider
    """

    assert metrics._METER_PROVIDER is None

    assert isinstance(get_meter_provider(), ProxyMeterProvider)

    metrics._METER_PROVIDER = None

    with patch.dict(
        "os.environ", {OTEL_PYTHON_METER_PROVIDER: "test_meter_provider"}
    ):

        with patch("opentelemetry.metrics._load_provider", Mock()):
            with patch(
                "opentelemetry.metrics.cast",
                Mock(**{"return_value": "test_meter_provider"}),
            ):
                assert get_meter_provider() == "test_meter_provider"


class TestGetMeter(TestCase):
    def test_get_meter_parameters(self):
        """
        Test that get_meter accepts name, version and schema_url
        """
        try:
            _DefaultMeterProvider().get_meter(
                "name", version="version", schema_url="schema_url"
            )
        except Exception as error:
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
        with self.assertLogs(level=WARNING):
            meter = _DefaultMeterProvider().get_meter("")

            self.assertTrue(isinstance(meter, _DefaultMeter))

        self.assertEqual(meter.name, "")

        with self.assertLogs(level=WARNING):
            meter = _DefaultMeterProvider().get_meter(None)

            self.assertTrue(isinstance(meter, _DefaultMeter))

        self.assertEqual(meter.name, None)

    def test_new_configuration(self):
        """
        Test that new configuration applies to previously returned meters.
        """

        # Configuration is to be stored in the MeterProvider. It is not
        # specified exactly how it will be stored, but it is enough for the
        # meter to have access to the meter provider to get configuration
        # changes automatically.

        meter_provider = _DefaultMeterProvider()
        self.assertIs(
            meter_provider.get_meter("name")._meter_provider, meter_provider
        )


class Provider(_DefaultMeterProvider):
    def get_meter(self, name, version=None, schema_url=None):
        return Meter(name, version=version, schema_url=schema_url)


class Meter(_DefaultMeter):
    def create_counter(self, name, unit="", description=""):
        return Counter("name")

    def create_up_down_counter(self, name, unit="", description=""):
        return UpDownCounter("name")

    def create_observable_counter(
        self, name, callback, unit="", description=""
    ):
        return ObservableCounter("name", callback)

    def create_histogram(self, name, unit="", description=""):
        return Histogram("name")

    def create_observable_gauge(self, name, callback, unit="", description=""):
        return ObservableGauge("name", callback)

    def create_observable_up_down_counter(
        self, name, callback, unit="", description=""
    ):
        return ObservableUpDownCounter("name", callback)


class Counter(DefaultCounter):
    pass


class Histogram(DefaultHistogram):
    pass


class ObservableCounter(DefaultObservableCounter):
    pass


class ObservableGauge(DefaultObservableGauge):
    pass


class ObservableUpDownCounter(DefaultObservableUpDownCounter):
    pass


class UpDownCounter(DefaultUpDownCounter):
    pass


class TestProxy(TestCase):
    def test_proxy_meter(self):

        """
        Test that the proxy meter provider and proxy meter automatically point
        to updated objects.
        """

        original_provider = metrics._METER_PROVIDER

        provider = get_meter_provider()
        self.assertIsInstance(provider, ProxyMeterProvider)

        meter = provider.get_meter("proxy-test")
        self.assertIsInstance(meter, ProxyMeter)

        self.assertIsInstance(meter.create_counter("counter0"), DefaultCounter)

        self.assertIsInstance(
            meter.create_histogram("histogram0"), DefaultHistogram
        )

        def callback():
            yield

        self.assertIsInstance(
            meter.create_observable_counter("observable_counter0", callback()),
            DefaultObservableCounter,
        )

        self.assertIsInstance(
            meter.create_observable_gauge("observable_gauge0", callback()),
            DefaultObservableGauge,
        )

        self.assertIsInstance(
            meter.create_observable_up_down_counter(
                "observable_up_down_counter0", callback()
            ),
            DefaultObservableUpDownCounter,
        )

        self.assertIsInstance(
            meter.create_up_down_counter("up_down_counter0"),
            DefaultUpDownCounter,
        )

        set_meter_provider(Provider())

        self.assertIsInstance(get_meter_provider(), Provider)
        self.assertIsInstance(provider.get_meter("proxy-test"), Meter)

        self.assertIsInstance(meter.create_counter("counter1"), Counter)

        self.assertIsInstance(meter.create_histogram("histogram1"), Histogram)

        self.assertIsInstance(
            meter.create_observable_counter("observable_counter1", callback()),
            ObservableCounter,
        )

        self.assertIsInstance(
            meter.create_observable_gauge("observable_gauge1", callback()),
            ObservableGauge,
        )

        self.assertIsInstance(
            meter.create_observable_up_down_counter(
                "observable_up_down_counter1", callback()
            ),
            ObservableUpDownCounter,
        )

        self.assertIsInstance(
            meter.create_up_down_counter("up_down_counter1"), UpDownCounter
        )

        metrics._METER_PROVIDER = original_provider
