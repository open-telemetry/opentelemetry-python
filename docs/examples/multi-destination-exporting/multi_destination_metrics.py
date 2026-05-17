# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""
This example shows how to export metrics to multiple destinations.
Each PeriodicExportingMetricReader has its own collection interval
and export queue, so destinations do not block each other.
"""

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
    OTLPMetricExporter as GrpcMetricExporter,
)
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    OTLPMetricExporter as HttpMetricExporter,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)

# Destination 1: OTLP over gRPC
grpc_reader = PeriodicExportingMetricReader(
    GrpcMetricExporter(endpoint="http://localhost:4317", insecure=True)
)

# Destination 2: OTLP over HTTP
http_reader = PeriodicExportingMetricReader(
    HttpMetricExporter(endpoint="http://localhost:4318/v1/metrics")
)

# Destination 3: Console (for debugging)
console_reader = PeriodicExportingMetricReader(ConsoleMetricExporter())

# Pass all readers to the MeterProvider
provider = MeterProvider(
    metric_readers=[grpc_reader, http_reader, console_reader]
)
metrics.set_meter_provider(provider)

meter = metrics.get_meter(__name__)
counter = meter.create_counter(
    "request.count", description="Number of requests"
)

counter.add(1, {"endpoint": "/api/users"})
counter.add(1, {"endpoint": "/api/orders"})

print("Metrics are exported to all three destinations.")

provider.shutdown()
