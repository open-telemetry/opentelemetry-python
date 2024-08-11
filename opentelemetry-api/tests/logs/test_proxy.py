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

# pylint: disable=W0212,W0222,W0221
import typing
import unittest

import opentelemetry._logs._internal as _logs_internal
from opentelemetry import _logs
from opentelemetry.test.globals_test import LoggingGlobalsTest
from opentelemetry.util.types import Attributes


class TestProvider(_logs.NoOpLoggerProvider):
    def get_logger(
        self,
        name: str,
        version: typing.Optional[str] = None,
        schema_url: typing.Optional[str] = None,
        attributes: typing.Optional[Attributes] = None,
    ) -> _logs.Logger:
        return LoggerTest(name)


class LoggerTest(_logs.NoOpLogger):
    def emit(self, record: _logs.LogRecord) -> None:
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
