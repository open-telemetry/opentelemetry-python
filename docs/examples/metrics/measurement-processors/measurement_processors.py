#!/usr/bin/env python3

"""
Example demonstrating the use of MeasurementProcessor with OpenTelemetry Python SDK.

This example shows how to:
1. Create custom measurement processors
2. Chain multiple processors together
3. Integrate with MeterProvider
4. Use the provided utility processors
"""

import time
from typing import Callable

from opentelemetry import baggage, metrics
from opentelemetry.context import attach, detach
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics._internal.measurement import Measurement
from opentelemetry.sdk.metrics._internal.measurement_processor import (
    AttributeFilterMeasurementProcessor,
    BaggageMeasurementProcessor,
    MeasurementProcessor,
    StaticAttributeMeasurementProcessor,
    ValueRangeMeasurementProcessor,
)
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)


class CustomMeasurementProcessor(MeasurementProcessor):
    """Example of a custom measurement processor that adds a timestamp attribute."""

    def process(
        self,
        measurement: Measurement,
        next_processor: Callable[[Measurement], None],
    ) -> None:
        # Add current timestamp as an attribute
        from dataclasses import replace

        new_attributes = dict(measurement.attributes or {})
        new_attributes["processed_at"] = str(int(time.time()))

        new_measurement = replace(measurement, attributes=new_attributes)
        next_processor(new_measurement)


def main():
    print("=== OpenTelemetry MeasurementProcessor Demo ===\n")

    # Create measurement processors
    processors = [
        # Add baggage values as attributes (for correlation)
        BaggageMeasurementProcessor(),
        # Add static environment attributes
        StaticAttributeMeasurementProcessor(
            {"environment": "demo", "service": "measurement-processor-example"}
        ),
        # Filter out any potentially sensitive attributes
        AttributeFilterMeasurementProcessor(["password", "secret"]),
        # Drop measurements with invalid values (negative for this demo)
        ValueRangeMeasurementProcessor(min_value=0),
        # Add custom processing
        CustomMeasurementProcessor(),
    ]

    # Create metrics export pipeline
    console_exporter = ConsoleMetricExporter()
    reader = PeriodicExportingMetricReader(
        exporter=console_exporter,
        export_interval_millis=5000,  # Export every 5 seconds
    )

    # Create MeterProvider with measurement processors
    meter_provider = MeterProvider(
        metric_readers=[reader], measurement_processors=processors
    )
    metrics.set_meter_provider(meter_provider)

    # Get meter and create instruments
    meter = metrics.get_meter(__name__)
    request_counter = meter.create_counter(
        "requests_total", description="Total number of requests"
    )
    response_time_histogram = meter.create_histogram(
        "response_time_seconds", description="Response time in seconds"
    )

    print("Recording measurements with different scenarios...\n")

    # Scenario 1: Regular measurement with baggage
    print("1. Recording with baggage context...")
    ctx = baggage.set_baggage("user.id", "12345")
    ctx = baggage.set_baggage("trace.id", "abc123", context=ctx)
    token = attach(ctx)

    try:
        request_counter.add(1, {"endpoint": "/api/users", "method": "GET"})
        response_time_histogram.record(
            0.150, {"endpoint": "/api/users", "status": "200"}
        )
    finally:
        detach(token)

    # Scenario 2: Measurement with filtered attributes
    print("2. Recording with attributes that should be filtered...")
    request_counter.add(
        1,
        {
            "endpoint": "/api/login",
            "method": "POST",
            "password": "should-be-filtered",  # This will be filtered out
            "username": "alice",
        },
    )

    # Scenario 3: Invalid measurement (negative value) - should be dropped
    print(
        "3. Recording invalid measurement (negative value - should be dropped)..."
    )
    response_time_histogram.record(
        -1.0, {"endpoint": "/api/error", "status": "500"}
    )

    # Scenario 4: Valid measurement without baggage
    print("4. Recording normal measurement...")
    request_counter.add(2, {"endpoint": "/api/products", "method": "GET"})
    response_time_histogram.record(
        0.075, {"endpoint": "/api/products", "status": "200"}
    )

    print("\nWaiting for metrics to be exported...")
    print("(Check the console output above for processed measurements)")

    # Wait a bit for export
    time.sleep(6)

    # Cleanup
    meter_provider.shutdown()
    print("\nDemo completed!")


if __name__ == "__main__":
    main()
