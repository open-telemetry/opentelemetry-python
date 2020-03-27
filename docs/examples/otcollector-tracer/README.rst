OT Collector Tracer Exporter Example
====================================

This example shows how to export traces to the OT collector.

The source files of this example are available :scm_web:`here <docs/examples/otcollector-tracer/>`.

Installation
------------

.. code-block:: sh

    pip install opentelemetry-api
    pip install opentelemetry-sdk
    pip install opentelemetry-ext-otcollector

Run the Example
---------------

Before running the example, it's necessary to run the OpenTelemetry collector
and Jaeger.  The :scm_web:`docker <docs/examples/otcollector-tracer/docker/>`
folder contains the a docker-compose template with the configuration of those
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
- OTCollector_
- :doc:`../../api/trace`
- :doc:`../../ext/otcollector/otcollector`

.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/
.. _OTCollector: https://github.com/open-telemetry/opentelemetry-collector