# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import time

from opentelemetry.metrics import get_meter_provider, set_meter_provider
from opentelemetry.sdk.metrics import Counter, MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.metrics.view import LastValueAggregation

aggregation_last_value = {Counter: LastValueAggregation()}

# Use console exporter for the example
exporter = ConsoleMetricExporter(
    preferred_aggregation=aggregation_last_value,
)

# The PeriodicExportingMetricReader takes the preferred aggregation
# from the passed in exporter
reader = PeriodicExportingMetricReader(
    exporter,
    export_interval_millis=5_000,
)

provider = MeterProvider(metric_readers=[reader])
set_meter_provider(provider)

meter = get_meter_provider().get_meter("preferred-aggregation", "0.1.2")

counter = meter.create_counter("my-counter")

# A counter normally would have an aggregation type of SumAggregation,
# in which it's value would be determined by a cumulative sum.
# In this example, the counter is configured with the LastValueAggregation,
# which will only hold the most recent value.
for x in range(10):
    counter.add(x)
    time.sleep(2.0)
