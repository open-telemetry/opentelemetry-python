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

from unittest.mock import Mock, patch

from opentelemetry.sdk._metrics.measurement import Measurement
from opentelemetry.sdk._metrics.metric_reader_storage import (
    MetricReaderStorage,
)
from opentelemetry.sdk._metrics.point import AggregationTemporality
from opentelemetry.sdk._metrics.sdk_configuration import SdkConfiguration
from opentelemetry.test.concurrency_test import ConcurrencyTestBase, MockFunc


def mock_view_matching(*instruments) -> Mock:
    mock = Mock()
    mock.match.side_effect = lambda instrument: instrument in instruments
    return mock


@patch("opentelemetry.sdk._metrics.metric_reader_storage.ViewStorage")
class TestMetricReaderStorage(ConcurrencyTestBase):
    def test_creates_view_storages(self, MockViewStorage: Mock):
        """It should create a ViewStorage when an instrument matches a view"""
        instrument1 = Mock(name="instrument1")
        instrument2 = Mock(name="instrument2")

        view1 = mock_view_matching(instrument1)
        view2 = mock_view_matching(instrument1, instrument2)
        storage = MetricReaderStorage(
            SdkConfiguration(
                resource=Mock(), metric_readers=(), views=(view1, view2)
            )
        )

        # instrument1 matches view1 and view2, so should create two ViewStorages
        storage.consume_measurement(Measurement(1, instrument1))
        self.assertEqual(
            len(MockViewStorage.call_args_list), 2, MockViewStorage.mock_calls
        )
        # they should only be created the first time the instrument is seen
        storage.consume_measurement(Measurement(1, instrument1))
        self.assertEqual(len(MockViewStorage.call_args_list), 2)

        # instrument2 matches view2, so should create a single ViewStorage
        MockViewStorage.call_args_list.clear()
        storage.consume_measurement(Measurement(1, instrument2))
        self.assertEqual(len(MockViewStorage.call_args_list), 1)

    def test_forwards_calls_to_view_storage(self, MockViewStorage: Mock):
        view_storage1 = Mock()
        view_storage2 = Mock()
        view_storage3 = Mock()
        MockViewStorage.side_effect = [
            view_storage1,
            view_storage2,
            view_storage3,
        ]

        instrument1 = Mock(name="instrument1")
        instrument2 = Mock(name="instrument2")
        view1 = mock_view_matching(instrument1)
        view2 = mock_view_matching(instrument1, instrument2)
        storage = MetricReaderStorage(
            SdkConfiguration(
                resource=Mock(), metric_readers=(), views=(view1, view2)
            )
        )

        # Measurements from an instrument should be passed on to each ViewStorage created for
        # that instrument
        measurement = Measurement(1, instrument1)
        storage.consume_measurement(measurement)
        view_storage1.consume_measurement.assert_called_once_with(measurement)
        view_storage2.consume_measurement.assert_called_once_with(measurement)
        view_storage3.consume_measurement.assert_not_called()

        measurement = Measurement(1, instrument2)
        storage.consume_measurement(measurement)
        view_storage3.consume_measurement.assert_called_once_with(measurement)

        # collect() should call collect on all of its ViewStorages and combine them together
        all_metrics = [Mock() for _ in range(6)]
        view_storage1.collect.return_value = all_metrics[:2]
        view_storage2.collect.return_value = all_metrics[2:4]
        view_storage3.collect.return_value = all_metrics[4:]

        result = storage.collect(AggregationTemporality.CUMULATIVE)
        view_storage1.collect.assert_called_once()
        view_storage2.collect.assert_called_once()
        view_storage3.collect.assert_called_once()
        self.assertEqual(result, all_metrics)

    def test_race_concurrent_measurements(self, MockViewStorage: Mock):
        mock_view_storage_ctor = MockFunc()
        MockViewStorage.side_effect = mock_view_storage_ctor

        instrument1 = Mock(name="instrument1")
        view1 = mock_view_matching(instrument1)
        storage = MetricReaderStorage(
            SdkConfiguration(
                resource=Mock(), metric_readers=(), views=(view1,)
            )
        )

        def send_measurement():
            storage.consume_measurement(Measurement(1, instrument1))

        # race sending many measurements concurrently
        self.run_with_many_threads(send_measurement)

        # ViewStorage constructor should have only been called once
        self.assertEqual(mock_view_storage_ctor.call_count, 1)
