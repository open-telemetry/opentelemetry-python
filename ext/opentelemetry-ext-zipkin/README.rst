OpenTelemetry Zipkin Exporter
=============================

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-ext-zipkin.svg
   :target: https://pypi.org/project/opentelemetry-ext-zipkin/

This library allows to export tracing data to `Zipkin <https://zipkin.io/>`_.

Installation
------------

::

     pip install opentelemetry-ext-zipkin


Usage
-----

The **OpenTelemetry Zipkin Exporter** allows to export `OpenTelemetry`_ traces to `Zipkin`_.
This exporter always send traces to the configured Zipkin collector using HTTP.


.. _Zipkin: https://zipkin.io/
.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/

.. code:: python

    from opentelemetry import trace
    from opentelemetry.ext import zipkin
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchExportSpanProcessor

    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)

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
    trace.tracer_provider().add_span_processor(span_processor)

    with tracer.start_as_current_span("foo"):
        print("Hello world!")

The `examples <./examples>`_ folder contains more elaborated examples.

References
----------

* `Zipkin <https://zipkin.io/>`_
* `OpenTelemetry Project <https://opentelemetry.io/>`_
