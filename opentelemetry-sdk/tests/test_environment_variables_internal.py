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

from unittest import TestCase
from unittest.mock import patch

from opentelemetry.sdk.environment_variables._internal import (
    parse_boolean_environment_variable,
)


class TestParseBooleanEnvironmentVariable(TestCase):
    def test_unset_returns_default(self):
        for default, expected in (
            (False, False),
            (True, True),
        ):
            with self.subTest(default=default):
                with patch.dict("os.environ", {}, clear=True):
                    self.assertEqual(
                        parse_boolean_environment_variable(
                            "TEST_BOOL", default=default
                        ),
                        expected,
                    )

    def test_valid_values(self):
        for value, expected in (
            ("true", True),
            (" TrUe ", True),
            ("false", False),
            (" FaLsE ", False),
        ):
            with self.subTest(value=value):
                with patch.dict("os.environ", {"TEST_BOOL": value}):
                    self.assertEqual(
                        parse_boolean_environment_variable("TEST_BOOL"),
                        expected,
                    )

    def test_invalid_value_warns_and_returns_default(self):
        for default, expected in (
            (False, False),
            (True, True),
        ):
            with self.subTest(default=default):
                with patch.dict("os.environ", {"TEST_BOOL": "yes"}):
                    with self.assertLogs(
                        "opentelemetry.sdk.environment_variables._internal",
                        level="WARNING",
                    ) as logs:
                        self.assertEqual(
                            parse_boolean_environment_variable(
                                "TEST_BOOL", default=default
                            ),
                            expected,
                        )

                    self.assertIn(
                        "Invalid value for TEST_BOOL",
                        logs.records[0].message,
                    )
