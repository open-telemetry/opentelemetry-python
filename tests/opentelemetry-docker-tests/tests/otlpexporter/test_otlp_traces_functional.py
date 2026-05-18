# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter as GRPCSpanExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter as HTTPSpanExporter,
)
from opentelemetry.sdk.trace.export import SpanExporter

from . import TracesExporterTestsBase


class HTTPProtobufTracesExporterTests(TracesExporterTestsBase):
    __test__ = True

    def build_exporter(self) -> SpanExporter:
        return HTTPSpanExporter(endpoint="http://localhost:4318/v1/traces")


class GrpcTracesExporterTests(TracesExporterTestsBase):
    __test__ = True

    def build_exporter(self) -> SpanExporter:
        return GRPCSpanExporter(insecure=True)
