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

from opentelemetry.sdk import trace
from opentelemetry.sdk._logs import LogEmitter, LoggingHandler
from opentelemetry.sdk._logs.severity import SeverityNumber
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.trace import INVALID_SPAN_CONTEXT


def get_logger(level=logging.NOTSET, log_emitter=None):
    logger = logging.getLogger(__name__)
    handler = LoggingHandler(level=level, log_emitter=log_emitter)
    logger.addHandler(handler)
    return logger


class TestLoggingHandler(unittest.TestCase):
    def test_handler_default_log_level(self):
        emitter_mock = Mock(spec=LogEmitter)
        logger = get_logger(log_emitter=emitter_mock)
        # Make sure debug messages are ignored by default
        logger.debug("Debug message")
        self.assertEqual(emitter_mock.emit.call_count, 0)
        # Assert emit gets called for warning message
        logger.warning("Warning message")
        self.assertEqual(emitter_mock.emit.call_count, 1)

    def test_handler_custom_log_level(self):
        emitter_mock = Mock(spec=LogEmitter)
        logger = get_logger(level=logging.ERROR, log_emitter=emitter_mock)
        logger.warning("Warning message test custom log level")
        # Make sure any log with level < ERROR is ignored
        self.assertEqual(emitter_mock.emit.call_count, 0)
        logger.error("Mumbai, we have a major problem")
        logger.critical("No Time For Caution")
        self.assertEqual(emitter_mock.emit.call_count, 2)

    def test_log_record_no_span_context(self):
        emitter_mock = Mock(spec=LogEmitter)
        logger = get_logger(log_emitter=emitter_mock)
        # Assert emit gets called for warning message
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
        emitter_mock = Mock(spec=LogEmitter)
        logger = get_logger(log_emitter=emitter_mock)
        # Assert emit gets called for warning message
        logger.warning("Warning message", extra={"http.status_code": 200})
        args, _ = emitter_mock.emit.call_args_list[0]
        log_record = args[0]

        self.assertIsNotNone(log_record)
        self.assertEqual(log_record.attributes, {"http.status_code": 200})

    def test_log_record_exception(self):
        """Exception information will be included in attributes"""
        emitter_mock = Mock(spec=LogEmitter)
        logger = get_logger(log_emitter=emitter_mock)
        try:
            raise ZeroDivisionError("division by zero")
        except ZeroDivisionError:
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

    def test_log_record_trace_correlation(self):
        emitter_mock = Mock(spec=LogEmitter)
        logger = get_logger(log_emitter=emitter_mock)

        tracer = trace.TracerProvider().get_tracer(__name__)
        with tracer.start_as_current_span("test") as span:
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
