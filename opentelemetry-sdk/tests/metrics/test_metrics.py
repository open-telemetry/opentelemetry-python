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

# pylint: disable=protected-access,no-self-use


from logging import WARNING
from time import sleep
from typing import Iterable, Sequence
from unittest.mock import MagicMock, Mock, patch

from opentelemetry.attributes import BoundedAttributes
from opentelemetry.metrics import NoOpMeter
from opentelemetry.sdk.environment_variables import OTEL_SDK_DISABLED
from opentelemetry.sdk.metrics import (
    Counter,
    Histogram,
    Meter,
    MeterProvider,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
    _Gauge,
)
from opentelemetry.sdk.metrics._internal import SynchronousMeasurementConsumer
from opentelemetry.sdk.metrics.export import (
    Metric,
    MetricExporter,
    MetricExportResult,
    MetricReader,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.metrics.view import SumAggregation, View
from opentelemetry.sdk.resources import Resource
from opentelemetry.test import TestCase
from opentelemetry.test.concurrency_test import ConcurrencyTestBase, MockFunc


class DummyMetricReader(MetricReader):
    def __init__(self):
        super().__init__()

    def _receive_metrics(
        self,
        metrics_data: Iterable[Metric],
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> None:
        pass

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        return True


class TestMeterProvider(ConcurrencyTestBase, TestCase):
    def tearDown(self):

        MeterProvider._all_metric_readers = set()

    @patch.object(Resource, "create")
    def test_init_default(self, resource_patch):
        meter_provider = MeterProvider()
        resource_mock = resource_patch.return_value
        resource_patch.assert_called_once()
        self.assertIsNotNone(meter_provider._sdk_config)
        self.assertEqual(meter_provider._sdk_config.resource, resource_mock)
        self.assertTrue(
            isinstance(
                meter_provider._measurement_consumer,
                SynchronousMeasurementConsumer,
            )
        )
        self.assertIsNotNone(meter_provider._atexit_handler)

    def test_register_metric_readers(self):
        mock_exporter = Mock()
        mock_exporter._preferred_temporality = None
        mock_exporter._preferred_aggregation = None
        metric_reader_0 = PeriodicExportingMetricReader(mock_exporter)
        metric_reader_1 = PeriodicExportingMetricReader(mock_exporter)

        with self.assertNotRaises(Exception):
            MeterProvider(metric_readers=(metric_reader_0,))
            MeterProvider(metric_readers=(metric_reader_1,))

        with self.assertRaises(Exception):
            MeterProvider(metric_readers=(metric_reader_0,))
            MeterProvider(metric_readers=(metric_reader_0,))

    def test_resource(self):
        """
        `MeterProvider` provides a way to allow a `Resource` to be specified.
        """

        meter_provider_0 = MeterProvider()
        meter_provider_1 = MeterProvider()

        self.assertEqual(
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
        `InstrumentationScope` object on the created `Meter`.
        """

        meter = MeterProvider().get_meter(
            "name",
            version="version",
            schema_url="schema_url",
            attributes={"key": "value"},
        )

        self.assertEqual(meter._instrumentation_scope.name, "name")
        self.assertEqual(meter._instrumentation_scope.version, "version")
        self.assertEqual(meter._instrumentation_scope.schema_url, "schema_url")
        self.assertEqual(
            meter._instrumentation_scope.attributes, {"key": "value"}
        )

    def test_get_meter_attributes(self):
        """
        `MeterProvider.get_meter` arguments are used to create an
        `InstrumentationScope` object on the created `Meter`.
        """

        meter = MeterProvider().get_meter(
            "name",
            version="version",
            schema_url="schema_url",
            attributes={"key": "value", "key2": 5, "key3": "value3"},
        )

        self.assertEqual(meter._instrumentation_scope.name, "name")
        self.assertEqual(meter._instrumentation_scope.version, "version")
        self.assertEqual(meter._instrumentation_scope.schema_url, "schema_url")
        self.assertEqual(
            meter._instrumentation_scope.attributes,
            {"key": "value", "key2": 5, "key3": "value3"},
        )

    def test_get_meter_empty(self):
        """
        `MeterProvider.get_meter` called with None or empty string as name
        should return a NoOpMeter.
        """

        with self.assertLogs(level=WARNING):
            meter = MeterProvider().get_meter(
                None,
                version="version",
                schema_url="schema_url",
            )
        self.assertIsInstance(meter, NoOpMeter)
        self.assertEqual(meter._name, None)

        with self.assertLogs(level=WARNING):
            meter = MeterProvider().get_meter(
                "",
                version="version",
                schema_url="schema_url",
            )
        self.assertIsInstance(meter, NoOpMeter)
        self.assertEqual(meter._name, "")

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

    def test_get_meter_comparison_with_attributes(self):
        """
        Subsequent calls to `MeterProvider.get_meter` with the same arguments
        should return the same `Meter` instance.
        """
        mp = MeterProvider()
        meter1 = mp.get_meter(
            "name",
            version="version",
            schema_url="schema_url",
            attributes={"key": "value", "key2": 5, "key3": "value3"},
        )
        meter2 = mp.get_meter(
            "name",
            version="version",
            schema_url="schema_url",
            attributes={"key": "value", "key2": 5, "key3": "value3"},
        )
        meter3 = mp.get_meter(
            "name2",
            version="version",
            schema_url="schema_url",
        )
        meter4 = mp.get_meter(
            "name",
            version="version",
            schema_url="schema_url",
            attributes={"key": "value", "key2": 5, "key3": "value4"},
        )
        self.assertIs(meter1, meter2)
        self.assertIsNot(meter1, meter3)
        self.assertTrue(
            meter3._instrumentation_scope > meter4._instrumentation_scope
        )
        self.assertIsInstance(
            meter4._instrumentation_scope.attributes, BoundedAttributes
        )

    def test_shutdown(self):

        mock_metric_reader_0 = MagicMock(
            **{
                "shutdown.side_effect": ZeroDivisionError(),
            }
        )
        mock_metric_reader_1 = MagicMock(
            **{
                "shutdown.side_effect": AssertionError(),
            }
        )

        meter_provider = MeterProvider(
            metric_readers=[mock_metric_reader_0, mock_metric_reader_1]
        )

        with self.assertRaises(Exception) as error:
            meter_provider.shutdown()

        error = error.exception

        self.assertEqual(
            str(error),
            (
                "MeterProvider.shutdown failed because the following "
                "metric readers failed during shutdown:\n"
                "MagicMock: ZeroDivisionError()\n"
                "MagicMock: AssertionError()"
            ),
        )

        mock_metric_reader_0.shutdown.assert_called_once()
        mock_metric_reader_1.shutdown.assert_called_once()

        mock_metric_reader_0 = Mock()
        mock_metric_reader_1 = Mock()

        meter_provider = MeterProvider(
            metric_readers=[mock_metric_reader_0, mock_metric_reader_1]
        )

        self.assertIsNone(meter_provider.shutdown())
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

    @patch("opentelemetry.sdk.metrics._internal._logger")
    def test_shutdown_race(self, mock_logger):
        mock_logger.warning = MockFunc()
        meter_provider = MeterProvider()
        num_threads = 70
        self.run_with_many_threads(
            meter_provider.shutdown, num_threads=num_threads
        )
        self.assertEqual(mock_logger.warning.call_count, num_threads - 1)

    @patch(
        "opentelemetry.sdk.metrics._internal.SynchronousMeasurementConsumer"
    )
    def test_measurement_collect_callback(
        self, mock_sync_measurement_consumer
    ):
        metric_readers = [
            DummyMetricReader(),
            DummyMetricReader(),
            DummyMetricReader(),
            DummyMetricReader(),
            DummyMetricReader(),
        ]
        sync_consumer_instance = mock_sync_measurement_consumer()
        sync_consumer_instance.collect = MockFunc()
        MeterProvider(metric_readers=metric_readers)

        for reader in metric_readers:
            reader.collect()
        self.assertEqual(
            sync_consumer_instance.collect.call_count, len(metric_readers)
        )

    @patch(
        "opentelemetry.sdk.metrics._internal.SynchronousMeasurementConsumer"
    )
    def test_creates_sync_measurement_consumer(
        self, mock_sync_measurement_consumer
    ):
        MeterProvider()
        mock_sync_measurement_consumer.assert_called()

    @patch(
        "opentelemetry.sdk.metrics._internal.SynchronousMeasurementConsumer"
    )
    def test_register_asynchronous_instrument(
        self, mock_sync_measurement_consumer
    ):

        meter_provider = MeterProvider()

        # pylint: disable=no-member
        meter_provider._measurement_consumer.register_asynchronous_instrument.assert_called_with(
            meter_provider.get_meter("name").create_observable_counter(
                "name0", callbacks=[Mock()]
            )
        )
        meter_provider._measurement_consumer.register_asynchronous_instrument.assert_called_with(
            meter_provider.get_meter("name").create_observable_up_down_counter(
                "name1", callbacks=[Mock()]
            )
        )
        meter_provider._measurement_consumer.register_asynchronous_instrument.assert_called_with(
            meter_provider.get_meter("name").create_observable_gauge(
                "name2", callbacks=[Mock()]
            )
        )

    @patch(
        "opentelemetry.sdk.metrics._internal.SynchronousMeasurementConsumer"
    )
    def test_consume_measurement_counter(self, mock_sync_measurement_consumer):
        sync_consumer_instance = mock_sync_measurement_consumer()
        meter_provider = MeterProvider()
        counter = meter_provider.get_meter("name").create_counter("name")

        counter.add(1)

        sync_consumer_instance.consume_measurement.assert_called()

    @patch(
        "opentelemetry.sdk.metrics._internal.SynchronousMeasurementConsumer"
    )
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

    @patch(
        "opentelemetry.sdk.metrics._internal.SynchronousMeasurementConsumer"
    )
    def test_consume_measurement_histogram(
        self, mock_sync_measurement_consumer
    ):
        sync_consumer_instance = mock_sync_measurement_consumer()
        meter_provider = MeterProvider()
        counter = meter_provider.get_meter("name").create_histogram("name")

        counter.record(1)

        sync_consumer_instance.consume_measurement.assert_called()

    @patch(
        "opentelemetry.sdk.metrics._internal.SynchronousMeasurementConsumer"
    )
    def test_consume_measurement_gauge(self, mock_sync_measurement_consumer):
        sync_consumer_instance = mock_sync_measurement_consumer()
        meter_provider = MeterProvider()
        gauge = meter_provider.get_meter("name").create_gauge("name")

        gauge.set(1)

        sync_consumer_instance.consume_measurement.assert_called()


class TestMeter(TestCase):
    def setUp(self):
        self.meter = Meter(Mock(), Mock())

    def test_repeated_instrument_names(self):
        with self.assertNotRaises(Exception):
            self.meter.create_counter("counter")
            self.meter.create_up_down_counter("up_down_counter")
            self.meter.create_observable_counter(
                "observable_counter", callbacks=[Mock()]
            )
            self.meter.create_histogram("histogram")
            self.meter.create_gauge("gauge")
            self.meter.create_observable_gauge(
                "observable_gauge", callbacks=[Mock()]
            )
            self.meter.create_observable_up_down_counter(
                "observable_up_down_counter", callbacks=[Mock()]
            )

        for instrument_name in [
            "counter",
            "up_down_counter",
            "histogram",
            "gauge",
        ]:
            with self.assertLogs(level=WARNING):
                getattr(self.meter, f"create_{instrument_name}")(
                    instrument_name
                )

        for instrument_name in [
            "observable_counter",
            "observable_gauge",
            "observable_up_down_counter",
        ]:
            with self.assertLogs(level=WARNING):
                getattr(self.meter, f"create_{instrument_name}")(
                    instrument_name, callbacks=[Mock()]
                )

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
            "name", callbacks=[Mock()], unit="unit", description="description"
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
            "name", callbacks=[Mock()], unit="unit", description="description"
        )

        self.assertIsInstance(observable_gauge, ObservableGauge)
        self.assertEqual(observable_gauge.name, "name")

    def test_create_gauge(self):
        gauge = self.meter.create_gauge(
            "name", unit="unit", description="description"
        )

        self.assertIsInstance(gauge, _Gauge)
        self.assertEqual(gauge.name, "name")

    def test_create_observable_up_down_counter(self):
        observable_up_down_counter = (
            self.meter.create_observable_up_down_counter(
                "name",
                callbacks=[Mock()],
                unit="unit",
                description="description",
            )
        )
        self.assertIsInstance(
            observable_up_down_counter, ObservableUpDownCounter
        )
        self.assertEqual(observable_up_down_counter.name, "name")

    @patch.dict("os.environ", {OTEL_SDK_DISABLED: "true"})
    def test_get_meter_with_sdk_disabled(self):
        meter_provider = MeterProvider()
        self.assertIsInstance(meter_provider.get_meter(Mock()), NoOpMeter)


class InMemoryMetricExporter(MetricExporter):
    def __init__(self):
        super().__init__()
        self.metrics = {}
        self._counter = 0

    def export(
        self,
        metrics_data: Sequence[Metric],
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> MetricExportResult:
        self.metrics[self._counter] = metrics_data
        self._counter += 1
        return MetricExportResult.SUCCESS

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        pass

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        return True


class TestDuplicateInstrumentAggregateData(TestCase):
    def test_duplicate_instrument_aggregate_data(self):

        exporter = InMemoryMetricExporter()
        reader = PeriodicExportingMetricReader(
            exporter, export_interval_millis=500
        )
        view = View(
            instrument_type=Counter,
            attribute_keys=[],
            aggregation=SumAggregation(),
        )
        provider = MeterProvider(
            metric_readers=[reader],
            resource=Resource.create(),
            views=[view],
        )

        meter_0 = provider.get_meter(
            name="meter_0",
            version="version",
            schema_url="schema_url",
        )
        meter_1 = provider.get_meter(
            name="meter_1",
            version="version",
            schema_url="schema_url",
        )
        counter_0_0 = meter_0.create_counter(
            "counter", unit="unit", description="description"
        )
        with self.assertLogs(level=WARNING):
            counter_0_1 = meter_0.create_counter(
                "counter", unit="unit", description="description"
            )
        counter_1_0 = meter_1.create_counter(
            "counter", unit="unit", description="description"
        )

        self.assertIs(counter_0_0, counter_0_1)
        self.assertIsNot(counter_0_0, counter_1_0)

        counter_0_0.add(1, {})
        counter_0_1.add(2, {})

        with self.assertLogs(level=WARNING):
            counter_1_0.add(7, {})

        sleep(1)

        reader.shutdown()

        sleep(1)

        metrics = exporter.metrics[0]

        scope_metrics = metrics.resource_metrics[0].scope_metrics
        self.assertEqual(len(scope_metrics), 2)

        metric_0 = scope_metrics[0].metrics[0]

        self.assertEqual(metric_0.name, "counter")
        self.assertEqual(metric_0.unit, "unit")
        self.assertEqual(metric_0.description, "description")
        self.assertEqual(next(iter(metric_0.data.data_points)).value, 3)

        metric_1 = scope_metrics[1].metrics[0]

        self.assertEqual(metric_1.name, "counter")
        self.assertEqual(metric_1.unit, "unit")
        self.assertEqual(metric_1.description, "description")
        self.assertEqual(next(iter(metric_1.data.data_points)).value, 7)
