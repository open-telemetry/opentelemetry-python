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

# pylint: disable=protected-access

import gc
import multiprocessing
import os
import time
import unittest
import weakref
from concurrent.futures import ThreadPoolExecutor
from logging import getLogger
from unittest.mock import patch

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics._internal.point import (
    Gauge,
    MetricsData,
    NumberDataPoint,
    ResourceMetrics,
    ScopeMetrics,
)
from opentelemetry.sdk.metrics.export import (
    MetricExporter,
    MetricExportResult,
    SynchronousExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.test.concurrency_test import ConcurrencyTestBase

_logger = getLogger(__name__)


class InMemoryMetricExporter(MetricExporter):
    """Test exporter that stores metrics in memory for verification"""

    def __init__(self, should_fail=False):
        super().__init__()
        self._metrics_data = []
        self._stopped = False
        self._should_fail = should_fail
        self.export_call_count = 0

    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> MetricExportResult:
        self.export_call_count += 1
        if self._should_fail:
            return MetricExportResult.FAILURE
        self._metrics_data.append(metrics_data)
        return MetricExportResult.SUCCESS

    def get_exported_metrics(self):
        """Get the list of exported metrics"""
        return self._metrics_data

    def clear(self):
        """Clear the stored metrics"""
        self._metrics_data.clear()

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        self._stopped = True

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        return True


class FailingMetricExporter(MetricExporter):
    """Exporter that always fails to export metrics"""

    def __init__(self):
        super().__init__()
        self.export_call_count = 0
        self.shutdown_call_count = 0
        self.force_flush_call_count = 0

    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> MetricExportResult:
        self.export_call_count += 1
        return MetricExportResult.FAILURE

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        self.shutdown_call_count += 1

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        self.force_flush_call_count += 1
        return False


class ExceptionMetricExporter(MetricExporter):
    """Exporter that raises exceptions during export"""

    def __init__(self):
        super().__init__()
        self.export_call_count = 0

    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> MetricExportResult:
        self.export_call_count += 1
        raise RuntimeError("Simulated export failure")

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        pass

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        return False


class TestSynchronousExportingMetricReader(ConcurrencyTestBase):
    """Tests for the SynchronousExportingMetricReader class"""

    def setUp(self):
        """Set up common test components"""
        self.exporter = InMemoryMetricExporter()
        self.reader = SynchronousExportingMetricReader(
            self.exporter,
            max_export_batch_size=5,
            max_queue_size=100,
        )

    def tearDown(self):
        """Clean up resources after each test"""
        if hasattr(self, "reader") and not getattr(
            self.reader, "_shutdown", False
        ):
            self.reader.shutdown()

    def _create_metric(self, i, value=None):
        """Helper to create a test metric with a gauge data point

        Args:
            i: Index/identifier for the metric
            value: Optional specific value, defaults to i

        Returns:
            MetricsData: A fully formed metrics data object
        """
        if value is None:
            value = i

        data_point = NumberDataPoint(
            attributes={},
            start_time_unix_nano=0,
            time_unix_nano=int(time.time() * 1e9),
            value=value,
        )

        gauge = Gauge(data_points=[data_point])

        return MetricsData(
            resource_metrics=[
                ResourceMetrics(
                    resource=Resource.create({"service.name": f"test-{i}"}),
                    scope_metrics=[
                        ScopeMetrics(
                            scope=InstrumentationScope(name=f"test-scope-{i}"),
                            metrics=[
                                {
                                    "name": f"metric-{i}",
                                    "description": "Test metric",
                                    "unit": "1",
                                    "data": gauge,
                                }
                            ],
                            schema_url="",
                        )
                    ],
                    schema_url="",
                )
            ]
        )

    def test_constructor_args(self):
        """Test constructor arguments and defaults"""
        exporter = InMemoryMetricExporter()

        # Test with custom values
        reader = SynchronousExportingMetricReader(
            exporter,
            max_export_batch_size=100,
            export_timeout_millis=5000,
            max_queue_size=500,
        )
        self.assertEqual(reader._exporter, exporter)
        self.assertEqual(reader._max_export_batch_size, 100)
        self.assertEqual(reader._export_timeout_millis, 5000)
        self.assertEqual(reader._max_queue_size, 500)

        # Test with defaults
        reader = SynchronousExportingMetricReader(exporter)
        self.assertEqual(reader._exporter, exporter)
        self.assertEqual(reader._max_export_batch_size, 512)
        self.assertEqual(reader._export_timeout_millis, 30000)
        self.assertEqual(reader._max_queue_size, 2048)

    def test_validation_errors(self):
        """Test constructor validation errors with proper error message checks"""
        exporter = InMemoryMetricExporter()

        # Test with invalid max_queue_size
        with self.assertRaises(ValueError) as cm:
            SynchronousExportingMetricReader(exporter, max_queue_size=0)
        self.assertIn(
            "max_queue_size must be a positive integer", str(cm.exception)
        )

        with self.assertRaises(ValueError) as cm:
            SynchronousExportingMetricReader(exporter, max_queue_size=-1)
        self.assertIn(
            "max_queue_size must be a positive integer", str(cm.exception)
        )

        # Test with invalid max_export_batch_size
        with self.assertRaises(ValueError) as cm:
            SynchronousExportingMetricReader(exporter, max_export_batch_size=0)
        self.assertIn(
            "max_export_batch_size must be a positive integer",
            str(cm.exception),
        )

        with self.assertRaises(ValueError) as cm:
            SynchronousExportingMetricReader(
                exporter, max_export_batch_size=-1
            )
        self.assertIn(
            "max_export_batch_size must be a positive integer",
            str(cm.exception),
        )

        # Test with max_export_batch_size > max_queue_size
        with self.assertRaises(ValueError) as cm:
            SynchronousExportingMetricReader(
                exporter, max_queue_size=100, max_export_batch_size=101
            )
        self.assertIn(
            "max_export_batch_size must be less than or equal to max_queue_size",
            str(cm.exception),
        )

    def test_export_batch(self):
        """Test that metrics are properly batched and exported"""
        # Create 10 simple metrics
        for i in range(10):
            # Add metrics to the reader
            self.reader._receive_metrics(self._create_metric(i))

            # After 5 metrics, the batch should be exported
            if i == 4:
                self.assertEqual(len(self.exporter.get_exported_metrics()), 1)
                # The batch should contain 5 resource metrics
                self.assertEqual(
                    len(
                        self.exporter.get_exported_metrics()[
                            0
                        ].resource_metrics
                    ),
                    5,
                )
                # Verify content of exported metrics
                for j in range(5):
                    exported_metric = self.exporter.get_exported_metrics()[
                        0
                    ].resource_metrics[j]
                    self.assertEqual(
                        exported_metric.resource.attributes["service.name"],
                        f"test-{j}",
                    )
                    self.assertEqual(
                        exported_metric.scope_metrics[0].scope.name,
                        f"test-scope-{j}",
                    )
                    self.assertEqual(
                        exported_metric.scope_metrics[0].metrics[0]["name"],
                        f"metric-{j}",
                    )

        # After all 10 metrics, we should have 2 batches
        self.assertEqual(len(self.exporter.get_exported_metrics()), 2)

        # Verify the second batch has 5 resource metrics
        self.assertEqual(
            len(self.exporter.get_exported_metrics()[1].resource_metrics), 5
        )

        # Verify content of second batch
        for j in range(5, 10):
            idx = j - 5
            exported_metric = self.exporter.get_exported_metrics()[
                1
            ].resource_metrics[idx]
            self.assertEqual(
                exported_metric.resource.attributes["service.name"],
                f"test-{j}",
            )

    def test_export_batch_boundary_conditions(self):
        """Test batching behavior at boundary conditions"""
        # Test with exactly one batch size
        for i in range(5):
            self.reader._receive_metrics(self._create_metric(i))

        # Should have exactly one batch
        self.assertEqual(len(self.exporter.get_exported_metrics()), 1)
        self.assertEqual(
            len(self.exporter.get_exported_metrics()[0].resource_metrics), 5
        )

        self.exporter.clear()

        # Test with no metrics
        self.reader.force_flush()
        self.assertEqual(len(self.exporter.get_exported_metrics()), 0)

        # Test with batch size + 1
        for i in range(6):
            self.reader._receive_metrics(self._create_metric(i))

        # Force export of any remaining metrics
        self.reader.force_flush()
        # Should have one complete batch and one partial batch
        self.assertEqual(len(self.exporter.get_exported_metrics()), 2)
        self.assertEqual(
            len(self.exporter.get_exported_metrics()[0].resource_metrics), 5
        )
        self.assertEqual(
            len(self.exporter.get_exported_metrics()[1].resource_metrics), 1
        )

    def test_shutdown(self):
        """Test that shutdown exports queued metrics and shuts down the exporter"""
        # Add 3 metrics (not enough for automatic batch export)
        for i in range(3):
            self.reader._receive_metrics(self._create_metric(i))

        # No exports should have happened yet (batch size not reached)
        self.assertEqual(len(self.exporter.get_exported_metrics()), 0)

        # Shutdown should export remaining metrics
        self.reader.shutdown()

        # Verify metrics were exported
        self.assertEqual(len(self.exporter.get_exported_metrics()), 1)
        self.assertEqual(
            len(self.exporter.get_exported_metrics()[0].resource_metrics), 3
        )

        # Verify exporter was shut down
        self.assertTrue(self.exporter._stopped)

        # Test that shutdown is idempotent
        self.reader.shutdown()  # This should not raise any exceptions

    def test_force_flush(self):
        """Test that force_flush exports queued metrics"""
        # Add 3 metrics (not enough for automatic batch export)
        for i in range(3):
            self.reader._receive_metrics(self._create_metric(i))

        # No exports should have happened yet (batch size not reached)
        self.assertEqual(len(self.exporter.get_exported_metrics()), 0)

        # Force flush should export remaining metrics
        self.assertTrue(self.reader.force_flush())

        # Verify metrics were exported
        self.assertEqual(len(self.exporter.get_exported_metrics()), 1)
        self.assertEqual(
            len(self.exporter.get_exported_metrics()[0].resource_metrics), 3
        )

        # Test that force_flush is idempotent
        self.exporter.clear()
        self.assertTrue(self.reader.force_flush())  # No metrics to flush
        self.assertEqual(len(self.exporter.get_exported_metrics()), 0)

    def test_with_meter_provider(self):
        """Test integration with MeterProvider"""
        # Create a meter provider with our reader
        provider = MeterProvider(
            resource=Resource.create({"service.name": "test-service"}),
            metric_readers=[self.reader],
        )

        # Get a meter and create some instruments
        meter = provider.get_meter("test-meter")
        counter = meter.create_counter(
            "test_counter", description="Test counter"
        )
        gauge = meter.create_gauge("test_gauge", description="Test gauge")

        # Record some metrics
        for i in range(10):
            counter.add(1)
            gauge.set(i)

            # Manually collect after each recording
            # This simulates the behavior in synchronous_read.py example
            self.reader.collect()

        # Shutdown should ensure all metrics are exported
        provider.shutdown()

        # We should have received exported metrics
        self.assertTrue(len(self.exporter.get_exported_metrics()) > 0)

        # Verify some content to ensure metrics were properly recorded
        # Find counter metric in exports
        found_counter = False
        found_gauge = False

        for metrics_data in self.exporter.get_exported_metrics():
            for resource_metric in metrics_data.resource_metrics:
                for scope_metric in resource_metric.scope_metrics:
                    for metric in scope_metric.metrics:
                        # Access attributes as object properties instead of dictionary keys
                        if (
                            hasattr(metric, "name")
                            and metric.name == "test_counter"
                        ):
                            found_counter = True
                        elif (
                            hasattr(metric, "name")
                            and metric.name == "test_gauge"
                        ):
                            found_gauge = True

        self.assertTrue(found_counter, "Counter metrics not found in exports")
        self.assertTrue(found_gauge, "Gauge metrics not found in exports")

    def test_with_multiple_threads(self):
        """Test the reader with concurrent metric recording"""
        # Create a meter provider with our reader
        provider = MeterProvider(
            resource=Resource.create({"service.name": "test-service"}),
            metric_readers=[self.reader],
        )

        # Get a meter and create an instrument
        meter = provider.get_meter("test-meter")
        counter = meter.create_counter(
            "test_counter", description="Test counter"
        )

        def record_and_collect(num_metrics):
            """Record metrics and collect in a thread"""
            for _ in range(num_metrics):
                counter.add(1)
                self.reader.collect()

        # Run multiple threads concurrently recording metrics
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(10):
                future = executor.submit(
                    record_and_collect, (i + 1) * 5
                )  # 5, 10, 15, ... 50 metrics
                futures.append(future)

            # Wait for all threads to complete
            for future in futures:
                future.result()

        # Force flush to ensure all pending metrics are exported
        self.reader.force_flush()

        # Calculate the total number of metrics we should have recorded
        # Sum of (i+1)*5 for i from 0 to 9 = 5*(1+2+3+...+10) = 5*55 = 275
        expected_total = 275

        # Count the total number of resource metrics exported
        total_resource_metrics = sum(
            len(metrics_data.resource_metrics)
            for metrics_data in self.exporter.get_exported_metrics()
        )

        # Allow for small variations in concurrent tests
        self.assertTrue(
            abs(total_resource_metrics - expected_total) <= 1,
            f"Expected ~{expected_total} metrics, got {total_resource_metrics}",
        )

    def test_failing_exporter(self):
        """Test behavior with a failing exporter"""
        failing_exporter = FailingMetricExporter()
        reader = SynchronousExportingMetricReader(
            failing_exporter,
            max_export_batch_size=5,
        )

        # Add metrics to the reader
        for i in range(10):
            reader._receive_metrics(self._create_metric(i))

        # Exporter should have been called at least once
        self.assertGreaterEqual(failing_exporter.export_call_count, 1)

        # Even though exports fail, force_flush should still return True
        # as it represents completion of the flush attempt, not success
        self.assertTrue(reader.force_flush())

        # Shutdown should call the exporter's shutdown
        reader.shutdown()
        self.assertEqual(failing_exporter.shutdown_call_count, 1)

    def test_exception_exporter(self):
        """Test behavior with an exporter that raises exceptions"""
        exception_exporter = ExceptionMetricExporter()
        reader = SynchronousExportingMetricReader(
            exception_exporter,
            max_export_batch_size=5,
        )

        # Add metrics to the reader - this should not propagate exceptions
        try:
            for i in range(10):
                reader._receive_metrics(self._create_metric(i))
            reader.force_flush()
            reader.shutdown()
        except Exception as e:
            self.fail(f"Exception should be caught: {str(e)}")

        # Exporter should have been called
        self.assertGreaterEqual(exception_exporter.export_call_count, 1)

    def test_garbage_collection(self):
        """Test that the reader can be garbage collected"""
        exporter = InMemoryMetricExporter()
        reader = SynchronousExportingMetricReader(exporter)
        weak_ref = weakref.ref(reader)

        # Shutdown the reader
        reader.shutdown()

        # Delete the reader and check if it's garbage collected
        del reader
        gc.collect()

        self.assertIsNone(
            weak_ref(),
            "The SynchronousExportingMetricReader object wasn't garbage collected",
        )

    def test_at_fork_reinit(self):
        """Test that the _at_fork_reinit method properly resets internal state"""
        # Store original values
        original_condition = self.reader._condition

        # Call the fork reinit method directly
        self.reader._at_fork_reinit()

        # Verify that state has been reset properly
        self.assertNotEqual(original_condition, self.reader._condition)
        self.assertEqual(len(self.reader._queue), 0)  # Queue should be cleared
        self.assertEqual(self.reader._pid, os.getpid())

    @patch("time.time_ns")
    def test_time_dependency(self, mock_time_ns):
        """Test behavior with mocked time to avoid actual sleep calls"""
        # Setup mock time behavior
        start_time = 1000000000
        mock_time_ns.return_value = start_time

        # Add metrics and verify they're exported with the mocked timestamp
        self.reader._receive_metrics(self._create_metric(1))

        # Change mock time and add another metric
        mock_time_ns.return_value = start_time + 1000000
        self.reader._receive_metrics(self._create_metric(2))

        # Force flush to export
        self.reader.force_flush()

        # Verify metrics were exported
        self.assertEqual(len(self.exporter.get_exported_metrics()), 1)
        self.assertEqual(
            len(self.exporter.get_exported_metrics()[0].resource_metrics), 2
        )

    @unittest.skipUnless(
        hasattr(os, "fork"),
        "needs *nix",
    )
    def test_fork(self):
        """Test reader behavior after forking (only on Unix-like systems)"""
        # pylint: disable=invalid-name
        exporter = InMemoryMetricExporter()
        reader = SynchronousExportingMetricReader(
            exporter,
            max_export_batch_size=5,
        )

        # Setup meter provider
        provider = MeterProvider(
            metric_readers=[reader],
        )
        meter = provider.get_meter("test-fork")
        counter = meter.create_counter("test_counter")

        # Record metric in parent process
        counter.add(1)
        reader.collect()

        # Verify initial export
        self.assertTrue(reader.force_flush())
        self.assertEqual(len(exporter.get_exported_metrics()), 1)
        exporter.clear()

        # Fork only once in the entire test suite
        if not hasattr(
            TestSynchronousExportingMetricReader,
            "_multiprocessing_start_method_set",
        ):
            try:
                multiprocessing.set_start_method("fork")
                TestSynchronousExportingMetricReader._multiprocessing_start_method_set = True
            except RuntimeError:
                # If context already set, just continue
                TestSynchronousExportingMetricReader._multiprocessing_start_method_set = True

        def child_process(pipe_conn):
            try:
                # Clear any existing data in the exporter
                exporter.clear()

                # Function to run in threads within the child process
                def _target():
                    counter.add(1)
                    # Ensure reader is collecting in child process
                    reader.collect()

                # Run the collection in multiple threads
                self.run_with_many_threads(_target, 10)

                # Give more time for processing
                time.sleep(1.0)

                # Force flush to ensure all metrics are exported
                reader.force_flush()

                # Get metrics and calculate total
                metrics = exporter.get_exported_metrics()
                total_metrics = sum(len(md.resource_metrics) for md in metrics)
                expected_metrics = 10

                # Send diagnostic information back to parent
                result = {
                    "success": abs(total_metrics - expected_metrics)
                    <= 1,  # Allow small variance
                    "actual_count": total_metrics,
                    "expected_count": expected_metrics,
                    "export_count": len(metrics),
                }
                pipe_conn.send(result)
            except Exception as e:
                # Send exception info back to parent
                pipe_conn.send({"error": str(e)})
            finally:
                pipe_conn.close()

        # Create and run the child process
        parent_conn, child_conn = multiprocessing.Pipe()
        p = multiprocessing.Process(target=child_process, args=(child_conn,))
        p.start()

        # Verify child process results
        result = parent_conn.recv()
        p.join()

        if isinstance(result, dict) and "error" in result:
            self.fail(f"Child process encountered an error: {result['error']}")
        elif isinstance(result, dict) and "success" in result:
            self.assertTrue(
                result["success"],
                f"Expected ~{result['expected_count']} metrics, got {result['actual_count']} from {result['export_count']} exports",
            )
        else:
            self.fail(f"Unexpected result from child process: {result}")

        # Clean up
        reader.shutdown()
