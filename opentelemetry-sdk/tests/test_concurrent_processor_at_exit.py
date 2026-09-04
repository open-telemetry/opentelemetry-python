# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Concurrent multi-processors must still flush during interpreter shutdown.

The providers register their shutdown with `atexit.register`, but
`concurrent.futures` registers its own cleanup through
`threading._register_atexit`, and CPython runs `threading._shutdown()` *before*
the `atexit` queue. By the time the provider's shutdown runs the thread pool is
closed, so submitting to it raises RuntimeError and the underlying batch
processor is never shut down.
"""

import subprocess
import sys
import textwrap
import unittest
from concurrent.futures import ThreadPoolExecutor

from opentelemetry.sdk._logs import ConcurrentMultiLogRecordProcessor
from opentelemetry.sdk.trace import ConcurrentMultiSpanProcessor

_SPAN_PROGRAM = """
    from opentelemetry.sdk.trace import TracerProvider, ConcurrentMultiSpanProcessor
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor, SpanExporter, SpanExportResult,
    )

    class Exporter(SpanExporter):
        def export(self, spans):
            for span in spans:
                print("EXPORTED", span.name)
            return SpanExportResult.SUCCESS

        def shutdown(self):
            print("EXPORTER_SHUTDOWN")

    provider = TracerProvider(active_span_processor=ConcurrentMultiSpanProcessor(2))
    # long delay so only shutdown can flush this span
    provider.add_span_processor(BatchSpanProcessor(Exporter(), schedule_delay_millis=600000))
    with provider.get_tracer(__name__).start_as_current_span("span-flushed-at-exit"):
        pass
"""

_LOG_PROGRAM = """
    from opentelemetry._logs import SeverityNumber
    from opentelemetry.sdk._logs import LoggerProvider, ConcurrentMultiLogRecordProcessor
    from opentelemetry.sdk._logs.export import (
        BatchLogRecordProcessor, LogExporter, LogExportResult,
    )

    class Exporter(LogExporter):
        def export(self, batch):
            for record in batch:
                print("EXPORTED", record.log_record.body)
            return LogExportResult.SUCCESS

        def force_flush(self, timeout_millis=30000):
            return True

        def shutdown(self):
            print("EXPORTER_SHUTDOWN")

    provider = LoggerProvider(
        multi_log_record_processor=ConcurrentMultiLogRecordProcessor(2)
    )
    provider.add_log_record_processor(
        BatchLogRecordProcessor(Exporter(), schedule_delay_millis=600000)
    )
    provider.get_logger(__name__).emit(
        body="log-flushed-at-exit", severity_number=SeverityNumber.INFO
    )
"""


def _run(program):
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(program)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


class TestFlushAtInterpreterExit(unittest.TestCase):
    """Driven in a subprocess: the defect only appears at real interpreter exit."""

    def test_spans_are_flushed_at_exit(self):
        result = _run(_SPAN_PROGRAM)
        self.assertIn("EXPORTED span-flushed-at-exit", result.stdout)
        self.assertIn("EXPORTER_SHUTDOWN", result.stdout)

    def test_span_shutdown_does_not_raise_at_exit(self):
        result = _run(_SPAN_PROGRAM)
        self.assertNotIn("cannot schedule new futures", result.stderr)

    def test_logs_are_flushed_at_exit(self):
        result = _run(_LOG_PROGRAM)
        self.assertIn("EXPORTED log-flushed-at-exit", result.stdout)
        self.assertIn("EXPORTER_SHUTDOWN", result.stdout)

    def test_log_shutdown_does_not_raise_at_exit(self):
        result = _run(_LOG_PROGRAM)
        self.assertNotIn("cannot schedule new futures", result.stderr)


class _RecordingSpanProcessor:
    def __init__(self):
        self.shutdown_called = False
        self.flushed = False

    def on_start(self, span, parent_context=None):
        pass

    def _on_ending(self, span):
        pass

    def on_end(self, span):
        pass

    def shutdown(self):
        self.shutdown_called = True

    def force_flush(self, timeout_millis=30000):
        self.flushed = True
        return True


class _RecordingLogProcessor:
    def __init__(self):
        self.shutdown_called = False
        self.flushed = False

    def on_emit(self, log_record):
        pass

    def shutdown(self):
        self.shutdown_called = True

    def force_flush(self, timeout_millis=30000):
        self.flushed = True
        return True


class TestDeadExecutorFallsBackInline(unittest.TestCase):
    """With the pool already closed, work must run inline rather than be lost."""

    def test_span_processor_shutdown_runs_inline(self):
        multi = ConcurrentMultiSpanProcessor(2)
        child = _RecordingSpanProcessor()
        multi.add_span_processor(child)
        multi._executor.shutdown()  # pylint: disable=protected-access
        multi.shutdown()
        self.assertTrue(child.shutdown_called)

    def test_span_processor_force_flush_runs_inline(self):
        multi = ConcurrentMultiSpanProcessor(2)
        child = _RecordingSpanProcessor()
        multi.add_span_processor(child)
        multi._executor.shutdown()  # pylint: disable=protected-access
        self.assertTrue(multi.force_flush())
        self.assertTrue(child.flushed)

    def test_log_processor_shutdown_runs_inline(self):
        multi = ConcurrentMultiLogRecordProcessor(2)
        child = _RecordingLogProcessor()
        multi.add_log_record_processor(child)
        multi._executor.shutdown()  # pylint: disable=protected-access
        multi.shutdown()
        self.assertTrue(child.shutdown_called)

    def test_log_processor_force_flush_runs_inline(self):
        multi = ConcurrentMultiLogRecordProcessor(2)
        child = _RecordingLogProcessor()
        multi.add_log_record_processor(child)
        multi._executor.shutdown()  # pylint: disable=protected-access
        self.assertTrue(multi.force_flush())
        self.assertTrue(child.flushed)

    def test_healthy_executor_is_still_used(self):
        """Control: nothing should change while the pool is alive."""
        multi = ConcurrentMultiSpanProcessor(2)
        child = _RecordingSpanProcessor()
        multi.add_span_processor(child)
        self.assertIsInstance(multi._executor, ThreadPoolExecutor)  # pylint: disable=protected-access
        multi.shutdown()
        self.assertTrue(child.shutdown_called)
