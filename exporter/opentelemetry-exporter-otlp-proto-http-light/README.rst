OpenTelemetry OTLP Protobuf HTTP Exporter (Light)
=================================================

This package provides OTLP/HTTP exporters for traces, metrics, and logs using
only Python stdlib for HTTP transport (``http.client``), with no dependency on
``requests``.

It is a drop-in alternative to ``opentelemetry-exporter-otlp-proto-http`` for
environments where minimizing the dependency footprint or import-time memory
overhead is a priority.

Differences from the standard package
--------------------------------------

- **No ``requests`` dependency.** HTTP is handled by stdlib ``http.client``
  with persistent keep-alive connections managed internally.

- **No custom session support.** The standard package accepts a
  ``requests.Session`` parameter and supports the
  ``OTEL_PYTHON_EXPORTER_OTLP_HTTP_*_CREDENTIAL_PROVIDER`` environment
  variables, which load a credential-provider plugin that returns a
  pre-configured ``requests.Session`` (e.g. for GCP auth). Neither the session
  parameter nor the credential-provider env vars are supported by this package.
  Use the standard package if you need pluggable session-level authentication.

- **Import path differs.** Use ``opentelemetry.exporter.otlp.proto.http_light``
  instead of ``opentelemetry.exporter.otlp.proto.http``.

- **Entry-point keys differ.** Auto-configuration uses ``otlp_proto_http_light``
  instead of ``otlp_proto_http``.

Installation
------------

.. code-block:: sh

    pip install opentelemetry-exporter-otlp-proto-http-light

Usage
-----

.. code-block:: python

    from opentelemetry.exporter.otlp.proto.http_light.trace_exporter import OTLPSpanExporter
    from opentelemetry.exporter.otlp.proto.http_light._log_exporter import OTLPLogExporter
    from opentelemetry.exporter.otlp.proto.http_light.metric_exporter import OTLPMetricExporter
