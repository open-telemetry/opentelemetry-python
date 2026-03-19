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

from opentelemetry._logs import LogRecord, SeverityNumber
from opentelemetry.exporter.otlp.json.common._internal import (
    _encode_span_id,
    _encode_trace_id,
)
from opentelemetry.exporter.otlp.json.common._log_encoder import encode_logs
from opentelemetry.proto_json.collector.logs.v1.logs_service import (
    ExportLogsServiceRequest as JSONExportLogsServiceRequest,
)
from opentelemetry.proto_json.common.v1.common import AnyValue as JSONAnyValue
from opentelemetry.proto_json.common.v1.common import (
    ArrayValue as JSONArrayValue,
)
from opentelemetry.proto_json.common.v1.common import KeyValue as JSONKeyValue
from opentelemetry.proto_json.common.v1.common import (
    KeyValueList as JSONKeyValueList,
)
from opentelemetry.sdk._logs import (
    LogRecordLimits,
    ReadableLogRecord,
    ReadWriteLogRecord,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.trace import (
    NonRecordingSpan,
    SpanContext,
    TraceFlags,
    set_span_in_context,
)
from tests import assert_proto_json_equal

_TIMESTAMP = 1644650195189786880
_OBSERVED_TIMESTAMP = 1644650195189786881
_TRACE_ID = 89564621134313219400156819398935297684
_SPAN_ID = 1312458408527513268
_UNSET = object()


def _make_log(
    body="test log message",
    severity_text="INFO",
    severity_number=SeverityNumber.INFO,
    attributes=None,
    timestamp=_TIMESTAMP,
    observed_timestamp=_OBSERVED_TIMESTAMP,
    resource=None,
    instrumentation_scope=_UNSET,
    event_name=None,
    context=None,
    limits=None,
):
    kwargs = dict(
        timestamp=timestamp,
        observed_timestamp=observed_timestamp,
        severity_text=severity_text,
        severity_number=severity_number,
        body=body,
        attributes=attributes or {},
        event_name=event_name,
    )
    if context is not None:
        kwargs["context"] = context

    rw_kwargs = dict(
        resource=resource or Resource({}),
        instrumentation_scope=InstrumentationScope("test_scope", "1.0")
        if instrumentation_scope is _UNSET
        else instrumentation_scope,
    )
    if limits is not None:
        rw_kwargs["limits"] = limits

    return ReadableLogRecord(LogRecord(**kwargs), **rw_kwargs)


def _make_context(trace_id=_TRACE_ID, span_id=_SPAN_ID):
    return set_span_in_context(
        NonRecordingSpan(
            SpanContext(trace_id, span_id, False, TraceFlags(0x01))
        )
    )


def _get_first_log_record(result):
    return result.resource_logs[0].scope_logs[0].log_records[0]


class TestOTLPLogEncoder(unittest.TestCase):
    def test_encode_single_log(self):
        log = _make_log()
        result = encode_logs([log])

        self.assertEqual(len(result.resource_logs), 1)
        self.assertEqual(len(result.resource_logs[0].scope_logs), 1)
        self.assertEqual(
            len(result.resource_logs[0].scope_logs[0].log_records), 1
        )

        lr = _get_first_log_record(result)
        self.assertEqual(lr.time_unix_nano, _TIMESTAMP)
        self.assertEqual(lr.observed_time_unix_nano, _OBSERVED_TIMESTAMP)
        self.assertEqual(lr.severity_text, "INFO")
        self.assertEqual(lr.severity_number, SeverityNumber.INFO.value)
        self.assertEqual(
            lr.body, JSONAnyValue(string_value="test log message")
        )

    def test_encode_log_with_trace_context(self):
        ctx = _make_context()
        log = _make_log(context=ctx)
        result = encode_logs([log])
        lr = _get_first_log_record(result)

        self.assertEqual(lr.trace_id, _encode_trace_id(_TRACE_ID))
        self.assertEqual(lr.span_id, _encode_span_id(_SPAN_ID))
        self.assertEqual(lr.flags, int(TraceFlags(0x01)))

    def test_encode_log_zero_span_trace_id(self):
        ctx = set_span_in_context(NonRecordingSpan(SpanContext(0, 0, False)))
        log = _make_log(context=ctx)
        result = encode_logs([log])
        lr = _get_first_log_record(result)

        self.assertIsNone(lr.span_id)
        self.assertIsNone(lr.trace_id)

        lr_dict = result.to_dict()["resourceLogs"][0]["scopeLogs"][0][
            "logRecords"
        ][0]
        self.assertNotIn("traceId", lr_dict)
        self.assertNotIn("spanId", lr_dict)

    def test_encode_log_severity_numbers(self):
        cases = [
            ("WARN", SeverityNumber.WARN),
            ("DEBUG", SeverityNumber.DEBUG),
            ("INFO", SeverityNumber.INFO),
            ("ERROR", SeverityNumber.ERROR),
            ("FATAL", SeverityNumber.FATAL),
        ]
        for text, number in cases:
            with self.subTest(severity=text):
                log = _make_log(severity_text=text, severity_number=number)
                result = encode_logs([log])
                lr = _get_first_log_record(result)
                self.assertEqual(lr.severity_text, text)
                self.assertEqual(lr.severity_number, number.value)

    def test_encode_log_string_body(self):
        log = _make_log(body="hello world")
        result = encode_logs([log])
        lr = _get_first_log_record(result)
        self.assertEqual(lr.body, JSONAnyValue(string_value="hello world"))

    def test_encode_log_dict_body_with_nulls(self):
        log = _make_log(body={"error": None, "array_with_nones": [1, None, 2]})
        result = encode_logs([log])
        lr = _get_first_log_record(result)

        self.assertEqual(
            lr.body,
            JSONAnyValue(
                kvlist_value=JSONKeyValueList(
                    values=[
                        JSONKeyValue(key="error"),
                        JSONKeyValue(
                            key="array_with_nones",
                            value=JSONAnyValue(
                                array_value=JSONArrayValue(
                                    values=[
                                        JSONAnyValue(int_value=1),
                                        JSONAnyValue(),
                                        JSONAnyValue(int_value=2),
                                    ]
                                )
                            ),
                        ),
                    ]
                )
            ),
        )

    def test_encode_log_no_body(self):
        log = _make_log(body=None)
        result = encode_logs([log])
        lr = _get_first_log_record(result)
        self.assertIsNone(lr.body)

        lr_dict = result.to_dict()["resourceLogs"][0]["scopeLogs"][0][
            "logRecords"
        ][0]
        self.assertNotIn("body", lr_dict)

    def test_encode_log_extended_attributes(self):
        log = _make_log(
            attributes={
                "extended": {"sequence": [{"inner": "mapping", "none": None}]}
            }
        )
        result = encode_logs([log])
        lr = _get_first_log_record(result)

        self.assertIsNotNone(lr.attributes)
        self.assertEqual(len(lr.attributes), 1)
        self.assertEqual(lr.attributes[0].key, "extended")
        # Verify nested structure was encoded
        self.assertIsNotNone(lr.attributes[0].value.kvlist_value)

    def test_encode_log_empty_record(self):
        ctx = _make_context()
        log = ReadableLogRecord(
            LogRecord(observed_timestamp=_OBSERVED_TIMESTAMP, context=ctx),
            resource=Resource({}),
            instrumentation_scope=InstrumentationScope("test", "1.0"),
        )
        result = encode_logs([log])
        lr = _get_first_log_record(result)

        self.assertIsNone(lr.time_unix_nano)
        self.assertEqual(lr.observed_time_unix_nano, _OBSERVED_TIMESTAMP)
        self.assertIsNone(lr.severity_text)
        self.assertIsNone(lr.severity_number)
        self.assertIsNone(lr.body)
        self.assertIsNone(lr.attributes)

    def test_encode_log_event_name(self):
        log = _make_log(body="event happened", event_name="my.event")
        result = encode_logs([log])
        lr = _get_first_log_record(result)
        self.assertEqual(lr.event_name, "my.event")

        lr_dict = result.to_dict()["resourceLogs"][0]["scopeLogs"][0][
            "logRecords"
        ][0]
        self.assertEqual(lr_dict["eventName"], "my.event")

    def test_dropped_attributes_count(self):
        ctx = _make_context()
        log = ReadWriteLogRecord(
            LogRecord(
                timestamp=_TIMESTAMP,
                context=ctx,
                severity_text="WARN",
                severity_number=SeverityNumber.WARN,
                body="test",
                attributes={"a": 1, "b": "c", "user_id": "B121092"},
            ),
            resource=Resource({}),
            limits=LogRecordLimits(max_attributes=1),
            instrumentation_scope=InstrumentationScope("test", "1.0"),
        )
        result = encode_logs([log])
        lr = _get_first_log_record(result)
        self.assertEqual(lr.dropped_attributes_count, 2)

    def test_encode_log_grouping_by_resource(self):
        r1 = Resource({"service": "svc1"})
        r2 = Resource({"service": "svc2"})
        log1 = _make_log(body="r1", resource=r1)
        log2 = _make_log(body="r2", resource=r2)

        result = encode_logs([log1, log2])
        self.assertEqual(len(result.resource_logs), 2)

        groups = {}
        for rl in result.resource_logs:
            svc_val = rl.resource.attributes[0].value.string_value
            bodies = [
                lr.body.string_value
                for sl in rl.scope_logs
                for lr in sl.log_records
            ]
            groups[svc_val] = bodies

        self.assertEqual(groups["svc1"], ["r1"])
        self.assertEqual(groups["svc2"], ["r2"])

    def test_encode_log_grouping_by_scope(self):
        resource = Resource({"svc": "test"})
        scope1 = InstrumentationScope("lib1", "1.0")
        scope2 = InstrumentationScope("lib2", "2.0")

        logs = [
            _make_log(
                body="s1a",
                resource=resource,
                instrumentation_scope=scope1,
            ),
            _make_log(
                body="s1b",
                resource=resource,
                instrumentation_scope=scope1,
            ),
            _make_log(
                body="s2",
                resource=resource,
                instrumentation_scope=scope2,
            ),
        ]
        result = encode_logs(logs)
        self.assertEqual(len(result.resource_logs), 1)
        scope_logs = result.resource_logs[0].scope_logs
        self.assertEqual(len(scope_logs), 2)

        groups = {
            sl.scope.name: [lr.body.string_value for lr in sl.log_records]
            for sl in scope_logs
        }
        self.assertEqual(groups["lib1"], ["s1a", "s1b"])
        self.assertEqual(groups["lib2"], ["s2"])
        self.assertEqual(scope_logs[0].scope.version, "1.0")
        self.assertEqual(scope_logs[1].scope.version, "2.0")

    def test_encode_log_scope_schema_url(self):
        scope = InstrumentationScope("my_scope", "1.0", "schema_url_value")
        log = _make_log(instrumentation_scope=scope)
        result = encode_logs([log])
        self.assertEqual(
            result.resource_logs[0].scope_logs[0].schema_url,
            "schema_url_value",
        )

    def test_encode_log_scope_attributes(self):
        scope = InstrumentationScope(
            "my_scope",
            "1.0",
            attributes={"scope_key": 42},
        )
        log = _make_log(instrumentation_scope=scope)
        result = encode_logs([log])
        encoded_scope = result.resource_logs[0].scope_logs[0].scope
        self.assertEqual(encoded_scope.name, "my_scope")
        self.assertEqual(len(encoded_scope.attributes), 1)
        self.assertEqual(encoded_scope.attributes[0].key, "scope_key")

    def test_encode_log_none_scope(self):
        log = _make_log(instrumentation_scope=None)
        result = encode_logs([log])
        encoded_scope = result.resource_logs[0].scope_logs[0].scope
        self.assertFalse(encoded_scope.name)
        self.assertFalse(encoded_scope.version)
        self.assertEqual(encoded_scope.to_dict(), {})

    def test_encode_logs_to_dict(self):
        ctx = _make_context()
        log = _make_log(context=ctx, attributes={"key": "val"})
        result = encode_logs([log])
        result_dict = result.to_dict()

        self.assertIn("resourceLogs", result_dict)
        lr = result_dict["resourceLogs"][0]["scopeLogs"][0]["logRecords"][0]

        self.assertIsInstance(lr["traceId"], str)
        self.assertEqual(len(lr["traceId"]), 32)
        self.assertIsInstance(lr["spanId"], str)
        self.assertEqual(len(lr["spanId"]), 16)

        self.assertIsInstance(lr["timeUnixNano"], str)
        self.assertIsInstance(lr["observedTimeUnixNano"], str)

        self.assertIn("severityText", lr)
        self.assertIn("severityNumber", lr)

    def test_encode_logs_json_roundtrip(self):
        ctx1 = _make_context()
        ctx2 = _make_context(trace_id=12345678, span_id=87654321)
        logs = [
            _make_log(
                body="log with context",
                context=ctx1,
                attributes={"a": 1},
                resource=Resource({"r": "v"}, "resource_schema"),
                instrumentation_scope=InstrumentationScope(
                    "lib",
                    "1.0",
                    "scope_schema",
                    {"sk": "sv"},
                ),
            ),
            _make_log(
                body={"dict_body": [1, None, 2]},
                context=ctx2,
                resource=Resource({}),
            ),
            _make_log(
                body=None,
                severity_text="WARN",
                severity_number=SeverityNumber.WARN,
                event_name="my.event",
            ),
        ]
        result = encode_logs(logs)
        json_str = result.to_json()
        roundtripped = JSONExportLogsServiceRequest.from_dict(
            json.loads(json_str)
        )
        assert_proto_json_equal(self, result, roundtripped)
