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

"""
This example demonstrates how to implement and use a MetricProducer to
bridge third-party metric sources with OpenTelemetry.

MetricProducer allows you to integrate pre-processed metrics from external
systems (like Prometheus, custom monitoring systems, etc.) into the
OpenTelemetry metrics pipeline.
"""

import time
from typing import Dict

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    Metric,
    MetricProducer,
    MetricsData,
    NumberDataPoint,
    PeriodicExportingMetricReader,
    ResourceMetrics,
    ScopeMetrics,
    Sum,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope


class PrometheusMetricProducer(MetricProducer):
    """Example MetricProducer that bridges Prometheus metrics.
    
    This example shows how to fetch metrics from a third-party source
    (simulating Prometheus) and convert them to OpenTelemetry format.
    """

    def __init__(self, prometheus_url: str = "http://localhost:9090"):
        self.prometheus_url = prometheus_url
        self.instrumentation_scope = InstrumentationScope(
            name="prometheus.bridge",
            version="1.0.0"
        )
        self.resource = Resource.create({
            "service.name": "prometheus-bridge",
            "bridge.source": "prometheus",
            "bridge.url": prometheus_url
        })

    def produce(self, timeout_millis: float = 10_000) -> MetricsData:
        """Fetch metrics from Prometheus and convert to OpenTelemetry format."""
        
        # In a real implementation, you would:
        # 1. Make HTTP request to Prometheus /api/v1/query_range or /metrics
        # 2. Parse the response (JSON or Prometheus text format)
        # 3. Convert to OpenTelemetry metrics
        
        # For this example, we'll simulate fetching metrics
        simulated_prometheus_metrics = self._fetch_prometheus_metrics()
        
        # Convert to OpenTelemetry format
        otel_metrics = []
        for metric_name, metric_data in simulated_prometheus_metrics.items():
            otel_metrics.append(
                Metric(
                    name=f"prometheus.{metric_name}",
                    description=f"Metric {metric_name} from Prometheus",
                    unit=metric_data.get("unit", "1"),
                    data=Sum(
                        data_points=[
                            NumberDataPoint(
                                attributes=metric_data.get("labels", {}),
                                start_time_unix_nano=int((time.time() - 60) * 1e9),  # 1 minute ago
                                time_unix_nano=int(time.time() * 1e9),
                                value=metric_data["value"],
                            )
                        ],
                        aggregation_temporality=1,  # CUMULATIVE
                        is_monotonic=metric_data.get("monotonic", False),
                    ),
                )
            )

        # Return as MetricsData
        return MetricsData(
            resource_metrics=[
                ResourceMetrics(
                    resource=self.resource,
                    scope_metrics=[
                        ScopeMetrics(
                            scope=self.instrumentation_scope,
                            metrics=otel_metrics,
                            schema_url="",
                        )
                    ],
                    schema_url="",
                )
            ]
        )

    def _fetch_prometheus_metrics(self) -> Dict[str, Dict]:
        """Simulate fetching metrics from Prometheus."""
        # In a real implementation, this would make HTTP requests to Prometheus
        # and parse the response. For this example, we return simulated data.
        
        return {
            "http_requests_total": {
                "value": 12345,
                "labels": {"method": "GET", "status": "200"},
                "unit": "1",
                "monotonic": True,
            },
            "http_request_duration_seconds": {
                "value": 0.234,
                "labels": {"method": "GET", "quantile": "0.95"},
                "unit": "s",
                "monotonic": False,
            },
            "memory_usage_bytes": {
                "value": 1024 * 1024 * 512,  # 512 MB
                "labels": {"instance": "server-1"},
                "unit": "bytes",
                "monotonic": False,
            },
        }


class CustomSystemMetricProducer(MetricProducer):
    """Example MetricProducer for a custom monitoring system."""

    def __init__(self, system_name: str = "custom-system"):
        self.system_name = system_name
        self.instrumentation_scope = InstrumentationScope(
            name=f"{system_name}.bridge",
            version="1.0.0"
        )
        self.resource = Resource.create({
            "service.name": f"{system_name}-bridge",
            "bridge.source": system_name,
        })

    def produce(self, timeout_millis: float = 10_000) -> MetricsData:
        """Fetch metrics from custom system."""
        
        # Simulate fetching from a custom system
        custom_metrics = self._fetch_custom_metrics()
        
        # Convert to OpenTelemetry format
        otel_metrics = []
        for metric in custom_metrics:
            otel_metrics.append(
                Metric(
                    name=f"custom.{metric['name']}",
                    description=metric.get("description", ""),
                    unit=metric.get("unit", "1"),
                    data=Sum(
                        data_points=[
                            NumberDataPoint(
                                attributes=metric.get("tags", {}),
                                start_time_unix_nano=int((time.time() - 30) * 1e9),  # 30 seconds ago
                                time_unix_nano=int(time.time() * 1e9),
                                value=metric["value"],
                            )
                        ],
                        aggregation_temporality=1,  # CUMULATIVE
                        is_monotonic=metric.get("is_counter", False),
                    ),
                )
            )

        return MetricsData(
            resource_metrics=[
                ResourceMetrics(
                    resource=self.resource,
                    scope_metrics=[
                        ScopeMetrics(
                            scope=self.instrumentation_scope,
                            metrics=otel_metrics,
                            schema_url="",
                        )
                    ],
                    schema_url="",
                )
            ]
        )

    def _fetch_custom_metrics(self) -> list:
        """Simulate fetching from a custom monitoring system."""
        return [
            {
                "name": "database_connections",
                "value": 25,
                "description": "Active database connections",
                "unit": "1",
                "tags": {"database": "postgres", "pool": "main"},
                "is_counter": False,
            },
            {
                "name": "api_calls_total",
                "value": 9876,
                "description": "Total API calls processed",
                "unit": "1",
                "tags": {"endpoint": "/api/v1/users", "method": "GET"},
                "is_counter": True,
            },
        ]


def main():
    """Example usage of MetricProducer with OpenTelemetry."""
    
    print("Starting MetricProducer example...")
    
    # Create MetricProducers for different third-party sources
    prometheus_producer = PrometheusMetricProducer("http://localhost:9090")
    custom_producer = CustomSystemMetricProducer("monitoring-system")
    
    # Create a metric reader that includes the producers
    exporter = ConsoleMetricExporter()
    reader = PeriodicExportingMetricReader(
        exporter=exporter,
        export_interval_millis=5000,  # Export every 5 seconds
        metric_producers=[prometheus_producer, custom_producer]
    )
    
    # IMPORTANT: Register the reader with a MeterProvider
    # This is required for the reader to be able to collect metrics
    meter_provider = MeterProvider(metric_readers=[reader])
    
    print("Configured MetricReader with the following producers:")
    print("- PrometheusMetricProducer (simulated)")
    print("- CustomSystemMetricProducer (simulated)")
    print("\nThe reader is now registered with a MeterProvider and will collect")
    print("metrics from these producers every 5 seconds and export them to the console.\n")
    
    # Note: You can also use the meter_provider to create meters and instruments
    # meter = meter_provider.get_meter("example.meter")
    # counter = meter.create_counter("example.counter")
    # counter.add(1)
    
    print("=== Metrics will be collected and exported every 5 seconds ===")
    print("Press Ctrl+C to stop...")
    
    try:
        # Let it run for a bit to show periodic collection
        time.sleep(20)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        # Clean shutdown
        meter_provider.shutdown()
        print("MeterProvider shut down successfully.")


if __name__ == "__main__":
    main()