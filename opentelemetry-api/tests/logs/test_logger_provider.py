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
from unittest.mock import Mock, patch

import opentelemetry._logs._internal as logs_internal
from opentelemetry._logs import get_logger_provider, set_logger_provider
from opentelemetry.environment_variables import _OTEL_PYTHON_LOGGER_PROVIDER
from opentelemetry.test.globals_test import reset_logging_globals


class TestGlobals(unittest.TestCase):
    def setUp(self):
        super().tearDown()
        reset_logging_globals()

    def tearDown(self):
        super().tearDown()
        reset_logging_globals()

    def test_set_logger_provider(self):
        lp_mock = Mock()
        # pylint: disable=protected-access
        self.assertIsNone(logs_internal._LOGGER_PROVIDER)
        set_logger_provider(lp_mock)
        self.assertIs(logs_internal._LOGGER_PROVIDER, lp_mock)
        self.assertIs(get_logger_provider(), lp_mock)

    def test_get_logger_provider(self):
        # pylint: disable=protected-access
        self.assertIsNone(logs_internal._LOGGER_PROVIDER)

        self.assertIsInstance(
            get_logger_provider(), logs_internal.ProxyLoggerProvider
        )

        logs_internal._LOGGER_PROVIDER = None

        with patch.dict(
            "os.environ",
            {_OTEL_PYTHON_LOGGER_PROVIDER: "test_logger_provider"},
        ):

            with patch("opentelemetry._logs._internal._load_provider", Mock()):
                with patch(
                    "opentelemetry._logs._internal.cast",
                    Mock(**{"return_value": "test_logger_provider"}),
                ):
                    self.assertEqual(
                        get_logger_provider(), "test_logger_provider"
                    )
