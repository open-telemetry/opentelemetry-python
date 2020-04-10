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

import unittest

from opentelemetry.metrics import DefaultMeter, DefaultMetric
from opentelemetry.sdk import metrics


class TestMeterImplementation(unittest.TestCase):
    """
    This test is in place to ensure the SDK implementation of the API
    is returning values that are valid. The same tests have been added
    to the API with different expected results. See issue for more details:
    https://github.com/open-telemetry/opentelemetry-python/issues/142
    """

    def test_meter(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        metric = meter.create_metric("", "", "", float, metrics.Counter)
        self.assertNotIsInstance(meter, DefaultMeter)
        self.assertNotIsInstance(metric, DefaultMetric)
