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
This example shows how to export metricsto prometheus.
"""

from prometheus_client import start_http_server

from opentelemetry import metrics
from opentelemetry.ext.prometheus import PrometheusMetricsExporter
from opentelemetry.sdk.metrics import Counter, Measure, MeterProvider
from opentelemetry.sdk.metrics.export.controller import PushController

# Start Prometheus client
start_http_server(port=8000, addr="localhost")

metrics.set_preferred_meter_provider_implementation(lambda _: MeterProvider())
meter = metrics.get_meter(__name__)

exporter = PrometheusMetricsExporter(prefix="MyAppPrefix")
controller = PushController(meter, exporter, 5)

requests_counter = meter.create_metric(
    name="requests",
    description="number of requests",
    unit="1",
    value_type=int,
    metric_type=Counter,
    label_keys=("environment",),
)

staging_label_set = meter.get_label_set({"environment": "staging"})
requests_counter.add(25, staging_label_set)

print("Metrics are available now at http://localhost:8000/")
input("Press any key to exit...")
