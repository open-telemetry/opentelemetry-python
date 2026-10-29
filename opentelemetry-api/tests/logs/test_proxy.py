# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=W0212,W0222,W0221
import unittest
from typing import cast
from unittest.mock import Mock

from typing_extensions import Unpack

import opentelemetry._logs._internal as _logs_internal
from opentelemetry import _logs
from opentelemetry.test.globals_test import LoggingGlobalsTest
from opentelemetry.util.types import Attributes

_FUTURE_LOGGER_PROVIDER_OPTIONS = cast(_logs.LoggerProviderOptions, {"future_option": True})
_FUTURE_LOGGER_OPTIONS = cast(_logs.LoggerOptions, {"future_option": True})


class TestProvider(_logs.NoOpLoggerProvider):
    def get_logger(
        self,
        name: str,
        version: str | None = None,
        schema_url: str | None = None,
        attributes: Attributes = None,
        **kwargs: Unpack[_logs.LoggerProviderOptions],
    ) -> _logs.Logger:
        return LoggerTest(name)


class LoggerTest(_logs.NoOpLogger):
    def emit(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        record: _logs.LogRecord | None = None,
        *,
        timestamp=None,
        observed_timestamp=None,
        context=None,
        severity_number=None,
        severity_text=None,
        body=None,
        attributes=None,
        event_name=None,
        exception: BaseException | None = None,
        **kwargs: Unpack[_logs.LoggerOptions],
    ) -> None:
        pass


class TestProxy(LoggingGlobalsTest, unittest.TestCase):
    def test_proxy_logger(self):
        provider = _logs.get_logger_provider()
        # proxy provider
        self.assertIsInstance(provider, _logs_internal.ProxyLoggerProvider)

        # provider returns proxy logger
        logger = provider.get_logger("proxy-test")
        self.assertIsInstance(logger, _logs_internal.ProxyLogger)

        # set a real provider
        _logs.set_logger_provider(TestProvider())

        # get_logger_provider() now returns the real provider
        self.assertIsInstance(_logs.get_logger_provider(), TestProvider)

        # logger provider now returns real instance
        self.assertIsInstance(_logs.get_logger_provider().get_logger("fresh"), LoggerTest)

        # references to the old provider still work but return real logger now
        real_logger = provider.get_logger("proxy-test")
        self.assertIsInstance(real_logger, LoggerTest)

    def test_proxy_logger_forwards_record_with_exception(self):
        logger = _logs_internal.ProxyLogger("proxy-test")
        logger._real_logger = Mock(spec=LoggerTest("proxy-test"))
        record = _logs.LogRecord(exception=ValueError("boom"))

        self.assertIsNotNone(logger._real_logger)
        logger.emit(record)

        logger._real_logger.emit.assert_called_once_with(record)

    def test_proxy_logger_enabled_delegates_to_real_logger(self):
        logger = _logs_internal.ProxyLogger("proxy-test")
        real_logger = Mock(spec=LoggerTest("proxy-test"))
        real_logger.enabled.return_value = True
        logger._real_logger = real_logger

        result = logger.enabled(severity_number=_logs.SeverityNumber.INFO, event_name="test")

        self.assertTrue(result)
        real_logger.enabled.assert_called_once_with(
            context=None,
            severity_number=_logs.SeverityNumber.INFO,
            event_name="test",
        )

    def test_proxy_logger_enabled_falls_back_to_noop(self):
        logger = _logs_internal.ProxyLogger("proxy-test")
        self.assertFalse(logger.enabled())

    def test_noop_logger_enabled_returns_false(self):
        logger = _logs.NoOpLogger("noop-test")
        self.assertFalse(logger.enabled())
        self.assertFalse(logger.enabled(severity_number=_logs.SeverityNumber.ERROR, event_name="e"))

    def test_noop_logger_accepts_unknown_kwargs(self):
        logger = _logs.NoOpLoggerProvider().get_logger("noop-test", **_FUTURE_LOGGER_PROVIDER_OPTIONS)
        logger.emit(body="body", **_FUTURE_LOGGER_OPTIONS)
        logger.emit(_logs.LogRecord(), **_FUTURE_LOGGER_OPTIONS)
        self.assertFalse(logger.enabled(**_FUTURE_LOGGER_OPTIONS))

    def test_proxy_logger_provider_forwards_kwargs(self):
        proxy_provider = _logs.get_logger_provider()
        self.assertIsInstance(proxy_provider, _logs_internal.ProxyLoggerProvider)
        proxy_logger = proxy_provider.get_logger("proxy-test", **_FUTURE_LOGGER_PROVIDER_OPTIONS)
        self.assertIsInstance(proxy_logger, _logs_internal.ProxyLogger)

        real_provider = Mock(spec=TestProvider())
        _logs.set_logger_provider(real_provider)

        # lazily resolved proxy logger passes the stored kwargs along
        proxy_logger.enabled()
        real_provider.get_logger.assert_called_once_with("proxy-test", None, None, None, future_option=True)

        real_provider.get_logger.reset_mock()
        proxy_provider.get_logger("fresh", **_FUTURE_LOGGER_PROVIDER_OPTIONS)
        real_provider.get_logger.assert_called_once_with(
            "fresh",
            version=None,
            schema_url=None,
            attributes=None,
            future_option=True,
        )

    def test_get_logger_forwards_kwargs(self):
        provider = Mock(spec=TestProvider())
        logger = _logs.get_logger("test", logger_provider=provider, **_FUTURE_LOGGER_PROVIDER_OPTIONS)
        self.assertIs(logger, provider.get_logger.return_value)
        provider.get_logger.assert_called_once_with("test", "", None, None, future_option=True)

    def test_proxy_logger_forwards_emit_and_enabled_kwargs(self):
        logger = _logs_internal.ProxyLogger("proxy-test")
        real_logger = Mock(spec=LoggerTest("proxy-test"))
        logger._real_logger = real_logger
        self.assertIs(logger._logger, real_logger)
        record = _logs.LogRecord()

        logger.emit(record, **_FUTURE_LOGGER_OPTIONS)
        real_logger.emit.assert_called_once_with(record, future_option=True)

        real_logger.emit.reset_mock()
        logger.emit(body="body", **_FUTURE_LOGGER_OPTIONS)
        real_logger.emit.assert_called_once_with(
            timestamp=None,
            observed_timestamp=None,
            context=None,
            severity_number=None,
            severity_text=None,
            body="body",
            attributes=None,
            event_name=None,
            exception=None,
            future_option=True,
        )

        logger.enabled(**_FUTURE_LOGGER_OPTIONS)
        real_logger.enabled.assert_called_once_with(
            context=None,
            severity_number=None,
            event_name=None,
            future_option=True,
        )
