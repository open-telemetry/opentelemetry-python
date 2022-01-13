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
from unittest.mock import Mock, patch

from opentelemetry.sdk._metrics import MeterProvider
from opentelemetry.sdk._metrics.measurement_consumer import (
    MeasurementConsumer,
    SynchronousMeasurementConsumer,
)


class TestSynchronousMeasurementConsumer(TestCase):
    def test_parent(self):

        self.assertIsInstance(
            SynchronousMeasurementConsumer(), MeasurementConsumer
        )

    @patch("opentelemetry.sdk._metrics.SynchronousMeasurementConsumer")
    def test_measurement_consumer_class(
        self, mock_serial_measurement_consumer
    ):
        MeterProvider()

        mock_serial_measurement_consumer.assert_called()

    @patch("opentelemetry.sdk._metrics.SynchronousMeasurementConsumer")
    def test_register_asynchronous_instrument(
        self, mock_serial_measurement_consumer
    ):

        meter_provider = MeterProvider()

        meter_provider._measurement_consumer.register_asynchronous_instrument.assert_called_with(
            meter_provider.get_meter("name").create_observable_counter(
                "name", Mock()
            )
        )
        meter_provider._measurement_consumer.register_asynchronous_instrument.assert_called_with(
            meter_provider.get_meter("name").create_observable_up_down_counter(
                "name", Mock()
            )
        )
        meter_provider._measurement_consumer.register_asynchronous_instrument.assert_called_with(
            meter_provider.get_meter("name").create_observable_gauge(
                "name", Mock()
            )
        )

    @patch("opentelemetry.sdk._metrics.SynchronousMeasurementConsumer")
    def test_consume_measurement_counter(
        self, mock_serial_measurement_consumer
    ):

        meter_provider = MeterProvider()
        counter = meter_provider.get_meter("name").create_counter("name")

        counter.add(1)

        meter_provider._measurement_consumer.consume_measurement.assert_called()

    @patch("opentelemetry.sdk._metrics.SynchronousMeasurementConsumer")
    def test_consume_measurement_up_down_counter(
        self, mock_serial_measurement_consumer
    ):

        meter_provider = MeterProvider()
        counter = meter_provider.get_meter("name").create_up_down_counter(
            "name"
        )

        counter.add(1)

        meter_provider._measurement_consumer.consume_measurement.assert_called()

    @patch("opentelemetry.sdk._metrics.SynchronousMeasurementConsumer")
    def test_consume_measurement_histogram(
        self, mock_serial_measurement_consumer
    ):

        meter_provider = MeterProvider()
        counter = meter_provider.get_meter("name").create_histogram("name")

        counter.record(1)

        meter_provider._measurement_consumer.consume_measurement.assert_called()
