# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import logging
from unittest import TestCase
from unittest.mock import patch

from opentelemetry.sdk.environment_variables import OTEL_LOG_LEVEL
from opentelemetry.sdk.environment_variables._internal import (
    configure_sdk_log_level,
    parse_boolean_environment_variable,
    parse_log_level_environment_variable,
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
                        parse_boolean_environment_variable("TEST_BOOL", default=default),
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
                            parse_boolean_environment_variable("TEST_BOOL", default=default),
                            expected,
                        )

                    self.assertIn(
                        "Invalid value for TEST_BOOL",
                        logs.records[0].message,
                    )


class TestParseLogLevelEnvironmentVariable(TestCase):
    def test_unset_returns_default(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertIsNone(parse_log_level_environment_variable(OTEL_LOG_LEVEL))
            self.assertEqual(
                parse_log_level_environment_variable(OTEL_LOG_LEVEL, default=logging.INFO),
                logging.INFO,
            )

    def test_valid_values(self):
        for value, expected in (
            ("error", logging.ERROR),
            ("warn", logging.WARNING),
            ("warning", logging.WARNING),
            ("info", logging.INFO),
            ("debug", logging.DEBUG),
            (" DeBuG ", logging.DEBUG),
            ("ERROR", logging.ERROR),
        ):
            with self.subTest(value=value):
                with patch.dict("os.environ", {OTEL_LOG_LEVEL: value}):
                    self.assertEqual(
                        parse_log_level_environment_variable(OTEL_LOG_LEVEL),
                        expected,
                    )

    def test_invalid_value_warns_and_returns_default(self):
        with patch.dict("os.environ", {OTEL_LOG_LEVEL: "verbose"}):
            with self.assertLogs(
                "opentelemetry.sdk.environment_variables._internal",
                level="WARNING",
            ) as logs:
                self.assertEqual(
                    parse_log_level_environment_variable(
                        OTEL_LOG_LEVEL,
                        default=logging.INFO,
                    ),
                    logging.INFO,
                )
            self.assertIn(f"Invalid value for {OTEL_LOG_LEVEL}", logs.records[0].message)

    def test_configure_sdk_log_level(self):
        otel_logger = logging.getLogger("opentelemetry")
        previous_level = otel_logger.level
        try:
            otel_logger.setLevel(logging.NOTSET)
            with patch.dict("os.environ", {}, clear=True):
                configure_sdk_log_level()
                self.assertEqual(otel_logger.level, logging.NOTSET)

            with patch.dict("os.environ", {OTEL_LOG_LEVEL: "debug"}):
                configure_sdk_log_level()
                self.assertEqual(otel_logger.level, logging.DEBUG)

            with patch.dict("os.environ", {OTEL_LOG_LEVEL: "invalid"}):
                with self.assertLogs(
                    "opentelemetry.sdk.environment_variables._internal",
                    level="WARNING",
                ):
                    configure_sdk_log_level()
                self.assertEqual(otel_logger.level, logging.INFO)
        finally:
            otel_logger.setLevel(previous_level)
