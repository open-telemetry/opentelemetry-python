# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry._logs import LogRecord, SeverityNumber
from opentelemetry.exporter.otlp.proto.common._log_encoder import (
    encode_logs as proto_encode_logs,
)
from opentelemetry.exporter.otlp._proto.common._internal._log_encoder import (
    encode_logs as pyproto_encode_logs,
)
from opentelemetry.sdk._logs import LogRecordLimits, ReadWriteLogRecord
from opentelemetry.sdk.resources import Resource as SDKResource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.trace import (
    NonRecordingSpan,
    SpanContext,
    TraceFlags,
    set_span_in_context,
)

_CONTEXT = set_span_in_context(
    NonRecordingSpan(
        SpanContext(
            89564621134313219400156819398935297684,
            1312458408527513268,
            False,
            TraceFlags(0x01),
        )
    )
)


def _make_basic_log() -> ReadWriteLogRecord:
    return ReadWriteLogRecord(
        LogRecord(
            timestamp=1644650195189786880,
            observed_timestamp=1644650195189786881,
            context=_CONTEXT,
            severity_text="WARN",
            severity_number=SeverityNumber.WARN,
            body="Do not go gentle into that good night.",
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


def test_encode_logs_basic_matches_proto() -> None:
    logs = [_make_basic_log()]
    assert pyproto_encode_logs(logs).SerializeToString() == proto_encode_logs(logs).SerializeToString()


def test_encode_logs_no_instrumentation_scope_matches_proto() -> None:
    log = ReadWriteLogRecord(
        LogRecord(
            timestamp=1644650427658989056,
            observed_timestamp=1644650427658989057,
            context=_CONTEXT,
            severity_text="DEBUG",
            severity_number=SeverityNumber.DEBUG,
            body={"error": None, "array_with_nones": [1, None, 2]},
            attributes={"a": 1, "b": "c"},
        ),
        resource=SDKResource({"second_resource": "CASE"}),
        instrumentation_scope=None,
    )
    logs = [log]
    assert pyproto_encode_logs(logs).SerializeToString() == proto_encode_logs(logs).SerializeToString()


def test_encode_logs_empty_resource_with_scope_attributes_matches_proto() -> None:
    log = ReadWriteLogRecord(
        LogRecord(
            timestamp=1644650584292683033,
            observed_timestamp=1644650584292683033,
            context=_CONTEXT,
            severity_text="FATAL",
            severity_number=SeverityNumber.FATAL,
            body="This instrumentation scope has a schema url and attributes",
            attributes={
                "extended": {
                    "sequence": [{"inner": "mapping", "none": None}]
                }
            },
        ),
        resource=SDKResource({}),
        instrumentation_scope=InstrumentationScope(
            "scope_with_attributes",
            "scope_with_attributes_version",
            "instrumentation_schema_url",
            {"one": 1, "two": "2"},
        ),
    )
    logs = [log]
    assert pyproto_encode_logs(logs).SerializeToString() == proto_encode_logs(logs).SerializeToString()


def test_encode_logs_dropped_attributes_matches_proto() -> None:
    log = ReadWriteLogRecord(
        LogRecord(
            timestamp=1644650195189786880,
            context=_CONTEXT,
            severity_text="WARN",
            severity_number=SeverityNumber.WARN,
            body="message with dropped attributes",
            attributes={"a": 1, "b": "c", "user_id": "B121092"},
        ),
        resource=SDKResource({"first_resource": "value"}),
        limits=LogRecordLimits(max_attributes=1),
        instrumentation_scope=InstrumentationScope(
            "first_name", "first_version"
        ),
    )
    logs = [log]
    assert pyproto_encode_logs(logs).SerializeToString() == proto_encode_logs(logs).SerializeToString()


def test_encode_logs_multiple_resources_matches_proto() -> None:
    log1 = _make_basic_log()
    log2 = ReadWriteLogRecord(
        LogRecord(
            timestamp=1644650249738562048,
            observed_timestamp=1644650249738562049,
            context=_CONTEXT,
            severity_text="ERROR",
            severity_number=SeverityNumber.ERROR,
            body="second log",
        ),
        resource=SDKResource({"second_resource": "value2"}),
        instrumentation_scope=InstrumentationScope(
            "second_name", "second_version"
        ),
    )
    logs = [log1, log2]
    assert pyproto_encode_logs(logs).SerializeToString() == proto_encode_logs(logs).SerializeToString()


def test_encode_logs_empty_list_matches_proto() -> None:
    assert pyproto_encode_logs([]).SerializeToString() == proto_encode_logs([]).SerializeToString()


def test_encode_logs_no_trace_context_matches_proto() -> None:
    no_context = set_span_in_context(NonRecordingSpan(SpanContext(0, 0, False)))
    log = ReadWriteLogRecord(
        LogRecord(
            timestamp=1644650195189786880,
            context=no_context,
            severity_text="INFO",
            severity_number=SeverityNumber.INFO,
            body="no trace context",
        ),
        resource=SDKResource({}),
        instrumentation_scope=None,
    )
    logs = [log]
    assert pyproto_encode_logs(logs).SerializeToString() == proto_encode_logs(logs).SerializeToString()
