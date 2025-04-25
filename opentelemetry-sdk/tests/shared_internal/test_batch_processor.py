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
import multiprocessing
import os
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

from opentelemetry.sdk._logs import (
    LogData,
    LogRecord,
)
from opentelemetry.sdk._logs.export import (
    InMemoryLogExporter,
)
from opentelemetry.sdk._shared_internal import BatchProcessor
from opentelemetry.sdk.util.instrumentation import InstrumentationScope

EMPTY_LOG = LogData(
    log_record=LogRecord(),
    instrumentation_scope=InstrumentationScope("example", "example"),
)


class TestBatchProcessor(unittest.TestCase):
    def test_logs_exported_once_batch_size_reached(self):
        exporter = Mock()
        log_record_processor = BatchProcessor(
            exporter=exporter,
            max_queue_size=15,
            max_export_batch_size=15,
            # Will not reach this during the test, this sleep should be interrupted when batch size is reached.
            schedule_delay_millis=30000,
            exporting="Log",
            export_timeout_millis=500,
        )
        before_export = time.time_ns()
        for _ in range(15):
            log_record_processor.emit(EMPTY_LOG)
        # Wait a bit for the worker thread to wake up and call export.
        time.sleep(0.1)
        exporter.export.assert_called_once()
        after_export = time.time_ns()
        # Shows the worker's 30 second sleep was interrupted within a second.
        self.assertLess(after_export - before_export, 1e9)

    # pylint: disable=no-self-use
    def test_logs_exported_once_schedule_delay_reached(self):
        exporter = Mock()
        log_record_processor = BatchProcessor(
            exporter=exporter,
            max_queue_size=15,
            max_export_batch_size=15,
            schedule_delay_millis=100,
            exporting="Log",
            export_timeout_millis=500,
        )
        log_record_processor.emit(EMPTY_LOG)
        time.sleep(0.2)
        exporter.export.assert_called_once_with([EMPTY_LOG])

    def test_logs_flushed_before_shutdown_and_dropped_after_shutdown(self):
        exporter = Mock()
        log_record_processor = BatchProcessor(
            exporter=exporter,
            # Neither of these thresholds should be hit before test ends.
            max_queue_size=15,
            max_export_batch_size=15,
            schedule_delay_millis=30000,
            exporting="Log",
            export_timeout_millis=500,
        )
        # This log should be flushed because it was written before shutdown.
        log_record_processor.emit(EMPTY_LOG)
        log_record_processor.shutdown()
        exporter.export.assert_called_once_with([EMPTY_LOG])
        self.assertTrue(exporter._stopped)

        with self.assertLogs(level="INFO") as log:
            # This log should not be flushed.
            log_record_processor.emit(EMPTY_LOG)
            self.assertEqual(len(log.output), 1)
            self.assertEqual(len(log.records), 1)
            self.assertIn("Shutdown called, ignoring Log.", log.output[0])
        exporter.export.assert_called_once()

    # pylint: disable=no-self-use
    def test_force_flush_flushes_logs(self):
        exporter = Mock()
        log_record_processor = BatchProcessor(
            exporter=exporter,
            # Neither of these thresholds should be hit before test ends.
            max_queue_size=15,
            max_export_batch_size=15,
            schedule_delay_millis=30000,
            exporting="Log",
            export_timeout_millis=500,
        )
        for _ in range(10):
            log_record_processor.emit(EMPTY_LOG)
        log_record_processor.force_flush()
        exporter.export.assert_called_once_with([EMPTY_LOG for _ in range(10)])

    def test_with_multiple_threads(self):
        exporter = InMemoryLogExporter()
        log_record_processor = BatchProcessor(
            exporter=exporter,
            max_queue_size=3000,
            max_export_batch_size=1000,
            schedule_delay_millis=30000,
            exporting="Log",
            export_timeout_millis=500,
        )

        def bulk_log_and_flush(num_logs):
            for _ in range(num_logs):
                log_record_processor.emit(EMPTY_LOG)
            log_record_processor.force_flush()

        with ThreadPoolExecutor(max_workers=69) as executor:
            for idx in range(69):
                executor.submit(bulk_log_and_flush, idx + 1)

            executor.shutdown()

        finished_logs = exporter.get_finished_logs()
        self.assertEqual(len(finished_logs), 2415)

    @unittest.skipUnless(
        hasattr(os, "fork"),
        "needs *nix",
    )
    def test_batch_log_record_processor_fork(self):
        exporter = InMemoryLogExporter()
        log_record_processor = BatchProcessor(
            exporter,
            max_queue_size=100,
            max_export_batch_size=64,
            schedule_delay_millis=30000,
            exporting="Log",
            export_timeout_millis=500,
        )
        # These logs should be flushed only from the parent process.
        # _at_fork_reinit should be called in the child process, to
        # clear these logs in the child process.
        for _ in range(10):
            log_record_processor.emit(EMPTY_LOG)

        multiprocessing.set_start_method("fork")

        def child(conn):
            for _ in range(100):
                log_record_processor.emit(EMPTY_LOG)
            log_record_processor.force_flush()

            logs = exporter.get_finished_logs()
            conn.send(len(logs) == 100)
            conn.close()

        parent_conn, child_conn = multiprocessing.Pipe()
        process = multiprocessing.Process(target=child, args=(child_conn,))
        process.start()
        self.assertTrue(parent_conn.recv())
        process.join()
        log_record_processor.force_flush()
        self.assertTrue(len(exporter.get_finished_logs()) == 10)
