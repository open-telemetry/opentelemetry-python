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

# pylint: disable=protected-access,invalid-name,no-self-use

import gc
import weakref
from logging import WARNING
from time import sleep, time_ns
from typing import Sequence
from unittest.mock import patch

from opentelemetry.sdk.metrics import Counter
from opentelemetry.sdk.metrics._internal import _Counter
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    Gauge,
    Metric,
    MetricExporter,
    MetricExportResult,
    NumberDataPoint,
    Sum,
    SynchronousExportingMetricReader,
)
from opentelemetry.sdk.metrics.view import (
    DefaultAggregation,
    LastValueAggregation,
)
from opentelemetry.test.concurrency_test import ConcurrencyTestBase


class FakeMetricsExporter(MetricExporter):
    def __init__(
        self, wait=0, preferred_temporality=None, preferred_aggregation=None
    ):
        self.wait = float(
            wait
        )  # Convert to float to handle both int and float inputs
        self.metrics = []
        self._shutdown = False
        super().__init__(
            preferred_temporality=preferred_temporality,
            preferred_aggregation=preferred_aggregation,
        )

    def export(
        self,
        metrics_data: Sequence[Metric],
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> MetricExportResult:
        sleep(self.wait)
        self.metrics.append(metrics_data)
        return MetricExportResult.SUCCESS

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        self._shutdown = True

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        return True


# Create sample metrics for testing
metrics_list = [
    Metric(
        name="sum_name",
        description="",
        unit="",
        data=Sum(
            data_points=[
                NumberDataPoint(
                    attributes={},
                    start_time_unix_nano=time_ns(),
                    time_unix_nano=time_ns(),
                    value=2,
                )
            ],
            aggregation_temporality=1,
            is_monotonic=True,
        ),
    ),
    Metric(
        name="gauge_name",
        description="",
        unit="",
        data=Gauge(
            data_points=[
                NumberDataPoint(
                    attributes={},
                    start_time_unix_nano=time_ns(),
                    time_unix_nano=time_ns(),
                    value=2,
                )
            ]
        ),
    ),
]


class TestBatchExportingMetricReader(ConcurrencyTestBase):
    def test_defaults(self):
        """Test default configuration values"""
        reader = SynchronousExportingMetricReader(FakeMetricsExporter())
        self.assertEqual(reader._max_export_batch_size, 512)
        self.assertEqual(reader._export_timeout_millis, 30000)
        self.assertEqual(reader._max_queue_size, 2048)
        reader.shutdown()

    def test_custom_configuration(self):
        """Test custom configuration values"""
        reader = SynchronousExportingMetricReader(
            FakeMetricsExporter(),
            max_export_batch_size=100,
            export_timeout_millis=5000,
            max_queue_size=1000,
        )
        self.assertEqual(reader._max_export_batch_size, 100)
        self.assertEqual(reader._export_timeout_millis, 5000)
        self.assertEqual(reader._max_queue_size, 1000)
        reader.shutdown()

    def test_invalid_configuration(self):
        """Test error handling for invalid configuration"""
        exporter = FakeMetricsExporter()

        # Test zero batch size
        with self.assertRaises(ValueError):
            SynchronousExportingMetricReader(exporter, max_export_batch_size=0)

        # Test batch size > queue size
        with self.assertRaises(ValueError):
            SynchronousExportingMetricReader(
                exporter, max_export_batch_size=1000, max_queue_size=500
            )

    def _create_batch_reader_with_metrics(self, exporter, metrics_data):
        """Helper to create a reader with metrics and stub the collect callback"""
        reader = SynchronousExportingMetricReader(
            exporter,
            # Use small values for testing
            max_export_batch_size=5,
            max_queue_size=10,
        )

        # Set up the collect callback to return our metrics
        def _collect(reader, timeout_millis=10_000):
            reader._receive_metrics(metrics_data, timeout_millis)
            return metrics_data

        reader._set_collect_callback(_collect)

        return reader

    def test_queue_and_batch_export(self):
        """Test that metrics are queued and exported in batches"""
        exporter = FakeMetricsExporter()
        reader = self._create_batch_reader_with_metrics(exporter, metrics_list)

        # Trigger collection which will add metrics to the queue
        reader.collect()

        # Verify metrics were queued
        self.assertEqual(len(reader._queue), 1)

        # Force flush to export
        reader.force_flush()

        # Verify metrics were exported
        self.assertEqual(len(exporter.metrics), 1)
        self.assertEqual(exporter.metrics[0], metrics_list)

        reader.shutdown()

    def test_shutdown(self):
        """Test proper cleanup during shutdown"""
        exporter = FakeMetricsExporter()
        reader = self._create_batch_reader_with_metrics(exporter, metrics_list)

        # Trigger collection
        reader.collect()

        # Shutdown reader
        reader.shutdown()

        # Verify exporter was also shut down
        self.assertTrue(exporter._shutdown)

        # Verify metrics were exported before shutdown
        self.assertEqual(len(exporter.metrics), 1)

    def test_force_flush(self):
        """Test that force_flush exports all queued metrics"""
        exporter = FakeMetricsExporter()
        reader = self._create_batch_reader_with_metrics(exporter, metrics_list)

        # Trigger collection
        reader.collect()

        # Force flush
        success = reader.force_flush()

        # Verify success and metrics exported
        self.assertTrue(success)
        self.assertEqual(len(exporter.metrics), 1)

        reader.shutdown()

    def test_force_flush_timeout(self):
        """Test timeout handling during force_flush"""
        # Create exporter with delay longer than timeout
        exporter = FakeMetricsExporter(wait=0.2)
        reader = self._create_batch_reader_with_metrics(exporter, metrics_list)

        # Add metrics to queue
        reader.collect()

        # Simulate force_flush exception with logging
        with patch.object(reader._exporter, "force_flush", return_value=False):
            with self.assertLogs(level=WARNING):
                success = reader.force_flush(timeout_millis=10)

            # Should return False due to exporter force_flush failure
            self.assertFalse(success)

        reader.shutdown()

    def test_receive_metrics(self):
        """Test that metrics are properly queued when received"""
        exporter = FakeMetricsExporter()
        reader = SynchronousExportingMetricReader(
            exporter,
            max_export_batch_size=5,
        )

        # Mock the collect callback
        def _collect(reader, timeout_millis=10_000):
            pass

        reader._set_collect_callback(_collect)

        # Directly call receive_metrics
        reader._receive_metrics(metrics_list)

        # Verify metrics were queued
        self.assertEqual(len(reader._queue), 1)

        reader.shutdown()

    def test_batch_triggered_by_size(self):
        """Test that export is triggered when batch size is reached"""
        exporter = FakeMetricsExporter()
        reader = SynchronousExportingMetricReader(
            exporter,
            max_export_batch_size=2,
        )

        # Mock the collect callback
        def _collect(reader, timeout_millis=10_000):
            pass

        reader._set_collect_callback(_collect)

        # Add first batch of metrics
        reader._receive_metrics(metrics_list)

        # Should not have exported yet
        self.assertEqual(exporter.metrics, [])

        # Add more metrics to reach batch size
        reader._receive_metrics(metrics_list)

        # Should have exported now due to batch size trigger
        self.assertEqual(len(exporter.metrics), 1)

        reader.shutdown()

    def test_exporter_temporality_preference(self):
        """Test that temporality preferences are passed from exporter"""
        exporter = FakeMetricsExporter(
            preferred_temporality={
                Counter: AggregationTemporality.DELTA,
            },
        )
        reader = SynchronousExportingMetricReader(exporter)

        for key, value in reader._instrument_class_temporality.items():
            if key is not _Counter:
                self.assertEqual(value, AggregationTemporality.CUMULATIVE)
            else:
                self.assertEqual(value, AggregationTemporality.DELTA)

        reader.shutdown()

    def test_exporter_aggregation_preference(self):
        """Test that aggregation preferences are passed from exporter"""
        exporter = FakeMetricsExporter(
            preferred_aggregation={
                Counter: LastValueAggregation(),
            },
        )
        reader = SynchronousExportingMetricReader(exporter)

        for key, value in reader._instrument_class_aggregation.items():
            if key is not _Counter:
                self.assertTrue(isinstance(value, DefaultAggregation))
            else:
                self.assertTrue(isinstance(value, LastValueAggregation))

        reader.shutdown()

    def test_concurrent_operations(self):
        """Test thread safety with concurrent operations"""
        exporter = FakeMetricsExporter()
        reader = SynchronousExportingMetricReader(exporter)
        # Run multiple force_flush operations concurrently
        self.run_with_many_threads(reader.force_flush)
        reader.shutdown()

    def test_queue_overflow(self):
        """Test behavior when queue reaches maximum capacity"""
        exporter = FakeMetricsExporter(wait=0.1)  # Slow exporter
        reader = SynchronousExportingMetricReader(
            exporter,
            max_queue_size=3,
        )

        # Fill queue to capacity
        for _ in range(5):  # More than queue size
            reader._receive_metrics(metrics_list)

        # Queue should be at max capacity (3)
        self.assertEqual(len(reader._queue), 3)

        # Force flush to clear queue
        reader.force_flush()
        reader.shutdown()

    def test_at_fork_reinit(self):
        """Test reinit after fork behavior"""
        exporter = FakeMetricsExporter()
        reader = SynchronousExportingMetricReader(exporter)
        original_pid = reader._pid
        # Mock os.getpid() to simulate a fork
        with patch("os.getpid", return_value=original_pid + 1):
            # Simulate receiving metrics after fork
            reader._receive_metrics(metrics_list)
            # Should have called _at_fork_reinit
            self.assertEqual(reader._pid, original_pid + 1)
        reader.shutdown()

    def test_multiple_shutdown(self):
        """Test that calling shutdown multiple times logs a warning"""
        reader = SynchronousExportingMetricReader(FakeMetricsExporter())
        # First shutdown should work fine
        reader.shutdown()
        # Second shutdown should log a warning
        with self.assertLogs(level=WARNING) as logs:
            reader.shutdown()
        self.assertTrue(
            any("Can't shutdown multiple times" in log for log in logs.output)
        )

    def test_drain_queue_on_shutdown(self):
        """Test that queue is drained on shutdown"""
        exporter = FakeMetricsExporter()
        reader = SynchronousExportingMetricReader(exporter)
        # Add metrics to queue
        reader._receive_metrics(metrics_list)
        reader._receive_metrics(metrics_list)
        # Shutdown should drain queue
        reader.shutdown()
        # Verify metrics were exported
        self.assertEqual(len(exporter.metrics), 2)

    def test_garbage_collection(self):
        """Test that reader can be garbage collected properly"""
        exporter = FakeMetricsExporter()
        reader = SynchronousExportingMetricReader(exporter)
        weak_ref = weakref.ref(reader)
        reader.shutdown()
        del reader
        gc.collect()
        # Reader should be garbage collected
        self.assertIsNone(
            weak_ref(),
            "The SynchronousExportingMetricReader object wasn't properly garbage collected",
        )
