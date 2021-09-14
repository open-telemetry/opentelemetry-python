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
from opentelemetry.metrics import set_meter_provider


class TestMeterProvider(TestCase):

    def setUp(self):
        self.original_meter_provider_value = metrics._METER_PROVIDER

    def tearDown(self):
        metrics._METER_PROVIDER = self.original_meter_provider_value

    def test_set_meter_provider(self):
        """
        Test that the API provides a way to set a global default MeterProvider
        """

        mock = Mock()

        self.assertIsNone(metrics._METER_PROVIDER)

        set_meter_provider(mock)

        self.assertIs(metrics._METER_PROVIDER, mock)

    def test_get_meter_provider(self):
        """
        Test that a global `MeterProvider` can be get.
        """
