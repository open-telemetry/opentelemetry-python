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
Examples show how to recording affects the collection of metrics to be exported
"""
import time

from opentelemetry import metrics
from opentelemetry.sdk.metrics import Counter, Meter
from opentelemetry.sdk.metrics.export import ConsoleMetricsExporter
from opentelemetry.sdk.metrics.export.batcher import UngroupedBatcher
from opentelemetry.sdk.metrics.export.controller import PushController

# Batcher used to collect all created metrics from meter ready for exporting
# Pass in true/false to indicate whether the batcher is stateful. True
# indicates the batcher computes checkpoints from over the process lifetime.
# False indicates the batcher computes checkpoints which describe the updates
# of a single collection period (deltas)
batcher = UngroupedBatcher(True)
# If a batcher is not provded, a default batcher is used
# Meter is responsible for creating and recording metrics
meter = Meter(batcher)
metrics.set_preferred_meter_implementation(meter)
# exporter to export metrics to the console
exporter = ConsoleMetricsExporter()
# controller collects metrics created from meter and exports it via the
# exporter every interval
controller = PushController(meter, exporter, 5)

counter = meter.create_metric(
    "available memory",
    "available memory",
    "bytes",
    int,
    Counter,
    ("environment",),
)

counter2 = meter.create_metric(
    "available memory2",
    "available memory2",
    "bytes2",
    int,
    Counter,
    ("environment",),
)

label_set = meter.get_label_set({"environment": "staging"})
label_set2 = meter.get_label_set({"environment": "testing"})

counter.add(25, label_set)
# We sleep for 5 seconds, exported value should be 25
time.sleep(5)

counter.add(50, label_set)
# exported value should be 75
time.sleep(5)

counter.add(35, label_set2)
# should be two exported values 75 and 35, one for each labelset
time.sleep(5)

counter2.add(5, label_set)
# should be three exported values, labelsets can be reused for different
# metrics but will be recorded seperately, 75, 35 and 5
time.sleep(5)
