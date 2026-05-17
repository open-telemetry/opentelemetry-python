# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import unittest

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter as GRPCSpanExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter as HTTPSpanExporter,
)
from opentelemetry.sdk.trace.export import SpanExporter

from . import ExporterTracesFunctionalTests


class ProtoHTTPExporterTracesFunctionalTests(
    ExporterTracesFunctionalTests, unittest.TestCase
):
    def build_exporter(self) -> SpanExporter:
        return HTTPSpanExporter(endpoint="http://localhost:4318/v1/traces")


class ProtoGRPCExporterTracesFunctionalTests(
    ExporterTracesFunctionalTests, unittest.TestCase
):
    def build_exporter(self) -> SpanExporter:
        return GRPCSpanExporter(insecure=True)
