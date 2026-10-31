# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint:disable=protected-access,no-self-use,no-member

import logging
import threading
import time
import unittest
from abc import ABC, abstractmethod
from unittest.mock import Mock

from opentelemetry._logs import LogRecord, SeverityNumber
from opentelemetry.sdk._logs._internal import (
    ConcurrentMultiLogRecordProcessor,
    LoggerProvider,
    LoggingHandler,
    LogRecordProcessor,
    ReadWriteLogRecord,
    SynchronousMultiLogRecordProcessor,
)
from opentelemetry.sdk._logs.export import (
    InMemoryLogRecordExporter,
    SimpleLogRecordProcessor,
)

_PROPAGATE_FALSE_LOGGER = "opentelemetry.sdk._logs._internal.propagate.false"


class FailingLogRecordProcessor(LogRecordProcessor):
    def __init__(self):
        self.emit_count = 0

    def on_emit(self, log_record: ReadWriteLogRecord):
        self.emit_count += 1
        raise RuntimeError("Exporter queue error")

    def shutdown(self):
        pass

    def force_flush(self, timeout_millis=30000):
        return True


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

    def test_on_emit_exception_does_not_stop_other_processors(self):
        multi_log_record_processor = self._get_multi_log_record_processor()
        before = Mock(spec=LogRecordProcessor)
        failing = Mock(spec=LogRecordProcessor)
        failing.on_emit.side_effect = RuntimeError("Exporter queue error")
        after = Mock(spec=LogRecordProcessor)
        multi_log_record_processor.add_log_record_processor(before)
        multi_log_record_processor.add_log_record_processor(failing)
        multi_log_record_processor.add_log_record_processor(after)

        record = self.make_record()
        with self.assertLogs(_PROPAGATE_FALSE_LOGGER, level="ERROR") as logs:
            multi_log_record_processor.on_emit(record)

        before.on_emit.assert_called_once_with(record)
        failing.on_emit.assert_called_once_with(record)
        after.on_emit.assert_called_once_with(record)
        self.assertTrue(any("Exception while calling on_emit" in message for message in logs.output))
        multi_log_record_processor.shutdown()

    def test_on_emit_exception_logger_provider_integration(self):
        multi_log_record_processor = self._get_multi_log_record_processor()
        provider = LoggerProvider(
            multi_log_record_processor=multi_log_record_processor,
            shutdown_on_exit=False,
        )
        before_exporter = InMemoryLogRecordExporter()
        after_exporter = InMemoryLogRecordExporter()
        failing_processor = FailingLogRecordProcessor()

        provider.add_log_record_processor(SimpleLogRecordProcessor(before_exporter))
        provider.add_log_record_processor(failing_processor)
        provider.add_log_record_processor(SimpleLogRecordProcessor(after_exporter))

        otel_logger = provider.get_logger("test.integration")
        with self.assertLogs(_PROPAGATE_FALSE_LOGGER, level="ERROR"):
            otel_logger.emit(
                LogRecord(
                    body="otel body",
                    severity_text="INFO",
                    severity_number=SeverityNumber.INFO,
                    attributes={"integration.key": "otel"},
                )
            )

        py_logger = logging.getLogger("test.integration.handler")
        py_logger.propagate = False
        handler = LoggingHandler(logger_provider=provider)
        py_logger.addHandler(handler)
        try:
            with self.assertLogs(_PROPAGATE_FALSE_LOGGER, level="ERROR"):
                py_logger.warning("handler body", extra={"integration.key": "handler"})
        finally:
            py_logger.removeHandler(handler)

        before_logs = before_exporter.get_finished_logs()
        after_logs = after_exporter.get_finished_logs()
        self.assertEqual(len(before_logs), 2)
        self.assertEqual(len(after_logs), 2)

        self.assertEqual(before_logs[0].log_record.body, "otel body")
        self.assertEqual(before_logs[0].log_record.attributes["integration.key"], "otel")
        self.assertEqual(before_logs[1].log_record.body, "handler body")
        self.assertEqual(before_logs[1].log_record.attributes["integration.key"], "handler")

        self.assertEqual(after_logs[0].log_record.body, "otel body")
        self.assertEqual(after_logs[0].log_record.attributes["integration.key"], "otel")
        self.assertEqual(after_logs[1].log_record.body, "handler body")
        self.assertEqual(after_logs[1].log_record.attributes["integration.key"], "handler")

        self.assertEqual(failing_processor.emit_count, 2)
        provider.shutdown()

    def test_on_emit_exception_does_not_reenter_root_logging_handler(self):
        multi_log_record_processor = self._get_multi_log_record_processor()
        provider = LoggerProvider(
            multi_log_record_processor=multi_log_record_processor,
            shutdown_on_exit=False,
        )
        failing_processor = FailingLogRecordProcessor()
        provider.add_log_record_processor(failing_processor)

        root_logger = logging.getLogger()
        handler = LoggingHandler(logger_provider=provider)
        root_logger.addHandler(handler)
        try:

            def emit_once():
                with self.assertLogs(_PROPAGATE_FALSE_LOGGER, level="ERROR"):
                    root_logger.warning("once")

            if isinstance(multi_log_record_processor, ConcurrentMultiLogRecordProcessor):
                thread = threading.Thread(target=emit_once)
                thread.start()
                thread.join(timeout=5)
                self.assertFalse(thread.is_alive(), "on_emit error logging deadlocked")
            else:
                emit_once()

            self.assertEqual(failing_processor.emit_count, 1)
        finally:
            root_logger.removeHandler(handler)
            provider.shutdown()

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
        multi_log_record_processor.shutdown()


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
