HTTP Example
============

This example shows how to use
`OpenTelemetryMiddleware <https://github.com/open-telemetry/opentelemetry-python/tree/master/ext/opentelemetry-ext-wsgi>`_
and `requests <https://github.com/open-telemetry/opentelemetry-python/tree/master/ext/opentelemetry-ext-http-requests>`_ integrations to instrument a client and a server in Python.
It supports exporting spans either to the console or to Jaeger_.

The source files required to run this example are available :scm_web:`here <docs/examples/http/>`.


Installation
------------

.. code-block:: sh

    $ pip install opentelemetry-api
    $ pip install opentelemetry-sdk
    $ pip install opentelemetry-ext-wsgi
    $ pip install opentelemetry-ext-http-requests


Run the application
-------------------

Console
*******

* Run the server

.. code-block:: sh

    $ python server.py


* Run the client from a different terminal

.. code-block:: sh

    $ python tracer_client.py


The output will be displayed at the console on the client side

::

    Span(name="/", context=SpanContext(trace_id=0x7c5c0d62031570f00fd106d968139300, span_id=0x3703fd889dcdeb2b, trace_state={}), kind=SpanKind.CLIENT, parent=None, start_time=2019-11-07T21:52:59.591634Z, end_time=2019-11-07T21:53:00.386014Z)


And on the server

::

    127.0.0.1 - - [07/Nov/2019 13:53:00] "GET / HTTP/1.1" 200 -
    Span(name="/wiki/Rabbit", context=SpanContext(trace_id=0x7c5c0d62031570f00fd106d968139300, span_id=0x4bf0be462b91d6ef, trace_state={}), kind=SpanKind.CLIENT, parent=Span(name="parent", context=SpanContext(trace_id=0x7c5c0d62031570f00fd106d968139300, span_id=0x68338643ccb2d53b, trace_state={})), start_time=2019-11-07T21:52:59.601597Z, end_time=2019-11-07T21:53:00.380491Z)
    Span(name="parent", context=SpanContext(trace_id=0x7c5c0d62031570f00fd106d968139300, span_id=0x68338643ccb2d53b, trace_state={}), kind=SpanKind.INTERNAL, parent=Span(name="/", context=SpanContext(trace_id=0x7c5c0d62031570f00fd106d968139300, span_id=0x36050ac596949bc1, trace_state={})), start_time=2019-11-07T21:52:59.601233Z, end_time=2019-11-07T21:53:00.384485Z)
    Span(name="/", context=SpanContext(trace_id=0x7c5c0d62031570f00fd106d968139300, span_id=0x36050ac596949bc1, trace_state={}), kind=SpanKind.SERVER, parent=SpanContext(trace_id=0x7c5c0d62031570f00fd106d968139300, span_id=0x3703fd889dcdeb2b, trace_state={}), start_time=2019-11-07T21:52:59.600816Z, end_time=2019-11-07T21:53:00.385322Z)


Jaeger
******

Setup `Jaeger Tracing <https://www.jaegertracing.io/docs/latest/getting-started/#all-in-one>`_.

* Run the server

.. code-block:: sh

    $ pip install opentelemetry-ext-jaeger
    $ EXPORTER=jaeger python server.py

* Run the client from a different terminal

.. code-block:: sh

    $ EXPORTER=jaeger python tracer_client.py

The traces should be available in the Jaeger UI at `<http://localhost:16686>`_

Useful links
------------

- For more information on OpenTelemetry, visit OpenTelemetry_.
- For more information on tracing in Python, visit Jaeger_.

.. _Jaeger: https://www.jaegertracing.io/
.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/