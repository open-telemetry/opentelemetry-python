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
This example shows how the Observer metric instrument can be used to capture
asynchronous metrics data.
"""
import psutil

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider, ValueObserver
from opentelemetry.sdk.metrics.export import ConsoleMetricsExporter
from opentelemetry.sdk.metrics.export.batcher import UngroupedBatcher
from opentelemetry.sdk.metrics.export.controller import PushController

metrics.set_meter_provider(MeterProvider())
meter = metrics.get_meter(__name__)
exporter = ConsoleMetricsExporter()
controller = PushController(meter=meter, exporter=exporter, interval=2)


# Callback to gather cpu usage
def get_cpu_usage_callback(observer):
    for (number, percent) in enumerate(psutil.cpu_percent(percpu=True)):
        labels = {"cpu_number": str(number)}
        observer.observe(percent, labels)


meter.register_observer(
    callback=get_cpu_usage_callback,
    name="cpu_percent",
    description="per-cpu usage",
    unit="1",
    value_type=float,
    observer_type=ValueObserver,
    label_keys=("cpu_number",),
)


# Callback to gather RAM memory usage
def get_ram_usage_callback(observer):
    ram_percent = psutil.virtual_memory().percent
    observer.observe(ram_percent, {})


meter.register_observer(
    callback=get_ram_usage_callback,
    name="ram_percent",
    description="RAM memory usage",
    unit="1",
    value_type=float,
    observer_type=ValueObserver,
    label_keys=(),
)

input("Metrics will be printed soon. Press a key to finish...\n")
