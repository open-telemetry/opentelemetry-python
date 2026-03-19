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

from typing import Optional, Union
from unittest import TestCase
from unittest.mock import Mock

from opentelemetry.sdk.metrics.export import (
    InMemoryMetricReader,
    Metric,
    MetricProducer,
    MetricsData,
    NumberDataPoint,
    ResourceMetrics,
    ScopeMetrics,
    Sum,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope


class TestMetricProducer(TestCase):
    def test_metric_producer_is_abstract(self):
        """Test that MetricProducer cannot be instantiated directly."""
        with self.assertRaises(TypeError):
            MetricProducer()  # pylint: disable=abstract-class-instantiated

    def test_metric_producer_produce_method_required(self):
        """Test that MetricProducer requires implementation of produce method."""
        
        class IncompleteProducer(MetricProducer):
            pass

        with self.assertRaises(TypeError):
            IncompleteProducer()  # pylint: disable=abstract-class-instantiated


class MockMetricProducer(MetricProducer):
    """Mock implementation of MetricProducer for testing."""

    def __init__(self, metrics_data: Union[MetricsData, None, str] = "default", should_raise: Optional[Exception] = None):
        self.metrics_data = metrics_data
        self.should_raise = should_raise
        self.produce_called = False

    def produce(self, timeout_millis: float = 10_000) -> MetricsData:
        """Produce mock metrics data."""
        self.produce_called = True
        
        if self.should_raise:
            raise self.should_raise
            
        # If explicitly set to None, return empty MetricsData
        if self.metrics_data is None:
            return MetricsData(resource_metrics=[])
            
        # If explicitly provided metrics_data, return it
        if self.metrics_data != "default" and isinstance(self.metrics_data, MetricsData):
            return self.metrics_data
            
        # Default mock data when no explicit metrics_data provided
        return MetricsData(
            resource_metrics=[
                ResourceMetrics(
                    resource=Resource.create({"service.name": "test-producer"}),
                    scope_metrics=[
                        ScopeMetrics(
                            scope=InstrumentationScope("test.producer"),
                            metrics=[
                                Metric(
                                    name="producer.counter",
                                    description="Test counter from producer",
                                    unit="1",
                                    data=Sum(
                                        data_points=[
                                            NumberDataPoint(
                                                attributes={"producer": "mock"},
                                                start_time_unix_nano=1647626444152947792,
                                                time_unix_nano=1647626444153163239,
                                                value=42,
                                            )
                                        ],
                                        aggregation_temporality=1,  # CUMULATIVE
                                        is_monotonic=True,
                                    ),
                                )
                            ],
                            schema_url="",
                        )
                    ],
                    schema_url="",
                )
            ]
        )


class TestInMemoryMetricReaderWithProducers(TestCase):
    def test_metric_reader_with_no_producers(self):
        """Test MetricReader with no producers behaves as before."""
        reader = InMemoryMetricReader()
        mock_collect_callback = Mock(return_value=[])
        reader._set_collect_callback(mock_collect_callback)
        
        metrics_data = reader.get_metrics_data()
        # When there are no metrics, should return empty list (same as before)
        self.assertEqual(metrics_data, [])

    def test_metric_reader_with_single_producer(self):
        """Test MetricReader with a single MetricProducer."""
        producer = MockMetricProducer()
        reader = InMemoryMetricReader(metric_producers=[producer])
        mock_collect_callback = Mock(return_value=MetricsData(resource_metrics=[]))
        reader._set_collect_callback(mock_collect_callback)
        
        metrics_data = reader.get_metrics_data()
        
        # Producer should have been called
        self.assertTrue(producer.produce_called)
        
        # Should have producer's metrics
        self.assertIsNotNone(metrics_data)
        if metrics_data is not None:
            self.assertEqual(len(metrics_data.resource_metrics), 1)
            self.assertEqual(
                metrics_data.resource_metrics[0].resource.attributes["service.name"],
                "test-producer"
            )

    def test_metric_reader_with_multiple_producers(self):
        """Test MetricReader with multiple MetricProducers."""
        producer1 = MockMetricProducer()
        producer2 = MockMetricProducer(
            MetricsData(
                resource_metrics=[
                    ResourceMetrics(
                        resource=Resource.create({"service.name": "test-producer-2"}),
                        scope_metrics=[
                            ScopeMetrics(
                                scope=InstrumentationScope("test.producer.2"),
                                metrics=[
                                    Metric(
                                        name="producer.gauge",
                                        description="Test gauge from producer 2",
                                        unit="bytes",
                                        data=Sum(
                                            data_points=[
                                                NumberDataPoint(
                                                    attributes={"producer": "mock2"},
                                                    start_time_unix_nano=1647626444152947792,
                                                    time_unix_nano=1647626444153163239,
                                                    value=100,
                                                )
                                            ],
                                            aggregation_temporality=1,  # CUMULATIVE
                                            is_monotonic=True,
                                        ),
                                    )
                                ],
                                schema_url="",
                            )
                        ],
                        schema_url="",
                    )
                ]
            )
        )
        
        reader = InMemoryMetricReader(metric_producers=[producer1, producer2])
        mock_collect_callback = Mock(return_value=MetricsData(resource_metrics=[]))
        reader._set_collect_callback(mock_collect_callback)
        
        metrics_data = reader.get_metrics_data()
        
        # Both producers should have been called
        self.assertTrue(producer1.produce_called)
        self.assertTrue(producer2.produce_called)
        
        # Should have metrics from both producers
        self.assertIsNotNone(metrics_data)
        if metrics_data is not None:
            self.assertEqual(len(metrics_data.resource_metrics), 2)
            
            service_names = {
                rm.resource.attributes["service.name"] 
                for rm in metrics_data.resource_metrics
            }
            self.assertEqual(service_names, {"test-producer", "test-producer-2"})

    def test_metric_reader_combines_sdk_and_producer_metrics(self):
        """Test that MetricReader combines both SDK and producer metrics."""
        producer = MockMetricProducer()
        reader = InMemoryMetricReader(metric_producers=[producer])
        
        # Mock SDK metrics
        sdk_resource_metrics = ResourceMetrics(
            resource=Resource.create({"service.name": "test-sdk"}),
            scope_metrics=[
                ScopeMetrics(
                    scope=InstrumentationScope("test.sdk"),
                    metrics=[
                        Metric(
                            name="sdk.counter",
                            description="Test counter from SDK",
                            unit="1",
                            data=Sum(
                                data_points=[
                                    NumberDataPoint(
                                        attributes={"source": "sdk"},
                                        start_time_unix_nano=1647626444152947792,
                                        time_unix_nano=1647626444153163239,
                                        value=10,
                                    )
                                ],
                                aggregation_temporality=1,  # CUMULATIVE
                                is_monotonic=True,
                            ),
                        )
                    ],
                    schema_url="",
                )
            ],
            schema_url="",
        )
        
        mock_collect_callback = Mock(
            return_value=MetricsData(resource_metrics=[sdk_resource_metrics])
        )
        reader._set_collect_callback(mock_collect_callback)
        
        metrics_data = reader.get_metrics_data()
        
        # Producer should have been called
        self.assertTrue(producer.produce_called)
        
        # Should have metrics from both SDK and producer
        self.assertIsNotNone(metrics_data)
        if metrics_data is not None:
            self.assertEqual(len(metrics_data.resource_metrics), 2)
            
            service_names = {
                rm.resource.attributes["service.name"] 
                for rm in metrics_data.resource_metrics
            }
            self.assertEqual(service_names, {"test-sdk", "test-producer"})

    def test_metric_reader_handles_producer_exception(self):
        """Test that MetricReader handles exceptions from producers gracefully."""
        failing_producer = MockMetricProducer(should_raise=RuntimeError("Producer failed"))
        working_producer = MockMetricProducer()
        
        reader = InMemoryMetricReader(
            metric_producers=[failing_producer, working_producer]
        )
        mock_collect_callback = Mock(return_value=MetricsData(resource_metrics=[]))
        reader._set_collect_callback(mock_collect_callback)
        
        # Should not raise exception and should still collect from working producer
        metrics_data = reader.get_metrics_data()
        
        # Working producer should have been called
        self.assertTrue(working_producer.produce_called)
        
        # Should have metrics from working producer only
        self.assertIsNotNone(metrics_data)
        if metrics_data is not None:
            self.assertEqual(len(metrics_data.resource_metrics), 1)
            self.assertEqual(
                metrics_data.resource_metrics[0].resource.attributes["service.name"],
                "test-producer"
            )

    def test_metric_reader_with_none_producer_data(self):
        """Test that MetricReader handles producers returning None."""
        producer = MockMetricProducer(metrics_data=None)
        reader = InMemoryMetricReader(metric_producers=[producer])
        # Mock the SDK to return None (no SDK metrics)
        mock_collect_callback = Mock(return_value=None)
        reader._set_collect_callback(mock_collect_callback)
        
        # Should not raise exception
        metrics_data = reader.get_metrics_data()
        
        # Producer should have been called
        self.assertTrue(producer.produce_called)
        
        # Should have no metrics since both SDK and producer return None/empty
        # When both sources are empty, get_metrics_data might return None
        self.assertIsNone(metrics_data)

    def test_periodic_exporting_metric_reader_with_producers(self):
        """Test PeriodicExportingMetricReader with MetricProducers."""
        from opentelemetry.sdk.metrics.export import (
            ConsoleMetricExporter, 
            PeriodicExportingMetricReader
        )
        
        producer = MockMetricProducer()
        exporter = ConsoleMetricExporter()
        reader = PeriodicExportingMetricReader(
            exporter=exporter,
            metric_producers=[producer]
        )
        
        # Should initialize without error
        self.assertIsNotNone(reader)
        self.assertEqual(len(reader._metric_producers), 1)
        
        # Clean up
        reader.shutdown()


class TestMetricProducerTimeoutEnforcement(TestCase):
    """Tests for timeout budget enforcement across SDK and MetricProducers."""
    
    def test_timeout_enforced_with_slow_producer(self):
        """Test that timeout is raised when producer takes too long."""
        import time
        from opentelemetry.sdk.metrics._internal.exceptions import MetricsTimeoutError
        
        class SlowMetricProducer(MetricProducer):
            def produce(self, timeout_millis=10_000):
                # Simulate slow producer that takes longer than timeout
                time.sleep(timeout_millis / 1000 + 0.5)  # Sleep longer than timeout
                return None
        
        producer = SlowMetricProducer()
        reader = InMemoryMetricReader(metric_producers=[producer])
        
        # Set up minimal callback
        mock_collect_callback = Mock(return_value=[])
        reader._set_collect_callback(mock_collect_callback)
        
        # Should raise timeout error
        with self.assertRaises(MetricsTimeoutError):
            reader.collect(timeout_millis=100)  # Very short timeout
    
    def test_timeout_budget_decremented_across_producers(self):
        """Test that remaining timeout decreases across multiple producers."""
        import time
        
        class TimeTrackingProducer(MetricProducer):
            def __init__(self):
                self.timeout_received = None
                self.call_time = None
            
            def produce(self, timeout_millis=10_000):
                self.timeout_received = timeout_millis
                self.call_time = time.time()
                time.sleep(0.05)  # Sleep 50ms
                return None
        
        producer1 = TimeTrackingProducer()
        producer2 = TimeTrackingProducer()
        producer3 = TimeTrackingProducer()
        
        reader = InMemoryMetricReader(
            metric_producers=[producer1, producer2, producer3]
        )
        
        # Set up minimal callback that takes some time
        def slow_collect(*args, **kwargs):
            time.sleep(0.05)  # SDK collection takes 50ms
            return []
        
        reader._set_collect_callback(slow_collect)
        
        # Collect with 1 second timeout
        reader.collect(timeout_millis=1000)
        
        # Verify each producer got less timeout than the previous
        self.assertIsNotNone(producer1.timeout_received)
        self.assertIsNotNone(producer2.timeout_received)
        self.assertIsNotNone(producer3.timeout_received)
        
        # Producer2 should have received less timeout than producer1
        # (accounting for SDK collection time and producer1 execution time)
        assert producer2.timeout_received is not None
        assert producer1.timeout_received is not None
        self.assertLess(producer2.timeout_received, producer1.timeout_received)
        
        # Producer3 should have received less timeout than producer2
        assert producer3.timeout_received is not None
        self.assertLess(producer3.timeout_received, producer2.timeout_received)
    
    def test_timeout_not_exceeded_with_fast_producers(self):
        """Test that fast producers complete successfully within timeout."""
        
        class FastMetricProducer(MetricProducer):
            def __init__(self):
                self.produce_called = False
            
            def produce(self, timeout_millis=10_000):
                self.produce_called = True
                # Return immediately
                return MetricsData(resource_metrics=[])
        
        producer1 = FastMetricProducer()
        producer2 = FastMetricProducer()
        producer3 = FastMetricProducer()
        
        reader = InMemoryMetricReader(
            metric_producers=[producer1, producer2, producer3]
        )
        
        mock_collect_callback = Mock(return_value=[])
        reader._set_collect_callback(mock_collect_callback)
        
        # Should complete without timeout error
        reader.collect(timeout_millis=1000)
        
        # All producers should have been called
        self.assertTrue(producer1.produce_called)
        self.assertTrue(producer2.produce_called)
        self.assertTrue(producer3.produce_called)
    
    def test_timeout_error_before_sdk_collection_completes(self):
        """Test timeout error if SDK collection takes too long."""
        import time
        from opentelemetry.sdk.metrics._internal.exceptions import MetricsTimeoutError
        
        class SlowProducer(MetricProducer):
            def produce(self, timeout_millis=10_000):
                return None
        
        producer = SlowProducer()
        reader = InMemoryMetricReader(metric_producers=[producer])
        
        # Set up slow SDK collection
        def very_slow_collect(*args, **kwargs):
            time.sleep(0.5)  # Sleep longer than timeout
            return []
        
        reader._set_collect_callback(very_slow_collect)
        
        # Should raise timeout error during SDK collection
        with self.assertRaises(MetricsTimeoutError) as context:
            reader.collect(timeout_millis=100)
        
        self.assertIn("SDK metric collection", str(context.exception))
    
    def test_timeout_error_identifies_failing_producer(self):
        """Test that timeout error identifies which producer exceeded timeout."""
        import time
        from opentelemetry.sdk.metrics._internal.exceptions import MetricsTimeoutError
        
        class FastProducer(MetricProducer):
            def produce(self, timeout_millis=10_000):
                return None
        
        class NamedSlowProducer(MetricProducer):
            def produce(self, timeout_millis=10_000):
                time.sleep(timeout_millis / 1000 + 0.1)
                return None
        
        producer1 = FastProducer()
        producer2 = NamedSlowProducer()
        
        reader = InMemoryMetricReader(metric_producers=[producer1, producer2])
        
        mock_collect_callback = Mock(return_value=[])
        reader._set_collect_callback(mock_collect_callback)
        
        # Should raise timeout error with producer name
        with self.assertRaises(MetricsTimeoutError) as context:
            reader.collect(timeout_millis=100)
        
        # Error message should mention the producer class
        self.assertIn("NamedSlowProducer", str(context.exception))