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

from opentelemetry._logs import LogRecord as APILogRecord
from opentelemetry._logs import NoOpLogger, SeverityNumber
from opentelemetry.context import get_current
from opentelemetry.sdk._logs import (
    Logger,
    LoggerProvider,
    LogRecord,
)
from opentelemetry.sdk._logs._internal import (
    LoggerConfig,
    SynchronousMultiLogRecordProcessor,
    create_logger_configurator_by_name,
    create_logger_configurator_with_pattern,
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
        logger_provider = LoggerProvider(
            min_severity_level=SeverityNumber.DEBUG4, trace_based_sampling=True
        )
        resource_patch.assert_called_once()
        self.assertIsNotNone(logger_provider._resource)
        self.assertTrue(
            isinstance(
                logger_provider._multi_log_record_processor,
                SynchronousMultiLogRecordProcessor,
            )
        )
        self.assertEqual(
            logger_provider._min_severity_level, SeverityNumber.DEBUG4
        )
        self.assertTrue(logger_provider._trace_based_sampling)
        self.assertIsNotNone(logger_provider._at_exit_handler)


class TestLogger(unittest.TestCase):
    @staticmethod
    def _get_logger(config=None):
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
            config=config,
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
        api_log_record = APILogRecord(
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
        self.assertEqual(log_record.context, {})
        self.assertEqual(log_record.severity_number, None)
        self.assertEqual(log_record.severity_text, None)
        self.assertEqual(log_record.body, "a log line")
        self.assertEqual(log_record.attributes, {})
        self.assertEqual(log_record.event_name, None)
        self.assertEqual(log_record.resource, logger.resource)

    def test_can_emit_with_keywords_arguments(self):
        logger, log_record_processor_mock = self._get_logger()

        logger.emit(
            timestamp=100,
            observed_timestamp=101,
            context=get_current(),
            severity_number=SeverityNumber.WARN,
            severity_text="warn",
            body="a body",
            attributes={"some": "attributes"},
            event_name="event_name",
        )
        log_record_processor_mock.on_emit.assert_called_once()
        log_data = log_record_processor_mock.on_emit.call_args.args[0]
        log_record = log_data.log_record
        self.assertTrue(isinstance(log_record, LogRecord))
        self.assertEqual(log_record.timestamp, 100)
        self.assertEqual(log_record.observed_timestamp, 101)
        self.assertEqual(log_record.context, {})
        self.assertEqual(log_record.severity_number, SeverityNumber.WARN)
        self.assertEqual(log_record.severity_text, "warn")
        self.assertEqual(log_record.body, "a body")
        self.assertEqual(log_record.attributes, {"some": "attributes"})
        self.assertEqual(log_record.event_name, "event_name")
        self.assertEqual(log_record.resource, logger.resource)

    def test_emit_logrecord_with_min_severity_filtering(self):
        """Test that logs below minimum severity are filtered out"""
        config = LoggerConfig(minimum_severity_level=SeverityNumber.DEBUG4)
        logger, log_record_processor_mock = self._get_logger(config)

        log_record_info = LogRecord(
            observed_timestamp=0,
            body="info log line",
            severity_number=SeverityNumber.DEBUG,
            severity_text="DEBUG",
        )

        logger.emit(log_record_info)
        log_record_processor_mock.on_emit.assert_not_called()

        log_record_processor_mock.reset_mock()

        log_record_error = LogRecord(
            observed_timestamp=0,
            body="error log line",
            severity_number=SeverityNumber.ERROR,
            severity_text="ERROR",
        )

        logger.emit(log_record_error)

        log_record_processor_mock.on_emit.assert_called_once()
        log_data = log_record_processor_mock.on_emit.call_args.args[0]
        self.assertTrue(isinstance(log_data.log_record, LogRecord))
        self.assertEqual(
            log_data.log_record.severity_number, SeverityNumber.ERROR
        )

    def test_emit_logrecord_with_min_severity_unspecified(self):
        """Test that when min severity is UNSPECIFIED, all logs are emitted"""
        logger, log_record_processor_mock = self._get_logger()
        log_record = LogRecord(
            observed_timestamp=0,
            body="debug log line",
            severity_number=SeverityNumber.DEBUG,
            severity_text="DEBUG",
        )
        logger.emit(log_record)
        log_record_processor_mock.on_emit.assert_called_once()

    def test_emit_logrecord_with_trace_based_sampling_filtering(self):
        """Test that logs are filtered based on trace sampling state"""
        config = LoggerConfig(trace_based_sampling=True)
        logger, log_record_processor_mock = self._get_logger(config)

        mock_span_context = Mock()
        mock_span_context.is_valid = True
        mock_span_context.trace_flags.sampled = False

        mock_span = Mock()
        mock_span.get_span_context.return_value = mock_span_context

        mock_context = Mock()

        with patch(
            "opentelemetry.sdk._logs._internal.get_current_span",
            return_value=mock_span,
        ):
            log_record = LogRecord(
                observed_timestamp=0,
                body="should be dropped",
                severity_number=SeverityNumber.INFO,
                severity_text="INFO",
                context=mock_context,
            )

            logger.emit(log_record)
            log_record_processor_mock.on_emit.assert_not_called()

        log_record_processor_mock.reset_mock()

        mock_span_context = Mock()
        mock_span_context.is_valid = True
        mock_span_context.trace_flags.sampled = True

        mock_span = Mock()
        mock_span.get_span_context.return_value = mock_span_context

    def test_emit_logrecord_trace_filtering_disabled(self):
        """Test that when trace-based filtering is disabled, all logs are emitted"""
        logger, log_record_processor_mock = self._get_logger()

        mock_span_context = Mock()
        mock_span_context.is_valid = False
        mock_span_context.trace_flags.sampled = False

        mock_span = Mock()
        mock_span.get_span_context.return_value = mock_span_context

        mock_context = Mock()

        with patch(
            "opentelemetry.sdk._logs._internal.get_current_span",
            return_value=mock_span,
        ):
            log_record = LogRecord(
                observed_timestamp=0,
                body="should be emitted when filtering disabled",
                severity_number=SeverityNumber.INFO,
                severity_text="INFO",
                context=mock_context,
            )

            logger.emit(log_record)
            log_record_processor_mock.on_emit.assert_called_once()

    def test_emit_logrecord_trace_filtering_edge_cases(self):
        """Test edge cases for trace-based filtering"""
        config = LoggerConfig(trace_based_sampling=True)
        logger, log_record_processor_mock = self._get_logger(config)

        mock_span_context = Mock()
        mock_span_context.is_valid = False
        mock_span_context.trace_flags.sampled = True

        mock_span = Mock()
        mock_span.get_span_context.return_value = mock_span_context

        mock_context = Mock()

        with patch(
            "opentelemetry.sdk._logs._internal.get_current_span",
            return_value=mock_span,
        ):
            log_record = LogRecord(
                observed_timestamp=0,
                body="invalid but sampled",
                severity_number=SeverityNumber.INFO,
                severity_text="INFO",
                context=mock_context,
            )

            logger.emit(log_record)
            log_record_processor_mock.on_emit.assert_called_once()

        log_record_processor_mock.reset_mock()

        mock_span_context = Mock()
        mock_span_context.is_valid = True
        mock_span_context.trace_flags.sampled = False

        mock_span = Mock()
        mock_span.get_span_context.return_value = mock_span_context

        with patch(
            "opentelemetry.sdk._logs._internal.get_current_span",
            return_value=mock_span,
        ):
            log_record = LogRecord(
                observed_timestamp=0,
                body="valid but not sampled",
                severity_number=SeverityNumber.INFO,
                severity_text="INFO",
                context=mock_context,
            )

            logger.emit(log_record)
            log_record_processor_mock.on_emit.assert_not_called()

    def test_emit_both_min_severity_and_trace_based_sampling_filtering(self):
        """Test that both min severity and trace-based filtering work together"""
        config = LoggerConfig(
            minimum_severity_level=SeverityNumber.WARN,
            trace_based_sampling=True,
        )
        logger, log_record_processor_mock = self._get_logger(config)

        mock_span_context = Mock()
        mock_span_context.is_valid = True
        mock_span_context.trace_flags.sampled = True

        mock_span = Mock()
        mock_span.get_span_context.return_value = mock_span_context

        mock_context = Mock()

        with patch(
            "opentelemetry.sdk._logs._internal.get_current_span",
            return_value=mock_span,
        ):
            log_record_info = LogRecord(
                observed_timestamp=0,
                body="info log line",
                severity_number=SeverityNumber.INFO,
                severity_text="INFO",
                context=mock_context,
            )

            logger.emit(log_record_info)
            log_record_processor_mock.on_emit.assert_not_called()

            log_record_processor_mock.reset_mock()

            log_record_error = LogRecord(
                observed_timestamp=0,
                body="error log line",
                severity_number=SeverityNumber.ERROR,
                severity_text="ERROR",
                context=mock_context,
            )

            logger.emit(log_record_error)
            log_record_processor_mock.on_emit.assert_called_once()

    def test_emit_logrecord_with_disabled_logger(self):
        """Test that disabled loggers don't emit any logs"""
        config = LoggerConfig(disabled=True)
        logger, log_record_processor_mock = self._get_logger(config)

        log_record = LogRecord(
            observed_timestamp=0,
            body="this should be dropped",
            severity_number=SeverityNumber.ERROR,
            severity_text="ERROR",
        )

        logger.emit(log_record)
        log_record_processor_mock.on_emit.assert_not_called()

    def test_logger_config_property(self):
        """Test that logger config property works correctly"""
        config = LoggerConfig(
            disabled=True,
            minimum_severity_level=SeverityNumber.WARN,
            trace_based_sampling=True,
        )
        logger, _ = self._get_logger(config)

        self.assertEqual(logger.config.disabled, True)
        self.assertEqual(
            logger.config.minimum_severity_level, SeverityNumber.WARN
        )
        self.assertEqual(logger.config.trace_based_sampling, True)

    def test_logger_configurator_behavior(self):
        """Test LoggerConfigurator functionality including custom configurators and dynamic updates"""

        logger_configs = {
            "test.database": LoggerConfig(
                minimum_severity_level=SeverityNumber.ERROR
            ),
            "test.auth": LoggerConfig(disabled=True),
            "test.performance": LoggerConfig(trace_based_sampling=True),
        }

        configurator = create_logger_configurator_by_name(logger_configs)

        provider = LoggerProvider(logger_configurator=configurator)

        db_logger = provider.get_logger("test.database")
        self.assertEqual(
            db_logger.config.minimum_severity_level, SeverityNumber.ERROR
        )
        self.assertFalse(db_logger.config.disabled)
        self.assertFalse(db_logger.config.trace_based_sampling)

        auth_logger = provider.get_logger("test.auth")
        self.assertTrue(auth_logger.config.disabled)

        perf_logger = provider.get_logger("test.performance")
        self.assertTrue(perf_logger.config.trace_based_sampling)

        other_logger = provider.get_logger("test.other")
        self.assertEqual(
            other_logger.config.minimum_severity_level,
            SeverityNumber.UNSPECIFIED,
        )
        self.assertFalse(other_logger.config.disabled)
        self.assertFalse(other_logger.config.trace_based_sampling)

    def test_logger_configurator_pattern_matching(self):
        """Test LoggerConfigurator with pattern matching"""
        patterns = [
            (
                "test.database.*",
                LoggerConfig(minimum_severity_level=SeverityNumber.ERROR),
            ),
            ("test.*.debug", LoggerConfig(disabled=True)),
            ("test.*", LoggerConfig(trace_based_sampling=True)),
            ("*", LoggerConfig(minimum_severity_level=SeverityNumber.WARN)),
        ]

        configurator = create_logger_configurator_with_pattern(patterns)
        provider = LoggerProvider(logger_configurator=configurator)

        db_logger = provider.get_logger("test.database.connection")
        self.assertEqual(
            db_logger.config.minimum_severity_level, SeverityNumber.ERROR
        )

        debug_logger = provider.get_logger("test.module.debug")
        self.assertTrue(debug_logger.config.disabled)

        general_logger = provider.get_logger("test.module")
        self.assertTrue(general_logger.config.trace_based_sampling)

        other_logger = provider.get_logger("other.module")
        self.assertEqual(
            other_logger.config.minimum_severity_level, SeverityNumber.WARN
        )

    def test_logger_configurator_dynamic_updates(self):
        """Test that LoggerConfigurator updates apply to existing loggers"""
        initial_configs = {
            "test.module": LoggerConfig(
                minimum_severity_level=SeverityNumber.INFO
            )
        }

        initial_configurator = create_logger_configurator_by_name(
            initial_configs
        )

        provider = LoggerProvider(logger_configurator=initial_configurator)

        logger = provider.get_logger("test.module")
        self.assertEqual(
            logger.config.minimum_severity_level, SeverityNumber.INFO
        )
        self.assertFalse(logger.config.disabled)

        updated_configs = {
            "test.module": LoggerConfig(
                minimum_severity_level=SeverityNumber.ERROR, disabled=True
            )
        }
        updated_configurator = create_logger_configurator_by_name(
            updated_configs
        )

        provider.set_logger_configurator(updated_configurator)

        self.assertEqual(
            logger.config.minimum_severity_level, SeverityNumber.ERROR
        )
        self.assertTrue(logger.config.disabled)

        new_logger = provider.get_logger("test.module")
        self.assertEqual(
            new_logger.config.minimum_severity_level, SeverityNumber.ERROR
        )
        self.assertTrue(new_logger.config.disabled)

    def test_logger_configurator_returns_none(self):
        """Test LoggerConfigurator that returns None falls back to default"""

        def none_configurator(scope):
            return None

        provider = LoggerProvider(
            logger_configurator=none_configurator,
            min_severity_level=SeverityNumber.WARN,
            trace_based_sampling=True,
        )

        logger = provider.get_logger("test.module")

        self.assertEqual(
            logger.config.minimum_severity_level, SeverityNumber.WARN
        )
        self.assertTrue(logger.config.trace_based_sampling)
        self.assertFalse(logger.config.disabled)

    @staticmethod
    def _selective_configurator(scope):
        if scope.name == "disabled.logger":
            return LoggerConfig(disabled=True)
        if scope.name == "error.logger":
            return LoggerConfig(minimum_severity_level=SeverityNumber.ERROR)
        if scope.name == "trace.logger":
            return LoggerConfig(trace_based_sampling=True)
        return LoggerConfig()

    def test_logger_configurator_with_filtering(self):
        """Test that LoggerConfigurator configs are properly applied during filtering"""

        provider = LoggerProvider(
            logger_configurator=self._selective_configurator
        )

        disabled_logger = provider.get_logger("disabled.logger")
        log_record_processor_mock = Mock()
        disabled_logger._multi_log_record_processor = log_record_processor_mock

        log_record = LogRecord(
            observed_timestamp=0,
            body="should not emit",
            severity_number=SeverityNumber.INFO,
        )
        disabled_logger.emit(log_record)
        log_record_processor_mock.on_emit.assert_not_called()

        error_logger = provider.get_logger("error.logger")
        log_record_processor_mock = Mock()
        error_logger._multi_log_record_processor = log_record_processor_mock

        info_record = LogRecord(
            observed_timestamp=0,
            body="info message",
            severity_number=SeverityNumber.INFO,
        )
        error_logger.emit(info_record)
        log_record_processor_mock.on_emit.assert_not_called()

        error_record = LogRecord(
            observed_timestamp=0,
            body="error message",
            severity_number=SeverityNumber.ERROR,
        )
        error_logger.emit(error_record)
        log_record_processor_mock.on_emit.assert_called_once()

        trace_logger = provider.get_logger("trace.logger")
        log_record_processor_mock = Mock()
        trace_logger._multi_log_record_processor = log_record_processor_mock

        mock_span_context = Mock()
        mock_span_context.is_valid = True
        mock_span_context.trace_flags.sampled = False

        mock_span = Mock()
        mock_span.get_span_context.return_value = mock_span_context

        mock_context = Mock()

        with patch(
            "opentelemetry.sdk._logs._internal.get_current_span",
            return_value=mock_span,
        ):
            trace_record = LogRecord(
                observed_timestamp=0,
                body="unsampled trace message",
                severity_number=SeverityNumber.INFO,
                context=mock_context,
            )
            trace_logger.emit(trace_record)
            log_record_processor_mock.on_emit.assert_not_called()
