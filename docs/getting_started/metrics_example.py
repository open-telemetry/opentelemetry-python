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

# metrics.py
# This is still work in progress as the metrics SDK is being implemented

from typing import Iterable

from opentelemetry.metrics import (
    CallbackOptions,
    Observation,
    get_meter_provider,
    set_meter_provider,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)

exporter = ConsoleMetricExporter()
reader = PeriodicExportingMetricReader(exporter)
provider = MeterProvider(metric_readers=[reader])
set_meter_provider(provider)


def observable_counter_func(options: CallbackOptions) -> Iterable[Observation]:
    yield Observation(1, {})


def observable_up_down_counter_func(
    options: CallbackOptions,
) -> Iterable[Observation]:
    yield Observation(-10, {})


def observable_gauge_func(options: CallbackOptions) -> Iterable[Observation]:
    yield Observation(9, {})


meter = get_meter_provider().get_meter("getting-started", "0.1.2")

# Counter
counter = meter.create_counter("counter")
counter.add(1)

# Async Counter
observable_counter = meter.create_observable_counter(
    "observable_counter", [observable_counter_func]
)

# UpDownCounter
updown_counter = meter.create_up_down_counter("updown_counter")
updown_counter.add(1)
updown_counter.add(-5)

# Async UpDownCounter
observable_updown_counter = meter.create_observable_up_down_counter(
    "observable_updown_counter", [observable_up_down_counter_func]
)

# Histogram
histogram = meter.create_histogram("histogram")
histogram.record(99.9)

# Async Gauge
gauge = meter.create_observable_gauge("gauge", [observable_gauge_func])
