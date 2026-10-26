# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint:disable=protected-access,no-self-use,no-member

import logging
import threading
import time
import unittest
from abc import ABC, abstractmethod
from unittest.mock import Mock, patch

from opentelemetry._logs import LogRecord, SeverityNumber
from opentelemetry.sdk._logs._internal import (
    ConcurrentMultiLogRecordProcessor,
    LoggerProvider,
    LoggingHandler,
    LogRecordProcessor,
    ReadWriteLogRecord,
    SynchronousMultiLogRecordProcessor,
)


class AnotherLogRecordProcessor(LogRecordProcessor):
    def __init__(self, exporter, logs_list):
        self._exporter = exporter
        self._log_list = logs_list
        self._closed = False

    def on_emit(self, log_record: ReadWriteLogRecord):
        if self._closed:
            return
        self._log_list.append(
            (
                log_record.log_record.body,
                log_record.log_record.severity_text,
            )
        )

    def shutdown(self):
        self._closed = True
        self._exporter.shutdown()

    def force_flush(self, timeout_millis=30000):
        self._log_list.clear()
        return True


class TestLogRecordProcessor(unittest.TestCase):
    def test_log_record_processor(self):
        provider = LoggerProvider()
        handler = LoggingHandler(logger_provider=provider)

        logs_list_1 = []
        processor1 = AnotherLogRecordProcessor(Mock(), logs_list_1)
        logs_list_2 = []
        processor2 = AnotherLogRecordProcessor(Mock(), logs_list_2)

        logger = logging.getLogger("test.span.processor")
        logger.addHandler(handler)

        # Test no proessor added
        with self.assertLogs(level=logging.CRITICAL):
            logger.critical("Odisha, we have another major cyclone")

        self.assertEqual(len(logs_list_1), 0)
        self.assertEqual(len(logs_list_2), 0)

        # Add one processor
        provider.add_log_record_processor(processor1)
        with self.assertLogs(level=logging.WARNING):
            logger.warning("Brace yourself")
        with self.assertLogs(level=logging.ERROR):
            logger.error("Some error message")

        expected_list_1 = [
            ("Brace yourself", "WARN"),
            ("Some error message", "ERROR"),
        ]
        self.assertEqual(logs_list_1, expected_list_1)

        # Add another processor
        provider.add_log_record_processor(processor2)
        with self.assertLogs(level=logging.CRITICAL):
            logger.critical("Something disastrous")
        expected_list_1.append(("Something disastrous", "FATAL"))

        expected_list_2 = [("Something disastrous", "FATAL")]

        self.assertEqual(logs_list_1, expected_list_1)
        self.assertEqual(logs_list_2, expected_list_2)


class MultiLogRecordProcessorTestBase(ABC):
    @abstractmethod
    def _get_multi_log_record_processor(self):
        pass

    def make_record(self):
        return ReadWriteLogRecord(
            LogRecord(
                timestamp=1622300111608942000,
                severity_text="WARN",
                severity_number=SeverityNumber.WARN,
                body="Warning message",
            )
        )

    def test_on_emit(self):
        multi_log_record_processor = self._get_multi_log_record_processor()
        mocks = [Mock(spec=LogRecordProcessor) for _ in range(5)]
        for mock in mocks:
            multi_log_record_processor.add_log_record_processor(mock)
        record = self.make_record()
        multi_log_record_processor.on_emit(record)
        for mock in mocks:
            mock.on_emit.assert_called_with(record)
        multi_log_record_processor.shutdown()

    def test_on_shutdown(self):
        multi_log_record_processor = self._get_multi_log_record_processor()
        mocks = [Mock(spec=LogRecordProcessor) for _ in range(5)]
        for mock in mocks:
            multi_log_record_processor.add_log_record_processor(mock)
        multi_log_record_processor.shutdown()
        for mock in mocks:
            mock.shutdown.assert_called_once_with()

    def test_on_force_flush(self):
        multi_log_record_processor = self._get_multi_log_record_processor()
        mocks = [Mock(spec=LogRecordProcessor) for _ in range(5)]
        for mock in mocks:
            multi_log_record_processor.add_log_record_processor(mock)
        ret_value = multi_log_record_processor.force_flush(100)

        self.assertTrue(ret_value)
        for mock_processor in mocks:
            self.assertEqual(1, mock_processor.force_flush.call_count)


class TestSynchronousMultiLogRecordProcessor(MultiLogRecordProcessorTestBase, unittest.TestCase):
    def _get_multi_log_record_processor(self):
        return SynchronousMultiLogRecordProcessor()

    def test_force_flush_delayed(self):
        multi_log_record_processor = SynchronousMultiLogRecordProcessor()

        def delay(_):
            time.sleep(0.09)

        mock_processor1 = Mock(spec=LogRecordProcessor)
        mock_processor1.force_flush = Mock(side_effect=delay)
        multi_log_record_processor.add_log_record_processor(mock_processor1)
        mock_processor2 = Mock(spec=LogRecordProcessor)
        multi_log_record_processor.add_log_record_processor(mock_processor2)

        ret_value = multi_log_record_processor.force_flush(50)
        self.assertFalse(ret_value)
        self.assertEqual(mock_processor1.force_flush.call_count, 1)
        self.assertEqual(mock_processor2.force_flush.call_count, 0)

    def test_force_flush_processor_returns_false(self):
        multi_log_record_processor = SynchronousMultiLogRecordProcessor()

        mock_processor1 = Mock(spec=LogRecordProcessor)
        mock_processor1.force_flush = Mock(return_value=False)
        multi_log_record_processor.add_log_record_processor(mock_processor1)
        mock_processor2 = Mock(spec=LogRecordProcessor)
        mock_processor2.force_flush = Mock(return_value=True)
        multi_log_record_processor.add_log_record_processor(mock_processor2)

        ret_value = multi_log_record_processor.force_flush(50)
        self.assertFalse(ret_value)
        self.assertEqual(mock_processor1.force_flush.call_count, 1)
        self.assertEqual(mock_processor2.force_flush.call_count, 1)

    def test_force_flush_processor_returns_none(self):
        multi_log_record_processor = SynchronousMultiLogRecordProcessor()

        mock_processor1 = Mock(spec=LogRecordProcessor)
        mock_processor1.force_flush = Mock(return_value=None)
        multi_log_record_processor.add_log_record_processor(mock_processor1)
        mock_processor2 = Mock(spec=LogRecordProcessor)
        mock_processor2.force_flush = Mock(return_value=True)
        multi_log_record_processor.add_log_record_processor(mock_processor2)

        ret_value = multi_log_record_processor.force_flush(50)
        self.assertTrue(ret_value)
        self.assertEqual(mock_processor1.force_flush.call_count, 1)
        self.assertEqual(mock_processor2.force_flush.call_count, 1)


class TestConcurrentMultiLogRecordProcessor(MultiLogRecordProcessorTestBase, unittest.TestCase):
    def _get_multi_log_record_processor(self):
        return ConcurrentMultiLogRecordProcessor()

    def test_force_flush_delayed(self):
        multi_log_record_processor = ConcurrentMultiLogRecordProcessor()
        wait_event = threading.Event()

        def delay(_):
            wait_event.wait()

        mock1 = Mock(spec=LogRecordProcessor)
        mock1.force_flush = Mock(side_effect=delay)
        mocks = [Mock(LogRecordProcessor) for _ in range(5)]
        mocks = [mock1] + mocks
        for mock_processor in mocks:
            multi_log_record_processor.add_log_record_processor(mock_processor)

        ret_value = multi_log_record_processor.force_flush(50)
        wait_event.set()

        self.assertFalse(ret_value)
        for mock in mocks:
            self.assertEqual(1, mock.force_flush.call_count)
        multi_log_record_processor.shutdown()

    def test_force_flush_processor_returns_false(self):
        multi_log_record_processor = ConcurrentMultiLogRecordProcessor()

        false_mock = Mock(spec=LogRecordProcessor)
        false_mock.force_flush = Mock(return_value=False)
        mocks = [Mock(spec=LogRecordProcessor) for _ in range(4)]
        mocks.insert(0, false_mock)

        for mock_processor in mocks:
            multi_log_record_processor.add_log_record_processor(mock_processor)

        ret_value = multi_log_record_processor.force_flush()

        self.assertFalse(ret_value)
        for mock in mocks:
            self.assertEqual(1, mock.force_flush.call_count)
        multi_log_record_processor.shutdown()

    def test_force_flush_processor_returns_none(self):
        multi_log_record_processor = ConcurrentMultiLogRecordProcessor()

        none_mock = Mock(spec=LogRecordProcessor)
        none_mock.force_flush = Mock(return_value=None)
        mocks = [Mock(spec=LogRecordProcessor) for _ in range(4)]
        mocks.insert(0, none_mock)

        for mock_processor in mocks:
            multi_log_record_processor.add_log_record_processor(mock_processor)

        ret_value = multi_log_record_processor.force_flush()

        self.assertTrue(ret_value)
        for mock in mocks:
            self.assertEqual(1, mock.force_flush.call_count)
        multi_log_record_processor.shutdown()

    # pylint: disable=no-self-use
    def test_shutdown_runs_inline_after_executor_shutdown(self):
        # Simulate the atexit scenario: CPython runs threading._shutdown()
        # before the atexit queue, so the ThreadPoolExecutor is closed by the
        # time LoggerProvider.shutdown() runs. Underlying processors must
        # still be shut down inline so buffered work is not dropped.
        multi_log_record_processor = ConcurrentMultiLogRecordProcessor(2)
        mock_processor = Mock(spec=LogRecordProcessor)
        multi_log_record_processor.add_log_record_processor(mock_processor)

        # pylint: disable=protected-access
        multi_log_record_processor._executor.shutdown(wait=True)

        multi_log_record_processor.shutdown()
        mock_processor.shutdown.assert_called_once_with()

    def test_callback_exception_does_not_block_siblings(self):
        # A LogRecordProcessor callback failure must not raise out of
        # shutdown() and must not prevent healthy siblings from running.
        multi_log_record_processor = ConcurrentMultiLogRecordProcessor(2)
        raising_processor = Mock(spec=LogRecordProcessor)
        raising_processor.shutdown.side_effect = RuntimeError("processor boom")
        healthy_processor = Mock(spec=LogRecordProcessor)
        multi_log_record_processor.add_log_record_processor(raising_processor)
        multi_log_record_processor.add_log_record_processor(healthy_processor)

        with self.assertLogs("opentelemetry.sdk._logs._internal", level="ERROR"):
            multi_log_record_processor.shutdown()

        raising_processor.shutdown.assert_called_once_with()
        healthy_processor.shutdown.assert_called_once_with()

    def test_submit_runtime_error_does_not_double_invoke(self):
        # If Thread.start fails AFTER the work item was enqueued, the inline
        # fallback must not run the callback a second time.
        multi_log_record_processor = ConcurrentMultiLogRecordProcessor(2)
        processor_a = Mock(spec=LogRecordProcessor)
        processor_b = Mock(spec=LogRecordProcessor)
        multi_log_record_processor.add_log_record_processor(processor_a)
        multi_log_record_processor.add_log_record_processor(processor_b)

        real_start = threading.Thread.start
        calls = {"n": 0}

        def first_start_fails(target):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("cannot start new thread")
            return real_start(target)

        with patch.object(threading.Thread, "start", first_start_fails):
            multi_log_record_processor.shutdown()

        self.assertEqual(processor_a.shutdown.call_count, 1)
        self.assertEqual(processor_b.shutdown.call_count, 1)

    def test_callback_logger_handler_raise_does_not_crash(self):
        # A logging handler attached to the OTel logger that raises must not
        # escape out of shutdown() nor deadlock; reentry guard routes to stderr.
        multi = ConcurrentMultiLogRecordProcessor(2)
        raising = Mock(spec=LogRecordProcessor)
        raising.shutdown.side_effect = RuntimeError("processor boom")
        healthy = Mock(spec=LogRecordProcessor)
        multi.add_log_record_processor(raising)
        multi.add_log_record_processor(healthy)

        class _BoomHandler(logging.Handler):
            def emit(self, record):
                try:
                    raise RuntimeError("handler boom")
                except RuntimeError:
                    pass  # simulate a handler whose emit raises and is contained by the logging framework

        handler = _BoomHandler(level=logging.ERROR)
        otel_logger = logging.getLogger("opentelemetry.sdk._logs._internal")
        otel_logger.addHandler(handler)
        old_raise = logging.raiseExceptions
        logging.raiseExceptions = False
        try:
            multi.shutdown()
        finally:
            logging.raiseExceptions = old_raise
            otel_logger.removeHandler(handler)
            multi._executor.shutdown(wait=True)

        healthy.shutdown.assert_called_once_with()
