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

import importlib
import logging
import unittest
from unittest.mock import Mock, patch

import opentelemetry.sdk._logs._internal as _logs_internal
from opentelemetry._logs import LogRecord, SeverityNumber
from opentelemetry.attributes import BoundedAttributes
from opentelemetry.context import get_current
from opentelemetry.metrics import NoOpMeterProvider
from opentelemetry.sdk._logs import (
    Logger,
    LoggerProvider,
    ReadableLogRecord,
    ReadWriteLogRecord,
)
from opentelemetry.sdk._logs._internal import (
    _OTEL_LOG_LEVEL_TO_PYTHON,
    LoggerMetrics,
    NoOpLogger,
    SynchronousMultiLogRecordProcessor,
    _disable_logger_configurator,
    _LoggerConfig,
    _RuleBasedLoggerConfigurator,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_LOG_LEVEL,
    OTEL_SDK_DISABLED,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import (
    InstrumentationScope,
    _scope_name_matches_glob,
)
from opentelemetry.semconv.attributes import exception_attributes


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

    def test_default_logger_configurator(self):
        provider = LoggerProvider()
        logger = provider.get_logger("module_name", "1.0", "schema_url")
        other_logger = provider.get_logger(
            "other_module_name", "1.0", "schema_url"
        )
        self.assertTrue(logger._is_enabled())
        self.assertTrue(other_logger._is_enabled())

    def test_logger_provider_with_disabled_configurator(self):
        provider = LoggerProvider(
            _logger_configurator=_disable_logger_configurator
        )
        logger = provider.get_logger("test")
        self.assertFalse(logger._is_enabled())

    def test_logger_provider_with_custom_configurator(self):
        def configurator(scope):
            if scope.name == "disabled_logger":
                return _LoggerConfig(is_enabled=False)
            return _LoggerConfig.default()

        provider = LoggerProvider(_logger_configurator=configurator)
        enabled = provider.get_logger("enabled_logger")
        disabled = provider.get_logger("disabled_logger")
        self.assertTrue(enabled._is_enabled())
        self.assertFalse(disabled._is_enabled())

    def test_set_logger_configurator_updates_existing_loggers(self):
        provider = LoggerProvider()
        logger = provider.get_logger("test")
        self.assertTrue(logger._is_enabled())

        provider._set_logger_configurator(
            logger_configurator=_disable_logger_configurator
        )
        self.assertFalse(logger._is_enabled())

    def test_set_logger_configurator_affects_new_loggers(self):
        provider = LoggerProvider()
        provider._set_logger_configurator(
            logger_configurator=_disable_logger_configurator
        )
        logger = provider.get_logger("new_logger")
        self.assertFalse(logger._is_enabled())

    # pylint: disable-next=no-self-use
    def test_disabled_logger_skips_emit(self):
        provider = LoggerProvider(
            _logger_configurator=_disable_logger_configurator
        )
        logger = provider.get_logger("test")
        processor_mock = Mock()
        provider.add_log_record_processor(processor_mock)

        logger.emit(
            LogRecord(observed_timestamp=0, body="should not be emitted")
        )
        processor_mock.on_emit.assert_not_called()

    def test_rule_based_logger_configurator(self):
        rules = [
            (
                _scope_name_matches_glob(glob_pattern="module_name"),
                _LoggerConfig(is_enabled=True),
            ),
            (
                _scope_name_matches_glob(glob_pattern="other_module_name"),
                _LoggerConfig(is_enabled=False),
            ),
        ]
        configurator = _RuleBasedLoggerConfigurator(
            rules=rules, default_config=_LoggerConfig(is_enabled=True)
        )

        provider = LoggerProvider()
        logger = provider.get_logger("module_name", "1.0", "schema_url")
        other_logger = provider.get_logger(
            "other_module_name", "1.0", "schema_url"
        )

        self.assertTrue(logger._is_enabled())
        self.assertTrue(other_logger._is_enabled())

        provider._set_logger_configurator(logger_configurator=configurator)

        self.assertTrue(logger._is_enabled())
        self.assertFalse(other_logger._is_enabled())

    def test_rule_based_logger_configurator_default_when_rules_dont_match(
        self,
    ):
        rules = [
            (
                _scope_name_matches_glob(glob_pattern="module_name"),
                _LoggerConfig(is_enabled=False),
            ),
        ]
        configurator = _RuleBasedLoggerConfigurator(
            rules=rules, default_config=_LoggerConfig(is_enabled=True)
        )

        provider = LoggerProvider()
        logger = provider.get_logger("module_name", "1.0", "schema_url")
        other_logger = provider.get_logger(
            "other_module_name", "1.0", "schema_url"
        )

        self.assertTrue(logger._is_enabled())
        self.assertTrue(other_logger._is_enabled())

        provider._set_logger_configurator(logger_configurator=configurator)

        self.assertFalse(logger._is_enabled())
        self.assertTrue(other_logger._is_enabled())

    def test_rule_based_configurator_first_match_wins(self):
        disabled_config = _LoggerConfig(is_enabled=False)
        enabled_config = _LoggerConfig(is_enabled=True)
        configurator = _RuleBasedLoggerConfigurator(
            rules=[
                (lambda s: s.name == "foo", disabled_config),
                (lambda s: s.name == "foo", enabled_config),
            ],
            default_config=enabled_config,
        )
        scope = InstrumentationScope("foo", "1.0")
        result = configurator(scope)
        self.assertFalse(result.is_enabled)


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
            logger_metrics=LoggerMetrics(NoOpMeterProvider()),
            _logger_config=_LoggerConfig.default(),
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

    def test_emit_with_exception_adds_attributes(self):
        logger, log_record_processor_mock = self._get_logger()
        exc = ValueError("boom")

        logger.emit(body="a log line", exception=exc)
        log_record_processor_mock.on_emit.assert_called_once()
        log_data = log_record_processor_mock.on_emit.call_args.args[0]
        attributes = dict(log_data.log_record.attributes)
        self.assertEqual(
            attributes[exception_attributes.EXCEPTION_TYPE], "ValueError"
        )
        self.assertEqual(
            attributes[exception_attributes.EXCEPTION_MESSAGE], "boom"
        )
        self.assertIn(
            "ValueError: boom",
            attributes[exception_attributes.EXCEPTION_STACKTRACE],
        )

    def test_emit_with_raised_exception_has_stacktrace(self):
        logger, log_record_processor_mock = self._get_logger()

        try:
            raise ValueError("boom")
        except ValueError as exc:
            logger.emit(body="error", exception=exc)

        log_record_processor_mock.on_emit.assert_called_once()
        log_data = log_record_processor_mock.on_emit.call_args.args[0]
        stacktrace = dict(log_data.log_record.attributes)[
            exception_attributes.EXCEPTION_STACKTRACE
        ]
        self.assertIn("Traceback (most recent call last)", stacktrace)
        self.assertIn("raise ValueError", stacktrace)

    def test_emit_logrecord_exception_preserves_user_attributes(self):
        logger, log_record_processor_mock = self._get_logger()
        exc = ValueError("boom")
        log_record = LogRecord(
            observed_timestamp=0,
            body="a log line",
            attributes={exception_attributes.EXCEPTION_TYPE: "custom"},
            exception=exc,
        )

        logger.emit(log_record)
        log_record_processor_mock.on_emit.assert_called_once()
        log_data = log_record_processor_mock.on_emit.call_args.args[0]
        attributes = dict(log_data.log_record.attributes)
        self.assertEqual(
            attributes[exception_attributes.EXCEPTION_TYPE], "custom"
        )
        self.assertEqual(
            attributes[exception_attributes.EXCEPTION_MESSAGE], "boom"
        )

    def test_emit_logrecord_exception_with_immutable_attributes(self):
        logger, log_record_processor_mock = self._get_logger()
        exc = ValueError("boom")
        original_attributes = BoundedAttributes(
            attributes={"custom": "value"},
            immutable=True,
            extended_attributes=True,
        )
        log_record = LogRecord(
            observed_timestamp=0,
            body="a log line",
            attributes=original_attributes,
            exception=exc,
        )

        logger.emit(log_record)

        self.assertNotIn(
            exception_attributes.EXCEPTION_TYPE, log_record.attributes
        )
        log_record_processor_mock.on_emit.assert_called_once()
        log_data = log_record_processor_mock.on_emit.call_args.args[0]
        attributes = dict(log_data.log_record.attributes)
        self.assertEqual(attributes["custom"], "value")
        self.assertEqual(
            attributes[exception_attributes.EXCEPTION_TYPE], "ValueError"
        )

    def test_emit_readwrite_logrecord_uses_exception(self):
        logger, log_record_processor_mock = self._get_logger()
        exc = RuntimeError("kaput")
        log_record = LogRecord(
            observed_timestamp=0,
            body="a log line",
            exception=exc,
        )
        readwrite = ReadWriteLogRecord(
            log_record=log_record,
            resource=Resource.create({}),
            instrumentation_scope=logger._instrumentation_scope,
        )

        logger.emit(readwrite)
        log_record_processor_mock.on_emit.assert_called_once()
        log_data = log_record_processor_mock.on_emit.call_args.args[0]
        attributes = dict(log_data.log_record.attributes)
        self.assertEqual(
            attributes[exception_attributes.EXCEPTION_TYPE], "RuntimeError"
        )


class TestOtelLogLevelEnvVar(unittest.TestCase):
    """Tests for OTEL_LOG_LEVEL → SDK internal logger level."""

    def setUp(self):
        self._sdk_logger = logging.getLogger("opentelemetry.sdk")

    def tearDown(self):
        importlib.reload(_logs_internal)

    def test_otel_log_level_to_python_mapping_accepted_values(self):
        expected_keys = {
            "debug",
            "info",
            "warn",
            "warning",
            "error",
            "critical",
        }
        self.assertEqual(set(_OTEL_LOG_LEVEL_TO_PYTHON.keys()), expected_keys)

    @patch.dict("os.environ", {OTEL_LOG_LEVEL: ""})
    def test_default_level_is_info(self):
        importlib.reload(_logs_internal)
        self.assertEqual(self._sdk_logger.level, logging.INFO)

    def test_invalid_value_warns_and_defaults_to_info(self):
        # "trace", "verbose", "none" are valid in other SDKs but not accepted here
        for invalid in ("INVALID", "trace", "verbose", "none", "0"):
            with self.subTest(invalid=invalid):
                with patch.dict("os.environ", {OTEL_LOG_LEVEL: invalid}):
                    with self.assertLogs(
                        "opentelemetry.sdk._logs._internal",
                        level=logging.WARNING,
                    ):
                        importlib.reload(_logs_internal)
                self.assertEqual(self._sdk_logger.level, logging.INFO)

    def test_case_insensitive(self):
        for env_value, expected_level in (
            ("DEBUG", logging.DEBUG),
            ("WARN", logging.WARNING),
            ("Warning", logging.WARNING),
            ("cRiTiCaL", logging.CRITICAL),
        ):
            with self.subTest(env_value=env_value):
                with patch.dict("os.environ", {OTEL_LOG_LEVEL: env_value}):
                    importlib.reload(_logs_internal)
                self.assertEqual(self._sdk_logger.level, expected_level)

    @patch.dict("os.environ", {OTEL_LOG_LEVEL: "critical"})
    def test_level_propagates_to_child_loggers(self):
        importlib.reload(_logs_internal)
        self.assertEqual(
            self._sdk_logger.getChild("trace").getEffectiveLevel(),
            logging.CRITICAL,
        )
        self.assertEqual(
            self._sdk_logger.getChild("metrics").getEffectiveLevel(),
            logging.CRITICAL,
        )
        self.assertEqual(
            self._sdk_logger.getChild("logs").getEffectiveLevel(),
            logging.CRITICAL,
        )

    def test_all_valid_values_map_to_correct_level(self):
        cases = [
            ("debug", logging.DEBUG),
            ("info", logging.INFO),
            ("warn", logging.WARNING),
            ("warning", logging.WARNING),
            ("error", logging.ERROR),
            ("critical", logging.CRITICAL),
        ]
        for env_value, expected_level in cases:
            with self.subTest(env_value=env_value):
                with patch.dict("os.environ", {OTEL_LOG_LEVEL: env_value}):
                    importlib.reload(_logs_internal)
                self.assertEqual(self._sdk_logger.level, expected_level)
