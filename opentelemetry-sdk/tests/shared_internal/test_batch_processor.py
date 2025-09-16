# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint: disable=protected-access
import gc
import logging
import multiprocessing
import os
import threading
import time
import unittest
import weakref
from platform import system
from typing import Any
from unittest.mock import Mock

import pytest

from opentelemetry._logs import (
    LogRecord,
)
from opentelemetry.sdk._logs import (
    ReadWriteLogRecord,
)
from opentelemetry.sdk._logs.export import (
    BatchLogRecordProcessor,
)
from opentelemetry.sdk._shared_internal import (
    DuplicateFilter,
)
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.util.instrumentation import InstrumentationScope

EMPTY_LOG = ReadWriteLogRecord(
    log_record=LogRecord(),
    instrumentation_scope=InstrumentationScope("example", "example"),
)

BASIC_SPAN = ReadableSpan(
    "MySpan",
    instrumentation_scope=InstrumentationScope("example", "example"),
)

if system() != "Windows":
    multiprocessing.set_start_method("fork")


class MockExporterForTesting:
    def __init__(self, export_sleep: int):
        self.num_export_calls = 0
        self.export_sleep = export_sleep
        self._shutdown = False
        self.sleep_interrupted = False
        self.export_sleep_event = threading.Event()

    def export(self, _: list[Any]):
        self.num_export_calls += 1
        if self._shutdown:
            raise ValueError("Cannot export, already shutdown")

        sleep_interrupted = self.export_sleep_event.wait(self.export_sleep)
        if sleep_interrupted:
            self.sleep_interrupted = True
            raise ValueError("Did not get to finish !")

    def shutdown(self):
        # Force export to finish sleeping.
        self._shutdown = True
        self.export_sleep_event.set()


# BatchLogRecodProcessor/BatchSpanProcessor initialize and use BatchProcessor.
# Important: make sure to call .shutdown() before the end of the test,
# otherwise the worker thread will continue to run after the end of the test.
@pytest.mark.parametrize(
    "batch_processor_class,telemetry",
    [(BatchLogRecordProcessor, EMPTY_LOG), (BatchSpanProcessor, BASIC_SPAN)],
)
class TestBatchProcessor:
    # pylint: disable=no-self-use
    def test_telemetry_exported_once_batch_size_reached(
        self, batch_processor_class, telemetry
    ):
        exporter = Mock()
        batch_processor = batch_processor_class(
            exporter,
            max_queue_size=15,
            max_export_batch_size=15,
            # Will not reach this during the test, this sleep should be interrupted when batch size is reached.
            schedule_delay_millis=30000,
            export_timeout_millis=500,
        )
        before_export = time.time_ns()
        for _ in range(15):
            batch_processor._batch_processor.emit(telemetry)
        # Wait a bit for the worker thread to wake up and call export.
        time.sleep(0.1)
        exporter.export.assert_called_once()
        after_export = time.time_ns()
        # Shows the worker's 30 second sleep was interrupted within a second.
        assert after_export - before_export < 1e9
        batch_processor.shutdown()

    # pylint: disable=no-self-use
    def test_telemetry_exported_once_schedule_delay_reached(
        self, batch_processor_class, telemetry
    ):
        exporter = Mock()
        batch_processor = batch_processor_class(
            exporter,
            max_queue_size=15,
            max_export_batch_size=15,
            schedule_delay_millis=100,
            export_timeout_millis=500,
        )
        batch_processor._batch_processor.emit(telemetry)
        time.sleep(0.2)
        exporter.export.assert_called_once_with([telemetry])
        batch_processor.shutdown()

    def test_telemetry_flushed_before_shutdown_and_dropped_after_shutdown(
        self, batch_processor_class, telemetry
    ):
        exporter = Mock()
        batch_processor = batch_processor_class(
            exporter,
            # Neither of these thresholds should be hit before test ends.
            max_queue_size=15,
            max_export_batch_size=15,
            schedule_delay_millis=30000,
            export_timeout_millis=500,
        )
        # This log should be flushed because it was written before shutdown.
        batch_processor._batch_processor.emit(telemetry)
        batch_processor.shutdown()
        exporter.export.assert_called_once_with([telemetry])
        assert batch_processor._batch_processor._shutdown is True

        # This should not be flushed.
        batch_processor._batch_processor.emit(telemetry)
        exporter.export.assert_called_once()

    # pylint: disable=no-self-use
    def test_force_flush_flushes_telemetry(
        self, batch_processor_class, telemetry
    ):
        exporter = Mock()
        batch_processor = batch_processor_class(
            exporter,
            # Neither of these thresholds should be hit before test ends.
            max_queue_size=15,
            max_export_batch_size=15,
            schedule_delay_millis=30000,
            export_timeout_millis=500,
        )
        for _ in range(10):
            batch_processor._batch_processor.emit(telemetry)
        batch_processor.force_flush()
        exporter.export.assert_called_once_with([telemetry for _ in range(10)])
        batch_processor.shutdown()

    @unittest.skipUnless(
        hasattr(os, "fork"),
        "needs *nix",
    )
    def test_batch_telemetry_record_processor_fork(
        self, batch_processor_class, telemetry
    ):
        exporter = Mock()
        batch_processor = batch_processor_class(
            exporter,
            max_queue_size=200,
            max_export_batch_size=10,
            schedule_delay_millis=30000,
            export_timeout_millis=500,
        )
        # This telemetry should be flushed only from the parent process.
        # _at_fork_reinit should be called in the child process, to
        # clear the logs/spans in the child process.
        for _ in range(9):
            batch_processor._batch_processor.emit(telemetry)

        def child(conn):
            for _ in range(100):
                batch_processor._batch_processor.emit(telemetry)
            batch_processor.force_flush()

            # Expect force flush to export 10 batches of max export batch size (10)
            conn.send(exporter.export.call_count == 10)
            conn.close()

        parent_conn, child_conn = multiprocessing.Pipe()
        process = multiprocessing.Process(target=child, args=(child_conn,))
        process.start()
        assert parent_conn.recv() is True
        process.join()
        batch_processor.force_flush()
        # Single export for the telemetry we emitted at the start of the test.
        assert exporter.export.call_count == 1
        batch_processor.shutdown()

    def test_record_processor_is_garbage_collected(
        self, batch_processor_class, telemetry
    ):
        exporter = Mock()
        processor = batch_processor_class(exporter)
        weak_ref = weakref.ref(processor)
        processor.shutdown()

        # When the processor is garbage collected
        del processor
        gc.collect()

        # Then the reference to the processor should no longer exist
        assert weak_ref() is None

    def test_shutdown_allows_1_export_to_finish(
        self, batch_processor_class, telemetry
    ):
        # This exporter throws an exception if it's export sleep cannot finish.
        exporter = MockExporterForTesting(export_sleep=2)
        processor = batch_processor_class(
            exporter,
            max_queue_size=200,
            max_export_batch_size=1,
            schedule_delay_millis=30000,
        )
        # Max export batch size is 1, so 3 emit calls requires 3 separate calls (each block for 2 seconds) to Export to clear the queue.
        processor._batch_processor.emit(telemetry)
        processor._batch_processor.emit(telemetry)
        processor._batch_processor.emit(telemetry)
        before = time.time()
        processor._batch_processor.shutdown(timeout_millis=3000)
        # Shutdown does not kill the thread.
        assert processor._batch_processor._worker_thread.is_alive() is True

        after = time.time()
        assert after - before < 3.3
        # Thread will naturally finish after a little bit.
        time.sleep(0.1)
        assert processor._batch_processor._worker_thread.is_alive() is False
        # Expect the second call to be interrupted by shutdown, and the third call to never be made.
        assert exporter.sleep_interrupted is True
        assert 2 == exporter.num_export_calls


class TestCommonFuncs(unittest.TestCase):
    def test_duplicate_logs_filter_works(self):
        test_logger = logging.getLogger("testLogger")
        test_logger.addFilter(DuplicateFilter())
        with self.assertLogs("testLogger") as cm:
            test_logger.info("message")
            test_logger.info("message")
        self.assertEqual(len(cm.output), 1)
