import random
import time

from opentelemetry.metrics import get_meter_provider, set_meter_provider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader
)
from opentelemetry.sdk.metrics.view import SumAggregation, View

# Create a view matching the histogram instrument name `http.client.request.latency`
# and configure the `SumAggregation` for the result metrics stream
hist_to_sum_view = View(
    instrument_name="http.client.request.latency", aggregation=SumAggregation()
)

# Use console exporter for the example
exporter = ConsoleMetricExporter()

# Create a metric reader with stdout exporter
reader = PeriodicExportingMetricReader(exporter, export_interval_millis=1_000)
provider = MeterProvider(
    metric_readers=[
        reader,
    ],
    views=[
        hist_to_sum_view,
    ],
)
set_meter_provider(provider)

meter = get_meter_provider().get_meter("view-change-aggregation", "0.1.2")

histogram = meter.create_histogram("http.client.request.latency")

while 1:
    histogram.record(99.9)
    time.sleep(random.random())
