# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

from opentelemetry.proto.collector.logs.v1 import logs_service_pb2 as opentelemetry_dot_proto_dot_collector_dot_logs_dot_v1_dot_logs__service__pb2


class LogsServiceStub:
    """Service that can be used to push logs between one Application instrumented with
    OpenTelemetry and an collector, or between an collector and a central collector (in this
    case logs are sent/received to/from multiple Applications).
    """

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.Export = channel.unary_unary(
                '/opentelemetry.proto.collector.logs.v1.LogsService/Export',
                request_serializer=opentelemetry_dot_proto_dot_collector_dot_logs_dot_v1_dot_logs__service__pb2.ExportLogsServiceRequest.SerializeToString,
                response_deserializer=opentelemetry_dot_proto_dot_collector_dot_logs_dot_v1_dot_logs__service__pb2.ExportLogsServiceResponse.FromString,
                )


class LogsServiceServicer:
    """Service that can be used to push logs between one Application instrumented with
    OpenTelemetry and an collector, or between an collector and a central collector (in this
    case logs are sent/received to/from multiple Applications).
    """

    def Export(self, request, context):
        """For performance reasons, it is recommended to keep this RPC
        alive for the entire life of the application.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_LogsServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'Export': grpc.unary_unary_rpc_method_handler(
                    servicer.Export,
                    request_deserializer=opentelemetry_dot_proto_dot_collector_dot_logs_dot_v1_dot_logs__service__pb2.ExportLogsServiceRequest.FromString,
                    response_serializer=opentelemetry_dot_proto_dot_collector_dot_logs_dot_v1_dot_logs__service__pb2.ExportLogsServiceResponse.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'opentelemetry.proto.collector.logs.v1.LogsService', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class LogsService:
    """Service that can be used to push logs between one Application instrumented with
    OpenTelemetry and an collector, or between an collector and a central collector (in this
    case logs are sent/received to/from multiple Applications).
    """

    @staticmethod
    def Export(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/opentelemetry.proto.collector.logs.v1.LogsService/Export',
            opentelemetry_dot_proto_dot_collector_dot_logs_dot_v1_dot_logs__service__pb2.ExportLogsServiceRequest.SerializeToString,
            opentelemetry_dot_proto_dot_collector_dot_logs_dot_v1_dot_logs__service__pb2.ExportLogsServiceResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)
