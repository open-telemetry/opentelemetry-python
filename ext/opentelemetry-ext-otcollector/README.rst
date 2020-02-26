OpenTelemetry Collector Exporter
=============================

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-ext-otcollector.svg
   :target: https://pypi.org/project/opentelemetry-ext-otcollector/

This library allows to export data to `OpenTelemetry Collector <https://github.com/open-telemetry/opentelemetry-collector/>`_.

Installation
------------

::

     pip install opentelemetry-ext-otcollector


Usage
-----

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

References
----------

* `OpenTelemetry Collector <https://github.com/open-telemetry/opentelemetry-collector/>`_
* `OpenTelemetry Project <https://opentelemetry.io/>`_
