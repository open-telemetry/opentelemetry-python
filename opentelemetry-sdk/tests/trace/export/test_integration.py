import time
import unittest
from concurrent import futures
from os import environ

import grpc

import util
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.proto.collector.logs.v1 import logs_service_pb2, logs_service_pb2_grpc
from opentelemetry.proto.collector.metrics.v1 import metrics_service_pb2, metrics_service_pb2_grpc
from opentelemetry.proto.collector.trace.v1 import trace_service_pb2, trace_service_pb2_grpc
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.export.experimental.exporter import OTLPSpanExporter2
from opentelemetry.sdk.trace.export.experimental.processor import BatchSpanProcessor2


@unittest.skipUnless(environ.get('RUN_LONG_TESTS', '').lower() == 'true', 'Skipping long-running test')
class TestIntegration(unittest.TestCase):

    def test_bsp2(self):
        server = OTLPServer()
        server.start()
        bsp = BatchSpanProcessor2(OTLPSpanExporter2())
        num_spans_sent = 10000
        start = time.time()
        span = util.mk_span('test-span')
        for i in range(num_spans_sent):
            bsp.on_end(span)
        end = time.time()
        elapsed = end - start
        print()
        print(f'new: elapsed: {elapsed}')
        bsp.force_flush()
        num_span_received = server.get_num_spans_received()
        self.assertEqual(num_spans_sent, num_span_received)
        server.stop()

    @unittest.SkipTest
    def test_bsp(self):
        server = OTLPServer()
        server.start()
        bsp = BatchSpanProcessor(OTLPSpanExporter())
        num_spans_sent = 10000
        start = time.time()
        span = util.mk_span('test-span')
        for i in range(num_spans_sent):
            bsp.on_end(span)
        end = time.time()
        elapsed = end - start
        print()
        print(f'old: elapsed: {elapsed}')
        bsp.force_flush()
        while num_spans_sent > server.get_num_spans_received():
            time.sleep(0.1)
        server.stop()


class OTLPServer:

    def __init__(self):
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

        self.trace_servicer = TraceServiceServicer()
        trace_service_pb2_grpc.add_TraceServiceServicer_to_server(self.trace_servicer, self.server)

        metrics_servicer = MetricsServiceServicer()
        metrics_service_pb2_grpc.add_MetricsServiceServicer_to_server(metrics_servicer, self.server)

        logs_servicer = LogsServiceServicer()
        logs_service_pb2_grpc.add_LogsServiceServicer_to_server(logs_servicer, self.server)

        self.server.add_insecure_port('0.0.0.0:4317')

    def start(self):
        self.server.start()

    def stop(self):
        self.server.stop(0)

    def get_num_spans_received(self):
        return self.trace_servicer.get_num_spans()


def serve_otel_grpc():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    trace_service_pb2_grpc.add_TraceServiceServicer_to_server(TraceServiceServicer(), server)
    metrics_service_pb2_grpc.add_MetricsServiceServicer_to_server(MetricsServiceServicer(), server)
    logs_service_pb2_grpc.add_LogsServiceServicer_to_server(LogsServiceServicer(), server)
    server.add_insecure_port('0.0.0.0:4317')
    server.start()
    return server


class LogsServiceServicer(logs_service_pb2_grpc.LogsServiceServicer):

    def __init__(self):
        self.requests_received = []

    def Export(self, request, context):
        self.requests_received.append(request)
        return logs_service_pb2.ExportLogsServiceResponse()


class TraceServiceServicer(trace_service_pb2_grpc.TraceServiceServicer):

    def __init__(self):
        self.requests_received = []

    def Export(self, request, context):
        self.requests_received.append(request)
        return trace_service_pb2.ExportTraceServiceResponse()

    def get_num_spans(self):
        out = 0
        for req in self.requests_received:
            out += len(req.resource_spans[0].scope_spans[0].spans)
        return out


class MetricsServiceServicer(metrics_service_pb2_grpc.MetricsServiceServicer):

    def __init__(self):
        self.requests_received = []

    def Export(self, request, context):
        self.requests_received.append(request)
        return metrics_service_pb2.ExportMetricsServiceResponse()
