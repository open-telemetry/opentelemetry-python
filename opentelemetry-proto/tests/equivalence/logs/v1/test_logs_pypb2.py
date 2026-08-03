from opentelemetry.proto.common.v1.common_pb2 import (
    AnyValue as ProtoAnyValue,
    InstrumentationScope as ProtoInstrumentationScope,
    KeyValue as ProtoKeyValue,
)
from opentelemetry.proto.logs.v1.logs_pb2 import (
    LogRecord as ProtoLogRecord,
    ResourceLogs as ProtoResourceLogs,
    ScopeLogs as ProtoScopeLogs,
)
from opentelemetry.proto.resource.v1.resource_pb2 import Resource as ProtoResource

from opentelemetry._proto.common.v1.common_pb2 import (
    AnyValue,
    InstrumentationScope,
    KeyValue,
)
from opentelemetry._proto.logs.v1.logs_pb2 import LogRecord, ResourceLogs, ScopeLogs
from opentelemetry._proto.resource.v1.resource_pb2 import Resource


# ── LogRecord ─────────────────────────────────────────────────────────────────

def test_log_record_empty() -> None:
    assert LogRecord().SerializeToString() == b""


def test_log_record_empty_matches_proto() -> None:
    assert LogRecord().SerializeToString() == ProtoLogRecord().SerializeToString()


def test_log_record_severity() -> None:
    our = LogRecord(severity_number=9, severity_text="INFO")
    proto = ProtoLogRecord(severity_number=9, severity_text="INFO")
    assert our.SerializeToString() == proto.SerializeToString()


def test_log_record_with_body() -> None:
    our = LogRecord(body=AnyValue(string_value="hello world"))
    proto = ProtoLogRecord(body=ProtoAnyValue(string_value="hello world"))
    assert our.SerializeToString() == proto.SerializeToString()


def test_log_record_with_trace_context() -> None:
    trace_id = b"\x01" * 16
    span_id = b"\x02" * 8
    our = LogRecord(
        time_unix_nano=1_000_000_000,
        trace_id=trace_id,
        span_id=span_id,
        observed_time_unix_nano=2_000_000_000,
    )
    proto = ProtoLogRecord(
        time_unix_nano=1_000_000_000,
        trace_id=trace_id,
        span_id=span_id,
        observed_time_unix_nano=2_000_000_000,
    )
    assert our.SerializeToString() == proto.SerializeToString()


def test_log_record_with_attributes() -> None:
    attr = KeyValue(key="env", value=AnyValue(string_value="prod"))
    proto_attr = ProtoKeyValue(key="env", value=ProtoAnyValue(string_value="prod"))
    our = LogRecord(
        body=AnyValue(string_value="msg"),
        attributes=[attr],
        dropped_attributes_count=1,
    )
    proto = ProtoLogRecord(
        body=ProtoAnyValue(string_value="msg"),
        attributes=[proto_attr],
        dropped_attributes_count=1,
    )
    assert our.SerializeToString() == proto.SerializeToString()


def test_log_record_event_name() -> None:
    our = LogRecord(event_name="user.click")
    proto = ProtoLogRecord(event_name="user.click")
    assert our.SerializeToString() == proto.SerializeToString()


def test_log_record_flags() -> None:
    our = LogRecord(flags=1)
    proto = ProtoLogRecord(flags=1)
    assert our.SerializeToString() == proto.SerializeToString()


# ── ScopeLogs ─────────────────────────────────────────────────────────────────

def test_scope_logs_empty() -> None:
    assert ScopeLogs().SerializeToString() == b""


def test_scope_logs_empty_matches_proto() -> None:
    assert ScopeLogs().SerializeToString() == ProtoScopeLogs().SerializeToString()


def test_scope_logs_schema_url() -> None:
    our = ScopeLogs(schema_url="https://example.com/schema")
    proto = ProtoScopeLogs(schema_url="https://example.com/schema")
    assert our.SerializeToString() == proto.SerializeToString()


def test_scope_logs_with_scope() -> None:
    scope = InstrumentationScope(name="mylib", version="1.0")
    proto_scope = ProtoInstrumentationScope(name="mylib", version="1.0")
    our = ScopeLogs(scope=scope)
    proto = ProtoScopeLogs(scope=proto_scope)
    assert our.SerializeToString() == proto.SerializeToString()


def test_scope_logs_with_scope_and_records() -> None:
    scope = InstrumentationScope(name="mylib", version="1.0")
    proto_scope = ProtoInstrumentationScope(name="mylib", version="1.0")
    rec = LogRecord(severity_text="WARN", severity_number=13)
    proto_rec = ProtoLogRecord(severity_text="WARN", severity_number=13)
    our = ScopeLogs(scope=scope, log_records=[rec], schema_url="s")
    proto = ProtoScopeLogs(scope=proto_scope, log_records=[proto_rec], schema_url="s")
    assert our.SerializeToString() == proto.SerializeToString()


# ── ResourceLogs ──────────────────────────────────────────────────────────────

def test_resource_logs_empty() -> None:
    assert ResourceLogs().SerializeToString() == b""


def test_resource_logs_empty_matches_proto() -> None:
    assert ResourceLogs().SerializeToString() == ProtoResourceLogs().SerializeToString()


def test_resource_logs_schema_url() -> None:
    our = ResourceLogs(schema_url="https://example.com")
    proto = ProtoResourceLogs(schema_url="https://example.com")
    assert our.SerializeToString() == proto.SerializeToString()


def test_resource_logs_with_resource() -> None:
    res = Resource(attributes=[KeyValue(key="k", value=AnyValue(string_value="v"))])
    proto_res = ProtoResource(attributes=[ProtoKeyValue(key="k", value=ProtoAnyValue(string_value="v"))])
    our = ResourceLogs(resource=res, schema_url="s")
    proto = ProtoResourceLogs(resource=proto_res, schema_url="s")
    assert our.SerializeToString() == proto.SerializeToString()


def test_resource_logs_with_scope_logs() -> None:
    rec = LogRecord(severity_text="INFO", severity_number=9)
    proto_rec = ProtoLogRecord(severity_text="INFO", severity_number=9)
    sl = ScopeLogs(log_records=[rec])
    proto_sl = ProtoScopeLogs(log_records=[proto_rec])
    our = ResourceLogs(scope_logs=[sl])
    proto = ProtoResourceLogs(scope_logs=[proto_sl])
    assert our.SerializeToString() == proto.SerializeToString()
