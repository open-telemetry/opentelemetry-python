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

import json
import unittest

from opentelemetry.attributes import BoundedAttributes
from opentelemetry.sdk._logs import LogRecord


class TestLogRecord(unittest.TestCase):
    def test_log_record_to_json(self):
        expected = json.dumps(
            {
                "body": "a log line",
                "severity_number": "None",
                "severity_text": None,
                "attributes": None,
                "timestamp": "1970-01-01T00:00:00.000000Z",
                "trace_id": "",
                "span_id": "",
                "trace_flags": None,
                "resource": "",
            },
            indent=4,
        )
        actual = LogRecord(
            timestamp=0,
            body="a log line",
        ).to_json()
        self.assertEqual(expected, actual)

    def test_log_record_bounded_attributes(self):
        attr = {"key": "value"}

        record = LogRecord(timestamp=0, body="a log line", attributes=attr)

        self.assertTrue(isinstance(record.attributes, BoundedAttributes))
