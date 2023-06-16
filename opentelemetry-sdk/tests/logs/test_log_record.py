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
from opentelemetry.sdk._logs import LogLimits, LogRecord


class TestLogRecord(unittest.TestCase):
    def test_log_record_to_json(self):
        expected = json.dumps(
            {
                "body": "a log line",
                "severity_number": "None",
                "severity_text": None,
                "attributes": None,
                "dropped_attributes": 0,
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

        result = LogRecord(timestamp=0, body="a log line", attributes=attr)

        self.assertTrue(isinstance(result.attributes, BoundedAttributes))

    def test_log_record_dropped_attributes_empty_limits(self):
        attr = {"key": "value"}

        result = LogRecord(timestamp=0, body="a log line", attributes=attr)

        self.assertTrue(result.dropped_attributes == 0)

    def test_log_record_dropped_attributes_set_limits_max_attribute(self):
        attr = {"key": "value", "key2": "value2"}
        limits = LogLimits(
            max_attributes=1,
        )

        result = LogRecord(
            timestamp=0, body="a log line", attributes=attr, limits=limits
        )
        self.assertTrue(result.dropped_attributes == 1)

    def test_log_record_dropped_attributes_set_limits_max_attribute_length(
        self,
    ):
        attr = {"key": "value", "key2": "value2"}
        expected = {"key": "v", "key2": "v"}
        limits = LogLimits(
            max_attribute_length=1,
        )

        result = LogRecord(
            timestamp=0, body="a log line", attributes=attr, limits=limits
        )
        self.assertTrue(result.dropped_attributes == 0)
        self.assertEqual(expected, result.attributes)

    def test_log_record_dropped_attributes_set_limits(self):
        attr = {"key": "value", "key2": "value2"}
        expected = {"key2": "v"}
        limits = LogLimits(
            max_attributes=1,
            max_attribute_length=1,
        )

        result = LogRecord(
            timestamp=0, body="a log line", attributes=attr, limits=limits
        )
        self.assertTrue(result.dropped_attributes == 1)
        self.assertEqual(expected, result.attributes)

    def test_log_record_dropped_attributes_unset_limits(self):
        attr = {"key": "value", "key2": "value2"}
        limits = LogLimits()

        result = LogRecord(
            timestamp=0, body="a log line", attributes=attr, limits=limits
        )
        self.assertTrue(result.dropped_attributes == 0)
        self.assertEqual(attr, result.attributes)
