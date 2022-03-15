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

# pylint:disable=protected-access,no-self-use,no-member

import logging
import threading
import time
import unittest
from abc import ABC, abstractmethod
from unittest.mock import Mock

from opentelemetry.sdk._logs import (
    ConcurrentMultiLogProcessor,
    LogEmitterProvider,
    LoggingHandler,
    LogProcessor,
    LogRecord,
    SynchronousMultiLogProcessor,
)
from opentelemetry.sdk._logs.severity import SeverityNumber


class AnotherLogProcessor(LogProcessor):
    def __init__(self, exporter, logs_list):
        self._exporter = exporter
        self._log_list = logs_list
        self._closed = False

    def emit(self, log_data):
        if self._closed:
            return
        self._log_list.append(
            (log_data.log_record.body, log_data.log_record.severity_text)
        )

    def shutdown(self):
        self._closed = True
        self._exporter.shutdown()

    def force_flush(self, timeout_millis=30000):
        self._log_list.clear()
        return True


class TestLogProcessor(unittest.TestCase):
    def test_log_processor(self):
        provider = LogEmitterProvider()
        log_emitter = provider.get_log_emitter(__name__)
        handler = LoggingHandler(log_emitter=log_emitter)

        logs_list_1 = []
        processor1 = AnotherLogProcessor(Mock(), logs_list_1)
        logs_list_2 = []
        processor2 = AnotherLogProcessor(Mock(), logs_list_2)

        logger = logging.getLogger("test.span.processor")
        logger.addHandler(handler)

        # Test no proessor added
        logger.critical("Odisha, we have another major cyclone")

        self.assertEqual(len(logs_list_1), 0)
        self.assertEqual(len(logs_list_2), 0)

        # Add one processor
        provider.add_log_processor(processor1)
        logger.warning("Brace yourself")
        logger.error("Some error message")

        expected_list_1 = [
            ("Brace yourself", "WARNING"),
            ("Some error message", "ERROR"),
        ]
        self.assertEqual(logs_list_1, expected_list_1)

        # Add another processor
        provider.add_log_processor(processor2)
        logger.critical("Something disastrous")
        expected_list_1.append(("Something disastrous", "CRITICAL"))

        expected_list_2 = [("Something disastrous", "CRITICAL")]

        self.assertEqual(logs_list_1, expected_list_1)
        self.assertEqual(logs_list_2, expected_list_2)


class MultiLogProcessorTestBase(ABC):
    @abstractmethod
    def _get_multi_log_processor(self):
        pass

    def make_record(self):
        return LogRecord(
            timestamp=1622300111608942000,
            severity_text="WARNING",
            severity_number=SeverityNumber.WARN,
            body="Warning message",
        )

    def test_on_emit(self):
        multi_log_processor = self._get_multi_log_processor()
        mocks = [Mock(spec=LogProcessor) for _ in range(5)]
        for mock in mocks:
            multi_log_processor.add_log_processor(mock)
        record = self.make_record()
        multi_log_processor.emit(record)
        for mock in mocks:
            mock.emit.assert_called_with(record)
        multi_log_processor.shutdown()

    def test_on_shutdown(self):
        multi_log_processor = self._get_multi_log_processor()
        mocks = [Mock(spec=LogProcessor) for _ in range(5)]
        for mock in mocks:
            multi_log_processor.add_log_processor(mock)
        multi_log_processor.shutdown()
        for mock in mocks:
            mock.shutdown.assert_called_once_with()

    def test_on_force_flush(self):
        multi_log_processor = self._get_multi_log_processor()
        mocks = [Mock(spec=LogProcessor) for _ in range(5)]
        for mock in mocks:
            multi_log_processor.add_log_processor(mock)
        ret_value = multi_log_processor.force_flush(100)

        self.assertTrue(ret_value)
        for mock_processor in mocks:
            self.assertEqual(1, mock_processor.force_flush.call_count)


class TestSynchronousMultiLogProcessor(
    MultiLogProcessorTestBase, unittest.TestCase
):
    def _get_multi_log_processor(self):
        return SynchronousMultiLogProcessor()

    def test_force_flush_delayed(self):
        multi_log_processor = SynchronousMultiLogProcessor()

        def delay(_):
            time.sleep(0.09)

        mock_processor1 = Mock(spec=LogProcessor)
        mock_processor1.force_flush = Mock(side_effect=delay)
        multi_log_processor.add_log_processor(mock_processor1)
        mock_processor2 = Mock(spec=LogProcessor)
        multi_log_processor.add_log_processor(mock_processor2)

        ret_value = multi_log_processor.force_flush(50)
        self.assertFalse(ret_value)
        self.assertEqual(mock_processor1.force_flush.call_count, 1)
        self.assertEqual(mock_processor2.force_flush.call_count, 0)


class TestConcurrentMultiLogProcessor(
    MultiLogProcessorTestBase, unittest.TestCase
):
    def _get_multi_log_processor(self):
        return ConcurrentMultiLogProcessor()

    def test_force_flush_delayed(self):
        multi_log_processor = ConcurrentMultiLogProcessor()
        wait_event = threading.Event()

        def delay(_):
            wait_event.wait()

        mock1 = Mock(spec=LogProcessor)
        mock1.force_flush = Mock(side_effect=delay)
        mocks = [Mock(LogProcessor) for _ in range(5)]
        mocks = [mock1] + mocks
        for mock_processor in mocks:
            multi_log_processor.add_log_processor(mock_processor)

        ret_value = multi_log_processor.force_flush(50)
        wait_event.set()

        self.assertFalse(ret_value)
        for mock in mocks:
            self.assertEqual(1, mock.force_flush.call_count)
        multi_log_processor.shutdown()
