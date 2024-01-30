import time
from concurrent import futures

import grpc

from opentelemetry.proto.collector.logs.v1 import (
    logs_service_pb2,
    logs_service_pb2_grpc,
)
from opentelemetry.proto.collector.metrics.v1 import (
    metrics_service_pb2,
    metrics_service_pb2_grpc,
)
from opentelemetry.proto.collector.trace.v1 import (
    trace_service_pb2,
    trace_service_pb2_grpc,
)
from opentelemetry.sdk.trace import SpanProcessor, _Span
from opentelemetry.trace import SpanContext, TraceFlags


class SpanFirehose:
    """ Creates a sampled Span and exports it num_spans times, pausing sleep_sec each time. """
    def __init__(self, sp: SpanProcessor, num_spans: int, sleep_sec: float):
        self._sp = sp
        self._num_spans = num_spans
        self._sleep_sec = sleep_sec

    def run(self) -> float:
        start = time.time()
        span = _Span(
            name="test-span",
            context=SpanContext(
                1, 2, False, trace_flags=TraceFlags(TraceFlags.SAMPLED)
            ),
        )
        for _ in range(self._num_spans):
            time.sleep(self._sleep_sec)
            self._sp.on_end(span)
        return time.time() - start


class TelemetrySink:
    """
    A simple GRPC server that receives metrics, traces, and logs, for later inspection during testing.
    """
    def __init__(self):
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

        self.trace_servicer = TraceServiceServicer()
        trace_service_pb2_grpc.add_TraceServiceServicer_to_server(
            self.trace_servicer, self.server
        )

        metrics_servicer = MetricsServiceServicer()
        metrics_service_pb2_grpc.add_MetricsServiceServicer_to_server(
            metrics_servicer, self.server
        )

        logs_servicer = LogsServiceServicer()
        logs_service_pb2_grpc.add_LogsServiceServicer_to_server(
            logs_servicer, self.server
        )

        self.server.add_insecure_port("0.0.0.0:4317")

    def start(self):
        self.server.start()

    def stop(self):
        self.server.stop(0)

    def get_num_spans_received(self):
        return self.trace_servicer.get_num_spans()


class TraceServiceServicer(trace_service_pb2_grpc.TraceServiceServicer):
    def __init__(self):
        self.requests_received = []

    def Export(self, request, context):
        self.requests_received.append(request)
        return trace_service_pb2.ExportTraceServiceResponse()

    def get_num_spans(self):
        out = 0
        for req in self.requests_received:
            for rs in req.resource_spans:
                for ss in rs.scope_spans:
                    out += len(ss.spans)
        return out


class MetricsServiceServicer(metrics_service_pb2_grpc.MetricsServiceServicer):
    def __init__(self):
        self.requests_received = []

    def Export(self, request, context):
        self.requests_received.append(request)
        return metrics_service_pb2.ExportMetricsServiceResponse()


class LogsServiceServicer(logs_service_pb2_grpc.LogsServiceServicer):
    def __init__(self):
        self.requests_received = []

    def Export(self, request, context):
        self.requests_received.append(request)
        return logs_service_pb2.ExportLogsServiceResponse()
