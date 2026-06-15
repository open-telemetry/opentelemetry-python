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

Scope labels
------------

By default, the Prometheus exporter adds instrumentation scope information as
labels on every exported metric. These labels include ``otel_scope_name``,
``otel_scope_version``, and ``otel_scope_schema_url``. Instrumentation scope
attributes are exported with the ``otel_scope_`` prefix::

    from prometheus_client import start_http_server

    from opentelemetry import metrics
    from opentelemetry.exporter.prometheus import PrometheusMetricReader
    from opentelemetry.sdk.metrics import MeterProvider

    start_http_server(port=9464, addr="localhost")
    reader = PrometheusMetricReader()
    provider = MeterProvider(metric_readers=[reader])
    metrics.set_meter_provider(provider)

    meter = metrics.get_meter(
        "checkout",
        "1.2.3",
        schema_url="https://opentelemetry.io/schemas/1.21.0",
        attributes={"region": "us-east-1"},
    )
    counter = meter.create_counter("orders")
    counter.add(1, {"environment": "production"})

The exported metric includes labels such as
``otel_scope_name="checkout"``,
``otel_scope_version="1.2.3"``,
``otel_scope_schema_url="https://opentelemetry.io/schemas/1.21.0"``,
``otel_scope_region="us-east-1"``, and
``environment="production"``.

To omit instrumentation scope labels from exported metrics, set
``without_scope_info`` to ``True``::

    reader = PrometheusMetricReader(without_scope_info=True)

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
