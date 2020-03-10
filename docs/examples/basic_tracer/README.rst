Basic Tracer
============

This example shows how to use OpenTelemetry to instrument a Python application - e.g. a batch job.
It supports exporting spans either to the console or to Jaeger_.

The source files required to run this example are available :scm_web:`here <docs/examples/basic_tracer/>`.


Run the application
-------------------

Console
*******

* Run the sample

.. code-block:: sh

    $ python tracer.py

The output will be displayed at the console

::

    Hello world from OpenTelemetry Python!
    Span(name="baz", context=SpanContext(trace_id=0xf906f80f64d57c71ea8da4dfbbd2ddf2, span_id=0x5611c1407e06e4d7, trace_state={}), kind=SpanKind.INTERNAL, parent=Span(name="bar", context=SpanContext(trace_id=0xf906f80f64d57c71ea8da4dfbbd2ddf2, span_id=0x1b9db0e0cc1a3f60, trace_state={})), start_time=2019-11-07T21:26:45.934412Z, end_time=2019-11-07T21:26:45.934567Z)
    Span(name="bar", context=SpanContext(trace_id=0xf906f80f64d57c71ea8da4dfbbd2ddf2, span_id=0x1b9db0e0cc1a3f60, trace_state={}), kind=SpanKind.INTERNAL, parent=Span(name="foo", context=SpanContext(trace_id=0xf906f80f64d57c71ea8da4dfbbd2ddf2, span_id=0x1d5d87441ec2f410, trace_state={})), start_time=2019-11-07T21:26:45.934396Z, end_time=2019-11-07T21:26:45.934576Z)
    Span(name="foo", context=SpanContext(trace_id=0xf906f80f64d57c71ea8da4dfbbd2ddf2, span_id=0x1d5d87441ec2f410, trace_state={}), kind=SpanKind.INTERNAL, parent=None, start_time=2019-11-07T21:26:45.934369Z, end_time=2019-11-07T21:26:45.934580Z)


Jaeger
******

Setup `Jaeger Tracing <https://www.jaegertracing.io/docs/latest/getting-started/#all-in-one>`_.

* Run the sample

.. code-block:: sh

    $ pip install opentelemetry-ext-jaeger
    $ EXPORTER=jaeger python tracer.py


The traces should be available in the Jaeger UI at `<http://localhost:16686>`_


Collector
*********

* Start Collector

.. code-block:: sh

    $ pip install docker-compose
    $ cd docker
    $ docker-compose up

* Run the sample

.. code-block:: sh

    $ pip install opentelemetry-ext-otcollector
    $ EXPORTER=collector python tracer.py


Collector is configured to export to Jaeger, follow Jaeger UI instructions to find the traces.

Useful links
------------

- For more information on OpenTelemetry, visit OpenTelemetry_.
- For more information on tracing in Python, visit Jaeger_.

.. _Jaeger: https://www.jaegertracing.io/
.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/