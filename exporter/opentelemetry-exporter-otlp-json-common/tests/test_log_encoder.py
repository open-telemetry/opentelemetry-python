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
from typing import List

from opentelemetry._logs import LogRecord, SeverityNumber
from opentelemetry.exporter.otlp.json.common._log_encoder import encode_logs
from opentelemetry.exporter.otlp.json.common.encoding import IdEncoding
from opentelemetry.sdk._logs import LogLimits, ReadWriteLogRecord
from opentelemetry.sdk.resources import Resource as SDKResource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.trace import (
    NonRecordingSpan,
    SpanContext,
    TraceFlags,
    set_span_in_context,
)


class TestLogEncoder(unittest.TestCase):
    def test_encode(self):
        # Create test log data
        sdk_logs = self._get_sdk_log_data()

        # Encode logs to JSON with hex ids
        json_logs = encode_logs(sdk_logs, IdEncoding.HEX)

        # Check ids in hex format
        self.assertEqual(
            json_logs["resourceLogs"][0]["scopeLogs"][0]["logRecords"][0]["traceId"],
            "436184c1a9210ea4a4b9f1a51f8dbe94")

        # Encode logs to JSON
        json_logs = encode_logs(sdk_logs)

        # Verify structure
        self.assertIn("resourceLogs", json_logs)
        self.assertEqual(len(json_logs["resourceLogs"]), 3)

        # Verify the content of the first resource log
        resource_log = json_logs["resourceLogs"][0]
        self.assertIn("resource", resource_log)
        self.assertIn("scopeLogs", resource_log)

        # Convert to JSON and back to ensure it's JSON-serializable
        json_str = json.dumps(json_logs)
        parsed_json = json.loads(json_str)
        self.assertEqual(len(parsed_json["resourceLogs"]), 3)

    def test_encode_no_body(self):
        # Create test log data with no body
        sdk_logs = self._get_sdk_log_data()
        for log in sdk_logs:
            log.log_record.body = None

        # Encode logs to JSON
        json_logs = encode_logs(sdk_logs)

        # Verify structure
        self.assertIn("resourceLogs", json_logs)

        # Verify the first log record has no body field
        resource_log = json_logs["resourceLogs"][0]
        scope_log = resource_log["scopeLogs"][0]
        log_record = scope_log["logRecords"][0]
        self.assertNotIn("body", log_record)

    def test_dropped_attributes_count(self):
        # Create test log data with dropped attributes
        sdk_logs = self._get_test_logs_dropped_attributes()

        # Encode logs to JSON
        json_logs = encode_logs(sdk_logs)

        # Verify dropped attributes count
        resource_log = json_logs["resourceLogs"][0]
        scope_log = resource_log["scopeLogs"][0]
        log_record = scope_log["logRecords"][0]
        self.assertEqual(log_record["droppedAttributesCount"], 2)

    @staticmethod
    def _get_sdk_log_data() -> List[ReadWriteLogRecord]:
        """Create a test list of log data for encoding tests."""
        ctx_log1 = set_span_in_context(
            NonRecordingSpan(
                SpanContext(
                    89564621134313219400156819398935297684,
                    1312458408527513268,
                    False,
                    TraceFlags(0x01),
                )
            )
        )
        log1 = ReadWriteLogRecord(
            LogRecord(
                timestamp=1644650195189786880,
                observed_timestamp=1644650195189786881,
                context=ctx_log1,
                severity_text="WARN",
                severity_number=SeverityNumber.WARN,
                body="Do not go gentle into that good night. Rage, rage against the dying of the light",
                attributes={"a": 1, "b": "c"},
            ),
            resource=SDKResource(
                {"first_resource": "value"},
                "resource_schema_url",
            ),
            instrumentation_scope=InstrumentationScope(
                "first_name", "first_version"
            ),
        )

        log2 = ReadWriteLogRecord(
            LogRecord(
                timestamp=1644650249738562048,
                observed_timestamp=1644650249738562049,
                severity_text="WARN",
                severity_number=SeverityNumber.WARN,
                body="Cooper, this is no time for caution!",
                attributes={},
            ),
            resource=SDKResource({"second_resource": "CASE"}),
            instrumentation_scope=InstrumentationScope(
                "second_name", "second_version"
            ),
        )

        log3 = ReadableLogRecord(
            log_record=ReadWriteLogRecord(
                timestamp=1644650427658989056,
                observed_timestamp=1644650427658989057,
                trace_id=271615924622795969659406376515024083555,
                span_id=4242561578944770265,
                trace_flags=TraceFlags(0x01),
                severity_text="DEBUG",
                severity_number=SeverityNumber.DEBUG,
                body="To our galaxy",
                resource=SDKResource({"second_resource": "CASE"}),
                attributes={"a": 1, "b": "c"},
            ),
            instrumentation_scope=None,
        )

        log4 = ReadableLogRecord(
            log_record=ReadWriteLogRecord(
                timestamp=1644650584292683008,
                observed_timestamp=1644650584292683009,
                trace_id=212592107417388365804938480559624925555,
                span_id=6077757853989569223,
                trace_flags=TraceFlags(0x01),
                severity_text="INFO",
                severity_number=SeverityNumber.INFO,
                body="Love is the one thing that transcends time and space",
                resource=SDKResource(
                    {"first_resource": "value"},
                    "resource_schema_url",
                ),
                attributes={"filename": "model.py", "func_name": "run_method"},
            ),
            instrumentation_scope=InstrumentationScope(
                "another_name", "another_version"
            ),
        )

        log5 = ReadableLogRecord(
            log_record=ReadWriteLogRecord(
                timestamp=1644650584292683009,
                observed_timestamp=1644650584292683010,
                trace_id=212592107417388365804938480559624925555,
                span_id=6077757853989569445,
                trace_flags=TraceFlags(0x01),
                severity_text="INFO",
                severity_number=SeverityNumber.INFO,
                body={"error": None, "array_with_nones": [1, None, 2]},
                resource=SDKResource({}),
                attributes={},
            ),
            instrumentation_scope=InstrumentationScope(
                "last_name", "last_version"
            ),
        )

        log6 = ReadableLogRecord(
            log_record=ReadWriteLogRecord(
                timestamp=1644650584292683022,
                observed_timestamp=1644650584292683022,
                trace_id=212592107417388365804938480559624925522,
                span_id=6077757853989569222,
                trace_flags=TraceFlags(0x01),
                severity_text="ERROR",
                severity_number=SeverityNumber.ERROR,
                body="This instrumentation scope has a schema url",
                resource=SDKResource(
                    {"first_resource": "value"},
                    "resource_schema_url",
                ),
                attributes={"filename": "model.py", "func_name": "run_method"},
            ),
            instrumentation_scope=InstrumentationScope(
                "scope_with_url",
                "scope_with_url_version",
                "instrumentation_schema_url",
            ),
        )

        log7 = ReadableLogRecord(
            log_record=ReadWriteLogRecord(
                timestamp=1644650584292683033,
                observed_timestamp=1644650584292683033,
                trace_id=212592107417388365804938480559624925533,
                span_id=6077757853989569233,
                trace_flags=TraceFlags(0x01),
                severity_text="FATAL",
                severity_number=SeverityNumber.FATAL,
                body="This instrumentation scope has a schema url and attributes",
                resource=SDKResource(
                    {"first_resource": "value"},
                    "resource_schema_url",
                ),
                attributes={"filename": "model.py", "func_name": "run_method"},
            ),
            instrumentation_scope=InstrumentationScope(
                "scope_with_attributes",
                "scope_with_attributes_version",
                "instrumentation_schema_url",
                {"one": 1, "two": "2"},
            ),
        )

        return [log1, log2, log3, log4, log5, log6, log7]

    @staticmethod
    def _get_test_logs_dropped_attributes() -> List[ReadableLogRecord]:
        """Create a test list of log data with dropped attributes."""
        log1 = ReadableLogRecord(
            log_record=ReadWriteLogRecord(
                timestamp=1644650195189786880,
                trace_id=89564621134313219400156819398935297684,
                span_id=1312458408527513268,
                trace_flags=TraceFlags(0x01),
                severity_text="WARN",
                severity_number=SeverityNumber.WARN,
                body="Do not go gentle into that good night. Rage, rage against the dying of the light",
                resource=SDKResource({"first_resource": "value"}),
                attributes={"a": 1, "b": "c", "user_id": "B121092"},
                limits=LogLimits(max_attributes=1),
            ),
            instrumentation_scope=InstrumentationScope(
                "first_name", "first_version"
            ),
        )

        log2 = ReadableLogRecord(
            log_record=ReadWriteLogRecord(
                timestamp=1644650249738562048,
                trace_id=0,
                span_id=0,
                trace_flags=TraceFlags.DEFAULT,
                severity_text="WARN",
                severity_number=SeverityNumber.WARN,
                body="Cooper, this is no time for caution!",
                resource=SDKResource({"second_resource": "CASE"}),
                attributes={},
            ),
            instrumentation_scope=InstrumentationScope(
                "second_name", "second_version"
            ),
        )

        return [log1, log2]
