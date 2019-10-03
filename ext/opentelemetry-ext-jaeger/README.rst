OpenTelemetry Jaeger Exporter
=============================

Installation
------------

::

     pip install opentelemetry-ext-jaeger


Usage
-----

The **OpenTelemetry Jaeger Exporter** allows to export `OpenTelemetry`_ traces to `Jaeger`_.
This exporter always send traces to the configured agent using Thrift compact protocol over UDP.
An optional collector can be configured, in this case Thrift binary protocol over HTTP is used.
gRPC is still not supported by this implementation.


.. _Jaeger: https://www.jaegertracing.io/
.. _OpenTelemetry: https://github.com/opentelemetry/opentelemetry-python/

.. code:: python

    from opentelemetry import trace
    from opentelemetry.sdk.trace import Tracer
    from opentelemetry.sdk.trace.export import BatchExportSpanProcessor
    from opentelemetry.ext import jaeger

    trace.set_preferred_tracer_implementation(lambda T: Tracer())
    tracer = trace.tracer()

    # create a JaegerSpanExporter
    jaeger_exporter = jaeger.JaegerSpanExporter(
        service_name='my-helloworld-service',
        # configure agent
        agent_host_name='localhost',
        agent_port=6831,
        # optional: configure also collector
        #collector_host_name='localhost',
        #collector_port=14268,
        #collector_endpoint='/api/traces?format=jaeger.thrift',
        #username=xxxx, # optional
        #password=xxxx, # optional
    )

    # Create a BatchExportSpanProcessor and add the exporter to it
    span_processor = BatchExportSpanProcessor(jaeger_exporter)

    # add to the tracer
    tracer.add_span_processor(span_processor)

    with tracer.start_span('foo'):
        print('Hello world!')

    # shutdown the span processor
    # TODO: this has to be improved so user doesn't need to call it manually
    span_processor.shutdown()

The `examples <./examples>`_ folder contains more elaborated examples.

References
----------

* `Jaeger <https://www.jaegertracing.io/>`_
* `OpenTelemetry Project <https://opentelemetry.io/>`_
