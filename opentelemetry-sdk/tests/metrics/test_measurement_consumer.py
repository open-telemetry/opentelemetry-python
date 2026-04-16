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

from threading import Event, Thread
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
            SynchronousMeasurementConsumer(MagicMock(), metric_readers=()),
            MeasurementConsumer,
        )

    def test_creates_metric_reader_storages(self, MockMetricReaderStorage):
        """It should create one MetricReaderStorage per metric reader passed in the SdkConfiguration"""
        reader_mocks = [Mock() for _ in range(5)]
        SynchronousMeasurementConsumer(
            SdkConfiguration(
                exemplar_filter=Mock(),
                resource=Mock(),
                views=Mock(),
            ),
            metric_readers=reader_mocks,
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
                exemplar_filter=Mock(should_sample=Mock(return_value=False)),
                resource=Mock(),
                views=Mock(),
            ),
            metric_readers=reader_mocks,
        )
        measurement_mock = Mock()
        consumer.consume_measurement(measurement_mock)

        for rs_mock in reader_storage_mocks:
            rs_mock.consume_measurement.assert_called_once_with(
                measurement_mock, False
            )

    def test_collect_passed_to_reader_stage(self, MockMetricReaderStorage):
        """Its collect() method should defer to the underlying MetricReaderStorage"""
        reader_mocks = [Mock() for _ in range(5)]
        reader_storage_mocks = [Mock() for _ in range(5)]
        MockMetricReaderStorage.side_effect = reader_storage_mocks

        consumer = SynchronousMeasurementConsumer(
            SdkConfiguration(
                exemplar_filter=Mock(),
                resource=Mock(),
                views=Mock(),
            ),
            metric_readers=reader_mocks,
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
                exemplar_filter=Mock(should_sample=Mock(return_value=False)),
                resource=Mock(),
                views=Mock(),
            ),
            metric_readers=[reader_mock],
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
        # assert consume_measurement was called with at least 2 arguments the second
        # matching the mocked exemplar filter
        self.assertFalse(reader_storage_mock.consume_measurement.call_args[1])

    def test_collect_timeout(self, MockMetricReaderStorage):
        reader_mock = Mock()
        reader_storage_mock = Mock()
        MockMetricReaderStorage.return_value = reader_storage_mock
        consumer = SynchronousMeasurementConsumer(
            SdkConfiguration(
                exemplar_filter=Mock(),
                resource=Mock(),
                views=Mock(),
            ),
            metric_readers=[reader_mock],
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
    @patch("opentelemetry.sdk.metrics._internal.measurement_consumer.time_ns")
    def test_collect_deadline(
        self, mock_time_ns, mock_callback_options, MockMetricReaderStorage
    ):
        reader_mock = Mock()
        reader_storage_mock = Mock()
        MockMetricReaderStorage.return_value = reader_storage_mock
        consumer = SynchronousMeasurementConsumer(
            SdkConfiguration(
                exemplar_filter=Mock(),
                resource=Mock(),
                views=Mock(),
            ),
            metric_readers=[reader_mock],
        )

        consumer.register_asynchronous_instrument(
            Mock(**{"callback.return_value": []})
        )
        consumer.register_asynchronous_instrument(
            Mock(**{"callback.return_value": []})
        )

        # collect start, first remaining_time, post-first callback,
        # second remaining_time, post-second callback
        mock_time_ns.side_effect = [
            0,
            0,
            int(1e9),
            int(1e9),
            int(2e9),
        ]

        consumer.collect(reader_mock)

        callback_options_time_call = mock_callback_options.mock_calls[
            -1
        ].kwargs["timeout_millis"]

        self.assertLess(
            callback_options_time_call,
            10000,
        )


class TestSynchronousMeasurementConsumerConcurrency(TestCase):
    def test_concurrent_changes_to_metric_readers(self):
        timeout = 1
        failure = None
        iteration_started = Event()
        mutation_done = Event()
        iteration_timeout_error = "Timed out waiting for iteration to start"
        mutation_timeout_error = "Timed out waiting for mutation to be done"

        consumer = SynchronousMeasurementConsumer(
            SdkConfiguration(
                exemplar_filter=MagicMock(),
                resource=MagicMock(),
                views=MagicMock(),
            ),
            metric_readers=[MagicMock()],
        )

        def _hooked_iter(iterable):
            nonlocal failure

            iterable = iter(iterable)
            iteration_started.set()
            if not mutation_done.wait(timeout):
                failure = mutation_timeout_error
            yield next(iterable, None)
            yield from iterable

        class HookedDict(dict):
            def __iter__(self):
                return _hooked_iter(super().__iter__())

            def keys(self):
                return _hooked_iter(super().keys())

            def values(self):
                return _hooked_iter(super().values())

            def items(self):
                return _hooked_iter(super().items())

        with patch.object(
            consumer,
            "_reader_storages",
            # pylint: disable-next=protected-access
            HookedDict(consumer._reader_storages),
        ):

            def mutate():
                """Directly mutate _reader_storages after iteration starts"""
                nonlocal failure
                if not iteration_started.wait(timeout):
                    failure = iteration_timeout_error
                # pylint: disable-next=protected-access
                consumer._reader_storages.clear()

            # Verify that test setup works (direct mutation with no synchronization fails)
            with self.assertRaises(RuntimeError) as cm:
                t = Thread(target=mutate)
                t.start()
                try:
                    consumer.consume_measurement(MagicMock())
                finally:
                    t.join()
            self.assertEqual(
                "dictionary changed size during iteration", str(cm.exception)
            )

            def add_and_remove_readers():
                """Modifies _reader_storages after iteration starts"""
                nonlocal failure
                if not iteration_started.wait(timeout):
                    failure = iteration_timeout_error
                reader = MagicMock()
                consumer.add_metric_reader(reader)
                consumer.remove_metric_reader(reader)

            # Verify the API calls do not attempt concurrent modification of reader storages
            t = Thread(target=add_and_remove_readers)
            t.start()
            try:
                consumer.add_metric_reader(MagicMock())
                consumer.consume_measurement(MagicMock())
            finally:
                t.join()
            self.assertEqual(mutation_timeout_error, failure)
