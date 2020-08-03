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
This example shows how to use the different modes to capture metrics.
It shows the usage of the direct, bound and batch calling conventions.
"""
import time

from opentelemetry import metrics
from opentelemetry.sdk.metrics import Counter, MeterProvider, ValueRecorder
from opentelemetry.sdk.metrics.export import ConsoleMetricsExporter

# Use the meter type provided by the SDK package
metrics.set_meter_provider(MeterProvider())
meter = metrics.get_meter(__name__)
metrics.get_meter_provider().start_pipeline(meter, ConsoleMetricsExporter(), 5)

requests_counter = meter.create_metric(
    name="requests",
    description="number of requests",
    unit="1",
    value_type=int,
    metric_type=Counter,
)

requests_size = meter.create_metric(
    name="requests_size",
    description="size of requests",
    unit="1",
    value_type=int,
    metric_type=ValueRecorder,
)

clicks_counter = meter.create_metric(
    name="clicks",
    description="number of clicks",
    unit="1",
    value_type=int,
    metric_type=Counter,
)

labels = {"environment": "staging"}

print("Updating using direct calling convention...")
# You can record metrics directly using the metric instrument. You pass in
# labels that you would like to record for.
requests_counter.add(25, labels)
time.sleep(10)

print("Updating using a bound instrument...")
# You can record metrics with bound metric instruments. Bound metric
# instruments are created by passing in labels. A bound metric instrument
# is essentially metric data that corresponds to a specific set of labels.
# Therefore, getting a bound metric instrument using the same set of labels
# will yield the same bound metric instrument.
bound_requests_counter = requests_counter.bind(labels)
bound_requests_counter.add(100)
time.sleep(5)

print("Updating using batch calling convention...")
# You can record metrics in a batch by passing in labels and a sequence of
# (metric, value) pairs. The value would be recorded for each metric using the
# specified labels for each.
meter.record_batch(labels, ((requests_counter, 50), (clicks_counter, 70)))
time.sleep(5)

input("...\n")
