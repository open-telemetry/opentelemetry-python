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
import logging
import unittest
from unittest.mock import Mock

from opentelemetry._logs import NoOpLoggerProvider, SeverityNumber
from opentelemetry._logs import get_logger as APIGetLogger
from opentelemetry.attributes import BoundedAttributes
from opentelemetry.sdk import trace
from opentelemetry.sdk._logs import (
    LogData,
    LoggerProvider,
    LoggingHandler,
    LogRecordProcessor,
)
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.trace import INVALID_SPAN_CONTEXT


class TestLoggingHandler(unittest.TestCase):
    def test_handler_default_log_level(self):
        processor, logger = set_up_test_logging(logging.NOTSET)

        # Make sure debug messages are ignored by default
        logger.debug("Debug message")
        assert processor.emit_count() == 0

        # Assert emit gets called for warning message
        with self.assertLogs(level=logging.WARNING):
            logger.warning("Warning message")
        self.assertEqual(processor.emit_count(), 1)

    def test_handler_custom_log_level(self):
        processor, logger = set_up_test_logging(logging.ERROR)

        with self.assertLogs(level=logging.WARNING):
            logger.warning("Warning message test custom log level")
        # Make sure any log with level < ERROR is ignored
        assert processor.emit_count() == 0

        with self.assertLogs(level=logging.ERROR):
            logger.error("Mumbai, we have a major problem")
        with self.assertLogs(level=logging.CRITICAL):
            logger.critical("No Time For Caution")
        self.assertEqual(processor.emit_count(), 2)

    # pylint: disable=protected-access
    def test_log_record_emit_noop(self):
        noop_logger_provder = NoOpLoggerProvider()
        logger_mock = APIGetLogger(
            __name__, logger_provider=noop_logger_provder
        )
        logger = logging.getLogger(__name__)
        handler_mock = Mock(spec=LoggingHandler)
        handler_mock._logger = logger_mock
        handler_mock.level = logging.WARNING
        logger.addHandler(handler_mock)
        with self.assertLogs(level=logging.WARNING):
            logger.warning("Warning message")

    def test_log_flush_noop(self):
        no_op_logger_provider = NoOpLoggerProvider()
        no_op_logger_provider.force_flush = Mock()

        logger = logging.getLogger("foo")
        handler = LoggingHandler(
            level=logging.NOTSET, logger_provider=no_op_logger_provider
        )
        logger.addHandler(handler)

        with self.assertLogs(level=logging.WARNING):
            logger.warning("Warning message")

        logger.handlers[0].flush()
        no_op_logger_provider.force_flush.assert_not_called()

    def test_log_record_no_span_context(self):
        processor, logger = set_up_test_logging(logging.WARNING)

        # Assert emit gets called for warning message
        with self.assertLogs(level=logging.WARNING):
            logger.warning("Warning message")

        log_record = processor.get_log_record(0)

        self.assertIsNotNone(log_record)
        self.assertEqual(log_record.trace_id, INVALID_SPAN_CONTEXT.trace_id)
        self.assertEqual(log_record.span_id, INVALID_SPAN_CONTEXT.span_id)
        self.assertEqual(
            log_record.trace_flags, INVALID_SPAN_CONTEXT.trace_flags
        )

    def test_log_record_observed_timestamp(self):
        processor, logger = set_up_test_logging(logging.WARNING)

        with self.assertLogs(level=logging.WARNING):
            logger.warning("Warning message")

        log_record = processor.get_log_record(0)
        self.assertIsNotNone(log_record.observed_timestamp)

    def test_log_record_user_attributes(self):
        """Attributes can be injected into logs by adding them to the LogRecord"""
        processor, logger = set_up_test_logging(logging.WARNING)

        # Assert emit gets called for warning message
        with self.assertLogs(level=logging.WARNING):
            logger.warning("Warning message", extra={"http.status_code": 200})

        log_record = processor.get_log_record(0)

        self.assertIsNotNone(log_record)
        self.assertEqual(len(log_record.attributes), 4)
        self.assertEqual(log_record.attributes["http.status_code"], 200)
        self.assertTrue(
            log_record.attributes[SpanAttributes.CODE_FILEPATH].endswith(
                "test_handler.py"
            )
        )
        self.assertEqual(
            log_record.attributes[SpanAttributes.CODE_FUNCTION],
            "test_log_record_user_attributes",
        )
        # The line of the log statement is not a constant (changing tests may change that),
        # so only check that the attribute is present.
        self.assertTrue(SpanAttributes.CODE_LINENO in log_record.attributes)
        self.assertTrue(isinstance(log_record.attributes, BoundedAttributes))

    def test_log_record_exception(self):
        """Exception information will be included in attributes"""
        processor, logger = set_up_test_logging(logging.ERROR)

        try:
            raise ZeroDivisionError("division by zero")
        except ZeroDivisionError:
            with self.assertLogs(level=logging.ERROR):
                logger.exception("Zero Division Error")

        log_record = processor.get_log_record(0)

        self.assertIsNotNone(log_record)
        self.assertEqual(log_record.body, "Zero Division Error")
        self.assertEqual(
            log_record.attributes[SpanAttributes.EXCEPTION_TYPE],
            ZeroDivisionError.__name__,
        )
        self.assertEqual(
            log_record.attributes[SpanAttributes.EXCEPTION_MESSAGE],
            "division by zero",
        )
        stack_trace = log_record.attributes[
            SpanAttributes.EXCEPTION_STACKTRACE
        ]
        self.assertIsInstance(stack_trace, str)
        self.assertTrue("Traceback" in stack_trace)
        self.assertTrue("ZeroDivisionError" in stack_trace)
        self.assertTrue("division by zero" in stack_trace)
        self.assertTrue(__file__ in stack_trace)

    def test_log_record_recursive_exception(self):
        """Exception information will be included in attributes even though it is recursive"""
        processor, logger = set_up_test_logging(logging.ERROR)

        try:
            raise ZeroDivisionError(
                ZeroDivisionError(ZeroDivisionError("division by zero"))
            )
        except ZeroDivisionError:
            with self.assertLogs(level=logging.ERROR):
                logger.exception("Zero Division Error")

        log_record = processor.get_log_record(0)

        self.assertIsNotNone(log_record)
        self.assertEqual(log_record.body, "Zero Division Error")
        self.assertEqual(
            log_record.attributes[SpanAttributes.EXCEPTION_TYPE],
            ZeroDivisionError.__name__,
        )
        self.assertEqual(
            log_record.attributes[SpanAttributes.EXCEPTION_MESSAGE],
            "division by zero",
        )
        stack_trace = log_record.attributes[
            SpanAttributes.EXCEPTION_STACKTRACE
        ]
        self.assertIsInstance(stack_trace, str)
        self.assertTrue("Traceback" in stack_trace)
        self.assertTrue("ZeroDivisionError" in stack_trace)
        self.assertTrue("division by zero" in stack_trace)
        self.assertTrue(__file__ in stack_trace)

    def test_log_exc_info_false(self):
        """Exception information will not be included in attributes"""
        processor, logger = set_up_test_logging(logging.NOTSET)

        try:
            raise ZeroDivisionError("division by zero")
        except ZeroDivisionError:
            with self.assertLogs(level=logging.ERROR):
                logger.error("Zero Division Error", exc_info=False)

        log_record = processor.get_log_record(0)

        self.assertIsNotNone(log_record)
        self.assertEqual(log_record.body, "Zero Division Error")
        self.assertNotIn(SpanAttributes.EXCEPTION_TYPE, log_record.attributes)
        self.assertNotIn(
            SpanAttributes.EXCEPTION_MESSAGE, log_record.attributes
        )
        self.assertNotIn(
            SpanAttributes.EXCEPTION_STACKTRACE, log_record.attributes
        )

    def test_log_record_trace_correlation(self):
        processor, logger = set_up_test_logging(logging.WARNING)

        tracer = trace.TracerProvider().get_tracer(__name__)
        with tracer.start_as_current_span("test") as span:
            with self.assertLogs(level=logging.CRITICAL):
                logger.critical("Critical message within span")

            log_record = processor.get_log_record(0)

            self.assertEqual(log_record.body, "Critical message within span")
            self.assertEqual(log_record.severity_text, "CRITICAL")
            self.assertEqual(log_record.severity_number, SeverityNumber.FATAL)
            span_context = span.get_span_context()
            self.assertEqual(log_record.trace_id, span_context.trace_id)
            self.assertEqual(log_record.span_id, span_context.span_id)
            self.assertEqual(log_record.trace_flags, span_context.trace_flags)


def set_up_test_logging(level):
    logger_provider = LoggerProvider()
    processor = FakeProcessor()
    logger_provider.add_log_record_processor(processor)
    logger = logging.getLogger("foo")
    handler = LoggingHandler(level=level, logger_provider=logger_provider)
    logger.addHandler(handler)
    return processor, logger


class FakeProcessor(LogRecordProcessor):
    def __init__(self):
        self.log_data_emitted = []

    def emit(self, log_data: LogData):
        self.log_data_emitted.append(log_data)

    def shutdown(self):
        pass

    def force_flush(self, timeout_millis: int = 30000):
        pass

    def emit_count(self):
        return len(self.log_data_emitted)

    def get_log_record(self, i):
        return self.log_data_emitted[i].log_record
