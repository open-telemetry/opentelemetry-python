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
import logging
import multiprocessing
import os
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch

from opentelemetry._logs import SeverityNumber
from opentelemetry.sdk import trace
from opentelemetry.sdk._logs import (
    LogData,
    LoggerProvider,
    LoggingHandler,
    LogRecord,
)
from opentelemetry.sdk._logs.export import (
    BatchLogRecordProcessor,
    ConsoleLogExporter,
    InMemoryLogExporter,
    SimpleLogRecordProcessor,
)
from opentelemetry.sdk.resources import Resource as SDKResource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.test.concurrency_test import ConcurrencyTestBase
from opentelemetry.trace import TraceFlags
from opentelemetry.trace.span import INVALID_SPAN_CONTEXT


class TestSimpleLogRecordProcessor(unittest.TestCase):
    def test_simple_log_record_processor_default_level(self):
        exporter = InMemoryLogExporter()
        logger_provider = LoggerProvider()

        logger_provider.add_log_record_processor(
            SimpleLogRecordProcessor(exporter)
        )

        logger = logging.getLogger("default_level")
        logger.addHandler(LoggingHandler(logger_provider=logger_provider))

        logger.warning("Something is wrong")
        finished_logs = exporter.get_finished_logs()
        self.assertEqual(len(finished_logs), 1)
        warning_log_record = finished_logs[0].log_record
        self.assertEqual(warning_log_record.body, "Something is wrong")
        self.assertEqual(warning_log_record.severity_text, "WARNING")
        self.assertEqual(
            warning_log_record.severity_number, SeverityNumber.WARN
        )

    def test_simple_log_record_processor_custom_level(self):
        exporter = InMemoryLogExporter()
        logger_provider = LoggerProvider()

        logger_provider.add_log_record_processor(
            SimpleLogRecordProcessor(exporter)
        )

        logger = logging.getLogger("custom_level")
        logger.setLevel(logging.ERROR)
        logger.addHandler(LoggingHandler(logger_provider=logger_provider))

        logger.warning("Warning message")
        logger.debug("Debug message")
        logger.error("Error message")
        logger.critical("Critical message")
        finished_logs = exporter.get_finished_logs()
        # Make sure only level >= logging.CRITICAL logs are recorded
        self.assertEqual(len(finished_logs), 2)
        critical_log_record = finished_logs[0].log_record
        fatal_log_record = finished_logs[1].log_record
        self.assertEqual(critical_log_record.body, "Error message")
        self.assertEqual(critical_log_record.severity_text, "ERROR")
        self.assertEqual(
            critical_log_record.severity_number, SeverityNumber.ERROR
        )
        self.assertEqual(fatal_log_record.body, "Critical message")
        self.assertEqual(fatal_log_record.severity_text, "CRITICAL")
        self.assertEqual(
            fatal_log_record.severity_number, SeverityNumber.FATAL
        )

    def test_simple_log_record_processor_trace_correlation(self):
        exporter = InMemoryLogExporter()
        logger_provider = LoggerProvider()

        logger_provider.add_log_record_processor(
            SimpleLogRecordProcessor(exporter)
        )

        logger = logging.getLogger("trace_correlation")
        logger.addHandler(LoggingHandler(logger_provider=logger_provider))

        logger.warning("Warning message")
        finished_logs = exporter.get_finished_logs()
        self.assertEqual(len(finished_logs), 1)
        log_record = finished_logs[0].log_record
        self.assertEqual(log_record.body, "Warning message")
        self.assertEqual(log_record.severity_text, "WARNING")
        self.assertEqual(log_record.severity_number, SeverityNumber.WARN)
        self.assertEqual(log_record.trace_id, INVALID_SPAN_CONTEXT.trace_id)
        self.assertEqual(log_record.span_id, INVALID_SPAN_CONTEXT.span_id)
        self.assertEqual(
            log_record.trace_flags, INVALID_SPAN_CONTEXT.trace_flags
        )
        exporter.clear()

        tracer = trace.TracerProvider().get_tracer(__name__)
        with tracer.start_as_current_span("test") as span:
            logger.critical("Critical message within span")

            finished_logs = exporter.get_finished_logs()
            log_record = finished_logs[0].log_record
            self.assertEqual(log_record.body, "Critical message within span")
            self.assertEqual(log_record.severity_text, "CRITICAL")
            self.assertEqual(log_record.severity_number, SeverityNumber.FATAL)
            span_context = span.get_span_context()
            self.assertEqual(log_record.trace_id, span_context.trace_id)
            self.assertEqual(log_record.span_id, span_context.span_id)
            self.assertEqual(log_record.trace_flags, span_context.trace_flags)

    def test_simple_log_record_processor_shutdown(self):
        exporter = InMemoryLogExporter()
        logger_provider = LoggerProvider()

        logger_provider.add_log_record_processor(
            SimpleLogRecordProcessor(exporter)
        )

        logger = logging.getLogger("shutdown")
        logger.addHandler(LoggingHandler(logger_provider=logger_provider))

        logger.warning("Something is wrong")
        finished_logs = exporter.get_finished_logs()
        self.assertEqual(len(finished_logs), 1)
        warning_log_record = finished_logs[0].log_record
        self.assertEqual(warning_log_record.body, "Something is wrong")
        self.assertEqual(warning_log_record.severity_text, "WARNING")
        self.assertEqual(
            warning_log_record.severity_number, SeverityNumber.WARN
        )
        exporter.clear()
        logger_provider.shutdown()
        logger.warning("Log after shutdown")
        finished_logs = exporter.get_finished_logs()
        self.assertEqual(len(finished_logs), 0)


class TestBatchLogRecordProcessor(ConcurrencyTestBase):
    def test_emit_call_log_record(self):
        exporter = InMemoryLogExporter()
        log_record_processor = Mock(wraps=BatchLogRecordProcessor(exporter))
        provider = LoggerProvider()
        provider.add_log_record_processor(log_record_processor)

        logger = logging.getLogger("emit_call")
        logger.addHandler(LoggingHandler(logger_provider=provider))

        logger.error("error")
        self.assertEqual(log_record_processor.emit.call_count, 1)

    def test_shutdown(self):
        exporter = InMemoryLogExporter()
        log_record_processor = BatchLogRecordProcessor(exporter)

        provider = LoggerProvider()
        provider.add_log_record_processor(log_record_processor)

        logger = logging.getLogger("shutdown")
        logger.addHandler(LoggingHandler(logger_provider=provider))

        logger.warning("warning message: %s", "possible upcoming heatwave")
        logger.error("Very high rise in temperatures across the globe")
        logger.critical("Temperature hits high 420 C in Hyderabad")

        log_record_processor.shutdown()
        self.assertTrue(exporter._stopped)

        finished_logs = exporter.get_finished_logs()
        expected = [
            ("warning message: possible upcoming heatwave", "WARNING"),
            ("Very high rise in temperatures across the globe", "ERROR"),
            (
                "Temperature hits high 420 C in Hyderabad",
                "CRITICAL",
            ),
        ]
        emitted = [
            (item.log_record.body, item.log_record.severity_text)
            for item in finished_logs
        ]
        self.assertEqual(expected, emitted)

    def test_force_flush(self):
        exporter = InMemoryLogExporter()
        log_record_processor = BatchLogRecordProcessor(exporter)

        provider = LoggerProvider()
        provider.add_log_record_processor(log_record_processor)

        logger = logging.getLogger("force_flush")
        logger.addHandler(LoggingHandler(logger_provider=provider))

        logger.critical("Earth is burning")
        log_record_processor.force_flush()
        finished_logs = exporter.get_finished_logs()
        self.assertEqual(len(finished_logs), 1)
        log_record = finished_logs[0].log_record
        self.assertEqual(log_record.body, "Earth is burning")
        self.assertEqual(log_record.severity_number, SeverityNumber.FATAL)

    def test_log_record_processor_too_many_logs(self):
        exporter = InMemoryLogExporter()
        log_record_processor = BatchLogRecordProcessor(exporter)

        provider = LoggerProvider()
        provider.add_log_record_processor(log_record_processor)

        logger = logging.getLogger("many_logs")
        logger.addHandler(LoggingHandler(logger_provider=provider))

        for log_no in range(1000):
            logger.critical("Log no: %s", log_no)

        self.assertTrue(log_record_processor.force_flush())
        finised_logs = exporter.get_finished_logs()
        self.assertEqual(len(finised_logs), 1000)

    def test_with_multiple_threads(self):
        exporter = InMemoryLogExporter()
        log_record_processor = BatchLogRecordProcessor(exporter)

        provider = LoggerProvider()
        provider.add_log_record_processor(log_record_processor)

        logger = logging.getLogger("threads")
        logger.addHandler(LoggingHandler(logger_provider=provider))

        def bulk_log_and_flush(num_logs):
            for _ in range(num_logs):
                logger.critical("Critical message")
            self.assertTrue(log_record_processor.force_flush())

        with ThreadPoolExecutor(max_workers=69) as executor:
            futures = []
            for idx in range(69):
                future = executor.submit(bulk_log_and_flush, idx + 1)
                futures.append(future)

            executor.shutdown()

        finished_logs = exporter.get_finished_logs()
        self.assertEqual(len(finished_logs), 2415)

    @unittest.skipUnless(
        hasattr(os, "fork"),
        "needs *nix",
    )
    def test_batch_log_record_processor_fork(self):
        # pylint: disable=invalid-name
        exporter = InMemoryLogExporter()
        log_record_processor = BatchLogRecordProcessor(
            exporter,
            max_export_batch_size=64,
            schedule_delay_millis=10,
        )
        provider = LoggerProvider()
        provider.add_log_record_processor(log_record_processor)

        logger = logging.getLogger("test-fork")
        logger.addHandler(LoggingHandler(logger_provider=provider))

        logger.critical("yolo")
        time.sleep(0.5)  # give some time for the exporter to upload

        self.assertTrue(log_record_processor.force_flush())
        self.assertEqual(len(exporter.get_finished_logs()), 1)
        exporter.clear()

        multiprocessing.set_start_method("fork")

        def child(conn):
            def _target():
                logger.critical("Critical message child")

            self.run_with_many_threads(_target, 100)

            time.sleep(0.5)

            logs = exporter.get_finished_logs()
            conn.send(len(logs) == 100)
            conn.close()

        parent_conn, child_conn = multiprocessing.Pipe()
        p = multiprocessing.Process(target=child, args=(child_conn,))
        p.start()
        self.assertTrue(parent_conn.recv())
        p.join()

        log_record_processor.shutdown()


class TestConsoleLogExporter(unittest.TestCase):
    def test_export(self):  # pylint: disable=no-self-use
        """Check that the console exporter prints log records."""
        log_data = LogData(
            log_record=LogRecord(
                timestamp=int(time.time() * 1e9),
                trace_id=2604504634922341076776623263868986797,
                span_id=5213367945872657620,
                trace_flags=TraceFlags(0x01),
                severity_text="WARN",
                severity_number=SeverityNumber.WARN,
                body="Zhengzhou, We have a heaviest rains in 1000 years",
                resource=SDKResource({"key": "value"}),
                attributes={"a": 1, "b": "c"},
            ),
            instrumentation_scope=InstrumentationScope(
                "first_name", "first_version"
            ),
        )
        exporter = ConsoleLogExporter()
        # Mocking stdout interferes with debugging and test reporting, mock on
        # the exporter instance instead.

        with patch.object(exporter, "out") as mock_stdout:
            exporter.export([log_data])
        mock_stdout.write.assert_called_once_with(
            log_data.log_record.to_json() + os.linesep
        )

        self.assertEqual(mock_stdout.write.call_count, 1)
        self.assertEqual(mock_stdout.flush.call_count, 1)

    def test_export_custom(self):  # pylint: disable=no-self-use
        """Check that console exporter uses custom io, formatter."""
        mock_record_str = Mock(str)

        def formatter(record):  # pylint: disable=unused-argument
            return mock_record_str

        mock_stdout = Mock()
        exporter = ConsoleLogExporter(out=mock_stdout, formatter=formatter)
        log_data = LogData(
            log_record=LogRecord(),
            instrumentation_scope=InstrumentationScope(
                "first_name", "first_version"
            ),
        )
        exporter.export([log_data])
        mock_stdout.write.assert_called_once_with(mock_record_str)
