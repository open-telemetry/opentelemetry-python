# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

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
