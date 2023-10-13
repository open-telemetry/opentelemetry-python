import time
import typing
import unittest
from os import environ

import grpc

import util
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.sdk.trace.export.experimental.client import RetryingGrpcClient, FakeGrpcClient
from opentelemetry.sdk.trace.export.experimental.exporter import OTLPSpanExporter2
from opentelemetry.sdk.trace.export.experimental.processor import BatchSpanProcessor2
from opentelemetry.sdk.trace.export.experimental.timer import PeriodicTimer, ThreadlessTimer


class TestBatchSpanProcessor(unittest.TestCase):

    def test_export_by_max_batch_size(self):
        exporter = FakeSpanExporter()
        timer = ThreadlessTimer()
        proc = BatchSpanProcessor2(exporter=exporter, timer=timer, max_batch_size=2)
        num_spans = 16
        for _ in range(num_spans):
            util.create_start_and_end_span('foo', proc)
        # we have a batch size of 2, and we've exported 16 spans, so we expect 8 batches
        self.assertEqual(8, exporter.count())

    def test_export_by_timer(self):
        exporter = FakeSpanExporter()
        timer = ThreadlessTimer()
        # we have a batch size of 32, which is larger than the 16 spans that we're planning on sending
        proc = BatchSpanProcessor2(exporter=exporter, timer=timer, max_batch_size=32)
        num_spans = 16
        for i in range(num_spans):
            util.create_start_and_end_span('foo', proc)
        self.assertEqual(0, exporter.count())
        # we want this test to be fast, so we don't sleep() -- instead we perform a manual poke()
        timer.poke()
        self.assertEqual(1, exporter.count())


class TestPeriodicTimer(unittest.TestCase):

    @unittest.skipUnless(environ.get('RUN_LONG_TESTS', '').lower() == 'true', 'Skipping long-running test')
    def test_x(self):
        t = PeriodicTimer(4)
        t.set_callback(lambda: print('callback!'))
        t.start()
        time.sleep(2)
        t.poke()
        time.sleep(2)
        t.stop()


class TestRetryingGrpcClient(unittest.TestCase):

    def test_success(self):
        fs = FakeSleeper()
        rt = RetryingGrpcClient(
            FakeGrpcClient([grpc.StatusCode.OK]),
            sleepfunc=fs.sleep
        )
        status_code = rt.send([(util.mk_readable_span())])
        self.assertEqual(grpc.StatusCode.OK, status_code)
        self.assertListEqual([], fs.get_sleeps())

    def test_retry_all_failed(self):
        fs = FakeSleeper()
        rt = RetryingGrpcClient(
            FakeGrpcClient([grpc.StatusCode.UNAVAILABLE]),
            sleepfunc=fs.sleep
        )
        status_code = rt.send([(util.mk_readable_span())])
        self.assertEqual(grpc.StatusCode.UNAVAILABLE, status_code)
        self.assertListEqual([0.5, 1.0, 2.0, 4.0], fs.get_sleeps())

    def test_retry_initial_failure_then_success(self):
        fs = FakeSleeper()
        rt = RetryingGrpcClient(
            FakeGrpcClient([grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.OK]),
            sleepfunc=fs.sleep
        )
        status_code = rt.send([(util.mk_readable_span())])
        self.assertEqual(grpc.StatusCode.OK, status_code)
        self.assertListEqual([0.5], fs.get_sleeps())


class TestOTLPSpanExporter(unittest.TestCase):

    def test_exporter(self):
        client = FakeGrpcClient()
        exporter = OTLPSpanExporter2(client=client)
        timer = ThreadlessTimer()
        proc = BatchSpanProcessor2(exporter, timer=timer, max_batch_size=128)
        span = util.mk_readable_span()
        num_spans = 100  # less than the batch size of 128
        for _ in range(num_spans):
            proc.on_end(span)
        timer.poke()
        client.num_batches()
        self.assertEqual(1, client.num_batches())
        self.assertEqual(num_spans, client.num_spans_in_batch(0))


class FakeSleeper:

    def __init__(self):
        self._sleeps = []

    def sleep(self, seconds):
        self._sleeps.append(seconds)

    def get_sleeps(self):
        return self._sleeps


class FakeSpanExporter(SpanExporter):

    def __init__(self):
        self._exported = []

    def export(self, spans: typing.Sequence[ReadableSpan]) -> SpanExportResult:
        self._exported.append(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        pass

    def get_exported(self):
        return self._exported

    def count(self):
        return len(self._exported)
