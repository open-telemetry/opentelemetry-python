OpenTracing Shim Example
==========================

This example shows how to use the `opentelemetry-ext-opentracing-shim
package <https://github.com/open-telemetry/opentelemetry-python/tree/master/ext/opentelemetry-ext-opentracing-shim>`_
to interact with libraries instrumented with
`opentracing-python <https://github.com/opentracing/opentracing-python>`_.

The included ``rediscache`` library creates spans via the OpenTracing Redis
integration,
`redis_opentracing <https://github.com/opentracing-contrib/python-redis>`_.
Spans are exported via the Jaeger exporter, which is attached to the
OpenTelemetry tracer.


The source files required to run this example are available :scm_web:`here <docs/examples/opentracing/>`.

Installation
------------

Jaeger
******

Setup `Jaeger Tracing <https://www.jaegertracing.io/docs/latest/getting-started/#all-in-one>`_.

Redis
*****

Install Redis following the `instructions <https://redis.io/topics/quickstart>`_.

Make sure that the Redis server is running by executing this:

.. code-block:: sh

    $ redis-server


Python Dependencies
*******************

Install the Python dependencies in :scm_raw_web:`requirements.txt <docs/examples/opentracing>`

.. code-block:: sh

  $ pip install -r requirements.txt


Alternatively, you can install the Python dependencies separately:

.. code-block:: sh

  $ pip install \
    opentelemetry-api \
    opentelemetry-sdk \
    opentelemetry-ext-jaeger \
    opentelemetry-opentracing-shim \
    redis \
    redis_opentracing


Run the Application
-------------------

The example script calculates a few Fibonacci numbers and stores the results in
Redis. The script, the ``rediscache`` library, and the OpenTracing Redis
integration all contribute spans to the trace.

To run the script:

.. code-block:: sh

  $ python main.py


After running, you can view the generated trace in the Jaeger UI.

Jaeger UI
*********

Open the Jaeger UI in your browser at
`<http://localhost:16686>`_ and view traces for the
"OpenTracing Shim Example" service.

Each ``main.py`` run should generate a trace, and each trace should include
multiple spans that represent calls to Redis.

Note that tags and logs (OpenTracing) and attributes and events (OpenTelemetry)
from both tracing systems appear in the exported trace.

Useful links
------------

- For more information on OpenTelemetry, visit OpenTelemetry_.
- For more information on tracing in Python, visit Jaeger_.

.. _Jaeger: https://www.jaegertracing.io/
.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/
