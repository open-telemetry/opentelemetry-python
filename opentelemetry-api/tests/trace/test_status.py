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
            status = Status(status_code=StatusCode.ERROR, description={"test": "val"})  # type: ignore
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
