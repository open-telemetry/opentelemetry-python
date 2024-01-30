import logging
import threading
import time
import unittest

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from opentelemetry.test.telemetry_sink import TelemetrySink, SpanFirehose

class TestBSPCorrectness(unittest.TestCase):
    """
    Note: running all of these tests takes ~1 minute.
    """

    def test_full_speed_drop_spans(self):
        # we expect this to drop spans as sleep is zero and total spans is greater than the queue size
        logging.disable(logging.WARN)  # suppress warnings about dropping spans
        do_test_bsp(4, 1024, 64, 0, self.assertNotEqual)
        logging.disable(logging.NOTSET)

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
    sink = TelemetrySink()
    sink.start()
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
    num_spans_received = sink.get_num_spans_received()
    assert_func(num_spans_per_firehose * num_threads, num_spans_received)
    sink.stop()
