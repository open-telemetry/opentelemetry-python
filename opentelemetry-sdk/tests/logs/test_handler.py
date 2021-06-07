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
from opentelemetry.sdk.logs import LogEmitter, OTLPHandler
from opentelemetry.sdk.logs.severity import SeverityNumber
from opentelemetry.trace import INVALID_SPAN_CONTEXT


def get_logger(level=logging.NOTSET, log_emitter=None):
    logger = logging.getLogger(__name__)
    handler = OTLPHandler(level=level, log_emitter=log_emitter)
    logger.addHandler(handler)
    return logger


class TestOTLPHandler(unittest.TestCase):
    def test_handler_default_log_level(self):
        emitter_mock = Mock(spec=LogEmitter)
        logger = get_logger(log_emitter=emitter_mock)
        # Make sure debug messages are ignored by default
        logger.debug("Debug message")
        self.assertEqual(emitter_mock.emit.call_count, 0)
        # Assert emit gets called for warning message
        logger.warning("Wanrning message")
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
        logger.warning("Wanrning message")
        log_record, *_ = emitter_mock.emit.call_args.args
        self.assertIsNotNone(log_record)
        self.assertEqual(log_record.trace_id, INVALID_SPAN_CONTEXT.trace_id)
        self.assertEqual(log_record.span_id, INVALID_SPAN_CONTEXT.span_id)
        self.assertEqual(
            log_record.trace_flags, INVALID_SPAN_CONTEXT.trace_flags
        )

    def test_log_record_trace_correlation(self):
        emitter_mock = Mock(spec=LogEmitter)
        logger = get_logger(log_emitter=emitter_mock)

        tracer = trace.TracerProvider().get_tracer(__name__)
        with tracer.start_as_current_span("test") as span:
            logger.critical("Critical message within span")

            log_record, *_ = emitter_mock.emit.call_args.args
            self.assertEqual(log_record.body, "Critical message within span")
            self.assertEqual(log_record.severity_text, "CRITICAL")
            self.assertEqual(log_record.severity_number, SeverityNumber.FATAL)
            span_context = span.get_span_context()
            self.assertEqual(log_record.trace_id, span_context.trace_id)
            self.assertEqual(log_record.span_id, span_context.span_id)
            self.assertEqual(log_record.trace_flags, span_context.trace_flags)
