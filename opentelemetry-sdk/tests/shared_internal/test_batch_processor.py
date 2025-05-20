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
import multiprocessing
import os
import time
import unittest
import weakref
from concurrent.futures import ThreadPoolExecutor
from platform import system
from sys import version_info
from unittest.mock import Mock

import pytest
from pytest import mark

from opentelemetry.sdk._logs import (
    LogData,
    LogRecord,
)
from opentelemetry.sdk._logs.export import (
    BatchLogRecordProcessor,
)
from opentelemetry.sdk.util.instrumentation import InstrumentationScope

EMPTY_LOG = LogData(
    log_record=LogRecord(),
    instrumentation_scope=InstrumentationScope("example", "example"),
)


# BatchLogRecodpRocessor initializes / uses BatchProcessor.
@pytest.mark.parametrize(
    "batch_processor_class,telemetry",
    [(BatchLogRecordProcessor, EMPTY_LOG)],
)
class TestBatchProcessor:
    # pylint: disable=no-self-use
    def test_telemetry_exported_once_batch_size_reached(
        self, batch_processor_class, telemetry
    ):
        exporter = Mock()
        batch_processor = batch_processor_class(
            exporter=exporter,
            max_queue_size=15,
            max_export_batch_size=15,
            # Will not reach this during the test, this sleep should be interrupted when batch size is reached.
            schedule_delay_millis=30000,
            export_timeout_millis=500,
        )
        before_export = time.time_ns()
        for _ in range(15):
            batch_processor.emit(telemetry)
        # Wait a bit for the worker thread to wake up and call export.
        time.sleep(0.1)
        exporter.export.assert_called_once()
        after_export = time.time_ns()
        # Shows the worker's 30 second sleep was interrupted within a second.
        assert after_export - before_export < 1e9

    # pylint: disable=no-self-use
    def test_telemetry_exported_once_schedule_delay_reached(
        self, batch_processor_class, telemetry
    ):
        exporter = Mock()
        batch_processor = batch_processor_class(
            exporter=exporter,
            max_queue_size=15,
            max_export_batch_size=15,
            schedule_delay_millis=100,
            export_timeout_millis=500,
        )
        batch_processor.emit(telemetry)
        time.sleep(0.2)
        exporter.export.assert_called_once_with([telemetry])

    def test_telemetry_flushed_before_shutdown_and_dropped_after_shutdown(
        self, batch_processor_class, telemetry
    ):
        exporter = Mock()
        batch_processor = batch_processor_class(
            exporter=exporter,
            # Neither of these thresholds should be hit before test ends.
            max_queue_size=15,
            max_export_batch_size=15,
            schedule_delay_millis=30000,
            export_timeout_millis=500,
        )
        # This log should be flushed because it was written before shutdown.
        batch_processor.emit(telemetry)
        batch_processor.shutdown()
        exporter.export.assert_called_once_with([telemetry])
        assert batch_processor._batch_processor._shutdown is True

        # This should not be flushed.
        batch_processor.emit(telemetry)
        exporter.export.assert_called_once()

    # pylint: disable=no-self-use
    def test_force_flush_flushes_telemetry(
        self, batch_processor_class, telemetry
    ):
        exporter = Mock()
        batch_processor = batch_processor_class(
            exporter=exporter,
            # Neither of these thresholds should be hit before test ends.
            max_queue_size=15,
            max_export_batch_size=15,
            schedule_delay_millis=30000,
            export_timeout_millis=500,
        )
        for _ in range(10):
            batch_processor.emit(telemetry)
        batch_processor.force_flush()
        exporter.export.assert_called_once_with([telemetry for _ in range(10)])

    @mark.skipif(
        system() == "Windows" or version_info < (3, 9),
        reason="This test randomly fails on windows and python 3.8.",
    )
    def test_with_multiple_threads(self, batch_processor_class, telemetry):
        exporter = Mock()
        batch_processor = batch_processor_class(
            exporter=exporter,
            max_queue_size=3000,
            max_export_batch_size=1000,
            schedule_delay_millis=30000,
            export_timeout_millis=500,
        )

        def bulk_emit_and_flush(num_emit):
            for _ in range(num_emit):
                batch_processor.emit(telemetry)
            batch_processor.force_flush()

        with ThreadPoolExecutor(max_workers=69) as executor:
            for idx in range(69):
                executor.submit(bulk_emit_and_flush, idx + 1)

            executor.shutdown()
        # 69 calls to force flush.
        assert exporter.export.call_count == 69

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
            batch_processor.emit(telemetry)

        multiprocessing.set_start_method("fork")

        def child(conn):
            for _ in range(100):
                batch_processor.emit(telemetry)
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
