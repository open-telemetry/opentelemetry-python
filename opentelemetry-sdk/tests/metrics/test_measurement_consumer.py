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


def _sdk_config(
    exemplar_filter=None, resource=None, metric_readers=None, views=None
):
    """Create SdkConfiguration for tests."""
    config = SdkConfiguration(
        resource=resource or Mock(),
        metric_readers=metric_readers or [Mock()],
        views=views or Mock(),
        exemplar_filter=exemplar_filter
        or Mock(should_sample=Mock(return_value=False)),
    )
    return config


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
                exemplar_filter=Mock(),
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
                exemplar_filter=Mock(should_sample=Mock(return_value=False)),
                resource=Mock(),
                metric_readers=reader_mocks,
                views=Mock(),
            )
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
                exemplar_filter=Mock(should_sample=Mock(return_value=False)),
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
                exemplar_filter=Mock(),
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


@patch(
    "opentelemetry.sdk.metrics._internal."
    "measurement_consumer.MetricReaderStorage"
)
class TestSynchronousMeasurementConsumerForkHandler(TestCase):  # pylint: disable=protected-access
    """Exhaustive tests for fork handler, needs_storage_reinit, and lazy _reinit_storages."""

    def test_register_at_fork_called_when_available(
        self, MockMetricReaderStorage
    ):
        """Consumer should register fork handler when os.register_at_fork exists."""
        register_mock = Mock()
        with patch(
            "opentelemetry.sdk.metrics._internal.measurement_consumer.os"
        ) as mock_os:
            mock_os.register_at_fork = register_mock

            SynchronousMeasurementConsumer(_sdk_config())
            register_mock.assert_called_once()
            call_kwargs = register_mock.call_args[1]
            self.assertIn("after_in_child", call_kwargs)
            self.assertTrue(callable(call_kwargs["after_in_child"]))

    def test_at_fork_reinit_sets_needs_storage_reinit_and_clears_async_instruments(
        self, MockMetricReaderStorage
    ):
        """_at_fork_reinit should set _needs_storage_reinit=True and clear _async_instruments."""
        reader_mock = Mock()
        storage_mock = Mock()
        storage_mock._lock = Mock()
        storage_mock._instrument_view_instrument_matches = {}
        MockMetricReaderStorage.return_value = storage_mock

        register_mock = Mock()
        with patch(
            "opentelemetry.sdk.metrics._internal.measurement_consumer.os"
        ) as mock_os:
            mock_os.register_at_fork = register_mock

            consumer = SynchronousMeasurementConsumer(
                _sdk_config(metric_readers=[reader_mock])
            )
            async_instrument = MagicMock()
            consumer.register_asynchronous_instrument(async_instrument)
            self.assertEqual(len(consumer._async_instruments), 1)

            # Simulate fork: call the after_in_child callback
            after_in_child = register_mock.call_args[1]["after_in_child"]
            after_in_child()

            self.assertTrue(consumer._needs_storage_reinit)
            self.assertEqual(len(consumer._async_instruments), 0)

    def test_consume_measurement_triggers_lazy_reinit_on_first_use_after_fork(
        self, MockMetricReaderStorage
    ):
        """First consume_measurement after fork should call _reinit_storages."""
        reader_mocks = [Mock()]
        storage_mocks = [Mock()]
        storage_mocks[0]._lock = Mock()
        storage_mocks[0]._instrument_view_instrument_matches = {}
        storage_mocks[0].consume_measurement = Mock()
        MockMetricReaderStorage.side_effect = storage_mocks

        register_mock = Mock()
        with patch(
            "opentelemetry.sdk.metrics._internal.measurement_consumer.os"
        ) as mock_os:
            mock_os.register_at_fork = register_mock

            consumer = SynchronousMeasurementConsumer(
                _sdk_config(metric_readers=reader_mocks)
            )
            after_in_child = register_mock.call_args[1]["after_in_child"]
            after_in_child()

            with patch.object(
                consumer, "_reinit_storages", wraps=consumer._reinit_storages
            ) as reinit_spy:
                consumer.consume_measurement(Mock())
                reinit_spy.assert_called_once()

    def test_consume_measurement_does_not_reinit_on_second_call(
        self, MockMetricReaderStorage
    ):
        """Second consume_measurement after fork should NOT call _reinit_storages again."""
        reader_mocks = [Mock()]
        storage_mock = Mock()
        storage_mock._lock = Mock()
        storage_mock._instrument_view_instrument_matches = {}
        storage_mock.consume_measurement = Mock()
        MockMetricReaderStorage.return_value = storage_mock

        register_mock = Mock()
        with patch(
            "opentelemetry.sdk.metrics._internal.measurement_consumer.os"
        ) as mock_os:
            mock_os.register_at_fork = register_mock

            consumer = SynchronousMeasurementConsumer(
                _sdk_config(metric_readers=reader_mocks)
            )
            after_in_child = register_mock.call_args[1]["after_in_child"]
            after_in_child()

            with patch.object(
                consumer, "_reinit_storages", wraps=consumer._reinit_storages
            ) as reinit_spy:
                consumer.consume_measurement(Mock())
                consumer.consume_measurement(Mock())
                reinit_spy.assert_called_once()

    def test_collect_triggers_lazy_reinit_on_first_use_after_fork(
        self, MockMetricReaderStorage
    ):
        """First collect after fork should call _reinit_storages."""
        reader_mock = Mock()
        storage_mock = Mock()
        storage_mock._lock = Mock()
        storage_mock._instrument_view_instrument_matches = {}
        storage_mock.collect.return_value = []
        MockMetricReaderStorage.return_value = storage_mock

        register_mock = Mock()
        with patch(
            "opentelemetry.sdk.metrics._internal.measurement_consumer.os"
        ) as mock_os:
            mock_os.register_at_fork = register_mock

            consumer = SynchronousMeasurementConsumer(
                _sdk_config(metric_readers=[reader_mock])
            )
            after_in_child = register_mock.call_args[1]["after_in_child"]
            after_in_child()

            with patch.object(
                consumer, "_reinit_storages", wraps=consumer._reinit_storages
            ) as reinit_spy:
                consumer.collect(reader_mock)
                reinit_spy.assert_called_once()

    def test_collect_does_not_reinit_on_second_call(
        self, MockMetricReaderStorage
    ):
        """Second collect after fork should NOT call _reinit_storages again."""
        reader_mock = Mock()
        storage_mock = Mock()
        storage_mock._lock = Mock()
        storage_mock._instrument_view_instrument_matches = {}
        storage_mock.collect.return_value = []
        MockMetricReaderStorage.return_value = storage_mock

        register_mock = Mock()
        with patch(
            "opentelemetry.sdk.metrics._internal.measurement_consumer.os"
        ) as mock_os:
            mock_os.register_at_fork = register_mock

            consumer = SynchronousMeasurementConsumer(
                _sdk_config(metric_readers=[reader_mock])
            )
            after_in_child = register_mock.call_args[1]["after_in_child"]
            after_in_child()

            with patch.object(
                consumer, "_reinit_storages", wraps=consumer._reinit_storages
            ) as reinit_spy:
                consumer.collect(reader_mock)
                consumer.collect(reader_mock)
                reinit_spy.assert_called_once()

    def test_consume_then_collect_after_fork_reinits_once(
        self, MockMetricReaderStorage
    ):
        """After fork, consume_measurement triggers reinit; collect uses same reinit (no second call)."""
        reader_mock = Mock()
        storage_mock = Mock()
        storage_mock._lock = Mock()
        storage_mock._instrument_view_instrument_matches = {}
        storage_mock.consume_measurement = Mock()
        storage_mock.collect.return_value = []
        MockMetricReaderStorage.return_value = storage_mock

        register_mock = Mock()
        with patch(
            "opentelemetry.sdk.metrics._internal.measurement_consumer.os"
        ) as mock_os:
            mock_os.register_at_fork = register_mock

            consumer = SynchronousMeasurementConsumer(
                _sdk_config(metric_readers=[reader_mock])
            )
            after_in_child = register_mock.call_args[1]["after_in_child"]
            after_in_child()

            with patch.object(
                consumer, "_reinit_storages", wraps=consumer._reinit_storages
            ) as reinit_spy:
                consumer.consume_measurement(Mock())
                consumer.collect(reader_mock)
                reinit_spy.assert_called_once()

    def test_collect_then_consume_after_fork_reinits_once(
        self, MockMetricReaderStorage
    ):
        """After fork, collect triggers reinit; consume_measurement uses same reinit (no second call)."""
        reader_mock = Mock()
        storage_mock = Mock()
        storage_mock._lock = Mock()
        storage_mock._instrument_view_instrument_matches = {}
        storage_mock.consume_measurement = Mock()
        storage_mock.collect.return_value = []
        MockMetricReaderStorage.return_value = storage_mock

        register_mock = Mock()
        with patch(
            "opentelemetry.sdk.metrics._internal.measurement_consumer.os"
        ) as mock_os:
            mock_os.register_at_fork = register_mock

            consumer = SynchronousMeasurementConsumer(
                _sdk_config(metric_readers=[reader_mock])
            )
            after_in_child = register_mock.call_args[1]["after_in_child"]
            after_in_child()

            with patch.object(
                consumer, "_reinit_storages", wraps=consumer._reinit_storages
            ) as reinit_spy:
                consumer.collect(reader_mock)
                consumer.consume_measurement(Mock())
                reinit_spy.assert_called_once()

    def test_no_reinit_on_consume_measurement_without_fork(
        self, MockMetricReaderStorage
    ):
        """consume_measurement without prior fork should NOT call _reinit_storages."""
        reader_mocks = [Mock()]
        storage_mock = Mock()
        storage_mock._lock = Mock()
        storage_mock._instrument_view_instrument_matches = {}
        storage_mock.consume_measurement = Mock()
        MockMetricReaderStorage.return_value = storage_mock

        with patch(
            "opentelemetry.sdk.metrics._internal.measurement_consumer.os"
        ) as mock_os:
            mock_os.register_at_fork = Mock()

            consumer = SynchronousMeasurementConsumer(
                _sdk_config(metric_readers=reader_mocks)
            )
            # Do NOT simulate fork
            with patch.object(
                consumer, "_reinit_storages", wraps=consumer._reinit_storages
            ) as reinit_spy:
                consumer.consume_measurement(Mock())
                reinit_spy.assert_not_called()

    def test_no_reinit_on_collect_without_fork(self, MockMetricReaderStorage):
        """collect without prior fork should NOT call _reinit_storages."""
        reader_mock = Mock()
        storage_mock = Mock()
        storage_mock._lock = Mock()
        storage_mock._instrument_view_instrument_matches = {}
        storage_mock.collect.return_value = []
        MockMetricReaderStorage.return_value = storage_mock

        with patch(
            "opentelemetry.sdk.metrics._internal.measurement_consumer.os"
        ) as mock_os:
            mock_os.register_at_fork = Mock()

            consumer = SynchronousMeasurementConsumer(
                _sdk_config(metric_readers=[reader_mock])
            )
            with patch.object(
                consumer, "_reinit_storages", wraps=consumer._reinit_storages
            ) as reinit_spy:
                consumer.collect(reader_mock)
                reinit_spy.assert_not_called()

    def test_collect_after_fork_does_not_invoke_cleared_async_instruments(
        self, MockMetricReaderStorage
    ):
        """After fork, collect should not invoke async instruments (they were cleared)."""
        reader_mock = Mock()
        storage_mock = Mock()
        storage_mock._lock = Mock()
        storage_mock._instrument_view_instrument_matches = {}
        storage_mock.collect.return_value = []
        MockMetricReaderStorage.return_value = storage_mock

        register_mock = Mock()
        with patch(
            "opentelemetry.sdk.metrics._internal.measurement_consumer.os"
        ) as mock_os:
            mock_os.register_at_fork = register_mock

            consumer = SynchronousMeasurementConsumer(
                _sdk_config(metric_readers=[reader_mock])
            )
            async_instrument = MagicMock()
            async_instrument.callback.return_value = []
            consumer.register_asynchronous_instrument(async_instrument)

            after_in_child = register_mock.call_args[1]["after_in_child"]
            after_in_child()

            consumer.collect(reader_mock)

            async_instrument.callback.assert_not_called()
