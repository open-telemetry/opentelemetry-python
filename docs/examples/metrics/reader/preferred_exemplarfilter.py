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
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.metrics._internal.exemplar import (
    AlwaysOffExemplarFilter,
    AlwaysOnExemplarFilter,
    TraceBasedExemplarFilter,
)

# Create an ExemplarFilter instance (e.g., TraceBasedExemplarFilter)
exemplar_filter = TraceBasedExemplarFilter()

exporter = ConsoleMetricExporter()

reader = PeriodicExportingMetricReader(
    exporter,
    export_interval_millis=5_000,
)

# Set up the MeterProvider with the ExemplarFilter
provider = MeterProvider(
    metric_readers=[reader],
    exemplar_filter=exemplar_filter,  # Pass the ExemplarFilter to the MeterProvider
)
set_meter_provider(provider)

meter = get_meter_provider().get_meter("exemplar-filter-example", "0.1.2")
counter = meter.create_counter("my-counter")

for value in range(10):
    counter.add(value)
    time.sleep(2.0)