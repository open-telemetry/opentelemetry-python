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

# pylint: disable=W0212,W0222,W0221

from unittest import TestCase

from opentelemetry import metrics
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
        self, instrumentation_module_name, instrumentaiton_library_version=None
    ):
        return TestMeter()


class TestMeter(_DefaultMeter):
    pass


class TestProxy(TestCase):
    def test_proxy_meter(self):
        original_provider = metrics._METER_PROVIDER

        provider = get_meter_provider()
        # proxy provider
        self.assertIsInstance(provider, ProxyMeterProvider)

        # provider returns proxy meter
        meter = provider.get_meter("proxy-test")
        self.assertIsInstance(meter, ProxyMeter)

        # with meter.start_span("span1") as span:
        #     self.assertIsInstance(span, NonRecordingSpan)

        # with meter.start_as_current_span("span2") as span:
        #     self.assertIsInstance(span, NonRecordingSpan)

        # set a real provider
        set_meter_provider(TestProvider())

        # meter provider now returns real instance
        self.assertIsInstance(get_meter_provider(), TestProvider)

        # references to the old provider still work but return real meter now
        real_meter = provider.get_meter("proxy-test")
        self.assertIsInstance(real_meter, TestMeter)

        # reference to old proxy meter now delegates to a real meter and
        # creates real spans
        # with meter.start_span("") as span:
        #     self.assertIsInstance(span, TestSpan)

        metrics._METER_PROVIDER = original_provider
