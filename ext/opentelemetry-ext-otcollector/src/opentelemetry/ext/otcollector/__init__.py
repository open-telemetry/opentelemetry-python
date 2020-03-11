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

"""
This library allows to export data to `OpenTelemetry Collector <https://github.com/open-telemetry/opentelemetry-collector/>`_ , currently using OpenCensus receiver in Collector side.

Traces Usage
------------

The **OpenTelemetry Collector Exporter** allows to export `OpenTelemetry`_ traces to `OpenTelemetry Collector`_.

.. code:: python

    from opentelemetry import trace
    from opentelemetry.ext.otcollector.trace_exporter  import CollectorSpanExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchExportSpanProcessor


    # create a CollectorSpanExporter
    collector_exporter = CollectorSpanExporter(
        # optional:
        # endpoint="myCollectorUrl:55678",
        # service_name="test_service",
        # host_name="machine/container name",
    )

    # Create a BatchExportSpanProcessor and add the exporter to it
    span_processor = BatchExportSpanProcessor(collector_exporter)

    # Configure the tracer to use the collector exporter
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(span_processor)
    tracer = TracerProvider().get_tracer(__name__)

    with tracer.start_as_current_span("foo"):
        print("Hello world!")

Metrics Usage
-------------

The **OpenTelemetry Collector Exporter** allows to export `OpenTelemetry`_ metrics to `OpenTelemetry Collector`_.

.. code:: python

    from opentelemetry import metrics
    from opentelemetry.ext.otcollector.metrics_exporter import CollectorMetricsExporter
    from opentelemetry.sdk.metrics import Counter, MeterProvider
    from opentelemetry.sdk.metrics.export.controller import PushController


    # create a CollectorMetricsExporter
    collector_exporter = CollectorMetricsExporter(
        # optional:
        # endpoint="myCollectorUrl:55678",
        # service_name="test_service",
        # host_name="machine/container name",
    )

    # Meter is responsible for creating and recording metrics
    metrics.set_preferred_meter_provider_implementation(lambda _: MeterProvider())
    meter = metrics.get_meter(__name__)
    # controller collects metrics created from meter and exports it via the
    # exporter every interval
    controller = PushController(meter, collector_exporter, 5)
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
"""
