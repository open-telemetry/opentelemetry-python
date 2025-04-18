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

import logging
import random
import time

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    SynchronousExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Create a resource that identifies our service
resource = Resource.create({"service.name": "batch-metrics-auto-export-demo"})
# Create a console exporter for visible output
exporter = ConsoleMetricExporter()
# Create a batch exporting reader with a small batch size for demonstration
reader = SynchronousExportingMetricReader(
    exporter,
    max_export_batch_size=5,  # Export after every 5 metrics
    max_queue_size=100,  # Queue up to 100 metrics
)
# Create a meter provider with our reader
meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
# Set the global meter provider
metrics.set_meter_provider(meter_provider)
# Get a meter
meter = metrics.get_meter("batch-demo-auto-export")
# Create instruments
request_counter = meter.create_counter(
    name="request_count",
    description="Number of requests processed",
    unit="1",
)
active_requests_gauge = meter.create_gauge(
    name="active_requests",
    description="Number of active requests",
    unit="1",
)
processing_time_histogram = meter.create_histogram(
    name="request_processing_time",
    description="Time taken to process requests",
    unit="ms",
)


def simulate_request():
    """Simulate a request and record metrics."""
    # Simulate active requests fluctuating
    active_requests = random.randint(1, 20)
    active_requests_gauge.set(active_requests)
    # Simulate processing time
    processing_time = random.uniform(10, 500)  # Between 10-500ms
    processing_time_histogram.record(processing_time)
    # Increment the request counter
    request_counter.add(1)
    logger.info("Processed a request")
    reader.collect()
    # Each request generates 3 metrics (counter, gauge, histogram)
    # With batch size of 5, we should see exports after every ~2 requests


def main():
    """Main application function to demonstrate reading and exporting metrics synchronously."""
    logger.info("Starting to process requests...")
    logger.info(
        "With batch size of 5, exports should happen automatically after every ~2 requests"
    )
    logger.info("Watch for the metric exports in the console...")
    # Process 25 requests with pauses to observe collection and export mechanism
    for i in range(1, 25):
        simulate_request()
        # Add a pause between requests to make it easier to observe the exports
        time.sleep(0.5)
    logger.info("\nAll requests completed.")
    # We still need to shut down cleanly
    logger.info("Shutting down...")
    meter_provider.shutdown()
    logger.info(
        "Done. Any metrics left in the queue were exported during shutdown."
    )


if __name__ == "__main__":
    main()
