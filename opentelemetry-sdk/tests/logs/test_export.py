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
import os
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from sys import version_info
from unittest.mock import Mock, patch

from pytest import mark

from opentelemetry._logs import SeverityNumber
from opentelemetry.sdk import trace
from opentelemetry.sdk._logs import (
    LogData,
    LoggerProvider,
    LoggingHandler,
    LogRecord,
)
from opentelemetry.sdk._logs._internal.export import _logger
from opentelemetry.sdk._logs.export import (
    BatchLogRecordProcessor,
    ConsoleLogExporter,
    InMemoryLogExporter,
    SimpleLogRecordProcessor,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_BLRP_EXPORT_TIMEOUT,
    OTEL_BLRP_MAX_EXPORT_BATCH_SIZE,
    OTEL_BLRP_MAX_QUEUE_SIZE,
    OTEL_BLRP_SCHEDULE_DELAY,
)
from opentelemetry.sdk.resources import Resource as SDKResource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.trace import TraceFlags
from opentelemetry.trace.span import INVALID_SPAN_CONTEXT

EMPTY_LOG = LogData(
    log_record=LogRecord(),
    instrumentation_scope=InstrumentationScope("example", "example"),
)


class TestSimpleLogRecordProcessor(unittest.TestCase):
    def test_simple_log_record_processor_default_level(self):
        exporter = InMemoryLogExporter()
        logger_provider = LoggerProvider()

        logger_provider.add_log_record_processor(
            SimpleLogRecordProcessor(exporter)
        )

        logger = logging.getLogger("default_level")
        logger.propagate = False
        logger.addHandler(LoggingHandler(logger_provider=logger_provider))

        logger.warning("Something is wrong")
        finished_logs = exporter.get_finished_logs()
        self.assertEqual(len(finished_logs), 1)
        warning_log_record = finished_logs[0].log_record
        self.assertEqual(warning_log_record.body, "Something is wrong")
        self.assertEqual(warning_log_record.severity_text, "WARN")
        self.assertEqual(
            warning_log_record.severity_number, SeverityNumber.WARN
        )
        self.assertEqual(
            finished_logs[0].instrumentation_scope.name, "default_level"
        )

    def test_simple_log_record_processor_custom_level(self):
        exporter = InMemoryLogExporter()
        logger_provider = LoggerProvider()

        logger_provider.add_log_record_processor(
            SimpleLogRecordProcessor(exporter)
        )

        logger = logging.getLogger("custom_level")
        logger.propagate = False
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
        self.assertEqual(
            finished_logs[0].instrumentation_scope.name, "custom_level"
        )
        self.assertEqual(
            finished_logs[1].instrumentation_scope.name, "custom_level"
        )

    def test_simple_log_record_processor_trace_correlation(self):
        exporter = InMemoryLogExporter()
        logger_provider = LoggerProvider()

        logger_provider.add_log_record_processor(
            SimpleLogRecordProcessor(exporter)
        )

        logger = logging.getLogger("trace_correlation")
        logger.propagate = False
        logger.addHandler(LoggingHandler(logger_provider=logger_provider))

        logger.warning("Warning message")
        finished_logs = exporter.get_finished_logs()
        self.assertEqual(len(finished_logs), 1)
        log_record = finished_logs[0].log_record
        self.assertEqual(log_record.body, "Warning message")
        self.assertEqual(log_record.severity_text, "WARN")
        self.assertEqual(log_record.severity_number, SeverityNumber.WARN)
        self.assertEqual(log_record.trace_id, INVALID_SPAN_CONTEXT.trace_id)
        self.assertEqual(log_record.span_id, INVALID_SPAN_CONTEXT.span_id)
        self.assertEqual(
            log_record.trace_flags, INVALID_SPAN_CONTEXT.trace_flags
        )
        self.assertEqual(
            finished_logs[0].instrumentation_scope.name, "trace_correlation"
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
            self.assertEqual(
                finished_logs[0].instrumentation_scope.name,
                "trace_correlation",
            )
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
        logger.propagate = False
        logger.addHandler(LoggingHandler(logger_provider=logger_provider))

        logger.warning("Something is wrong")
        finished_logs = exporter.get_finished_logs()
        self.assertEqual(len(finished_logs), 1)
        warning_log_record = finished_logs[0].log_record
        self.assertEqual(warning_log_record.body, "Something is wrong")
        self.assertEqual(warning_log_record.severity_text, "WARN")
        self.assertEqual(
            warning_log_record.severity_number, SeverityNumber.WARN
        )
        self.assertEqual(
            finished_logs[0].instrumentation_scope.name, "shutdown"
        )
        exporter.clear()
        logger_provider.shutdown()
        with self.assertLogs(level=logging.WARNING):
            logger.warning("Log after shutdown")
        finished_logs = exporter.get_finished_logs()
        self.assertEqual(len(finished_logs), 0)

    def test_simple_log_record_processor_different_msg_types(self):
        exporter = InMemoryLogExporter()
        log_record_processor = BatchLogRecordProcessor(exporter)

        provider = LoggerProvider()
        provider.add_log_record_processor(log_record_processor)

        logger = logging.getLogger("different_msg_types")
        logger.addHandler(LoggingHandler(logger_provider=provider))

        logger.warning("warning message: %s", "possible upcoming heatwave")
        logger.error("Very high rise in temperatures across the globe")
        logger.critical("Temperature hits high 420 C in Hyderabad")
        logger.warning(["list", "of", "strings"])
        logger.error({"key": "value"})
        log_record_processor.shutdown()

        finished_logs = exporter.get_finished_logs()
        expected = [
            ("warning message: possible upcoming heatwave", "WARN"),
            ("Very high rise in temperatures across the globe", "ERROR"),
            (
                "Temperature hits high 420 C in Hyderabad",
                "CRITICAL",
            ),
            (["list", "of", "strings"], "WARN"),
            ({"key": "value"}, "ERROR"),
        ]
        emitted = [
            (item.log_record.body, item.log_record.severity_text)
            for item in finished_logs
        ]
        self.assertEqual(expected, emitted)
        for item in finished_logs:
            self.assertEqual(
                item.instrumentation_scope.name, "different_msg_types"
            )

    def test_simple_log_record_processor_custom_single_obj(self):
        """
        Tests that special-case handling for logging a single non-string object
        is correctly applied.
        """
        exporter = InMemoryLogExporter()
        log_record_processor = BatchLogRecordProcessor(exporter)

        provider = LoggerProvider()
        provider.add_log_record_processor(log_record_processor)

        logger = logging.getLogger("single_obj")
        logger.addHandler(LoggingHandler(logger_provider=provider))

        # NOTE: the behaviour of `record.getMessage` is detailed in the
        # `logging.Logger.debug` documentation:
        # > The msg is the message format string, and the args are the arguments
        # > which are merged into msg using the string formatting operator. [...]
        # > No % formatting operation is performed on msg when no args are supplied.

        # This test uses the presence of '%s' in the first arg to determine if
        # formatting was applied

        # string msg with no args - getMessage bypasses formatting and sets the string directly
        logger.warning("a string with a percent-s: %s")
        # string msg with args - getMessage formats args into the msg
        logger.warning("a string with a percent-s: %s", "and arg")
        # non-string msg with args - getMessage stringifies msg and formats args into it
        logger.warning(["a non-string with a percent-s", "%s"], "and arg")
        # non-string msg with no args:
        #  - normally getMessage would stringify the object and bypass formatting
        #  - SPECIAL CASE: bypass stringification as well to keep the raw object
        logger.warning(["a non-string with a percent-s", "%s"])
        log_record_processor.shutdown()

        finished_logs = exporter.get_finished_logs()
        expected = [
            ("a string with a percent-s: %s"),
            ("a string with a percent-s: and arg"),
            ("['a non-string with a percent-s', 'and arg']"),
            (["a non-string with a percent-s", "%s"]),
        ]
        for emitted, expected in zip(finished_logs, expected):
            self.assertEqual(emitted.log_record.body, expected)
            self.assertEqual(emitted.instrumentation_scope.name, "single_obj")

    def test_simple_log_record_processor_different_msg_types_with_formatter(
        self,
    ):
        exporter = InMemoryLogExporter()
        log_record_processor = BatchLogRecordProcessor(exporter)

        provider = LoggerProvider()
        provider.add_log_record_processor(log_record_processor)

        logger = logging.getLogger("different_msg_types")
        handler = LoggingHandler(logger_provider=provider)
        handler.setFormatter(
            logging.Formatter("%(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(handler)

        logger.warning("warning message: %s", "possible upcoming heatwave")
        logger.error("Very high rise in temperatures across the globe")
        logger.critical("Temperature hits high 420 C in Hyderabad")
        logger.warning(["list", "of", "strings"])
        logger.error({"key": "value"})
        log_record_processor.shutdown()

        finished_logs = exporter.get_finished_logs()
        expected = [
            (
                "different_msg_types - WARNING - warning message: possible upcoming heatwave",
                "WARN",
            ),
            (
                "different_msg_types - ERROR - Very high rise in temperatures across the globe",
                "ERROR",
            ),
            (
                "different_msg_types - CRITICAL - Temperature hits high 420 C in Hyderabad",
                "CRITICAL",
            ),
            (
                "different_msg_types - WARNING - ['list', 'of', 'strings']",
                "WARN",
            ),
            ("different_msg_types - ERROR - {'key': 'value'}", "ERROR"),
        ]
        emitted = [
            (item.log_record.body, item.log_record.severity_text)
            for item in finished_logs
        ]
        self.assertEqual(expected, emitted)


# Many more test cases for the BatchLogRecordProcessor exist under
# opentelemetry-sdk/tests/shared_internal/test_batch_processor.py.
# Important: make sure to call .shutdown() on the BatchLogRecordProcessor
# before the end of the test, otherwise the worker thread will continue
# to run after the end of the test.
class TestBatchLogRecordProcessor(unittest.TestCase):
    def test_emit_call_log_record(self):
        exporter = InMemoryLogExporter()
        log_record_processor = Mock(wraps=BatchLogRecordProcessor(exporter))
        provider = LoggerProvider()
        provider.add_log_record_processor(log_record_processor)

        logger = logging.getLogger("emit_call")
        logger.propagate = False
        logger.addHandler(LoggingHandler(logger_provider=provider))

        logger.error("error")
        self.assertEqual(log_record_processor.emit.call_count, 1)
        log_record_processor.shutdown()

    def test_with_multiple_threads(self):  # pylint: disable=no-self-use
        exporter = InMemoryLogExporter()
        batch_processor = BatchLogRecordProcessor(
            exporter,
            max_queue_size=3000,
            max_export_batch_size=50,
            schedule_delay_millis=30000,
            export_timeout_millis=500,
        )

        def bulk_emit(num_emit):
            for _ in range(num_emit):
                batch_processor.emit(EMPTY_LOG)

        total_expected_logs = 0
        with ThreadPoolExecutor(max_workers=69) as executor:
            for num_logs_to_emit in range(1, 70):
                executor.submit(bulk_emit, num_logs_to_emit)
                total_expected_logs += num_logs_to_emit

            executor.shutdown()

        batch_processor.shutdown()
        # Wait a bit for logs to flush.
        time.sleep(2)
        assert len(exporter.get_finished_logs()) == total_expected_logs

    @mark.skipif(
        version_info < (3, 10),
        reason="assertNoLogs only exists in python 3.10+.",
    )
    def test_logging_lib_not_invoked_in_batch_log_record_emit(self):  # pylint: disable=no-self-use
        # See https://github.com/open-telemetry/opentelemetry-python/issues/4261
        exporter = Mock()
        processor = BatchLogRecordProcessor(exporter)
        logger_provider = LoggerProvider(
            resource=SDKResource.create(
                {
                    "service.name": "shoppingcart",
                    "service.instance.id": "instance-12",
                }
            ),
        )
        logger_provider.add_log_record_processor(processor)
        handler = LoggingHandler(
            level=logging.INFO, logger_provider=logger_provider
        )
        sdk_logger = logging.getLogger("opentelemetry.sdk")
        # Attach OTLP handler to SDK logger
        sdk_logger.addHandler(handler)
        # If `emit` calls logging.log then this test will throw a maximum recursion depth exceeded exception and fail.
        try:
            with self.assertNoLogs(sdk_logger, logging.NOTSET):
                processor.emit(EMPTY_LOG)
            processor.shutdown()
            with self.assertNoLogs(sdk_logger, logging.NOTSET):
                processor.emit(EMPTY_LOG)
        finally:
            sdk_logger.removeHandler(handler)

    def test_args(self):
        exporter = InMemoryLogExporter()
        log_record_processor = BatchLogRecordProcessor(
            exporter,
            max_queue_size=1024,
            schedule_delay_millis=2500,
            max_export_batch_size=256,
            export_timeout_millis=15000,
        )
        self.assertEqual(
            log_record_processor._batch_processor._exporter, exporter
        )
        self.assertEqual(
            log_record_processor._batch_processor._max_queue_size, 1024
        )
        self.assertEqual(
            log_record_processor._batch_processor._schedule_delay, 2.5
        )
        self.assertEqual(
            log_record_processor._batch_processor._max_export_batch_size, 256
        )
        self.assertEqual(
            log_record_processor._batch_processor._export_timeout_millis, 15000
        )
        log_record_processor.shutdown()

    @patch.dict(
        "os.environ",
        {
            OTEL_BLRP_MAX_QUEUE_SIZE: "1024",
            OTEL_BLRP_SCHEDULE_DELAY: "2500",
            OTEL_BLRP_MAX_EXPORT_BATCH_SIZE: "256",
            OTEL_BLRP_EXPORT_TIMEOUT: "15000",
        },
    )
    def test_env_vars(self):
        exporter = InMemoryLogExporter()
        log_record_processor = BatchLogRecordProcessor(exporter)
        self.assertEqual(
            log_record_processor._batch_processor._exporter, exporter
        )
        self.assertEqual(
            log_record_processor._batch_processor._max_queue_size, 1024
        )
        self.assertEqual(
            log_record_processor._batch_processor._schedule_delay, 2.5
        )
        self.assertEqual(
            log_record_processor._batch_processor._max_export_batch_size, 256
        )
        self.assertEqual(
            log_record_processor._batch_processor._export_timeout_millis, 15000
        )
        log_record_processor.shutdown()

    def test_args_defaults(self):
        exporter = InMemoryLogExporter()
        log_record_processor = BatchLogRecordProcessor(exporter)
        self.assertEqual(
            log_record_processor._batch_processor._exporter, exporter
        )
        self.assertEqual(
            log_record_processor._batch_processor._max_queue_size, 2048
        )
        self.assertEqual(
            log_record_processor._batch_processor._schedule_delay, 5
        )
        self.assertEqual(
            log_record_processor._batch_processor._max_export_batch_size, 512
        )
        self.assertEqual(
            log_record_processor._batch_processor._export_timeout_millis, 30000
        )
        log_record_processor.shutdown()

    @patch.dict(
        "os.environ",
        {
            OTEL_BLRP_MAX_QUEUE_SIZE: "a",
            OTEL_BLRP_SCHEDULE_DELAY: " ",
            OTEL_BLRP_MAX_EXPORT_BATCH_SIZE: "One",
            OTEL_BLRP_EXPORT_TIMEOUT: "@",
        },
    )
    def test_args_env_var_value_error(self):
        exporter = InMemoryLogExporter()
        _logger.disabled = True
        log_record_processor = BatchLogRecordProcessor(exporter)
        _logger.disabled = False
        self.assertEqual(
            log_record_processor._batch_processor._exporter, exporter
        )
        self.assertEqual(
            log_record_processor._batch_processor._max_queue_size, 2048
        )
        self.assertEqual(
            log_record_processor._batch_processor._schedule_delay, 5
        )
        self.assertEqual(
            log_record_processor._batch_processor._max_export_batch_size, 512
        )
        self.assertEqual(
            log_record_processor._batch_processor._export_timeout_millis, 30000
        )
        log_record_processor.shutdown()

    def test_args_none_defaults(self):
        exporter = InMemoryLogExporter()
        log_record_processor = BatchLogRecordProcessor(
            exporter,
            max_queue_size=None,
            schedule_delay_millis=None,
            max_export_batch_size=None,
            export_timeout_millis=None,
        )
        self.assertEqual(
            log_record_processor._batch_processor._exporter, exporter
        )
        self.assertEqual(
            log_record_processor._batch_processor._max_queue_size, 2048
        )
        self.assertEqual(
            log_record_processor._batch_processor._schedule_delay, 5
        )
        self.assertEqual(
            log_record_processor._batch_processor._max_export_batch_size, 512
        )
        self.assertEqual(
            log_record_processor._batch_processor._export_timeout_millis, 30000
        )
        log_record_processor.shutdown()

    def test_validation_negative_max_queue_size(self):
        exporter = InMemoryLogExporter()
        self.assertRaises(
            ValueError,
            BatchLogRecordProcessor,
            exporter,
            max_queue_size=0,
        )
        self.assertRaises(
            ValueError,
            BatchLogRecordProcessor,
            exporter,
            max_queue_size=-1,
        )
        self.assertRaises(
            ValueError,
            BatchLogRecordProcessor,
            exporter,
            schedule_delay_millis=0,
        )
        self.assertRaises(
            ValueError,
            BatchLogRecordProcessor,
            exporter,
            schedule_delay_millis=-1,
        )
        self.assertRaises(
            ValueError,
            BatchLogRecordProcessor,
            exporter,
            max_export_batch_size=0,
        )
        self.assertRaises(
            ValueError,
            BatchLogRecordProcessor,
            exporter,
            max_export_batch_size=-1,
        )
        self.assertRaises(
            ValueError,
            BatchLogRecordProcessor,
            exporter,
            max_queue_size=100,
            max_export_batch_size=101,
        )


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
        exporter.export([EMPTY_LOG])

        mock_stdout.write.assert_called_once_with(mock_record_str)
