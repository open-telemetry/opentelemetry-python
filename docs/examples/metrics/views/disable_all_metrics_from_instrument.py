# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""
Example: Turn off all metrics from a given instrumentation library.

This shows how to drop every metric produced by a specific meter/library
without affecting metrics from other instrumentation sources.
"""

import random
import time

from opentelemetry.metrics import get_meter_provider, set_meter_provider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.metrics.view import DropAggregation, View

# Drop every instrument whose meter name matches "noisy.library".
# The wildcard "*" on instrument_name means all instruments from that meter.
drop_noisy_library_view = View(
    instrument_name="*",
    meter_name="noisy.library",
    aggregation=DropAggregation(),
)

exporter = ConsoleMetricExporter()
reader = PeriodicExportingMetricReader(exporter, export_interval_millis=1_000)
provider = MeterProvider(
    metric_readers=[reader],
    views=[drop_noisy_library_view],
)
set_meter_provider(provider)

# This meter is silenced — none of its instruments will be exported.
noisy_meter = get_meter_provider().get_meter("noisy.library", "0.1.0")
noisy_counter = noisy_meter.create_counter("noisy.requests")

# This meter is unaffected and will still export normally.
normal_meter = get_meter_provider().get_meter("my.app", "0.1.0")
normal_counter = normal_meter.create_counter("app.requests")

while True:
    noisy_counter.add(random.randint(1, 10))
    normal_counter.add(random.randint(1, 5))
    time.sleep(random.random())
