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
This example shows how the Observer metric instrument can be used to capture
asynchronous metrics data.
"""
import psutil

from opentelemetry import metrics
from opentelemetry.sdk.metrics import LabelSet, Meter
from opentelemetry.sdk.metrics.export import ConsoleMetricsExporter
from opentelemetry.sdk.metrics.export.batcher import UngroupedBatcher
from opentelemetry.sdk.metrics.export.controller import PushController

# Configure a stateful batcher
batcher = UngroupedBatcher(True)

metrics.set_preferred_meter_implementation(lambda _: Meter(batcher))
meter = metrics.meter()

# Exporter to export metrics to the console
exporter = ConsoleMetricsExporter()

# Configure a push controller
controller = PushController(meter, exporter, 2)


# Callback to gather cpu usage
def get_cpu_usage_callback(observer):
    for (number, percent) in enumerate(psutil.cpu_percent(percpu=True)):
        label_set = meter.get_label_set({"cpu_number": str(number)})
        observer.observe(percent, label_set)


meter.register_observer(
    get_cpu_usage_callback,
    "cpu_percent",
    "per-cpu usage",
    1,
    float,
    ("cpu_number",),
)


# Callback to gather RAM memory usage
def get_ram_usage_callback(observer):
    ram_percent = psutil.virtual_memory().percent
    observer.observe(ram_percent, LabelSet())


meter.register_observer(
    get_ram_usage_callback, "ram_percent", "RAM memory usage", 1, float, (),
)

input("Press a key to finish...\n")
