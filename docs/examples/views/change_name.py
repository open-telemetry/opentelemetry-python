import random
import time

from opentelemetry.metrics import get_meter_provider, set_meter_provider
from opentelemetry.sdk.metrics import Counter, MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.metrics.view import View

# Create a view matching the counter instrument `my.counter`
# and configure the new name `my.counter.total` for the result metrics stream
change_metric_name_view = View(
    instrument_type=Counter,
    instrument_name="my.counter",
    name="my.counter.total",
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
        change_metric_name_view,
    ],
)
set_meter_provider(provider)

meter = get_meter_provider().get_meter("view-name-change", "0.1.2")

my_counter = meter.create_counter("my.counter")

while 1:
    my_counter.add(random.randint(1, 10))
    time.sleep(random.random())
