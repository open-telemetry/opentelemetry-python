OpenTelemetry Prometheus Exporter
=================================

.. automodule:: opentelemetry.exporter.prometheus
    :members:
    :undoc-members:
    :show-inheritance:

Installation
------------

The OpenTelemetry Prometheus Exporter package is available on PyPI::

    pip install opentelemetry-exporter-prometheus

Usage
-----

The Prometheus exporter starts an HTTP server that collects metrics and serializes them to 
Prometheus text format on request::

    from prometheus_client import start_http_server

    from opentelemetry import metrics
    from opentelemetry.exporter.prometheus import PrometheusMetricReader
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource

    # Service name is required for most backends
    resource = Resource.create(attributes={
        SERVICE_NAME: "your-service-name"
    })

    # Start Prometheus client
    start_http_server(port=9464, addr="localhost")
    # Initialize PrometheusMetricReader which pulls metrics from the SDK
    # on-demand to respond to scrape requests
    reader = PrometheusMetricReader()
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)

Configuration
-------------

The following environment variables are supported:

* ``OTEL_EXPORTER_PROMETHEUS_HOST`` (default: "localhost"): The host to bind to
* ``OTEL_EXPORTER_PROMETHEUS_PORT`` (default: 9464): The port to bind to

Limitations
-----------

* No multiprocessing support: The Prometheus exporter is not designed to operate in multiprocessing environments (see `#3747 <https://github.com/open-telemetry/opentelemetry-python/issues/3747>`_).

References
----------

* `Prometheus <https://prometheus.io/>`_
* `OpenTelemetry Project <https://opentelemetry.io/>`_ 