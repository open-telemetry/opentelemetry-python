# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import random
import time
from collections.abc import Iterable

from opentelemetry.metrics import (
    CallbackOptions,
    Observation,
    get_meter_provider,
    set_meter_provider,
)
from opentelemetry.sdk.metrics import MeterProvider, ObservableGauge
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.metrics.view import View

# Create a view matching the observable gauge instrument `observable_gauge`
# and configure the attributes in the result metric stream
# to contain only the attributes with keys with `k_3` and `k_5`
view_with_attributes_limit = View(
    instrument_type=ObservableGauge,
    instrument_name="observable_gauge",
    attribute_keys={"k_3", "k_5"},
)

exporter = ConsoleMetricExporter()

reader = PeriodicExportingMetricReader(exporter, export_interval_millis=1_000)
provider = MeterProvider(
    metric_readers=[
        reader,
    ],
    views=[
        view_with_attributes_limit,
    ],
)
set_meter_provider(provider)

meter = get_meter_provider().get_meter("reduce-cardinality-with-view", "0.1.2")


def observable_gauge_func(options: CallbackOptions) -> Iterable[Observation]:
    attrs = {}
    for i in range(random.randint(1, 100)):
        attrs[f"k_{i}"] = f"v_{i}"
    yield Observation(1, attrs)


# Async gauge
observable_gauge = meter.create_observable_gauge(
    "observable_gauge",
    [observable_gauge_func],
)

while 1:
    time.sleep(1)
