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
#
"""
This module serves as an example for a simple application using metrics.

It shows:
- How to configure a meter passing a sateful or stateless.
- How to configure an exporter and how to create a controller.
- How to create some metrics intruments and how to capture data with them.
"""
import sys
import time

from opentelemetry import metrics
from opentelemetry.sdk.metrics import Counter, MeterProvider, ValueRecorder
from opentelemetry.sdk.metrics.export import ConsoleMetricsExporter
from opentelemetry.sdk.metrics.export.controller import PushController

print(
    "Starting example, values will be printed to the console every 5 seconds."
)

# Stateful determines whether how metrics are collected: if true, metrics
# accumulate over the process lifetime. If false, metrics are reset at the
# beginning of each collection interval.
stateful = True

# Exporter to export metrics to the console
exporter = ConsoleMetricsExporter()

metrics.set_meter_provider(
    MeterProvider(
        exporter=exporter,
        interval=5,
        stateful=stateful
    )
)
# The Meter is responsible for creating and recording metrics. Each meter has a
# unique name, which we set as the module's name here.
meter = metrics.get_meter(__name__)

# Metric instruments allow to capture measurements
requests_counter = meter.create_metric(
    name="requests",
    description="number of requests",
    unit="1",
    value_type=int,
    metric_type=Counter,
    label_keys=("environment",),
)

requests_size = meter.create_metric(
    name="requests_size",
    description="size of requests",
    unit="1",
    value_type=int,
    metric_type=ValueRecorder,
    label_keys=("environment",),
)

# Labels are used to identify key-values that are associated with a specific
# metric that you want to record. These are useful for pre-aggregation and can
# be used to store custom dimensions pertaining to a metric
staging_labels = {"environment": "staging"}
testing_labels = {"environment": "testing"}

# Update the metric instruments using the direct calling convention
requests_counter.add(25, staging_labels)
requests_size.record(100, staging_labels)
time.sleep(5)

requests_counter.add(50, staging_labels)
requests_size.record(5000, staging_labels)
time.sleep(5)

requests_counter.add(35, testing_labels)
requests_size.record(2, testing_labels)
time.sleep(5)
