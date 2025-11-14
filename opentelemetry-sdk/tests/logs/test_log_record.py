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

from opentelemetry._logs import LogRecord, SeverityNumber
from opentelemetry.attributes import BoundedAttributes
from opentelemetry.context import get_current
from opentelemetry.sdk._logs import (
    LogRecordDroppedAttributesWarning,
    LogRecordLimits,
    ReadableLogRecord,
    ReadWriteLogRecord,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace.span import TraceFlags


class TestLogRecord(unittest.TestCase):
    def test_log_record_to_json(self):
        log_record = ReadableLogRecord(
            LogRecord(
                timestamp=0,
                observed_timestamp=0,
                body={"key": "logLine", "bytes": b"123"},
                attributes={
                    "mapping": {"key": "value"},
                    "none": None,
                    "sequence": [1, 2],
                    "str": "string",
                },
                event_name="a.event",
            ),
            resource=Resource({"service.name": "foo"}),
        )

        self.assertEqual(
            log_record.to_json(indent=None),
            '{"body": {"key": "logLine", "bytes": "MTIz"}, "severity_number": null, "severity_text": null, "attributes": {"mapping": {"key": "value"}, "none": null, "sequence": [1, 2], "str": "string"}, "dropped_attributes": 0, "timestamp": "1970-01-01T00:00:00.000000Z", "observed_timestamp": "1970-01-01T00:00:00.000000Z", "trace_id": "0x00000000000000000000000000000000", "span_id": "0x0000000000000000", "trace_flags": 0, "resource": {"attributes": {"service.name": "foo"}, "schema_url": ""}, "event_name": "a.event"}',
        )

    def test_log_record_to_json_serializes_severity_number_as_int(self):
        actual = ReadableLogRecord(
            LogRecord(
                timestamp=0,
                severity_number=SeverityNumber.WARN,
                observed_timestamp=0,
                body="a log line",
            ),
            resource=Resource({"service.name": "foo"}),
        )

        decoded = json.loads(actual.to_json())
        self.assertEqual(SeverityNumber.WARN.value, decoded["severity_number"])

    def test_log_record_to_json_serializes_null_severity_number(self):
        actual = ReadableLogRecord(
            LogRecord(
                observed_timestamp=0,
                body="a log line",
            ),
            resource=Resource({"service.name": "foo"}),
        )

        decoded = json.loads(actual.to_json())
        self.assertEqual(None, decoded["timestamp"])

    def test_log_record_bounded_attributes(self):
        attr = {"key": "value"}

        result = ReadWriteLogRecord(
            LogRecord(timestamp=0, body="a log line", attributes=attr)
        )

        self.assertTrue(
            isinstance(result.log_record.attributes, BoundedAttributes)
        )

    def test_log_record_dropped_attributes_empty_limits(self):
        attr = {"key": "value"}

        result = ReadWriteLogRecord(
            LogRecord(timestamp=0, body="a log line", attributes=attr)
        )

        self.assertTrue(result.dropped_attributes == 0)

    def test_log_record_dropped_attributes_set_limits_max_attribute(self):
        attr = {"key": "value", "key2": "value2"}
        limits = LogRecordLimits(
            max_attributes=1,
        )

        result = ReadWriteLogRecord(
            LogRecord(timestamp=0, body="a log line", attributes=attr),
            limits=limits,
        )
        self.assertTrue(result.dropped_attributes == 1)

    def test_log_record_dropped_attributes_set_limits_max_attribute_length(
        self,
    ):
        attr = {"key": "value", "key2": "value2"}
        expected = {"key": "v", "key2": "v"}
        limits = LogRecordLimits(
            max_attribute_length=1,
        )

        result = ReadWriteLogRecord(
            LogRecord(
                timestamp=0,
                body="a log line",
                attributes=attr,
            ),
            limits=limits,
        )
        self.assertTrue(result.dropped_attributes == 0)
        self.assertEqual(expected, result.log_record.attributes)

    def test_log_record_dropped_attributes_set_limits(self):
        attr = {"key": "value", "key2": "value2"}
        expected = {"key2": "v"}
        limits = LogRecordLimits(
            max_attributes=1,
            max_attribute_length=1,
        )

        result = ReadWriteLogRecord(
            LogRecord(
                timestamp=0,
                body="a log line",
                attributes=attr,
            ),
            limits=limits,
        )
        self.assertTrue(result.dropped_attributes == 1)
        self.assertEqual(expected, result.log_record.attributes)

    def test_log_record_dropped_attributes_set_limits_warning_once(self):
        attr = {"key1": "value1", "key2": "value2"}
        limits = LogRecordLimits(
            max_attributes=1,
            max_attribute_length=1,
        )

        with warnings.catch_warnings(record=True) as cw:
            for _ in range(10):
                ReadWriteLogRecord(
                    LogRecord(
                        timestamp=0,
                        body="a log line",
                        attributes=attr,
                    ),
                    limits=limits,
                )

        # Check that at least one LogRecordDroppedAttributesWarning was emitted
        dropped_attributes_warnings = [
            w
            for w in cw
            if isinstance(w.message, LogRecordDroppedAttributesWarning)
        ]
        self.assertEqual(
            len(dropped_attributes_warnings),
            1,
            "Expected exactly one LogRecordDroppedAttributesWarning due to simplefilter('once')",
        )

        # Check the message content of the LogRecordDroppedAttributesWarning
        warning_message = str(dropped_attributes_warnings[0].message)
        self.assertIn(
            "Log record attributes were dropped due to limits",
            warning_message,
        )

    def test_log_record_dropped_attributes_unset_limits(self):
        attr = {"key": "value", "key2": "value2"}
        limits = LogRecordLimits()

        result = ReadWriteLogRecord(
            LogRecord(
                timestamp=0,
                body="a log line",
                attributes=attr,
            ),
            limits=limits,
        )
        self.assertTrue(result.dropped_attributes == 0)
        self.assertEqual(attr, result.log_record.attributes)

    # pylint:disable=protected-access
    def test_log_record_from_api_log_record(self):
        api_log_record = LogRecord(
            timestamp=1,
            observed_timestamp=2,
            context=get_current(),
            severity_text="WARN",
            severity_number=SeverityNumber.WARN,
            body="a log line",
            attributes={"a": "b"},
            event_name="an.event",
        )

        resource = Resource.create({})
        record = ReadWriteLogRecord._from_api_log_record(
            record=api_log_record, resource=resource
        )

        self.assertEqual(record.log_record.timestamp, 1)
        self.assertEqual(record.log_record.observed_timestamp, 2)
        self.assertEqual(record.log_record.context, get_current())
        # trace_id, span_id, and trace_flags come from the context's span
        self.assertEqual(record.log_record.trace_id, 0)
        self.assertEqual(record.log_record.span_id, 0)
        self.assertEqual(record.log_record.trace_flags, TraceFlags(0x00))
        self.assertEqual(record.log_record.severity_text, "WARN")
        self.assertEqual(
            record.log_record.severity_number, SeverityNumber.WARN
        )
        self.assertEqual(record.log_record.body, "a log line")
        self.assertEqual(record.log_record.attributes, {"a": "b"})
        self.assertEqual(record.log_record.event_name, "an.event")
        self.assertEqual(record.resource, resource)
