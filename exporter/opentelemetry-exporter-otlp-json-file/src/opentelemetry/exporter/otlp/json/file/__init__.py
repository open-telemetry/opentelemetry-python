# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

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
