# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import unittest
from logging import WARNING
from unittest.mock import patch

from opentelemetry.exporter.otlp.proto.common._internal import (
    _timeout_from_env,
)


class TestTimeoutFromEnv(unittest.TestCase):
    def test_simple_cases(self):
        cases = [
            ("valid value", {"TEST_TIMEOUT": "15"}, 10, 15),
            ("unset falls back to default", {}, 10, 10),
            ("unset with no default returns None", {}, None, None),
            (
                "empty/whitespace falls back to default",
                {"TEST_TIMEOUT": " "},
                10,
                10,
            ),
        ]
        for name, env, default, expected in cases:
            with self.subTest(name), patch.dict("os.environ", env, clear=True):
                self.assertEqual(
                    _timeout_from_env("TEST_TIMEOUT", default=default),
                    expected,
                )

    @patch.dict("os.environ", {"TEST_TIMEOUT": "abc"})
    def test_invalid_value_warns_and_returns_default(self):
        with self.assertLogs(level=WARNING) as warning:
            self.assertEqual(_timeout_from_env("TEST_TIMEOUT", default=10), 10)
        self.assertIn("Invalid value", warning.records[0].message)
        self.assertIn("TEST_TIMEOUT", warning.records[0].message)

    @patch.dict(
        "os.environ", {"TEST_SIGNAL_TIMEOUT": "5", "TEST_TIMEOUT": "15"}
    )
    def test_first_key_takes_priority(self):
        self.assertEqual(
            _timeout_from_env(
                "TEST_SIGNAL_TIMEOUT", "TEST_TIMEOUT", default=10
            ),
            5,
        )

    @patch.dict(
        "os.environ", {"TEST_SIGNAL_TIMEOUT": "abc", "TEST_TIMEOUT": "15"}
    )
    def test_invalid_first_key_falls_back_to_next(self):
        with self.assertLogs(level=WARNING):
            self.assertEqual(
                _timeout_from_env(
                    "TEST_SIGNAL_TIMEOUT", "TEST_TIMEOUT", default=10
                ),
                15,
            )
