import logging
import threading
from unittest import TestCase
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import InMemoryLogExporter, SimpleLogRecordProcessor


class TestLoggingHandlerRecursionGuard(TestCase):

    def _create_handler(self):
        exporter = InMemoryLogExporter()
        provider = LoggerProvider()
        provider.add_log_record_processor(SimpleLogRecordProcessor(exporter))
        handler = LoggingHandler(logger_provider=provider)
        return handler, exporter

    def _make_record(self, msg="test"):
        return logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg=msg, args=(), exc_info=None,
        )

    def test_recursive_emit_is_skipped(self):
        """Recursive emit() on the same thread should be skipped.
        Prevents deadlock when _translate() triggers _logger.warning().
        Regression test for https://github.com/open-telemetry/opentelemetry-python/issues/3858
        """
        handler, exporter = self._create_handler()
        handler._guard.emitting = True
        handler.emit(self._make_record("should be skipped"))
        self.assertEqual(len(exporter.get_finished_logs()), 0)
        handler._guard.emitting = False

    def test_normal_emit_works(self):
        """Non-recursive emit() should process logs normally."""
        handler, exporter = self._create_handler()
        handler.emit(self._make_record("should be captured"))
        logs = exporter.get_finished_logs()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].log_record.body, "should be captured")

    def test_guard_is_reset_after_emit(self):
        """Guard must reset after emit(), allowing subsequent logs."""
        handler, exporter = self._create_handler()
        handler.emit(self._make_record("first"))
        self.assertFalse(getattr(handler._guard, "emitting", False))
        handler.emit(self._make_record("second"))
        self.assertEqual(len(exporter.get_finished_logs()), 2)

    def test_guard_is_thread_local(self):
        """Guard on one thread must not block other threads."""
        handler, exporter = self._create_handler()
        handler._guard.emitting = True  # block main thread

        result = [False]
        def log_from_other_thread():
            handler.emit(self._make_record("from other thread"))
            result[0] = True

        t = threading.Thread(target=log_from_other_thread)
        t.start()
        t.join(timeout=5)

        self.assertTrue(result[0], "Other thread should not be blocked")
        self.assertEqual(len(exporter.get_finished_logs()), 1)
        handler._guard.emitting = False