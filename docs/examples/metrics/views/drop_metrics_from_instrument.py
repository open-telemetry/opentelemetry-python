# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import random
import time

from opentelemetry.metrics import get_meter_provider, set_meter_provider
from opentelemetry.sdk.metrics import Counter, MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.metrics.view import DropAggregation, View

# Create a view matching the counter instrument `my.counter`
# and configure the view to drop the aggregation.
drop_aggregation_view = View(
    instrument_type=Counter,
    instrument_name="my.counter",
    aggregation=DropAggregation(),
)

exporter = ConsoleMetricExporter()

reader = PeriodicExportingMetricReader(exporter, export_interval_millis=1_000)
provider = MeterProvider(
    metric_readers=[
        reader,
    ],
    views=[
        drop_aggregation_view,
    ],
)
set_meter_provider(provider)

meter = get_meter_provider().get_meter("view-drop-aggregation", "0.1.2")

my_counter = meter.create_counter("my.counter")

while 1:
    my_counter.add(random.randint(1, 10))
    time.sleep(random.random())
