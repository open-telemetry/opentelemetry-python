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
    LogEmitterProvider,
    get_log_emitter_provider,
    set_log_emitter_provider,
)
from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_LOG_EMITTER_PROVIDER,
)


class TestGlobals(unittest.TestCase):
    def tearDown(self):
        reload(_logs)

    def check_override_not_allowed(self):
        """set_log_emitter_provider should throw a warning when overridden"""
        provider = get_log_emitter_provider()
        with self.assertLogs(level=WARNING) as test:
            set_log_emitter_provider(LogEmitterProvider())
            self.assertEqual(
                test.output,
                [
                    (
                        "WARNING:opentelemetry.sdk._logs:Overriding of current "
                        "LogEmitterProvider is not allowed"
                    )
                ],
            )
        self.assertIs(provider, get_log_emitter_provider())

    def test_set_tracer_provider(self):
        reload(_logs)
        provider = LogEmitterProvider()
        set_log_emitter_provider(provider)
        retrieved_provider = get_log_emitter_provider()
        self.assertEqual(provider, retrieved_provider)

    def test_tracer_provider_override_warning(self):
        reload(_logs)
        self.check_override_not_allowed()

    @patch.dict(
        "os.environ",
        {_OTEL_PYTHON_LOG_EMITTER_PROVIDER: "sdk_log_emitter_provider"},
    )
    def test_sdk_log_emitter_provider(self):
        reload(_logs)
        self.check_override_not_allowed()

    @patch.dict("os.environ", {_OTEL_PYTHON_LOG_EMITTER_PROVIDER: "unknown"})
    def test_unknown_log_emitter_provider(self):
        reload(_logs)
        with self.assertRaises(Exception):
            get_log_emitter_provider()
