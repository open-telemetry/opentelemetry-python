Prometheus Metrics Exporter Example
===================================

This example shows how to export metrics to Prometheus.

The source files of this example are available :scm_web:`here <docs/examples/prometheus/>`.

Installation
------------

.. code-block:: sh

    pip install opentelemetry-api
    pip install opentelemetry-sdk
    pip install opentelemetry-ext-prometheus

Run the Example
---------------

.. code-block:: sh

    python prometheus.py


The metrics are available at http://localhost:8000/.

Useful links
------------

- OpenTelemetry_
- :doc:`../../api/metrics`
- :doc:`OpenTelemetry Prometheus Exporter <../../ext/prometheus/prometheus>`

.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/
