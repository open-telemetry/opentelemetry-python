OpenCensus Shim
================

This example shows how to use the :doc:`opentelemetry-opencensus-shim
package <../../shim/opencensus_shim/opencensus_shim>`
to interact with libraries instrumented with
`opencensus-python <https://github.com/census-instrumentation/opencensus-python>`_.


The source files required to run this example are available :scm_web:`here <docs/examples/opencensus-shim/>`.

Installation
------------

Jaeger
******

Start Jaeger

.. code-block:: sh

    docker run --rm \
        -p 6831:6831/udp \
        -p 6832:6832/udp \
        -p 16686:16686 \
        jaegertracing/all-in-one:1.13 \
        --log-level=debug

Python Dependencies
*******************

Install the Python dependencies in :scm_raw_web:`requirements.txt <docs/examples/opencensus-shim/requirements.txt >`

.. code-block:: sh

    pip install -r requirements.txt


Alternatively, you can install the Python dependencies separately:

.. code-block:: sh

    pip install \
        opentelemetry-api \
        opentelemetry-sdk \
        opentelemetry-exporter-jaeger \
        opentelemetry-opencensus-shim


Run the Application
-------------------

.. TODO implement the example

Jaeger UI
*********

Open the Jaeger UI in your browser at
`<http://localhost:16686>`_ and view traces for the
"OpenCensus Shim Example" service.

Note that tags and logs (OpenCensus) and attributes and events (OpenTelemetry)
from both tracing systems appear in the exported trace.

Useful links
------------

- OpenTelemetry_
- :doc:`../../shim/opencensus_shim/opencensus_shim`

.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/
