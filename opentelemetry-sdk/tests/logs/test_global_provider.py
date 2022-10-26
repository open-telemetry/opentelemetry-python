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

# type:ignore
import unittest
from importlib import reload
from logging import WARNING
from unittest.mock import patch

from opentelemetry.sdk import _logs
from opentelemetry.sdk._logs import (
    LoggerProvider,
    get_logger_provider,
    set_logger_provider,
)
from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_LOGGER_PROVIDER,
)


class TestGlobals(unittest.TestCase):
    def tearDown(self):
        reload(_logs)

    def check_override_not_allowed(self):
        """set_logger_provider should throw a warning when overridden"""
        provider = get_logger_provider()
        with self.assertLogs(level=WARNING) as test:
            set_logger_provider(LoggerProvider())
            self.assertEqual(
                test.output,
                [
                    (
                        "WARNING:opentelemetry.sdk._logs:Overriding of current "
                        "LoggerProvider is not allowed"
                    )
                ],
            )
        self.assertIs(provider, get_logger_provider())

    def test_set_tracer_provider(self):
        reload(_logs)
        provider = LoggerProvider()
        set_logger_provider(provider)
        retrieved_provider = get_logger_provider()
        self.assertEqual(provider, retrieved_provider)

    def test_tracer_provider_override_warning(self):
        reload(_logs)
        self.check_override_not_allowed()

    @patch.dict(
        "os.environ",
        {_OTEL_PYTHON_LOGGER_PROVIDER: "sdk_logger_provider"},
    )
    def test_sdk_logger_provider(self):
        reload(_logs)
        self.check_override_not_allowed()

    @patch.dict("os.environ", {_OTEL_PYTHON_LOGGER_PROVIDER: "unknown"})
    def test_unknown_logger_provider(self):
        reload(_logs)
        with self.assertRaises(Exception):
            get_logger_provider()
