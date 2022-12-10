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

import random
import time

from opentelemetry.metrics import get_meter_provider, set_meter_provider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.metrics.view import (
    DropAggregation,
    SumAggregation,
    View,
)

# disable_default_aggregation.
disable_default_aggregation = View(
    instrument_name="*", aggregation=DropAggregation()
)

exporter = ConsoleMetricExporter()

reader = PeriodicExportingMetricReader(exporter, export_interval_millis=1_000)
provider = MeterProvider(
    metric_readers=[
        reader,
    ],
    views=[
        disable_default_aggregation,
        View(instrument_name="mycounter", aggregation=SumAggregation()),
    ],
)
set_meter_provider(provider)

meter = get_meter_provider().get_meter(
    "view-disable-default-aggregation", "0.1.2"
)
# Create a view to configure aggregation specific for this counter.
my_counter = meter.create_counter("mycounter")

while 1:
    my_counter.add(random.randint(1, 10))
    time.sleep(random.random())
