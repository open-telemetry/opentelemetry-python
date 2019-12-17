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
"""

from opentelemetry import metrics
from opentelemetry.sdk.metrics import Counter, Meter
from opentelemetry.sdk.metrics.export import ConsoleMetricsExporter
from opentelemetry.sdk.metrics.export.batcher import UngroupedBatcher
from opentelemetry.sdk.metrics.export.controller import PushController

batcher = UngroupedBatcher(True)
metrics.set_preferred_meter_implementation(lambda _: Meter(batcher))
meter = metrics.meter()
counter = meter.create_metric(
    "available memory",
    "available memory",
    "bytes",
    int,
    Counter,
    ("environment",)
)

label_set = meter.get_label_set({"environment": "staging"})

# Direct metric usage
counter.add(label_set, 25)

# Handle usage
counter_handle = counter.get_handle(label_set)
counter_handle.add(100)

# Record batch usage
meter.record_batch(label_set, [(counter, 50)])

exporter = ConsoleMetricsExporter()
controller = PushController(meter, exporter, 5)
