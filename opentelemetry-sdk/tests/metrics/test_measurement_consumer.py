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

# pylint: disable=invalid-name,no-self-use

from time import sleep
from unittest import TestCase
from unittest.mock import MagicMock, Mock, patch

from opentelemetry.sdk.metrics._internal.measurement_consumer import (
    MeasurementConsumer,
    SynchronousMeasurementConsumer,
)
from opentelemetry.sdk.metrics._internal.sdk_configuration import (
    SdkConfiguration,
)


@patch(
    "opentelemetry.sdk.metrics._internal."
    "measurement_consumer.MetricReaderStorage"
)
class TestSynchronousMeasurementConsumer(TestCase):
    def test_parent(self, _):

        self.assertIsInstance(
            SynchronousMeasurementConsumer(MagicMock()), MeasurementConsumer
        )

    def test_creates_metric_reader_storages(self, MockMetricReaderStorage):
        """It should create one MetricReaderStorage per metric reader passed in the SdkConfiguration"""
        reader_mocks = [Mock() for _ in range(5)]
        SynchronousMeasurementConsumer(
            SdkConfiguration(
                resource=Mock(),
                metric_readers=reader_mocks,
                views=Mock(),
            )
        )
        self.assertEqual(len(MockMetricReaderStorage.mock_calls), 5)

    def test_measurements_passed_to_each_reader_storage(
        self, MockMetricReaderStorage
    ):
        reader_mocks = [Mock() for _ in range(5)]
        reader_storage_mocks = [Mock() for _ in range(5)]
        MockMetricReaderStorage.side_effect = reader_storage_mocks

        consumer = SynchronousMeasurementConsumer(
            SdkConfiguration(
                resource=Mock(),
                metric_readers=reader_mocks,
                views=Mock(),
            )
        )
        measurement_mock = Mock()
        consumer.consume_measurement(measurement_mock)

        for rs_mock in reader_storage_mocks:
            rs_mock.consume_measurement.assert_called_once_with(
                measurement_mock
            )

    def test_collect_passed_to_reader_stage(self, MockMetricReaderStorage):
        """Its collect() method should defer to the underlying MetricReaderStorage"""
        reader_mocks = [Mock() for _ in range(5)]
        reader_storage_mocks = [Mock() for _ in range(5)]
        MockMetricReaderStorage.side_effect = reader_storage_mocks

        consumer = SynchronousMeasurementConsumer(
            SdkConfiguration(
                resource=Mock(),
                metric_readers=reader_mocks,
                views=Mock(),
            )
        )
        for r_mock, rs_mock in zip(reader_mocks, reader_storage_mocks):
            rs_mock.collect.assert_not_called()
            consumer.collect(r_mock)
            rs_mock.collect.assert_called_once_with()

    def test_collect_calls_async_instruments(self, MockMetricReaderStorage):
        """Its collect() method should invoke async instruments and pass measurements to the
        corresponding metric reader storage"""
        reader_mock = Mock()
        reader_storage_mock = Mock()
        MockMetricReaderStorage.return_value = reader_storage_mock
        consumer = SynchronousMeasurementConsumer(
            SdkConfiguration(
                resource=Mock(),
                metric_readers=[reader_mock],
                views=Mock(),
            )
        )
        async_instrument_mocks = [MagicMock() for _ in range(5)]
        for i_mock in async_instrument_mocks:
            i_mock.callback.return_value = [Mock()]
            consumer.register_asynchronous_instrument(i_mock)

        consumer.collect(reader_mock)

        # it should call async instruments
        for i_mock in async_instrument_mocks:
            i_mock.callback.assert_called_once()

        # it should pass measurements to reader storage
        self.assertEqual(
            len(reader_storage_mock.consume_measurement.mock_calls), 5
        )

    def test_collect_timeout(self, MockMetricReaderStorage):
        reader_mock = Mock()
        reader_storage_mock = Mock()
        MockMetricReaderStorage.return_value = reader_storage_mock
        consumer = SynchronousMeasurementConsumer(
            SdkConfiguration(
                resource=Mock(),
                metric_readers=[reader_mock],
                views=Mock(),
            )
        )

        def sleep_1(*args, **kwargs):
            sleep(1)

        consumer.register_asynchronous_instrument(
            Mock(**{"callback.side_effect": sleep_1})
        )

        with self.assertRaises(Exception) as error:
            consumer.collect(reader_mock, timeout_millis=10)

        self.assertIn(
            "Timed out while executing callback", error.exception.args[0]
        )

    @patch(
        "opentelemetry.sdk.metrics._internal."
        "measurement_consumer.CallbackOptions"
    )
    def test_collect_deadline(
        self, mock_callback_options, MockMetricReaderStorage
    ):
        reader_mock = Mock()
        reader_storage_mock = Mock()
        MockMetricReaderStorage.return_value = reader_storage_mock
        consumer = SynchronousMeasurementConsumer(
            SdkConfiguration(
                resource=Mock(),
                metric_readers=[reader_mock],
                views=Mock(),
            )
        )

        def sleep_1(*args, **kwargs):
            sleep(1)
            return []

        consumer.register_asynchronous_instrument(
            Mock(**{"callback.side_effect": sleep_1})
        )
        consumer.register_asynchronous_instrument(
            Mock(**{"callback.side_effect": sleep_1})
        )

        consumer.collect(reader_mock)

        callback_options_time_call = mock_callback_options.mock_calls[
            -1
        ].kwargs["timeout_millis"]

        self.assertLess(
            callback_options_time_call,
            10000,
        )
