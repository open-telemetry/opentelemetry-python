OpenTelemetry Collector Tracer OpenCensus Exporter Example
==========================================================

This example shows how to use the OpenCensus Exporter to export traces to the
OpenTelemetry collector.

The source files of this example are available :scm_web:`here <docs/examples/opencensus-exporter-tracer/>`.

Installation
------------

.. code-block:: sh

    pip install opentelemetry-api
    pip install opentelemetry-sdk
    pip install opentelemetry-exporter-opencensus

Run the Example
---------------

Before running the example, it's necessary to run the OpenTelemetry collector
and Jaeger.  The :scm_web:`docker <docs/examples/opencensus-exporter-tracer/docker/>`
folder contains a ``docker-compose`` template with the configuration of those
services.

.. code-block:: sh

    pip install docker-compose
    cd docker
    docker-compose up


Now, the example can be executed:

.. code-block:: sh

    python collector.py


The traces are available in the Jaeger UI at http://localhost:16686/.

Useful links
------------

- OpenTelemetry_
- `OpenTelemetry Collector`_
- :doc:`../../api/trace`
- :doc:`../../exporter/opencensus/opencensus`

.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/
.. _OpenTelemetry Collector: https://github.com/open-telemetry/opentelemetry-collector
