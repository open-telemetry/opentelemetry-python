# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""
This library allows exporting OpenTelemetry telemetry to an OTLP collector
using the OTLP JSON over HTTP wire format.

Usage
-----

The **OTLP JSON HTTP Exporter** exports `OpenTelemetry`_ traces, metrics,
and logs to an `OTLP`_ collector via HTTP, using OTLP JSON encoding instead
of protobuf.

Three exporters are provided:

- :class:`~opentelemetry.exporter.otlp.json.http.trace_exporter.OTLPSpanExporter` - traces
- :class:`~opentelemetry.exporter.otlp.json.http.metric_exporter.OTLPMetricExporter` - metrics
- :class:`~opentelemetry.exporter.otlp.json.http._log_exporter.OTLPLogExporter` - logs

You can configure each exporter with the following environment variables,
using the appropriate per-signal prefix (``TRACES``, ``METRICS``, or
``LOGS``) or the generic variant that applies to all three:

- :envvar:`OTEL_EXPORTER_OTLP_ENDPOINT`
- :envvar:`OTEL_EXPORTER_OTLP_HEADERS`
- :envvar:`OTEL_EXPORTER_OTLP_TIMEOUT`
- :envvar:`OTEL_EXPORTER_OTLP_COMPRESSION`
- :envvar:`OTEL_EXPORTER_OTLP_CERTIFICATE`
- :envvar:`OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE`
- :envvar:`OTEL_EXPORTER_OTLP_CLIENT_KEY`

The metric exporter also supports the following environment variables:

- :envvar:`OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE`
- :envvar:`OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION`

.. _OTLP: https://github.com/open-telemetry/opentelemetry-collector/
.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/

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

API
---
"""

from opentelemetry.exporter.otlp.json.http.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.exporter.otlp.json.http.trace_exporter import (
    OTLPSpanExporter,
)

__all__ = [
    "OTLPMetricExporter",
    "OTLPSpanExporter",
]
