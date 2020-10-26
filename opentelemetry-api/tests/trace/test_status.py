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
        self.assertIs(status.canonical_code, StatusCode.OK)
        self.assertIsNone(status.description)

        status = Status(StatusCode.UNAVAILABLE, "unavailable")
        self.assertIs(status.canonical_code, StatusCode.UNAVAILABLE)
        self.assertEqual(status.description, "unavailable")

    def test_invalid_description(self):
        with self.assertLogs(level=WARNING):
            status = Status(description={"test": "val"})  # type: ignore
            self.assertIs(status.canonical_code, StatusCode.OK)
            self.assertEqual(status.description, None)
