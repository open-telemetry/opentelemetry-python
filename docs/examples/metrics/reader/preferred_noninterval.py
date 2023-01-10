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
from opentelemetry.sdk.metrics.view import LastValueAggregation

aggregation_last_value = {Counter: LastValueAggregation()}

# Use console exporter for the example
exporter = ConsoleMetricExporter(
    preferred_aggregation=aggregation_last_value,
)

# The PeriodicExportingMetricReader can also be configured with zero
# interval. This will disable reader from collecting metrics in
# set interval.
reader = PeriodicExportingMetricReader(
    exporter,
    export_interval_millis=0,
)

provider = MeterProvider(metric_readers=[reader])
set_meter_provider(provider)

meter = get_meter_provider().get_meter("preferred-noninterval", "0.1.2")
counter = meter.create_counter("my-counter")

# A counter normally would have an aggregation type of SumAggregation,
# in which it's value would be determined by a cumulative sum.
# In this example, the counter is configured with the LastValueAggregation,
# which will only hold the most recent value.
for x in range(10):
    counter.add(x)
    time.sleep(1.0)

# However, due to the intrerval set to zero, these will not get collected,
# unless the reader explicitly calls `collect` method.
reader.collect()

# And this is when the counter metric would get collected.

# Manual collection is helpful when you `do not` wish to rely on the
# reader's own interval based triggering of metric collection, but have your
# own triggering mechanism that could make the reader collect the metric.

# Warning: Setting a time interval of 0 allows you to export metric records
# manually. Calling collect() explicitly is not officially recommended by
# OpenTelemetry in conjunction with the PeriodicExportingMetricReader.
# Therefore, pelase use at your own discretion.
