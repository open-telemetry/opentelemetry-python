# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import grpc

from opentelemetry._proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
    ExportTraceServiceResponse,
)


class TraceServiceStub:
    def __init__(self, channel):
        self.Export = channel.unary_unary(
            "/opentelemetry.proto.collector.trace.v1.TraceService/Export",
            request_serializer=ExportTraceServiceRequest.SerializeToString,
            response_deserializer=ExportTraceServiceResponse.FromString,
        )


class TraceServiceServicer:
    def Export(self, request, context):
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")


def add_TraceServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {
        "Export": grpc.unary_unary_rpc_method_handler(
            servicer.Export,
            request_deserializer=ExportTraceServiceRequest.FromString,
            response_serializer=ExportTraceServiceResponse.SerializeToString,
        ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
        "opentelemetry.proto.collector.trace.v1.TraceService", rpc_method_handlers
    )
    server.add_generic_rpc_handlers((generic_handler,))
