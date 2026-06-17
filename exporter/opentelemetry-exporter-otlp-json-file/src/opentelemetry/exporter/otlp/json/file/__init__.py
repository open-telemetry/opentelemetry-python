# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""
This library allows exporting OpenTelemetry telemetry to a file or stream
in OTLP JSON (JSON Lines) format.

Usage
-----

The **OTLP JSON File Exporter** writes `OpenTelemetry`_ traces, metrics, and
logs as compact JSON Lines to a file, an arbitrary ``IO[str]`` stream or
``sys.stdout``.

Three exporters are provided:

- :class:`~opentelemetry.exporter.otlp.json.file.trace_exporter.FileSpanExporter` - traces
- :class:`~opentelemetry.exporter.otlp.json.file.metric_exporter.FileMetricExporter` - metrics
- :class:`~opentelemetry.exporter.otlp.json.file._log_exporter.FileLogExporter` - logs

Each exporter accepts a destination in one of three ways:

- ``path`` - a file path opened in append mode (UTF-8)
- ``stream`` - any ``IO[str]`` text stream
- neither - defaults to ``sys.stdout``

.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/

.. code:: python

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.json.file import FileSpanExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    # Write traces to a file (append mode, UTF-8)
    exporter = FileSpanExporter("/var/log/otel/traces.jsonl")

    # Alternatively, write to an explicit stream:
    # exporter = FileSpanExporter(stream=open("traces.jsonl", "a"))

    # Or write to sys.stdout (default when no path or stream is given):
    # exporter = FileSpanExporter()

    trace.set_tracer_provider(TracerProvider())
    trace.get_tracer_provider().add_span_processor(
        BatchSpanProcessor(exporter)
    )

    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("foo"):
        print("Hello world!")

The metric exporter supports the following environment variables:

- :envvar:`OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE`
- :envvar:`OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION`

API
---
"""

from opentelemetry.exporter.otlp.json.file.metric_exporter import (
    FileMetricExporter,
)
from opentelemetry.exporter.otlp.json.file.trace_exporter import (
    FileSpanExporter,
)

__all__ = [
    "FileMetricExporter",
    "FileSpanExporter",
]
