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
from opentelemetry.sdk.metrics import Measure, MeterProvider
from opentelemetry.sdk.metrics.export.aggregate import HistogramAggregation, SummaryAggregation
from opentelemetry.sdk.metrics.export import ConsoleMetricsExporter
from opentelemetry.sdk.metrics.export.controller import PushController
from opentelemetry.sdk.metrics.view import View

# Use the meter type provided by the SDK package
metrics.set_meter_provider(MeterProvider())
meter = metrics.get_meter(__name__)
exporter = ConsoleMetricsExporter()
controller = PushController(meter=meter, exporter=exporter, interval=5)

requests_size = meter.create_metric(
    name="requests_size",
    description="size of requests",
    unit="1",
    value_type=float,
    metric_type=Measure,
)

hist_view = View(
    requests_size,
    HistogramAggregation(config=[0.2,0.4,0.6,0.8,1.0]),
    label_keys=["environment"],
)

# summary_view = View(
#     requests_size,
#     SummaryAggregation(),
#     label_keys=["environment"],
# )

# Register the views to the view manager to use the views. Views MUST be
# registered before recording metrics. Metrics that are recorded without
# views defined for them will use a default for that type of metric
meter.register_view(hist_view)
# meter.register_view(summary_view)

requests_size.record(-0.1, {"environment": "staging", "os_type": "linux"})
requests_size.record(0.5, {"environment": "staging", "os_type": "linux"})
requests_size.record(2.5, {"environment": "staging", "os_type": "linux"})
requests_size.record(0.6, {"environment": "testing", "os_type": "linux"})

input("...\n")
