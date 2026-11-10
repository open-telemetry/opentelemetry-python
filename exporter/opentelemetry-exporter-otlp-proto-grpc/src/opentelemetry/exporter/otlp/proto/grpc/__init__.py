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
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
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

    otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)

    span_processor = BatchSpanProcessor(otlp_exporter)

    trace.get_tracer_provider().add_span_processor(span_processor)

    with tracer.start_as_current_span("foo"):
        print("Hello world!")

API
---
"""

from logging import getLogger
from os import environ
from typing import overload

from .version import __version__

_logger = getLogger(__name__)

_USER_AGENT_HEADER_VALUE = "OTel-OTLP-Exporter-Python/" + __version__
_OTLP_GRPC_CHANNEL_OPTIONS = [
    # this will appear in the http User-Agent header
    ("grpc.primary_user_agent", _USER_AGENT_HEADER_VALUE)
]


@overload
def _timeout_from_env(*environ_keys: str, default: float) -> float: ...


@overload
def _timeout_from_env(*environ_keys: str, default: None = None) -> float | None: ...


def _timeout_from_env(*environ_keys: str, default: float | None = None) -> float | None:
    """Return the first environment variable in ``environ_keys`` holding a
    valid float, or ``default`` if none does.

    Unset or empty variables are skipped silently; variables with a
    non-numeric value are skipped with a warning.
    """
    for environ_key in environ_keys:
        value = environ.get(environ_key)
        if value is None or not value.strip():
            continue
        try:
            return float(value)
        except ValueError:
            _logger.warning(
                "Invalid value %r for environment variable %s, ignoring it.",
                value,
                environ_key,
            )
    return default
