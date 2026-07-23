OpenTelemetry Collector JSON over HTTP Exporter
================================================

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-exporter-otlp-json-http.svg
   :target: https://pypi.org/project/opentelemetry-exporter-otlp-json-http/

This library exports OpenTelemetry traces, metrics and logs using the
OpenTelemetry Protocol (OTLP) JSON encoding over HTTP. It can be used to
send data to any backend that accepts OTLP JSON such as the OpenTelemetry
Collector.

Installation
------------

::

     pip install opentelemetry-exporter-otlp-json-http


Usage
-----

.. code:: python

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.json.http import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create({
        "service.name": "service"
    })

    trace.set_tracer_provider(TracerProvider(resource=resource))
    tracer = trace.get_tracer(__name__)

    otlp_exporter = OTLPSpanExporter()

    span_processor = BatchSpanProcessor(otlp_exporter)

    trace.get_tracer_provider().add_span_processor(span_processor)

    with tracer.start_as_current_span("foo"):
        print("Hello world!")


References
----------

* `OpenTelemetry OTLP Exporters <https://opentelemetry-python.readthedocs.io/en/latest/exporter/otlp/otlp.html>`_
* `OpenTelemetry Collector <https://github.com/open-telemetry/opentelemetry-collector/>`_
* `OpenTelemetry <https://opentelemetry.io/>`_
* `OpenTelemetry Protocol Specification <https://github.com/open-telemetry/oteps/blob/main/text/0035-opentelemetry-protocol.md>`_
* `OTLP JSON Encoding Specification <https://opentelemetry.io/docs/specs/otlp/#json-protobuf-encoding>`_
