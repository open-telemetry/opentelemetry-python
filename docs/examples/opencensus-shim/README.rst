OpenCensus Shim
================

These examples show how to use the :doc:`opentelemetry-opencensus-shim
package <../../shim/opencensus_shim/opencensus_shim>`
to interact with libraries instrumented with
`opencensus-python <https://github.com/census-instrumentation/opencensus-python>`_.

The source files required to run these examples are available :scm_web:`here <docs/examples/opencensus-shim/>`.


OpenTelemetry OpenCensus Shim HTTP Example
============================================

This example demonstrates how to use the OpenTelemetry OpenCensus Shim to bridge spans from OpenCensus to OpenTelemetry in a Flask application. 
The application is a simple Flask web server that integrates OpenCensus tracing and exports traces to the console using OpenTelemetry. The server includes an endpoint that makes an external HTTP request, which is traced using OpenCensus flask integration.
This is a link to the http.py file: docs/examples/opencensus-shim/http.py 



To install Python Dependencies:
 .. code-block:: bash
    pip install \ 
    Flask \
    requests \
    opencensus \
    opentelemetry-api \
    opentelemetry-sdk \
    opentelemetry-exporter-console \
    opencensus-ext-flask \
    opencensus-ext-requests \
    opentelemetry-shim-opencensus 

Running the Application
-----------------------

To run the Flask application, use the following command:

.. code-block:: bash

   python http.py

Navigate to `http://localhost:8080` to access the application. The traces will be output to the console.


OpenTelemetry OpenCensus Shim Full Example
===========================================

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
        opentelemetry-opencensus-shim \
        opentelemetry-instrumentation-sqlite3 \
        opencensus \
        opencensus-ext-flask \
        Flask


Run the Application
-------------------

Start the application in a terminal.

.. code-block:: sh

    flask --app app run -h 0.0.0.0

Point your browser to the address printed out (probably http://127.0.0.1:5000). Alternatively, just use curl to trigger a request:

.. code-block:: sh

    curl http://127.0.0.1:5000

Jaeger UI
*********

Open the Jaeger UI in your browser at `<http://localhost:16686>`_ and view traces for the
"opencensus-shim-example-flask" service. Click on a span named "span" in the scatter plot. You
will see a span tree with the following structure:

* ``span``
    * ``query movies from db``
        * ``SELECT``
    * ``build response html``

The root span comes from OpenCensus Flask instrumentation. The children ``query movies from
db`` and ``build response html`` come from the manual instrumentation using OpenTelemetry's
:meth:`opentelemetry.trace.Tracer.start_as_current_span`. Finally, the ``SELECT`` span is
created by OpenTelemetry's SQLite3 instrumentation. Everything is exported to Jaeger using the
OpenTelemetry exporter.

Useful links
------------

- OpenTelemetry_
- :doc:`../../shim/opencensus_shim/opencensus_shim`

.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/
