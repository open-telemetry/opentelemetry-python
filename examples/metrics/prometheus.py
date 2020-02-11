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
This module serves as an example for a simple application using metrics
Examples show how to recording affects the collection of metrics to be exported
"""
import time

from opentelemetry import metrics
from opentelemetry.ext.prometheus import PrometheusMetricsExporter
from opentelemetry.sdk.metrics import Counter, Meter
from opentelemetry.sdk.metrics.export.controller import PushController

# Meter is responsible for creating and recording metrics
meter = Meter()
metrics.set_preferred_meter_implementation(meter)
# exporter to export metrics to Prometheus
port = 8000
address = "localhost"
prefix = "MyAppPrefix"
exporter = PrometheusMetricsExporter(port, address, prefix)
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

# Labelsets are used to identify key-values that are associated with a specific
# metric that you want to record. These are useful for pre-aggregation and can
# be used to store custom dimensions pertaining to a metric
label_set = meter.get_label_set({"environment": "staging"})

counter.add(25, label_set)
input("Press any key to exit...")
