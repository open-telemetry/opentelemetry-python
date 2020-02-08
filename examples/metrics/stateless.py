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
# Pass in false for non-stateful batcher. Indicates the batcher computes
# checkpoints which describe the updates of a single collection period (deltas)
batcher = UngroupedBatcher(False)
# Meter is responsible for creating and recording metrics
metrics.set_preferred_meter_implementation(lambda _: Meter(batcher))
meter = metrics.meter()
# exporter to export metrics to the console
exporter = ConsoleMetricsExporter()
# controller collects metrics created from meter and exports it via the
# exporter every interval
controller = PushController(meter, exporter, 5)

counter = meter.create_metric(
    "requests",
    "number of requests",
    "requests",
    int,
    Counter,
    ("environment",),
)

# Labelsets are used to identify key-values that are associated with a specific
# metric that you want to record. These are useful for pre-aggregation and can
# be used to store custom dimensions pertaining to a metric
label_set = meter.get_label_set({"environment": "staging"})

counter.add(25, label_set)
# We sleep for 5 seconds, exported value should be 25
time.sleep(5)

counter.add(50, label_set)
# exported value should be 50 due to non-stateful batcher
time.sleep(20)

# Following exported values would be 0
