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

from prometheus_client import start_http_server

from opentelemetry import metrics
from opentelemetry.ext.prometheus import PrometheusMetricsExporter
from opentelemetry.sdk.metrics import Counter, MeterProvider
from opentelemetry.sdk.metrics.export.controller import PushController

# Start Prometheus client
start_http_server(port=8000, addr="localhost")

# Meter is responsible for creating and recording metrics
metrics.set_preferred_meter_provider_implementation(lambda _: MeterProvider())
meter = metrics.get_meter(__name__)
# exporter to export metrics to Prometheus
prefix = "MyAppPrefix"
exporter = PrometheusMetricsExporter(prefix)
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
input("Press any key to exit...")
