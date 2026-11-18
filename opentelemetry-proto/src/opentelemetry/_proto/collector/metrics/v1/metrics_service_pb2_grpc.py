# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import grpc

from opentelemetry._proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
    ExportMetricsServiceResponse,
)


class MetricsServiceStub:
    def __init__(self, channel):
        self.Export = channel.unary_unary(
            "/opentelemetry.proto.collector.metrics.v1.MetricsService/Export",
            request_serializer=ExportMetricsServiceRequest.SerializeToString,
            response_deserializer=ExportMetricsServiceResponse.FromString,
        )


class MetricsServiceServicer:
    def Export(self, request, context):
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")


def add_MetricsServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {
        "Export": grpc.unary_unary_rpc_method_handler(
            servicer.Export,
            request_deserializer=ExportMetricsServiceRequest.FromString,
            response_serializer=ExportMetricsServiceResponse.SerializeToString,
        ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
        "opentelemetry.proto.collector.metrics.v1.MetricsService", rpc_method_handlers
    )
    server.add_generic_rpc_handlers((generic_handler,))
