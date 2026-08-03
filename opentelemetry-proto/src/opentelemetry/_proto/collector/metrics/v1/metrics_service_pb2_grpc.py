# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry._proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
    ExportMetricsServiceResponse,
)


class MetricsServiceStub:
    def __init__(self, channel):
        self.Export = channel.unary_unary(
            '/opentelemetry.proto.collector.metrics.v1.MetricsService/Export',
            request_serializer=ExportMetricsServiceRequest.SerializeToString,
            response_deserializer=ExportMetricsServiceResponse.FromString,
        )
