# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import unittest
from logging import WARNING

from opentelemetry.trace.status import Status, StatusCode


class TestStatus(unittest.TestCase):
    def test_constructor(self):
        status = Status()
        self.assertIs(status.status_code, StatusCode.UNSET)
        self.assertIsNone(status.description)

        status = Status(StatusCode.ERROR, "unavailable")
        self.assertIs(status.status_code, StatusCode.ERROR)
        self.assertEqual(status.description, "unavailable")

    def test_invalid_description(self):
        with self.assertLogs(level=WARNING) as warning:
            status = Status(
                status_code=StatusCode.ERROR,
                description={"test": "val"},  # type: ignore
            )
            self.assertIs(status.status_code, StatusCode.ERROR)
            self.assertEqual(status.description, None)
            self.assertIn(
                "Invalid status description type, expected str",
                warning.output[0],  # type: ignore
            )

    def test_description_and_non_error_status(self):
        with self.assertLogs(level=WARNING) as warning:
            status = Status(
                status_code=StatusCode.OK, description="status description"
            )
            self.assertIs(status.status_code, StatusCode.OK)
            self.assertEqual(status.description, None)
            self.assertIn(
                "description should only be set when status_code is set to StatusCode.ERROR",
                warning.output[0],  # type: ignore
            )

        with self.assertLogs(level=WARNING) as warning:
            status = Status(
                status_code=StatusCode.UNSET, description="status description"
            )
            self.assertIs(status.status_code, StatusCode.UNSET)
            self.assertEqual(status.description, None)
            self.assertIn(
                "description should only be set when status_code is set to StatusCode.ERROR",
                warning.output[0],  # type: ignore
            )

        status = Status(
            status_code=StatusCode.ERROR, description="status description"
        )
        self.assertIs(status.status_code, StatusCode.ERROR)
        self.assertEqual(status.description, "status description")
