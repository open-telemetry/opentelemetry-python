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

# pylint: disable=protected-access,no-self-use

import unittest
from unittest.mock import Mock, patch

from opentelemetry._events import Event
from opentelemetry._logs import SeverityNumber, set_logger_provider
from opentelemetry.sdk._events import EventLoggerProvider
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs._internal import Logger, NoOpLogger
from opentelemetry.sdk.environment_variables import OTEL_SDK_DISABLED


class TestEventLoggerProvider(unittest.TestCase):
    def test_event_logger_provider(self):
        logger_provider = LoggerProvider()
        event_logger_provider = EventLoggerProvider(
            logger_provider=logger_provider
        )

        self.assertEqual(
            event_logger_provider._logger_provider,
            logger_provider,
        )

    def test_event_logger_provider_default(self):
        logger_provider = LoggerProvider()
        set_logger_provider(logger_provider)
        event_logger_provider = EventLoggerProvider()

        self.assertEqual(
            event_logger_provider._logger_provider,
            logger_provider,
        )

    def test_get_event_logger(self):
        logger_provider = LoggerProvider()
        event_logger = EventLoggerProvider(logger_provider).get_event_logger(
            "name",
            version="version",
            schema_url="schema_url",
            attributes={"key": "value"},
        )
        self.assertTrue(
            event_logger._logger,
            Logger,
        )
        logger = event_logger._logger
        self.assertEqual(logger._instrumentation_scope.name, "name")
        self.assertEqual(logger._instrumentation_scope.version, "version")
        self.assertEqual(
            logger._instrumentation_scope.schema_url, "schema_url"
        )
        self.assertEqual(
            logger._instrumentation_scope.attributes, {"key": "value"}
        )

    @patch.dict("os.environ", {OTEL_SDK_DISABLED: "true"})
    def test_get_event_logger_with_sdk_disabled(self):
        logger_provider = LoggerProvider()
        event_logger = EventLoggerProvider(logger_provider).get_event_logger(
            "name",
            version="version",
            schema_url="schema_url",
            attributes={"key": "value"},
        )
        self.assertIsInstance(event_logger._logger, NoOpLogger)

    def test_force_flush(self):
        logger_provider = Mock()
        event_logger = EventLoggerProvider(logger_provider)
        event_logger.force_flush(1000)
        logger_provider.force_flush.assert_called_once_with(1000)

    def test_shutdown(self):
        logger_provider = Mock()
        event_logger = EventLoggerProvider(logger_provider)
        event_logger.shutdown()
        logger_provider.shutdown.assert_called_once()

    @patch("opentelemetry.sdk._logs._internal.LoggerProvider.get_logger")
    def test_event_logger(self, logger_mock):
        logger_provider = LoggerProvider()
        logger_mock_inst = Mock()
        logger_mock.return_value = logger_mock_inst
        EventLoggerProvider(logger_provider).get_event_logger(
            "name",
            version="version",
            schema_url="schema_url",
            attributes={"key": "value"},
        )
        logger_mock.assert_called_once_with(
            "name", "version", "schema_url", {"key": "value"}
        )

    @patch("opentelemetry.sdk._events.LogRecord")
    @patch("opentelemetry.sdk._logs._internal.LoggerProvider.get_logger")
    def test_event_logger_emit(self, logger_mock, log_record_mock):
        logger_provider = LoggerProvider()
        logger_mock_inst = Mock()
        logger_mock.return_value = logger_mock_inst
        event_logger = EventLoggerProvider(logger_provider).get_event_logger(
            "name",
            version="version",
            schema_url="schema_url",
            attributes={"key": "value"},
        )
        logger_mock.assert_called_once_with(
            "name", "version", "schema_url", {"key": "value"}
        )
        now = Mock()
        trace_id = Mock()
        span_id = Mock()
        trace_flags = Mock()
        event = Event(
            name="test_event",
            timestamp=now,
            trace_id=trace_id,
            span_id=span_id,
            trace_flags=trace_flags,
            body="test body",
            severity_number=SeverityNumber.ERROR,
            attributes={
                "key": "val",
                "foo": "bar",
                "event.name": "not this one",
            },
        )
        log_record_mock_inst = Mock()
        log_record_mock.return_value = log_record_mock_inst
        event_logger.emit(event)
        log_record_mock.assert_called_once_with(
            timestamp=now,
            observed_timestamp=None,
            trace_id=trace_id,
            span_id=span_id,
            trace_flags=trace_flags,
            severity_text=None,
            severity_number=SeverityNumber.ERROR,
            body="test body",
            resource=event_logger._logger.resource,
            attributes={
                "key": "val",
                "foo": "bar",
                "event.name": "test_event",
            },
        )
        logger_mock_inst.emit.assert_called_once_with(log_record_mock_inst)

    @patch("opentelemetry.sdk._events.LogRecord")
    @patch("opentelemetry.sdk._logs._internal.LoggerProvider.get_logger")
    def test_event_logger_emit_sdk_disabled(
        self, logger_mock, log_record_mock
    ):
        logger_provider = LoggerProvider()
        logger_mock_inst = Mock(spec=NoOpLogger)
        logger_mock.return_value = logger_mock_inst
        event_logger = EventLoggerProvider(logger_provider).get_event_logger(
            "name",
            version="version",
            schema_url="schema_url",
            attributes={"key": "value"},
        )
        logger_mock.assert_called_once_with(
            "name", "version", "schema_url", {"key": "value"}
        )
        now = Mock()
        trace_id = Mock()
        span_id = Mock()
        trace_flags = Mock()
        event = Event(
            name="test_event",
            timestamp=now,
            trace_id=trace_id,
            span_id=span_id,
            trace_flags=trace_flags,
            body="test body",
            severity_number=SeverityNumber.ERROR,
            attributes={
                "key": "val",
                "foo": "bar",
                "event.name": "not this one",
            },
        )
        log_record_mock_inst = Mock()
        log_record_mock.return_value = log_record_mock_inst
        event_logger.emit(event)
        logger_mock_inst.emit.assert_not_called()
