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


from unittest import TestCase
from unittest.mock import Mock

from opentelemetry import metrics
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
        return ObservableCounter("name", Mock())

    def create_histogram(self, name, unit="", description=""):
        return Histogram("name")

    def create_observable_gauge(self, name, callback, unit="", description=""):
        return ObservableGauge("name", Mock())

    def create_observable_up_down_counter(
        self, name, callback, unit="", description=""
    ):
        return ObservableUpDownCounter("name", Mock())


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
        original_provider = metrics._METER_PROVIDER

        provider = get_meter_provider()
        self.assertIsInstance(provider, ProxyMeterProvider)

        meter = provider.get_meter("proxy-test")
        self.assertIsInstance(meter, ProxyMeter)

        self.assertIsInstance(meter.create_counter("counter"), DefaultCounter)

        self.assertIsInstance(
            meter.create_histogram("histogram"), DefaultHistogram
        )

        self.assertIsInstance(
            meter.create_observable_counter("observable_counter", Mock()),
            DefaultObservableCounter,
        )

        self.assertIsInstance(
            meter.create_observable_gauge("observable_gauge", Mock()),
            DefaultObservableGauge,
        )

        self.assertIsInstance(
            meter.create_observable_up_down_counter(
                "observable_up_down_counter", Mock()
            ),
            DefaultObservableUpDownCounter,
        )

        self.assertIsInstance(
            meter.create_up_down_counter("up_down_counter"),
            DefaultUpDownCounter,
        )

        set_meter_provider(Provider())

        self.assertIsInstance(get_meter_provider(), Provider)
        self.assertIsInstance(provider.get_meter("proxy-test"), Meter)

        self.assertIsInstance(meter.create_counter("counter"), Counter)

        self.assertIsInstance(meter.create_histogram("histogram"), Histogram)

        self.assertIsInstance(
            meter.create_observable_counter("observable_counter", Mock()),
            ObservableCounter,
        )

        self.assertIsInstance(
            meter.create_observable_gauge("observable_gauge", Mock()),
            ObservableGauge,
        )

        self.assertIsInstance(
            meter.create_observable_up_down_counter(
                "observable_up_down_counter", Mock()
            ),
            ObservableUpDownCounter,
        )

        self.assertIsInstance(
            meter.create_up_down_counter("up_down_counter"), UpDownCounter
        )

        metrics._METER_PROVIDER = original_provider
