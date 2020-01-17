OpenTelemetry Prometheus Exporter
=============================

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-ext-prometheus.svg
   :target: https://pypi.org/project/opentelemetry-ext-prometheus/

This library allows to export metrics data to `Prometheus <https://prometheus.io/>`_.

Installation
------------

::

     pip install opentelemetry-ext-prometheus


Usage
-----

The **OpenTelemetry Prometheus Exporter** allows to export `OpenTelemetry`_ metrics to `Prometheus`_.


.. _Prometheus: https://prometheus.io/
.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/

.. code:: python

    from opentelemetry import trace
    from opentelemetry.ext import zipkin
    from opentelemetry.sdk.trace import TracerSource
    from opentelemetry.sdk.trace.export import BatchExportSpanProcessor

    trace.set_preferred_tracer_source_implementation(lambda T: TracerSource())
    tracer = trace.tracer_source().get_tracer(__name__)

    # create a ZipkinSpanExporter
    zipkin_exporter = zipkin.ZipkinSpanExporter(
        service_name="my-helloworld-service",
        # optional:
        # host_name="localhost",
        # port=9411,
        # endpoint="/api/v2/spans",
        # protocol="http",
        # ipv4="",
        # ipv6="",
        # retry=False,
    )

    # Create a BatchExportSpanProcessor and add the exporter to it
    span_processor = BatchExportSpanProcessor(zipkin_exporter)

    # add to the tracer
    trace.tracer_source().add_span_processor(span_processor)

    with tracer.start_as_current_span("foo"):
        print("Hello world!")


References
----------

* `Prometheus <https://prometheus.io/>`_
* `OpenTelemetry Project <https://opentelemetry.io/>`_
