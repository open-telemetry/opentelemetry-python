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

from opentelemetry.sdk._logs import LogRecordLimits
from opentelemetry.sdk._logs._internal import (
    _DEFAULT_OTEL_ATTRIBUTE_COUNT_LIMIT,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_ATTRIBUTE_COUNT_LIMIT,
    OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT,
    OTEL_LOGRECORD_ATTRIBUTE_COUNT_LIMIT,
    OTEL_LOGRECORD_ATTRIBUTE_VALUE_LENGTH_LIMIT,
)


class TestLogLimits(unittest.TestCase):
    def test_log_limits_repr_unset(self):
        expected = (
            f"LogRecordLimits("
            f"max_attributes={_DEFAULT_OTEL_ATTRIBUTE_COUNT_LIMIT}, "
            f"max_attribute_length=None, "
            f"max_log_record_attributes={_DEFAULT_OTEL_ATTRIBUTE_COUNT_LIMIT}, "
            f"max_log_record_attribute_length=None)"
        )
        limits = str(LogRecordLimits())

        self.assertEqual(expected, limits)

    def test_log_limits_max_attributes(self):
        expected = 1
        limits = LogRecordLimits(max_attributes=1)

        self.assertEqual(expected, limits.max_attributes)

    def test_log_limits_max_attribute_length(self):
        expected = 1
        limits = LogRecordLimits(max_attribute_length=1)

        self.assertEqual(expected, limits.max_attribute_length)

    def test_log_limits_max_log_record_attributes(self):
        limits = LogRecordLimits(max_log_record_attributes=5)

        self.assertEqual(5, limits.max_log_record_attributes)

    def test_log_limits_max_log_record_attribute_length(self):
        limits = LogRecordLimits(max_log_record_attribute_length=10)

        self.assertEqual(10, limits.max_log_record_attribute_length)

    @patch.dict("os.environ", {OTEL_LOGRECORD_ATTRIBUTE_COUNT_LIMIT: "7"})
    def test_logrecord_count_env_var(self):
        limits = LogRecordLimits()

        self.assertEqual(7, limits.max_log_record_attributes)
        self.assertEqual(
            _DEFAULT_OTEL_ATTRIBUTE_COUNT_LIMIT, limits.max_attributes
        )

    @patch.dict(
        "os.environ", {OTEL_LOGRECORD_ATTRIBUTE_VALUE_LENGTH_LIMIT: "20"}
    )
    def test_logrecord_length_env_var(self):
        limits = LogRecordLimits()

        self.assertEqual(20, limits.max_log_record_attribute_length)
        self.assertIsNone(limits.max_attribute_length)

    @patch.dict(
        "os.environ",
        {
            OTEL_ATTRIBUTE_COUNT_LIMIT: "50",
            OTEL_LOGRECORD_ATTRIBUTE_COUNT_LIMIT: "3",
        },
    )
    def test_logrecord_count_env_takes_precedence(self):
        limits = LogRecordLimits()

        self.assertEqual(50, limits.max_attributes)
        self.assertEqual(3, limits.max_log_record_attributes)

    @patch.dict(
        "os.environ",
        {
            OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT: "100",
            OTEL_LOGRECORD_ATTRIBUTE_VALUE_LENGTH_LIMIT: "25",
        },
    )
    def test_logrecord_length_env_takes_precedence(self):
        limits = LogRecordLimits()

        self.assertEqual(100, limits.max_attribute_length)
        self.assertEqual(25, limits.max_log_record_attribute_length)

    @patch.dict("os.environ", {OTEL_ATTRIBUTE_COUNT_LIMIT: "42"}, clear=True)
    def test_global_count_env_applies_as_fallback(self):
        limits = LogRecordLimits()

        self.assertEqual(42, limits.max_attributes)
        self.assertEqual(42, limits.max_log_record_attributes)

    @patch.dict(
        "os.environ", {OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT: "60"}, clear=True
    )
    def test_global_length_env_applies_as_fallback(self):
        limits = LogRecordLimits()

        self.assertEqual(60, limits.max_attribute_length)
        self.assertEqual(60, limits.max_log_record_attribute_length)

    def test_invalid_env_vars_raise(self):
        env_vars = [
            OTEL_ATTRIBUTE_COUNT_LIMIT,
            OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT,
            OTEL_LOGRECORD_ATTRIBUTE_COUNT_LIMIT,
            OTEL_LOGRECORD_ATTRIBUTE_VALUE_LENGTH_LIMIT,
        ]

        bad_values = ["bad", "-1"]
        test_cases = {
            env_var: bad_value
            for env_var in env_vars
            for bad_value in bad_values
        }

        for env_var, bad_value in test_cases.items():
            with self.subTest(f"Testing {env_var}={bad_value}"):
                with (
                    self.assertRaises(ValueError) as error,
                    patch.dict("os.environ", {env_var: bad_value}, clear=True),
                ):
                    LogRecordLimits()

                expected_msg = f"{env_var} must be a non-negative integer but got {bad_value}"
                self.assertEqual(
                    expected_msg,
                    str(error.exception),
                    f"Unexpected error message for {env_var}={bad_value}",
                )
