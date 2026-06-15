# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
    OTLPMetricExporter as GRPCMetricExporter,
)
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    OTLPMetricExporter as HTTPMetricExporter,
)
from opentelemetry.sdk.metrics.export import MetricExporter

from . import MetricsExporterTestsBase


class HTTPProtobufMetricsExporterTests(MetricsExporterTestsBase):
    __test__ = True

    def build_exporter(self) -> MetricExporter:
        return HTTPMetricExporter(endpoint="http://localhost:4318/v1/metrics")


class GrpcMetricsExporterTests(MetricsExporterTestsBase):
    __test__ = True

    def build_exporter(self) -> MetricExporter:
        return GRPCMetricExporter(insecure=True)
