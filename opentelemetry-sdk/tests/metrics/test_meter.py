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

from opentelemetry.metrics.meter import Meter, MeterProvider
from opentelemetry.sdk.metrics.meter import Meter as SDKMeter
from opentelemetry.sdk.metrics.meter import MeterProvider as SDKMeterProvider


class TestMeter(TestCase):
    def test_meter_provider(self):
        meter_provider = SDKMeterProvider()
        self.assertIsInstance(meter_provider, SDKMeterProvider)
        self.assertIsInstance(meter_provider, MeterProvider)

    def test_meter(self):
        meter = SDKMeterProvider().get_meter(__name__)
        self.assertIsInstance(meter, SDKMeter)
        self.assertIsInstance(meter, Meter)
