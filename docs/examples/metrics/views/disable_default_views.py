# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""
Example: Disable default views and opt-in to individual instruments explicitly.

By default the SDK records every instrument. This example shows how to:
1. Drop all instruments globally (opt-out by default).
2. Explicitly re-enable only the instruments you care about.
"""

import random
import time

from opentelemetry.metrics import get_meter_provider, set_meter_provider
from opentelemetry.sdk.metrics import Counter, Histogram, MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.metrics.view import DefaultAggregation, DropAggregation, View

# 1. Catch-all view: drop everything by default.
drop_all_view = View(
    instrument_name="*",
    aggregation=DropAggregation(),
)

# 2. Opt-in: explicitly enable only the instruments you want.
enable_request_counter = View(
    instrument_type=Counter,
    instrument_name="app.requests",
    aggregation=DefaultAggregation(),
)

enable_latency_histogram = View(
    instrument_type=Histogram,
    instrument_name="app.latency",
    aggregation=DefaultAggregation(),
)

exporter = ConsoleMetricExporter()
reader = PeriodicExportingMetricReader(exporter, export_interval_millis=1_000)

# Order matters: more specific views take precedence when listed first.
provider = MeterProvider(
    metric_readers=[reader],
    views=[
        enable_request_counter,
        enable_latency_histogram,
        drop_all_view,   # catch-all at the end
    ],
)
set_meter_provider(provider)

meter = get_meter_provider().get_meter("my.app", "0.1.0")

# These two are opted-in and will be exported.
request_counter = meter.create_counter("app.requests")
latency_histogram = meter.create_histogram("app.latency")

# This one is NOT opted-in and will be silently dropped.
debug_counter = meter.create_counter("app.debug.internal")

while True:
    request_counter.add(random.randint(1, 10))
    latency_histogram.record(random.uniform(0.5, 2.0))
    debug_counter.add(1)
    time.sleep(random.random())
