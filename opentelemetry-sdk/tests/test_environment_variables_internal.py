# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

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
