# Copyright 2020, OpenTelemetry Authors
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
from opentelemetry.sdk.metrics import Counter, Measure, MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricsExporter
from opentelemetry.sdk.metrics.export.controller import PushController

stateful = True


def usage(argv):
    print("usage:")
    print("{} [mode]".format(argv[0]))
    print("mode: stateful (default) or stateless")


if len(sys.argv) >= 2:
    batcher_mode = sys.argv[1]
    if batcher_mode not in ("stateful", "stateless"):
        print("bad mode specified.")
        usage(sys.argv)
        sys.exit(1)
    stateful = batcher_mode == "stateful"

print(
    "Starting example, values will be printed to the console each 5 seconds."
)


# The Meter is responsible for creating and recording metrics. Each meter has a
# unique name, which we set as the module's name here. The second argument
# determines whether how metrics are collected: if true, metrics accumulate
# over the process lifetime. If false, metrics are reset at the beginning of
# each collection interval.
metrics.set_meter_provider(MeterProvider())
meter = metrics.get_meter(__name__, batcher_mode == "stateful")

# Exporter to export metrics to the console
exporter = ConsoleMetricsExporter()

# A PushController collects metrics created from meter and exports it via the
# exporter every interval
controller = PushController(meter=meter, exporter=exporter, interval=5)

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
    metric_type=Measure,
    label_keys=("environment",),
)

# Labelsets are used to identify key-values that are associated with a specific
# metric that you want to record. These are useful for pre-aggregation and can
# be used to store custom dimensions pertaining to a metric
staging_label_set = meter.get_label_set({"environment": "staging"})
testing_label_set = meter.get_label_set({"environment": "testing"})

# Update the metric instruments using the direct calling convention
requests_counter.add(25, staging_label_set)
requests_size.record(100, staging_label_set)
time.sleep(5)

requests_counter.add(50, staging_label_set)
requests_size.record(5000, staging_label_set)
time.sleep(5)

requests_counter.add(35, testing_label_set)
requests_size.record(2, testing_label_set)
time.sleep(5)
