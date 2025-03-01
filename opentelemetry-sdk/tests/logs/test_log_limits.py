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

import unittest
from unittest.mock import patch

from opentelemetry.sdk._logs import LogLimits
from opentelemetry.sdk._logs._internal import (
    _DEFAULT_OTEL_ATTRIBUTE_COUNT_LIMIT,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_ATTRIBUTE_COUNT_LIMIT,
    OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT,
)


class TestLogLimits(unittest.TestCase):
    def test_log_limits_repr_unset(self):
        expected = f"LogLimits(max_attributes={_DEFAULT_OTEL_ATTRIBUTE_COUNT_LIMIT}, max_attribute_length=None)"
        limits = str(LogLimits())

        self.assertEqual(expected, limits)

    def test_log_limits_max_attributes(self):
        expected = 1
        limits = LogLimits(max_attributes=1)

        self.assertEqual(expected, limits.max_attributes)

    def test_log_limits_max_attribute_length(self):
        expected = 1
        limits = LogLimits(max_attribute_length=1)

        self.assertEqual(expected, limits.max_attribute_length)

    def test_invalid_env_vars_raise(self):
        env_vars = [
            OTEL_ATTRIBUTE_COUNT_LIMIT,
            OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT,
        ]

        bad_values = ["bad", "-1"]
        test_cases = {
            env_var: bad_value
            for env_var in env_vars
            for bad_value in bad_values
        }

        for env_var, bad_value in test_cases.items():
            with self.subTest(f"Testing {env_var}={bad_value}"):
                with self.assertRaises(ValueError) as error, patch.dict(
                    "os.environ", {env_var: bad_value}, clear=True
                ):
                    LogLimits()

                expected_msg = f"{env_var} must be a non-negative integer but got {bad_value}"
                self.assertEqual(
                    expected_msg,
                    str(error.exception),
                    f"Unexpected error message for {env_var}={bad_value}",
                )
