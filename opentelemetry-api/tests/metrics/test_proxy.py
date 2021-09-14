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
from opentelemetry.metrics.instrument import (
    DefaultCounter,
    DefaultHistogram,
    DefaultObservableCounter,
    DefaultObservableGauge,
    DefaultObservableUpDownCounter,
    DefaultUpDownCounter,
)
from opentelemetry.metrics import (
    _DefaultMeterProvider,
    _DefaultMeter,
    ProxyMeter,
    ProxyMeterProvider,
    set_meter_provider,
    get_meter_provider,
)


class TestProvider(_DefaultMeterProvider):
    def get_meter(
        self, instrumentation_module_name, instrumentation_library_version=None
    ):
        return TestMeter()


class TestMeter(_DefaultMeter):
    pass


class TestDefaultHistogram(DefaultHistogram):
    pass


class TestDefaultObservableCounter(DefaultObservableCounter):
    pass


class TestDefaultObservableGauge(DefaultObservableGauge):
    pass


class TestDefaultObservableUpDownCounter(DefaultObservableUpDownCounter):
    pass


class TestDefaultUpDownCounter(DefaultUpDownCounter):
    pass


class TestProxy(TestCase):
    def test_proxy_meter(self):
        original_provider = metrics._METER_PROVIDER

        provider = get_meter_provider()
        self.assertIsInstance(provider, ProxyMeterProvider)

        meter = provider.get_meter("proxy-test")
        self.assertIsInstance(meter, ProxyMeter)

        counter = meter.create_counter("counter")
        self.assertIsInstance(counter, DefaultCounter)

        histogram = meter.create_histogram("histogram")
        self.assertIsInstance(histogram, DefaultHistogram)

        observable_counter = meter.create_observable_counter("observable_counter", Mock())
        self.assertIsInstance(observable_counter, DefaultObservableCounter)

        observable_gauge = meter.create_observable_gauge("observable_gauge", Mock())
        self.assertIsInstance(observable_gauge, DefaultObservableGauge)

        observable_up_down_counter = meter.create_observable_up_down_counter("observable_up_down_counter", Mock())
        self.assertIsInstance(observable_up_down_counter, DefaultObservableUpDownCounter)

        up_down_counter = meter.create_up_down_counter("up_down_counter")
        self.assertIsInstance(up_down_counter, DefaultUpDownCounter)

        set_meter_provider(TestProvider())

        self.assertIsInstance(get_meter_provider(), TestProvider)

        # references to the old provider still work but return real meter now
        real_meter = provider.get_meter("proxy-test")
        self.assertIsInstance(real_meter, TestMeter)

        # reference to old proxy meter now delegates to a real meter and
        # creates real spans
        # with meter.start_span("") as span:
        #     self.assertIsInstance(span, TestSpan)

        metrics._METER_PROVIDER = original_provider
