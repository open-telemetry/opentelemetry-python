# Copyright 2019, OpenCensus Authors
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

from opentelemetry import metrics
from opentelemetry.ext.azure_monitor import AzureMonitorMetricsExporter
from opentelemetry.sdk.metrics import Counter, Meter
from opentelemetry.sdk.metrics.export import ConsoleMetricsExporter

metrics.set_preferred_meter_implementation(lambda T: Meter())
meter = metrics.meter()
exporter = AzureMonitorMetricsExporter()
console_exporter = ConsoleMetricsExporter()

counter = meter.create_metric(
    "available memory",
    "available memory",
    "bytes",
    int,
    Counter,
    ("environment",),
)
label_values = ("staging",)
counter_handle = counter.get_handle(label_values)
counter_handle.add(100)

console_exporter.export([(counter, label_values)])
exporter.export([(counter, label_values)])
