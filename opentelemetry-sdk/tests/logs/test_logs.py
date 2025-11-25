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

import unittest
from unittest.mock import Mock, patch

from opentelemetry._logs import LogRecord, SeverityNumber
from opentelemetry.context import get_current
from opentelemetry.sdk._logs import (
    Logger,
    LoggerProvider,
    ReadableLogRecord,
)
from opentelemetry.sdk._logs._internal import (
    NoOpLogger,
    SynchronousMultiLogRecordProcessor,
)
from opentelemetry.sdk.environment_variables import OTEL_SDK_DISABLED
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope


class TestLoggerProvider(unittest.TestCase):
    def test_resource(self):
        """
        `LoggerProvider` provides a way to allow a `Resource` to be specified.
        """

        logger_provider_0 = LoggerProvider()
        logger_provider_1 = LoggerProvider()

        self.assertEqual(
            logger_provider_0.resource,
            logger_provider_1.resource,
        )
        self.assertIsInstance(logger_provider_0.resource, Resource)
        self.assertIsInstance(logger_provider_1.resource, Resource)

        resource = Resource({"key": "value"})
        self.assertIs(LoggerProvider(resource=resource).resource, resource)

    def test_get_logger(self):
        """
        `LoggerProvider.get_logger` arguments are used to create an
        `InstrumentationScope` object on the created `Logger`.
        """

        logger = LoggerProvider().get_logger(
            "name",
            version="version",
            schema_url="schema_url",
            attributes={"key": "value"},
        )

        self.assertEqual(logger._instrumentation_scope.name, "name")
        self.assertEqual(logger._instrumentation_scope.version, "version")
        self.assertEqual(
            logger._instrumentation_scope.schema_url, "schema_url"
        )
        self.assertEqual(
            logger._instrumentation_scope.attributes, {"key": "value"}
        )

    @patch.dict("os.environ", {OTEL_SDK_DISABLED: "true"})
    def test_get_logger_with_sdk_disabled(self):
        logger = LoggerProvider().get_logger(Mock())

        self.assertIsInstance(logger, NoOpLogger)

    @patch.object(Resource, "create")
    def test_logger_provider_init(self, resource_patch):
        logger_provider = LoggerProvider()
        resource_patch.assert_called_once()
        self.assertIsNotNone(logger_provider._resource)
        self.assertTrue(
            isinstance(
                logger_provider._multi_log_record_processor,
                SynchronousMultiLogRecordProcessor,
            )
        )
        self.assertIsNotNone(logger_provider._at_exit_handler)


class TestReadableLogRecord(unittest.TestCase):
    def setUp(self):
        self.log_record = LogRecord(
            timestamp=1234567890,
            observed_timestamp=1234567891,
            body="Test log message",
            attributes={"key": "value"},
            severity_number=SeverityNumber.INFO,
            severity_text="INFO",
        )
        self.resource = Resource({"service.name": "test-service"})
        self.readable_log_record = ReadableLogRecord(
            log_record=self.log_record,
            resource=self.resource,
            instrumentation_scope=None,
        )

    def test_readable_log_record_is_frozen(self):
        """Test that ReadableLogRecord is frozen and cannot be modified."""
        with self.assertRaises((AttributeError, TypeError)):
            self.readable_log_record.log_record = LogRecord(
                timestamp=999, body="Modified"
            )

    def test_readable_log_record_can_read_attributes(self):
        """Test that ReadableLogRecord provides read access to all fields."""
        self.assertEqual(
            self.readable_log_record.log_record.timestamp, 1234567890
        )
        self.assertEqual(
            self.readable_log_record.log_record.body, "Test log message"
        )
        self.assertEqual(
            self.readable_log_record.log_record.attributes["key"], "value"
        )
        self.assertEqual(
            self.readable_log_record.resource.attributes["service.name"],
            "test-service",
        )


class TestLogger(unittest.TestCase):
    @staticmethod
    def _get_logger():
        log_record_processor_mock = Mock()
        logger = Logger(
            resource=Resource.create({}),
            multi_log_record_processor=log_record_processor_mock,
            instrumentation_scope=InstrumentationScope(
                "name",
                "version",
                "schema_url",
                {"an": "attribute"},
            ),
        )
        return logger, log_record_processor_mock

    def test_can_emit_logrecord(self):
        logger, log_record_processor_mock = self._get_logger()
        log_record = LogRecord(
            observed_timestamp=0,
            body="a log line",
        )

        logger.emit(log_record)
        log_record_processor_mock.on_emit.assert_called_once()
        log_data = log_record_processor_mock.on_emit.call_args.args[0]
        self.assertTrue(isinstance(log_data.log_record, LogRecord))
        self.assertTrue(log_data.log_record is log_record)

    def test_can_emit_api_logrecord(self):
        logger, log_record_processor_mock = self._get_logger()
        api_log_record = LogRecord(
            observed_timestamp=0,
            body="a log line",
        )
        logger.emit(api_log_record)
        log_record_processor_mock.on_emit.assert_called_once()
        log_data = log_record_processor_mock.on_emit.call_args.args[0]
        log_record = log_data.log_record
        self.assertTrue(isinstance(log_record, LogRecord))
        self.assertEqual(log_record.timestamp, None)
        self.assertEqual(log_record.observed_timestamp, 0)
        self.assertIsNotNone(log_record.context)
        self.assertEqual(log_record.severity_number, None)
        self.assertEqual(log_record.severity_text, None)
        self.assertEqual(log_record.body, "a log line")
        self.assertEqual(log_record.attributes, {})
        self.assertEqual(log_record.event_name, None)
        self.assertEqual(log_data.resource, logger.resource)

    def test_can_emit_with_keywords_arguments(self):
        logger, log_record_processor_mock = self._get_logger()

        log_record = LogRecord(
            timestamp=100,
            observed_timestamp=101,
            context=get_current(),
            severity_number=SeverityNumber.WARN,
            severity_text="warn",
            body="a body",
            attributes={"some": "attributes"},
            event_name="event_name",
        )
        logger.emit(log_record)
        log_record_processor_mock.on_emit.assert_called_once()
        log_data = log_record_processor_mock.on_emit.call_args.args[0]
        result_log_record = log_data.log_record
        self.assertTrue(isinstance(result_log_record, LogRecord))
        self.assertEqual(result_log_record.timestamp, 100)
        self.assertEqual(result_log_record.observed_timestamp, 101)
        self.assertIsNotNone(result_log_record.context)
        self.assertEqual(
            result_log_record.severity_number, SeverityNumber.WARN
        )
        self.assertEqual(result_log_record.severity_text, "warn")
        self.assertEqual(result_log_record.body, "a body")
        self.assertEqual(result_log_record.attributes, {"some": "attributes"})
        self.assertEqual(result_log_record.event_name, "event_name")
        self.assertEqual(log_data.resource, logger.resource)
