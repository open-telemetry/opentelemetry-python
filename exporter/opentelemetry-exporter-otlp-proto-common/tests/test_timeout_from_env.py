# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import unittest
from logging import WARNING
from unittest.mock import patch

from opentelemetry.exporter.otlp.proto.common._internal import (
    _timeout_from_env,
)


class TestTimeoutFromEnv(unittest.TestCase):
    @patch.dict("os.environ", {"TEST_TIMEOUT": "15"})
    def test_valid_value(self):
        self.assertEqual(_timeout_from_env("TEST_TIMEOUT", default=10), 15)

    @patch.dict("os.environ", {}, clear=True)
    def test_unset_returns_default(self):
        self.assertEqual(_timeout_from_env("TEST_TIMEOUT", default=10), 10)
        self.assertIsNone(_timeout_from_env("TEST_TIMEOUT"))

    @patch.dict("os.environ", {"TEST_TIMEOUT": " "})
    def test_empty_value_returns_default(self):
        self.assertEqual(_timeout_from_env("TEST_TIMEOUT", default=10), 10)

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
