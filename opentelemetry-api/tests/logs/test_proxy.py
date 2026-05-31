# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=W0212,W0222,W0221
import unittest
from typing import cast
from unittest.mock import Mock

import opentelemetry._logs._internal as _logs_internal
from opentelemetry import _logs
from opentelemetry.test.globals_test import LoggingGlobalsTest
from opentelemetry.util.types import _ExtendedAttributes


class TestProvider(_logs.NoOpLoggerProvider):
    def get_logger(
        self,
        name: str,
        version: str | None = None,
        schema_url: str | None = None,
        attributes: _ExtendedAttributes | None = None,
        instrumentation_scope=None,
    ) -> _logs.Logger:
        _ = instrumentation_scope
        return LoggerTest(name)


class OldSignatureLoggerProvider:
    def get_logger(  # pylint: disable=no-self-use
        self,
        name: str,
        version: str | None = None,
        schema_url: str | None = None,
        attributes: _ExtendedAttributes | None = None,
    ) -> _logs.Logger:
        return LoggerTest(name)


class LoggerProviderTest(_logs.NoOpLoggerProvider):
    def __init__(self):
        self.instrumentation_scope = None

    def get_logger(
        self,
        name: str,
        version: str | None = None,
        schema_url: str | None = None,
        attributes: _ExtendedAttributes | None = None,
        instrumentation_scope=None,
    ) -> _logs.Logger:
        self.instrumentation_scope = instrumentation_scope
        return LoggerTest(name)


class LoggerTest(_logs.NoOpLogger):
    def emit(
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
        self.assertIsInstance(
            _logs.get_logger_provider().get_logger("fresh"), LoggerTest
        )

        # references to the old provider still work but return real logger now
        real_logger = provider.get_logger("proxy-test")
        self.assertIsInstance(real_logger, LoggerTest)

    def test_proxy_logger_instrumentation_scope(self):
        provider = _logs.get_logger_provider()
        instrumentation_scope = object()

        logger = provider.get_logger(
            "proxy-test", instrumentation_scope=instrumentation_scope
        )

        logger_provider = LoggerProviderTest()
        _logs.set_logger_provider(logger_provider)

        proxy_logger = cast(_logs_internal.ProxyLogger, logger)
        self.assertIsInstance(proxy_logger._logger, LoggerTest)
        self.assertIs(
            logger_provider.instrumentation_scope, instrumentation_scope
        )

    def test_get_logger_works_with_old_signature_provider(self):
        logger_provider = cast(
            _logs.LoggerProvider, OldSignatureLoggerProvider()
        )

        logger = _logs.get_logger(
            "proxy-test", logger_provider=logger_provider
        )

        self.assertIsInstance(logger, LoggerTest)

    def test_proxy_logger_forwards_record_with_exception(self):
        logger = _logs_internal.ProxyLogger("proxy-test")
        logger._real_logger = Mock(spec=LoggerTest("proxy-test"))
        record = _logs.LogRecord(exception=ValueError("boom"))

        self.assertIsNotNone(logger._real_logger)
        logger.emit(record)

        logger._real_logger.emit.assert_called_once_with(record)
