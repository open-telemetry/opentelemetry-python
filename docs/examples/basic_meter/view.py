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
from opentelemetry.sdk.metrics import Counter, Measure, MeterProvider
from opentelemetry.sdk.metrics.export.aggregate import CountAggregation
from opentelemetry.sdk.metrics.export import ConsoleMetricsExporter
from opentelemetry.sdk.metrics.export.controller import PushController
from opentelemetry.sdk.metrics.view import View, ViewConfig

# Use the meter type provided by the SDK package
metrics.set_meter_provider(MeterProvider())
meter = metrics.get_meter(__name__)
exporter = ConsoleMetricsExporter()
controller = PushController(meter=meter, exporter=exporter, interval=5)

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
    metric_type=Measure,
)

# Views are used to define an aggregation type and label keys to aggregate by
# for a given metric

# Two views with the same metric and aggregation type but different label keys
# With ViewConfig.LABEL_KEYS, all labels but the ones defined in label_keys are
# dropped from the aggregation
counter_view1 = View(
    requests_counter,
    CountAggregation(),
    label_keys=["environment"],
    config=ViewConfig.LABEL_KEYS
)
counter_view2 = View(
    requests_counter,
    CountAggregation(),
    label_keys=["os_type"],
    config=ViewConfig.LABEL_KEYS
)
# This view has ViewConfig set to UNGROUPED, meaning all recorded metrics take
# the labels directly without and consideration for label_keys
counter_view3 = View(
    requests_counter,
    CountAggregation(),
    label_keys=["environment"], # is not used due to ViewConfig.UNGROUPED
    config=ViewConfig.UNGROUPED
)

# Register the views to the view manager to use the views. Views MUST be
# registered before recording metrics. Metrics that are recorded without
# views defined for them will use a default for that type of metric
meter.register_view(counter_view1)
meter.register_view(counter_view2)
meter.register_view(counter_view3)

# The views will evaluate the labels passed into the record and aggregate upon
# the unique labels that are generated
# view1 labels will evaluate to {"environment": "staging"}
# view2 labels will evaluate to {"os_type": linux}
# view3 labels will evaluate to {"environment": "staging", "os_type": "linux"}
requests_counter.add(100, {"environment": "staging", "os_type": "linux"})

# Notice we did not create a view for requests_size, this will use the default
# SummaryAggregation for Measure metrics with UNGROUPED keys
requests_size.record(25, {"test": "value"})

input("...\n")
