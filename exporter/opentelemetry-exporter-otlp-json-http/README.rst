OpenTelemetry Collector JSON over HTTP Exporter
==============================================

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-exporter-otlp-json-http.svg
   :target: https://pypi.org/project/opentelemetry-exporter-otlp-json-http/

This library allows to export data to the OpenTelemetry Collector using the OpenTelemetry Protocol using JSON over HTTP.

Installation
------------

::

     pip install opentelemetry-exporter-otlp-json-http


Usage
-----

The **OTLP JSON HTTP Exporter** allows to export `OpenTelemetry`_ traces, metrics, and logs to the
`OTLP`_ collector or any compatible receiver, using JSON encoding over HTTP.

.. _OTLP: https://github.com/open-telemetry/opentelemetry-collector/
.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/

.. code:: python

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.json.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    # Resource can be required for some backends, e.g. Jaeger
    resource = Resource(attributes={
        "service.name": "service"
    })

    trace.set_tracer_provider(TracerProvider(resource=resource))
    tracer = trace.get_tracer(__name__)

    otlp_exporter = OTLPSpanExporter()

    span_processor = BatchSpanProcessor(otlp_exporter)

    trace.get_tracer_provider().add_span_processor(span_processor)

    with tracer.start_as_current_span("foo"):
        print("Hello world!")

Environment Variables
--------------------

You can configure the exporter using environment variables:

- ``OTEL_EXPORTER_OTLP_ENDPOINT``: The base endpoint URL (for all signals)
- ``OTEL_EXPORTER_OTLP_TRACES_ENDPOINT``: The trace-specific endpoint URL (overrides the base endpoint)
- ``OTEL_EXPORTER_OTLP_METRICS_ENDPOINT``: The metrics-specific endpoint URL (overrides the base endpoint)
- ``OTEL_EXPORTER_OTLP_LOGS_ENDPOINT``: The logs-specific endpoint URL (overrides the base endpoint)
- ``OTEL_EXPORTER_OTLP_HEADERS``: The headers to include in all requests
- ``OTEL_EXPORTER_OTLP_TRACES_HEADERS``: The headers to include in trace requests
- ``OTEL_EXPORTER_OTLP_METRICS_HEADERS``: The headers to include in metrics requests
- ``OTEL_EXPORTER_OTLP_LOGS_HEADERS``: The headers to include in logs requests
- ``OTEL_EXPORTER_OTLP_TIMEOUT``: The timeout (in seconds) for all requests
- ``OTEL_EXPORTER_OTLP_TRACES_TIMEOUT``: The timeout (in seconds) for trace requests
- ``OTEL_EXPORTER_OTLP_METRICS_TIMEOUT``: The timeout (in seconds) for metrics requests
- ``OTEL_EXPORTER_OTLP_LOGS_TIMEOUT``: The timeout (in seconds) for logs requests
- ``OTEL_EXPORTER_OTLP_COMPRESSION``: The compression format to use for all requests
- ``OTEL_EXPORTER_OTLP_TRACES_COMPRESSION``: The compression format to use for trace requests
- ``OTEL_EXPORTER_OTLP_METRICS_COMPRESSION``: The compression format to use for metrics requests
- ``OTEL_EXPORTER_OTLP_LOGS_COMPRESSION``: The compression format to use for logs requests
- ``OTEL_EXPORTER_OTLP_CERTIFICATE``: Path to the CA certificate to verify server's identity
- ``OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE``: Path to the CA certificate for trace requests
- ``OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE``: Path to the CA certificate for metrics requests
- ``OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE``: Path to the CA certificate for logs requests
- ``OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE``: Path to client certificate
- ``OTEL_EXPORTER_OTLP_TRACES_CLIENT_CERTIFICATE``: Path to client certificate for trace requests
- ``OTEL_EXPORTER_OTLP_METRICS_CLIENT_CERTIFICATE``: Path to client certificate for metrics requests
- ``OTEL_EXPORTER_OTLP_LOGS_CLIENT_CERTIFICATE``: Path to client certificate for logs requests
- ``OTEL_EXPORTER_OTLP_CLIENT_KEY``: Path to client key
- ``OTEL_EXPORTER_OTLP_TRACES_CLIENT_KEY``: Path to client key for trace requests
- ``OTEL_EXPORTER_OTLP_METRICS_CLIENT_KEY``: Path to client key for metrics requests
- ``OTEL_EXPORTER_OTLP_LOGS_CLIENT_KEY``: Path to client key for logs requests

References
----------

* `OpenTelemetry <https://opentelemetry.io/>`_
* `OpenTelemetry Protocol Specification <https://github.com/open-telemetry/oteps/blob/main/text/0035-opentelemetry-protocol.md>`_