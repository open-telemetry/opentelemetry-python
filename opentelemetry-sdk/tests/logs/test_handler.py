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

from opentelemetry._logs import SeverityNumber
from opentelemetry._logs import get_logger as APIGetLogger
from opentelemetry.attributes import BoundedAttributes
from opentelemetry.sdk import trace
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.trace import INVALID_SPAN_CONTEXT


def get_logger(level=logging.NOTSET, logger_provider=None):
    logger = logging.getLogger(__name__)
    handler = LoggingHandler(level=level, logger_provider=logger_provider)
    logger.addHandler(handler)
    return logger


class TestLoggingHandler(unittest.TestCase):
    def test_handler_default_log_level(self):
        emitter_provider_mock = Mock(spec=LoggerProvider)
        emitter_mock = APIGetLogger(
            __name__, logger_provider=emitter_provider_mock
        )
        logger = get_logger(logger_provider=emitter_provider_mock)
        # Make sure debug messages are ignored by default
        logger.debug("Debug message")
        self.assertEqual(emitter_mock.emit.call_count, 0)
        # Assert emit gets called for warning message
        with self.assertLogs(level=logging.WARNING):
            logger.warning("Warning message")
        self.assertEqual(emitter_mock.emit.call_count, 1)

    def test_handler_custom_log_level(self):
        emitter_provider_mock = Mock(spec=LoggerProvider)
        emitter_mock = APIGetLogger(
            __name__, logger_provider=emitter_provider_mock
        )
        logger = get_logger(
            level=logging.ERROR, logger_provider=emitter_provider_mock
        )
        with self.assertLogs(level=logging.WARNING):
            logger.warning("Warning message test custom log level")
        # Make sure any log with level < ERROR is ignored
        self.assertEqual(emitter_mock.emit.call_count, 0)
        with self.assertLogs(level=logging.ERROR):
            logger.error("Mumbai, we have a major problem")
        with self.assertLogs(level=logging.CRITICAL):
            logger.critical("No Time For Caution")
        self.assertEqual(emitter_mock.emit.call_count, 2)

    def test_log_record_no_span_context(self):
        emitter_provider_mock = Mock(spec=LoggerProvider)
        emitter_mock = APIGetLogger(
            __name__, logger_provider=emitter_provider_mock
        )
        logger = get_logger(logger_provider=emitter_provider_mock)
        # Assert emit gets called for warning message
        with self.assertLogs(level=logging.WARNING):
            logger.warning("Warning message")
        args, _ = emitter_mock.emit.call_args_list[0]
        log_record = args[0]

        self.assertIsNotNone(log_record)
        self.assertEqual(log_record.trace_id, INVALID_SPAN_CONTEXT.trace_id)
        self.assertEqual(log_record.span_id, INVALID_SPAN_CONTEXT.span_id)
        self.assertEqual(
            log_record.trace_flags, INVALID_SPAN_CONTEXT.trace_flags
        )

    def test_log_record_user_attributes(self):
        """Attributes can be injected into logs by adding them to the LogRecord"""
        emitter_provider_mock = Mock(spec=LoggerProvider)
        emitter_mock = APIGetLogger(
            __name__, logger_provider=emitter_provider_mock
        )
        logger = get_logger(logger_provider=emitter_provider_mock)
        # Assert emit gets called for warning message
        with self.assertLogs(level=logging.WARNING):
            logger.warning("Warning message", extra={"http.status_code": 200})
        args, _ = emitter_mock.emit.call_args_list[0]
        log_record = args[0]

        self.assertIsNotNone(log_record)
        self.assertEqual(log_record.attributes, {"http.status_code": 200})
        self.assertTrue(isinstance(log_record.attributes, BoundedAttributes))

    def test_log_record_exception(self):
        """Exception information will be included in attributes"""
        emitter_provider_mock = Mock(spec=LoggerProvider)
        emitter_mock = APIGetLogger(
            __name__, logger_provider=emitter_provider_mock
        )
        logger = get_logger(logger_provider=emitter_provider_mock)
        try:
            raise ZeroDivisionError("division by zero")
        except ZeroDivisionError:
            with self.assertLogs(level=logging.ERROR):
                logger.exception("Zero Division Error")
        args, _ = emitter_mock.emit.call_args_list[0]
        log_record = args[0]

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
        """Exception information will be included in attributes"""
        emitter_provider_mock = Mock(spec=LoggerProvider)
        emitter_mock = APIGetLogger(
            __name__, logger_provider=emitter_provider_mock
        )
        logger = get_logger(logger_provider=emitter_provider_mock)
        try:
            raise ZeroDivisionError("division by zero")
        except ZeroDivisionError:
            with self.assertLogs(level=logging.ERROR):
                logger.error("Zero Division Error", exc_info=False)
        args, _ = emitter_mock.emit.call_args_list[0]
        log_record = args[0]

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
        emitter_provider_mock = Mock(spec=LoggerProvider)
        emitter_mock = APIGetLogger(
            __name__, logger_provider=emitter_provider_mock
        )
        logger = get_logger(logger_provider=emitter_provider_mock)

        tracer = trace.TracerProvider().get_tracer(__name__)
        with tracer.start_as_current_span("test") as span:
            with self.assertLogs(level=logging.CRITICAL):
                logger.critical("Critical message within span")

            args, _ = emitter_mock.emit.call_args_list[0]
            log_record = args[0]
            self.assertEqual(log_record.body, "Critical message within span")
            self.assertEqual(log_record.severity_text, "CRITICAL")
            self.assertEqual(log_record.severity_number, SeverityNumber.FATAL)
            span_context = span.get_span_context()
            self.assertEqual(log_record.trace_id, span_context.trace_id)
            self.assertEqual(log_record.span_id, span_context.span_id)
            self.assertEqual(log_record.trace_flags, span_context.trace_flags)
