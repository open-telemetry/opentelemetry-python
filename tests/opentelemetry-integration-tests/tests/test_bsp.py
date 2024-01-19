import threading
import time
import unittest
from concurrent import futures

import grpc

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
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
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import SpanContext, TraceFlags


class TestBSPCorrectness(unittest.TestCase):
    """
    Note: running all of these tests takes ~1 minute.
    """

    def test_full_speed_drop_spans(self):
        # we expect this to drop spans as sleep is zero and total spans is greater than the queue size
        do_test_bsp(4, 1024, 64, 0, self.assertNotEqual)

    def test_full_speed(self):
        # we expect this to not drop spans as max queue size is 2048 == 128 (num_spans_per_firehose) * 16 (num_threads)
        do_test_bsp(4, 128, 16, 0, self.assertEqual)

    def test_throttled(self):
        # simulate work with a 0.01 sleep time between sends
        do_test_bsp(4, 1024, 8, 0.01, self.assertEqual)

    def test_slow_enough_to_engage_timer(self):
        # send spans slowly enough that batch timeouts happen so we can test whether that works
        do_test_bsp(4, 12, 1, 1, self.assertEqual)


def do_test_bsp(
    max_batch_interval_sec,
    num_spans_per_firehose,
    num_threads,
    sleep_sec,
    assert_func,
):
    server = OTLPServer()
    server.start()
    bsp = BatchSpanProcessor(
        OTLPSpanExporter(),
        schedule_delay_millis=max_batch_interval_sec * 1e3,
    )
    sf = SpanFirehose(
        bsp, num_spans=num_spans_per_firehose, sleep_sec=sleep_sec
    )
    threads = []
    for _ in range(num_threads):
        thread = threading.Thread(target=sf.run)
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()
    # sleep long enough to ensure a timeout
    time.sleep(max_batch_interval_sec * 2)
    num_spans_received = server.get_num_spans_received()
    assert_func(num_spans_per_firehose * num_threads, num_spans_received)
    server.stop()


class SpanFirehose:
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


class OTLPServer:
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
