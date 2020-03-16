OpenTelemetry Collector Exporter
================================

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-ext-otcollector.svg
   :target: https://pypi.org/project/opentelemetry-ext-otcollector/

This library allows to export data to `OpenTelemetry Collector`_ , currently using OpenCensus receiver in Collector side.

Installation
------------

::

     pip install opentelemetry-ext-otcollector


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


References
----------

* `OpenTelemetry Collector <https://github.com/open-telemetry/opentelemetry-collector/>`_
* `OpenTelemetry <https://opentelemetry.io/>`_
