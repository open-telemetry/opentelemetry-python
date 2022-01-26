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


from logging import WARNING
from unittest import TestCase
from unittest.mock import MagicMock, Mock, patch

from opentelemetry.sdk._metrics import Meter, MeterProvider
from opentelemetry.sdk._metrics.instrument import (
    Counter,
    Histogram,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.sdk._metrics.metric_reader import MetricReader
from opentelemetry.sdk._metrics.point import AggregationTemporality
from opentelemetry.sdk.resources import Resource
from opentelemetry.test.concurrency_test import ConcurrencyTestBase, MockFunc


class DummyMetricReader(MetricReader):
    def __init__(self):
        super().__init__(AggregationTemporality.CUMULATIVE)

    def _receive_metrics(self, metrics):
        pass

    def shutdown(self):
        return True


class TestMeterProvider(ConcurrencyTestBase):
    def test_resource(self):
        """
        `MeterProvider` provides a way to allow a `Resource` to be specified.
        """

        meter_provider_0 = MeterProvider()
        meter_provider_1 = MeterProvider()

        self.assertIs(
            meter_provider_0._sdk_config.resource,
            meter_provider_1._sdk_config.resource,
        )
        self.assertIsInstance(meter_provider_0._sdk_config.resource, Resource)
        self.assertIsInstance(meter_provider_1._sdk_config.resource, Resource)

        resource = Resource({"key": "value"})
        self.assertIs(
            MeterProvider(resource=resource)._sdk_config.resource, resource
        )

    def test_get_meter(self):
        """
        `MeterProvider.get_meter` arguments are used to create an
        `InstrumentationInfo` object on the created `Meter`.
        """

        meter = MeterProvider().get_meter(
            "name",
            version="version",
            schema_url="schema_url",
        )

        self.assertEqual(meter._instrumentation_info.name, "name")
        self.assertEqual(meter._instrumentation_info.version, "version")
        self.assertEqual(meter._instrumentation_info.schema_url, "schema_url")

    def test_get_meter_duplicate(self):
        """
        Subsequent calls to `MeterProvider.get_meter` with the same arguments
        should return the same `Meter` instance.
        """
        mp = MeterProvider()
        meter1 = mp.get_meter(
            "name",
            version="version",
            schema_url="schema_url",
        )
        meter2 = mp.get_meter(
            "name",
            version="version",
            schema_url="schema_url",
        )
        meter3 = mp.get_meter(
            "name2",
            version="version",
            schema_url="schema_url",
        )
        self.assertIs(meter1, meter2)
        self.assertIsNot(meter1, meter3)

    def test_shutdown(self):

        mock_metric_reader_0 = MagicMock(
            **{
                "shutdown.return_value": False,
                "__str__.return_value": "mock_metric_reader_0",
            }
        )
        mock_metric_reader_1 = Mock(**{"shutdown.return_value": True})

        meter_provider = MeterProvider(
            metric_readers=[mock_metric_reader_0, mock_metric_reader_1]
        )

        with self.assertLogs(level=WARNING) as log:
            self.assertFalse(meter_provider.shutdown())
            self.assertEqual(
                log.records[0].getMessage(),
                "MetricReader mock_metric_reader_0 failed to shutdown",
            )
        mock_metric_reader_0.shutdown.assert_called_once()
        mock_metric_reader_1.shutdown.assert_called_once()

        mock_metric_reader_0 = Mock(**{"shutdown.return_value": True})
        mock_metric_reader_1 = Mock(**{"shutdown.return_value": True})

        meter_provider = MeterProvider(
            metric_readers=[mock_metric_reader_0, mock_metric_reader_1]
        )

        self.assertTrue(meter_provider.shutdown())
        mock_metric_reader_0.shutdown.assert_called_once()
        mock_metric_reader_1.shutdown.assert_called_once()

    def test_shutdown_subsequent_calls(self):
        """
        No subsequent attempts to get a `Meter` are allowed after calling
        `MeterProvider.shutdown`
        """

        meter_provider = MeterProvider()

        with self.assertRaises(AssertionError):
            with self.assertLogs(level=WARNING):
                meter_provider.shutdown()

        with self.assertLogs(level=WARNING):
            meter_provider.shutdown()

    @patch("opentelemetry.sdk._metrics._logger")
    def test_shutdown_race(self, mock_logger):
        mock_logger.warning = MockFunc()
        meter_provider = MeterProvider()
        num_threads = 70
        self.run_with_many_threads(
            meter_provider.shutdown, num_threads=num_threads
        )
        self.assertEqual(mock_logger.warning.call_count, num_threads - 1)

    @patch("opentelemetry.sdk._metrics.SynchronousMeasurementConsumer")
    def test_measurement_collect_callback(
        self, mock_sync_measurement_consumer
    ):
        metric_readers = [DummyMetricReader()] * 5
        sync_consumer_instance = mock_sync_measurement_consumer()
        sync_consumer_instance.collect = MockFunc()
        MeterProvider(metric_readers=metric_readers)

        for reader in metric_readers:
            reader.collect()
        self.assertEqual(
            sync_consumer_instance.collect.call_count, len(metric_readers)
        )

    @patch("opentelemetry.sdk._metrics.SynchronousMeasurementConsumer")
    def test_creates_sync_measurement_consumer(
        self, mock_sync_measurement_consumer
    ):
        MeterProvider()
        mock_sync_measurement_consumer.assert_called()

    @patch("opentelemetry.sdk._metrics.SynchronousMeasurementConsumer")
    def test_register_asynchronous_instrument(
        self, mock_sync_measurement_consumer
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
    def test_consume_measurement_counter(self, mock_sync_measurement_consumer):
        sync_consumer_instance = mock_sync_measurement_consumer()
        meter_provider = MeterProvider()
        counter = meter_provider.get_meter("name").create_counter("name")

        counter.add(1)

        sync_consumer_instance.consume_measurement.assert_called()

    @patch("opentelemetry.sdk._metrics.SynchronousMeasurementConsumer")
    def test_consume_measurement_up_down_counter(
        self, mock_sync_measurement_consumer
    ):
        sync_consumer_instance = mock_sync_measurement_consumer()
        meter_provider = MeterProvider()
        counter = meter_provider.get_meter("name").create_up_down_counter(
            "name"
        )

        counter.add(1)

        sync_consumer_instance.consume_measurement.assert_called()

    @patch("opentelemetry.sdk._metrics.SynchronousMeasurementConsumer")
    def test_consume_measurement_histogram(
        self, mock_sync_measurement_consumer
    ):
        sync_consumer_instance = mock_sync_measurement_consumer()
        meter_provider = MeterProvider()
        counter = meter_provider.get_meter("name").create_histogram("name")

        counter.record(1)

        sync_consumer_instance.consume_measurement.assert_called()


class TestMeter(TestCase):
    def setUp(self):
        self.meter = Meter(Mock(), Mock())

    def test_create_counter(self):
        counter = self.meter.create_counter(
            "name", unit="unit", description="description"
        )

        self.assertIsInstance(counter, Counter)
        self.assertEqual(counter.name, "name")

    def test_create_up_down_counter(self):
        up_down_counter = self.meter.create_up_down_counter(
            "name", unit="unit", description="description"
        )

        self.assertIsInstance(up_down_counter, UpDownCounter)
        self.assertEqual(up_down_counter.name, "name")

    def test_create_observable_counter(self):
        observable_counter = self.meter.create_observable_counter(
            "name", Mock(), unit="unit", description="description"
        )

        self.assertIsInstance(observable_counter, ObservableCounter)
        self.assertEqual(observable_counter.name, "name")

    def test_create_histogram(self):
        histogram = self.meter.create_histogram(
            "name", unit="unit", description="description"
        )

        self.assertIsInstance(histogram, Histogram)
        self.assertEqual(histogram.name, "name")

    def test_create_observable_gauge(self):
        observable_gauge = self.meter.create_observable_gauge(
            "name", Mock(), unit="unit", description="description"
        )

        self.assertIsInstance(observable_gauge, ObservableGauge)
        self.assertEqual(observable_gauge.name, "name")

    def test_create_observable_up_down_counter(self):
        observable_up_down_counter = (
            self.meter.create_observable_up_down_counter(
                "name", Mock(), unit="unit", description="description"
            )
        )
        self.assertIsInstance(
            observable_up_down_counter, ObservableUpDownCounter
        )
        self.assertEqual(observable_up_down_counter.name, "name")
