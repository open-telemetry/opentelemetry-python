# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0


"""
This library allows to export tracing data to an OTLP collector.

Usage
-----

The **OTLP Span Exporter** allows to export `OpenTelemetry`_ traces to the
`OTLP`_ collector.

You can configure the exporter with the following environment variables:

- :envvar:`OTEL_EXPORTER_OTLP_TRACES_TIMEOUT`
- :envvar:`OTEL_EXPORTER_OTLP_TRACES_PROTOCOL`
- :envvar:`OTEL_EXPORTER_OTLP_TRACES_HEADERS`
- :envvar:`OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`
- :envvar:`OTEL_EXPORTER_OTLP_TRACES_COMPRESSION`
- :envvar:`OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE`
- :envvar:`OTEL_EXPORTER_OTLP_TIMEOUT`
- :envvar:`OTEL_EXPORTER_OTLP_PROTOCOL`
- :envvar:`OTEL_EXPORTER_OTLP_HEADERS`
- :envvar:`OTEL_EXPORTER_OTLP_ENDPOINT`
- :envvar:`OTEL_EXPORTER_OTLP_COMPRESSION`
- :envvar:`OTEL_EXPORTER_OTLP_CERTIFICATE`

.. _OTLP: https://github.com/open-telemetry/opentelemetry-collector/
.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/

.. code:: python

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    # Resource can be required for some backends, e.g. Jaeger
    # If resource wouldn't be set - traces wouldn't appears in Jaeger
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

API
---
"""

import enum

from .version import __version__

_OTLP_HTTP_HEADERS = {
    "Content-Type": "application/x-protobuf",
    "User-Agent": "OTel-OTLP-Exporter-Python/" + __version__,
}


class Compression(enum.Enum):
    NoCompression = "none"
    Deflate = "deflate"
    Gzip = "gzip"
