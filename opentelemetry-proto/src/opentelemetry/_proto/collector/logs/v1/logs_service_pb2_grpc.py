# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import grpc

from opentelemetry._proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceRequest,
    ExportLogsServiceResponse,
)


class LogsServiceStub:
    def __init__(self, channel):
        self.Export = channel.unary_unary(
            "/opentelemetry.proto.collector.logs.v1.LogsService/Export",
            request_serializer=ExportLogsServiceRequest.SerializeToString,
            response_deserializer=ExportLogsServiceResponse.FromString,
        )


class LogsServiceServicer:
    def Export(self, request, context):
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")


def add_LogsServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {
        "Export": grpc.unary_unary_rpc_method_handler(
            servicer.Export,
            request_deserializer=ExportLogsServiceRequest.FromString,
            response_serializer=ExportLogsServiceResponse.SerializeToString,
        ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
        "opentelemetry.proto.collector.logs.v1.LogsService", rpc_method_handlers
    )
    server.add_generic_rpc_handlers((generic_handler,))
