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

import time

from opentelemetry.metrics import get_meter_provider, set_meter_provider
from opentelemetry.sdk.metrics import Counter, MeterProvider
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)

# Use console exporter for the example
exporter = ConsoleMetricExporter()

temporality_cumulative = {Counter: AggregationTemporality.CUMULATIVE}
temporality_delta = {Counter: AggregationTemporality.DELTA}
# Create a metric reader with cumulative preferred temporality
reader = PeriodicExportingMetricReader(
    exporter,
    preferred_temporality=temporality_cumulative,
    export_interval_millis=5_000,
)
# Create a metric reader with delta preferred temporality
reader2 = PeriodicExportingMetricReader(
    exporter,
    preferred_temporality=temporality_delta,
    export_interval_millis=5_000,
)
provider = MeterProvider(metric_readers=[reader, reader2])
set_meter_provider(provider)

meter = get_meter_provider().get_meter("preferred-temporality", "0.1.2")

counter = meter.create_counter("my-counter")

for x in range(10):
    counter.add(x)
    time.sleep(5.0)
