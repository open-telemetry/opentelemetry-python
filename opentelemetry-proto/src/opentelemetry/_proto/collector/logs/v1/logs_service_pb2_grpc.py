# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry._proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceRequest,
    ExportLogsServiceResponse,
)


class LogsServiceStub:
    def __init__(self, channel):
        self.Export = channel.unary_unary(
            '/opentelemetry.proto.collector.logs.v1.LogsService/Export',
            request_serializer=ExportLogsServiceRequest.SerializeToString,
            response_deserializer=ExportLogsServiceResponse.FromString,
        )
