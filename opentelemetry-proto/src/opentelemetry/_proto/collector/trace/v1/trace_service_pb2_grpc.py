# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry._proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
    ExportTraceServiceResponse,
)


class TraceServiceStub:
    def __init__(self, channel):
        self.Export = channel.unary_unary(
            '/opentelemetry.proto.collector.trace.v1.TraceService/Export',
            request_serializer=ExportTraceServiceRequest.SerializeToString,
            response_deserializer=ExportTraceServiceResponse.FromString,
        )
