from opentelemetry.proto.collector.logs.v1 import (  # type: ignore
    logs_service_pb2,
    logs_service_pb2_grpc,
)
from opentelemetry.proto.collector.metrics.v1 import (  # type: ignore
    metrics_service_pb2,
    metrics_service_pb2_grpc,
)
from opentelemetry.proto.collector.trace.v1 import (  # type: ignore
    trace_service_pb2,
    trace_service_pb2_grpc,
)


class _LogsServiceServicer(logs_service_pb2_grpc.LogsServiceServicer):
    def __init__(self, handle_request):
        self.handle_request = handle_request

    def Export(self, request, context):  # noqa: N802
        self.handle_request(request, context)
        return logs_service_pb2.ExportLogsServiceResponse()


class _TraceServiceServicer(trace_service_pb2_grpc.TraceServiceServicer):
    def __init__(self, handle_request):
        self.handle_request = handle_request

    def Export(self, request, context):  # noqa: N802
        self.handle_request(request, context)
        return trace_service_pb2.ExportTraceServiceResponse()


class _MetricsServiceServicer(metrics_service_pb2_grpc.MetricsServiceServicer):
    def __init__(self, handle_request):
        self.handle_request = handle_request

    def Export(self, request, context):  # noqa: N802
        self.handle_request(request, context)
        return metrics_service_pb2.ExportMetricsServiceResponse()
