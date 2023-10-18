import threading
import time
import unittest
from concurrent import futures
from os import environ

import grpc

import util
from opentelemetry.proto.collector.logs.v1 import logs_service_pb2, logs_service_pb2_grpc
from opentelemetry.proto.collector.metrics.v1 import metrics_service_pb2, metrics_service_pb2_grpc
from opentelemetry.proto.collector.trace.v1 import trace_service_pb2, trace_service_pb2_grpc
from opentelemetry.sdk.trace import SpanProcessor
from opentelemetry.sdk.trace.export.experimental.exporter import OTLPSpanExporter2
from opentelemetry.sdk.trace.export.experimental.processor import BatchSpanProcessor2
from opentelemetry.sdk.trace.export.experimental.timer import ThreadingTimer, PeriodicTimer, ThreadlessTimer


@unittest.skipUnless(environ.get('RUN_LONG_TESTS', '').lower() == 'true', 'Skipping, RUN_LONG_TESTS not set')
class TestIntegration(unittest.TestCase):

    def test_full_speed(self):
        server = OTLPServer()
        server.start()
        max_interval_sec = 4

        bsp = BatchSpanProcessor2(OTLPSpanExporter2())
        num_spans_per_firehose = 1_000
        sf = SpanFirehose(bsp, num_spans=num_spans_per_firehose, sleep_sec=0)

        threads = []
        num_threads = 128
        for _ in range(num_threads):
            thread = threading.Thread(target=sf.run)
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        time.sleep(max_interval_sec * 2)

        num_span_received = server.get_num_spans_received()
        self.assertEqual(num_spans_per_firehose * num_threads, num_span_received)
        server.stop()

    def test_slower(self):
        server = OTLPServer()
        server.start()
        max_interval_sec = 4
        bsp = BatchSpanProcessor2(OTLPSpanExporter2(), timer=ThreadingTimer(max_interval_sec))
        num_spans_per_firehose = 1000
        sf = SpanFirehose(bsp, num_spans=num_spans_per_firehose, sleep_sec=0.01)
        threads = []
        num_threads = 128
        for _ in range(num_threads):
            thread = threading.Thread(target=sf.run)
            thread.start()
            threads.append(thread)
        for thread in threads:
            thread.join()
        time.sleep(max_interval_sec * 2)
        num_span_received = server.get_num_spans_received()
        self.assertEqual(num_spans_per_firehose * num_threads, num_span_received)
        server.stop()

    def test_slow_enough_to_engage_timer(self):
        server = OTLPServer()
        server.start()
        bsp = BatchSpanProcessor2(OTLPSpanExporter2())
        num_spans = 10
        sf = SpanFirehose(bsp, num_spans=num_spans, sleep_sec=1)
        sf.run()
        time.sleep(5)
        num_span_received = server.get_num_spans_received()
        self.assertEqual(num_spans, num_span_received)
        server.stop()


class SpanFirehose:

    def __init__(self, sp: SpanProcessor, num_spans: int, sleep_sec: float):
        self._sp = sp
        self._num_spans = num_spans
        self._sleep_sec = sleep_sec

    def run(self) -> float:
        start = time.time()
        span = util.mk_span('test-span')
        for _ in range(self._num_spans):
            time.sleep(self._sleep_sec)
            self._sp.on_end(span)
        return time.time() - start


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
