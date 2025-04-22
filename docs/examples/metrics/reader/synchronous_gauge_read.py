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

import math
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

temperature = 0.0
humidity = 0.0


# Function called by the gauge to read the temperature
def read_temperature(options: CallbackOptions) -> Iterable[Observation]:
    global temperature
    yield Observation(value=temperature, attributes={"room": "living-room"})


# Function called by the gauge to read the humidity
def read_humidity(options: CallbackOptions) -> Iterable[Observation]:
    global humidity
    yield Observation(value=humidity, attributes={"room": "living-room"})


# Use console exporter for the example
exporter = ConsoleMetricExporter()

# The PeriodicExportingMetricReader If the time interval is set to math.inf
# the reader will not invoke periodic collection
reader = PeriodicExportingMetricReader(
    exporter,
    export_interval_millis=math.inf,
)

provider = MeterProvider(metric_readers=[reader])
set_meter_provider(provider)

meter = get_meter_provider().get_meter("synchronous_read", "0.1.2")

gauge = meter.create_observable_gauge(
    name="synchronous_gauge_temperature",
    description="Gauge value captured synchronously",
    callbacks=[read_temperature],
)

# Simulate synchronous reading of temperature
print("--- Simulating synchronous reading of temperature ---", flush=True)
temperature = 25.0
reader.collect()
# Note: The reader will only collect the last value before `collect` is called
print("--- Last value only ---", flush=True)
temperature = 30.0
temperature = 35.0
reader.collect()
# Invoking `collect` will read all measurements assigned to the reader
gauge2 = meter.create_observable_gauge(
    name="synchronous_gauge_humidity",
    description="Gauge value captured synchronously",
    callbacks=[read_humidity],
)
print("--- Multiple Measurements ---", flush=True)
temperature = 20.0
humidity = 50.0
reader.collect()
# Invoking `force_flush` will read all measurements assigned to the reader
print("--- Invoking force_flush ---", flush=True)
provider.force_flush()
