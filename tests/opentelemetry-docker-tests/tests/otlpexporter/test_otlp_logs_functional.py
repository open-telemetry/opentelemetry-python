# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
    OTLPLogExporter as GRPCLogExporter,
)
from opentelemetry.exporter.otlp.proto.http._log_exporter import (
    OTLPLogExporter as HTTPLogExporter,
)
from opentelemetry.sdk._logs.export import LogRecordExporter

from . import LogsExporterTestsBase


class HTTPProtobufLogsExporterTests(LogsExporterTestsBase):
    __test__ = True

    def build_exporter(self) -> LogRecordExporter:
        return HTTPLogExporter(endpoint="http://localhost:4318/v1/logs")


class GrpcLogsExporterTests(LogsExporterTestsBase):
    __test__ = True

    def build_exporter(self) -> LogRecordExporter:
        return GRPCLogExporter(insecure=True)
