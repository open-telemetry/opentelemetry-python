Jaeger Exporter Example
=======================

This example shows how to use OpenTelemetry to send tracing data to Jaeger.

The source files of this example are available :scm_web:`here <docs/examples/jaeger_exporter/>`.

Installation
------------

.. code-block:: sh

    pip install opentelemetry-api
    pip install opentelemetry-sdk
    pip install opentelemetry-ext-jaeger

Run the Example
---------------

* Start Jaeger

.. code-block:: sh

    docker run --rm \
        -p 6831:6831/udp \
        -p 6832:6832/udp \
        -p 16686:16686 \
        jaegertracing/all-in-one:1.13 \
        --log-level=debug

* Run the example

.. code-block:: sh

    python jaeger_exporter.py

The traces will be available at http://localhost:16686/.

Useful links
------------

- OpenTelemetry_
- :doc:`../../api/trace`
- :doc:`../../ext/jaeger/jaeger`

.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/