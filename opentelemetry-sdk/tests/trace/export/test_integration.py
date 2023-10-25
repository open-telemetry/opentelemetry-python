import threading
import time
import unittest
from concurrent import futures
from os import environ

import grpc

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.proto.collector.logs.v1 import logs_service_pb2, logs_service_pb2_grpc
from opentelemetry.proto.collector.metrics.v1 import metrics_service_pb2, metrics_service_pb2_grpc
from opentelemetry.proto.collector.trace.v1 import trace_service_pb2, trace_service_pb2_grpc
from opentelemetry.sdk.trace import ReadableSpan, _Span
from opentelemetry.sdk.trace import SpanProcessor
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import SpanContext, TraceFlags


@unittest.skipUnless(environ.get('RUN_LONG_TESTS', '').lower() == 'true', 'Skipping, RUN_LONG_TESTS not set')
class TestBSPIntegration(unittest.TestCase):
    """
    These are longer-running tests (total ~1 minute) that start up a local python grpc server and send spans to
    it, comparing the number of received spans against how many were sent.
    """

    def test_full_speed(self):
        self.run_bsp_test(
            num_threads=128,
            max_interval_sec=4,
            num_spans_per_firehose=1000,
            firehose_sleep_sec=0,
        )

    def test_slower(self):
        self.run_bsp_test(
            num_threads=128,
            max_interval_sec=4,
            num_spans_per_firehose=1000,
            firehose_sleep_sec=0.01,
        )

    def test_slow_enough_to_engage_timer(self):
        self.run_bsp_test(
            num_threads=1,
            max_interval_sec=4,
            num_spans_per_firehose=10,
            firehose_sleep_sec=1,
        )

    def run_bsp_test(self, num_threads, max_interval_sec, num_spans_per_firehose, firehose_sleep_sec):
        server = OTLPServer()
        server.start()

        bsp = BatchSpanProcessor(OTLPSpanExporter(), schedule_delay_millis=max_interval_sec * 1e3)

        firehose = SpanFirehose(bsp, num_spans=num_spans_per_firehose, sleep_sec=firehose_sleep_sec)

        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=firehose.run)
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        time.sleep(max_interval_sec * 2)

        num_span_received = server.get_num_spans_received()
        self.assertEqual(num_spans_per_firehose * num_threads, num_span_received)
        server.stop()


class SpanFirehose:

    def __init__(self, sp: SpanProcessor, num_spans: int, sleep_sec: float):
        self._sp = sp
        self._num_spans = num_spans
        self._sleep_sec = sleep_sec

    def run(self) -> float:
        start = time.time()
        span = mk_span('test-span')
        for i in range(self._num_spans):
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


def mk_readable_span():
    ctx = SpanContext(0, 0, False)
    return ReadableSpan(context=ctx, attributes={})


def mk_spans(n):
    span = mk_span('foo')
    out = []
    for _ in range(n):
        out.append(span)
    return out


def create_start_and_end_span(name, span_processor):
    span = _Span(name, mk_ctx(), span_processor=span_processor)
    span.start()
    span.end()


def mk_span(name='foo'):
    return _Span(name=name, context=mk_ctx())


def mk_ctx():
    return SpanContext(1, 2, False, trace_flags=TraceFlags(TraceFlags.SAMPLED))
