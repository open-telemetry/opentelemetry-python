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
import warnings

from opentelemetry._logs.severity import SeverityNumber
from opentelemetry.attributes import BoundedAttributes
from opentelemetry.sdk._logs import (
    LogDroppedAttributesWarning,
    LogLimits,
    LogRecord,
)
from opentelemetry.sdk.resources import Resource


class TestLogRecord(unittest.TestCase):
    def test_log_record_to_json(self):
        expected = json.dumps(
            {
                "body": "a log line",
                "severity_number": None,
                "severity_text": None,
                "attributes": None,
                "dropped_attributes": 0,
                "timestamp": "1970-01-01T00:00:00.000000Z",
                "observed_timestamp": "1970-01-01T00:00:00.000000Z",
                "trace_id": "",
                "span_id": "",
                "trace_flags": None,
                "resource": {
                    "attributes": {"service.name": "foo"},
                    "schema_url": "",
                },
            },
            indent=4,
        )
        actual = LogRecord(
            timestamp=0,
            observed_timestamp=0,
            body="a log line",
            resource=Resource({"service.name": "foo"}),
        )

        self.assertEqual(expected, actual.to_json(indent=4))
        self.assertEqual(
            actual.to_json(indent=None),
            '{"body": "a log line", "severity_number": null, "severity_text": null, "attributes": null, "dropped_attributes": 0, "timestamp": "1970-01-01T00:00:00.000000Z", "observed_timestamp": "1970-01-01T00:00:00.000000Z", "trace_id": "", "span_id": "", "trace_flags": null, "resource": {"attributes": {"service.name": "foo"}, "schema_url": ""}}',
        )

    def test_log_record_to_json_serializes_severity_number_as_int(self):
        actual = LogRecord(
            timestamp=0,
            severity_number=SeverityNumber.WARN,
            observed_timestamp=0,
            body="a log line",
            resource=Resource({"service.name": "foo"}),
        )

        decoded = json.loads(actual.to_json())
        self.assertEqual(SeverityNumber.WARN.value, decoded["severity_number"])

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

    def test_log_record_dropped_attributes_set_limits_warning_once(self):
        attr = {"key1": "value1", "key2": "value2"}
        limits = LogLimits(
            max_attributes=1,
            max_attribute_length=1,
        )

        with warnings.catch_warnings(record=True) as cw:
            for _ in range(10):
                LogRecord(
                    timestamp=0,
                    body="a log line",
                    attributes=attr,
                    limits=limits,
                )
        self.assertEqual(len(cw), 1)
        self.assertIsInstance(cw[-1].message, LogDroppedAttributesWarning)
        self.assertIn(
            "Log record attributes were dropped due to limits",
            str(cw[-1].message),
        )

    def test_log_record_dropped_attributes_unset_limits(self):
        attr = {"key": "value", "key2": "value2"}
        limits = LogLimits()

        result = LogRecord(
            timestamp=0, body="a log line", attributes=attr, limits=limits
        )
        self.assertTrue(result.dropped_attributes == 0)
        self.assertEqual(attr, result.attributes)
