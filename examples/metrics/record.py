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
It demonstrates the different ways you can record metrics via the meter.
"""
import time

from opentelemetry import metrics
from opentelemetry.sdk.metrics import Counter, MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricsExporter
from opentelemetry.sdk.metrics.export.controller import PushController

# The preferred tracer implementation must be set, as the opentelemetry-api
# defines the interface with a no-op implementation.
metrics.set_preferred_meter_provider_implementation(lambda _: MeterProvider())
# Meter is responsible for creating and recording metrics
meter = metrics.get_meter(__name__)
# exporter to export metrics to the console
exporter = ConsoleMetricsExporter()
# controller collects metrics created from meter and exports it via the
# exporter every interval
controller = PushController(meter=meter, exporter=exporter, interval=5)

# Example to show how to record using the meter
counter = meter.create_metric(
    name="requests",
    description="number of requests",
    unit="1",
    value_type=int,
    metric_type=Counter,
    label_keys=("environment",),
)

counter2 = meter.create_metric(
    name="clicks",
    description="number of clicks",
    unit="1",
    value_type=int,
    metric_type=Counter,
    label_keys=("environment",),
)

# Labelsets are used to identify key-values that are associated with a specific
# metric that you want to record. These are useful for pre-aggregation and can
# be used to store custom dimensions pertaining to a metric

# The meter takes a dictionary of key value pairs
label_set = meter.get_label_set({"environment": "staging"})

# Handle usage
# You can record metrics with metric handles. Handles are created by passing in
# a labelset. A handle is essentially metric data that corresponds to a specific
# set of labels. Therefore, getting a handle using the same set of labels will
# yield the same metric handle.
# Get a handle when you have to perform multiple operations using the same
# labelset
counter_handle = counter.get_handle(label_set)
for i in range(1000):
    counter_handle.add(i)

# You can release the handle we you are done
counter_handle.release()

# Direct metric usage
# You can record metrics directly using the metric instrument. You pass in a
# labelset that you would like to record for.
counter.add(25, label_set)

# Record batch usage
# You can record metrics in a batch by passing in a labelset and a sequence of
# (metric, value) pairs. The value would be recorded for each metric using the
# specified labelset for each.
meter.record_batch(label_set, [(counter, 50), (counter2, 70)])

time.sleep(10)
