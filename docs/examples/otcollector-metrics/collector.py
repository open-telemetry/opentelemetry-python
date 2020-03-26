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
This example shows how to export metrics to the OT collector.
"""

from opentelemetry import metrics
from opentelemetry.ext.otcollector.metrics_exporter import (
    CollectorMetricsExporter,
)
from opentelemetry.sdk.metrics import Counter, MeterProvider
from opentelemetry.sdk.metrics.export.controller import PushController

exporter = CollectorMetricsExporter(
    service_name="basic-service", endpoint="localhost:55678"
)

metrics.set_meter_provider(MeterProvider())
meter = metrics.get_meter(__name__)
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

print("Metrics are available now at http://localhost:9090/graph")
input("Press any key to exit...")
