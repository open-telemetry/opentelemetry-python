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

# otcollector.py
import time

from opentelemetry import metrics, trace
from opentelemetry.ext.otcollector.metrics_exporter import (
    CollectorMetricsExporter,
)
from opentelemetry.ext.otcollector.trace_exporter import CollectorSpanExporter
from opentelemetry.sdk.metrics import Counter, MeterProvider
from opentelemetry.sdk.metrics.export.controller import PushController
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchExportSpanProcessor

# create a CollectorSpanExporter
span_exporter = CollectorSpanExporter(
    # optional:
    # endpoint="myCollectorUrl:55678",
    # service_name="test_service",
    # host_name="machine/container name",
)
tracer_provider = TracerProvider()
trace.set_tracer_provider(tracer_provider)
span_processor = BatchExportSpanProcessor(span_exporter)
tracer_provider.add_span_processor(span_processor)

# create a CollectorMetricsExporter
metric_exporter = CollectorMetricsExporter(
    # optional:
    # endpoint="myCollectorUrl:55678",
    # service_name="test_service",
    # host_name="machine/container name",
)

# Meter is responsible for creating and recording metrics
metrics.set_meter_provider(MeterProvider())
meter = metrics.get_meter(__name__)
# controller collects metrics created from meter and exports it via the
# exporter every interval
controller = PushController(meter, metric_exporter, 5)

# Configure the tracer to use the collector exporter
tracer = trace.get_tracer_provider().get_tracer(__name__)

with tracer.start_as_current_span("foo"):
    print("Hello world!")

requests_counter = meter.create_metric(
    name="requests",
    description="number of requests",
    unit="1",
    value_type=int,
    metric_type=Counter,
    label_keys=("environment",),
)
# Labels are used to identify key-values that are associated with a specific
# metric that you want to record. These are useful for pre-aggregation and can
# be used to store custom dimensions pertaining to a metric
labels = {"environment": "staging"}
requests_counter.add(25, labels)
time.sleep(10)  # give push_controller time to push metrics
