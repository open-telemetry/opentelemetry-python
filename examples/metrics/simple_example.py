# Copyright 2019, OpenTelemetry Authors
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
This module serves as an example for a simple application using metrics
It shows:
- How to configure a meter passing a sateful or stateless.
- How to configure an exporter and how to create a controller.
- How to create some metrics intruments and how to capture data with them.
"""
import sys
import time

from opentelemetry import metrics
from opentelemetry.sdk.metrics import Counter, Measure, MeterSource
from opentelemetry.sdk.metrics.export import ConsoleMetricsExporter
from opentelemetry.sdk.metrics.export.batcher import UngroupedBatcher
from opentelemetry.sdk.metrics.export.controller import PushController

batcher_mode = "stateful"


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

# Batcher used to collect all created metrics from meter ready for exporting
# Pass in True/False to indicate whether the batcher is stateful.
# True indicates the batcher computes checkpoints from over the process
# lifetime.
# False indicates the batcher computes checkpoints which describe the updates
# of a single collection period (deltas)
batcher = UngroupedBatcher(batcher_mode == "stateful")

# If a batcher is not provided, a default batcher is used
# Meter is responsible for creating and recording metrics
metrics.set_preferred_meter_source_implementation(lambda _: MeterSource())
meter = metrics.meter_source().get_meter(__name__, batcher)

# Exporter to export metrics to the console
exporter = ConsoleMetricsExporter()

# A PushController collects metrics created from meter and exports it via the
# exporter every interval
controller = PushController(meter, exporter, 5)

# Metric instruments allow to capture measurements
requests_counter = meter.create_metric(
    "requests", "number of requests", 1, int, Counter, ("environment",)
)

clicks_counter = meter.create_metric(
    "clicks", "number of clicks", 1, int, Counter, ("environment",)
)

requests_size = meter.create_metric(
    "requests_size", "size of requests", 1, int, Measure, ("environment",)
)

# Labelsets are used to identify key-values that are associated with a specific
# metric that you want to record. These are useful for pre-aggregation and can
# be used to store custom dimensions pertaining to a metric
staging_label_set = meter.get_label_set({"environment": "staging"})
testing_label_set = meter.get_label_set({"environment": "testing"})

# Update the metric instruments using the direct calling convention
requests_size.record(100, staging_label_set)
requests_counter.add(25, staging_label_set)
# Sleep for 5 seconds, exported value should be 25
time.sleep(5)

requests_size.record(5000, staging_label_set)
requests_counter.add(50, staging_label_set)
# Exported value should be 75
time.sleep(5)

requests_size.record(2, testing_label_set)
requests_counter.add(35, testing_label_set)
# There should be two exported values 75 and 35, one for each labelset
time.sleep(5)

clicks_counter.add(5, staging_label_set)
# There should be three exported values, labelsets can be reused for different
# metrics but will be recorded seperately, 75, 35 and 5

time.sleep(5)
