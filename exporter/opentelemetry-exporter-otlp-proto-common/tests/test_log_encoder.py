# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import unittest

from opentelemetry._logs import LogRecord, SeverityNumber
from opentelemetry.exporter.otlp.proto.common._internal import (
    _encode_attributes,
    _encode_span_id,
    _encode_trace_id,
    _encode_value,
)
from opentelemetry.exporter.otlp.proto.common._log_encoder import encode_logs
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceRequest,
)
from opentelemetry.proto.common.v1.common_pb2 import AnyValue as PB2AnyValue
from opentelemetry.proto.common.v1.common_pb2 import (
    InstrumentationScope as PB2InstrumentationScope,
)
from opentelemetry.proto.common.v1.common_pb2 import KeyValue as PB2KeyValue
from opentelemetry.proto.logs.v1.logs_pb2 import LogRecord as PB2LogRecord
from opentelemetry.proto.logs.v1.logs_pb2 import (
    ResourceLogs as PB2ResourceLogs,
)
from opentelemetry.proto.logs.v1.logs_pb2 import ScopeLogs as PB2ScopeLogs
from opentelemetry.proto.resource.v1.resource_pb2 import (
    Resource as PB2Resource,
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

_CONTEXT_LOG = set_span_in_context(
    NonRecordingSpan(
        SpanContext(
            89564621134313219400156819398935297684,
            1312458408527513268,
            False,
            TraceFlags(0x01),
        )
    )
)


class TestOTLPLogEncoder(unittest.TestCase):
    def test_encode_basic_log_record(self):
        basic_log_record = ReadWriteLogRecord(
            LogRecord(
                timestamp=1644650195189786880,
                observed_timestamp=1644650195189786881,
                context=_CONTEXT_LOG,
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
        pb2_service_request = ExportLogsServiceRequest(
            resource_logs=[
                PB2ResourceLogs(
                    resource=PB2Resource(
                        attributes=[
                            PB2KeyValue(
                                key="first_resource",
                                value=PB2AnyValue(string_value="value"),
                            )
                        ]
                    ),
                    scope_logs=[
                        PB2ScopeLogs(
                            scope=PB2InstrumentationScope(
                                name="first_name", version="first_version"
                            ),
                            log_records=[
                                PB2LogRecord(
                                    time_unix_nano=1644650195189786880,
                                    observed_time_unix_nano=1644650195189786881,
                                    trace_id=_encode_trace_id(
                                        89564621134313219400156819398935297684
                                    ),
                                    span_id=_encode_span_id(
                                        1312458408527513268
                                    ),
                                    flags=int(TraceFlags(0x01)),
                                    severity_text="WARN",
                                    severity_number=SeverityNumber.WARN.value,
                                    body=_encode_value(
                                        "Do not go gentle into that good night. Rage, rage against the dying of the light"
                                    ),
                                    attributes=_encode_attributes(
                                        {"a": 1, "b": "c"}
                                    ),
                                )
                            ],
                        ),
                    ],
                    schema_url="resource_schema_url",
                )
            ]
        )
        self.assertEqual(encode_logs([basic_log_record]), pb2_service_request)

    def test_encode_log_record_with_no_instrumentation_scope_and_dict_body(
        self,
    ):
        log_record_with_no_instrumentation_scope_and_dict_body = (
            ReadWriteLogRecord(
                LogRecord(
                    timestamp=1644650427658989056,
                    observed_timestamp=1644650427658989057,
                    context=_CONTEXT_LOG,
                    severity_text="DEBUG",
                    severity_number=SeverityNumber.DEBUG,
                    body={"error": None, "array_with_nones": [1, None, 2]},
                    attributes={"a": 1, "b": "c"},
                ),
                resource=SDKResource({"second_resource": "CASE"}),
                instrumentation_scope=None,
            )
        )
        pb2_resource_logs = PB2ResourceLogs(
            resource=PB2Resource(
                attributes=[
                    PB2KeyValue(
                        key="second_resource",
                        value=PB2AnyValue(string_value="CASE"),
                    )
                ]
            ),
            scope_logs=[
                PB2ScopeLogs(
                    scope=PB2InstrumentationScope(),
                    log_records=[
                        PB2LogRecord(
                            time_unix_nano=1644650427658989056,
                            observed_time_unix_nano=1644650427658989057,
                            trace_id=_encode_trace_id(
                                89564621134313219400156819398935297684
                            ),
                            span_id=_encode_span_id(1312458408527513268),
                            flags=int(TraceFlags(0x01)),
                            severity_text="DEBUG",
                            severity_number=SeverityNumber.DEBUG.value,
                            body=_encode_value(
                                {
                                    "error": None,
                                    "array_with_nones": [1, None, 2],
                                }
                            ),
                            attributes=_encode_attributes({"a": 1, "b": "c"}),
                        )
                    ],
                )
            ],
        )
        self.assertEqual(
            encode_logs(
                [log_record_with_no_instrumentation_scope_and_dict_body]
            ),
            ExportLogsServiceRequest(resource_logs=[pb2_resource_logs]),
        )

    def test_encode_log_record_with_empty_resource_and_dict_attribute_value(
        self,
    ):
        log_record_with_empty_resource_and_dict_attribute_value = ReadWriteLogRecord(
            LogRecord(
                timestamp=1644650584292683033,
                observed_timestamp=1644650584292683033,
                context=_CONTEXT_LOG,
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
        pb2_resource_logs = PB2ResourceLogs(
            resource=PB2Resource(attributes=[]),
            scope_logs=[
                PB2ScopeLogs(
                    scope=PB2InstrumentationScope(
                        name="scope_with_attributes",
                        version="scope_with_attributes_version",
                        attributes=_encode_attributes({"one": 1, "two": "2"}),
                    ),
                    log_records=[
                        PB2LogRecord(
                            time_unix_nano=1644650584292683033,
                            observed_time_unix_nano=1644650584292683033,
                            trace_id=_encode_trace_id(
                                89564621134313219400156819398935297684
                            ),
                            span_id=_encode_span_id(1312458408527513268),
                            flags=int(TraceFlags(0x01)),
                            severity_text="FATAL",
                            severity_number=SeverityNumber.FATAL.value,
                            body=_encode_value(
                                "This instrumentation scope has a schema url and attributes"
                            ),
                            attributes=_encode_attributes(
                                {
                                    "extended": {
                                        "sequence": [
                                            {"inner": "mapping", "none": None}
                                        ]
                                    }
                                }
                            ),
                        )
                    ],
                    schema_url="instrumentation_schema_url",
                )
            ],
        )
        self.assertEqual(
            encode_logs(
                [log_record_with_empty_resource_and_dict_attribute_value]
            ),
            ExportLogsServiceRequest(resource_logs=[pb2_resource_logs]),
        )

    def test_dropped_attributes_count(self):
        sdk_logs = self._get_test_logs_dropped_attributes()
        encoded_logs = encode_logs(sdk_logs)
        self.assertTrue(hasattr(sdk_logs[0], "dropped_attributes"))
        self.assertEqual(
            # pylint:disable=no-member
            encoded_logs.resource_logs[0]
            .scope_logs[0]
            .log_records[0]
            .dropped_attributes_count,
            2,
        )

    @staticmethod
    def _get_test_logs_dropped_attributes() -> list[ReadWriteLogRecord]:
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
                context=ctx_log1,
                severity_text="WARN",
                severity_number=SeverityNumber.WARN,
                body="Do not go gentle into that good night. Rage, rage against the dying of the light",
                attributes={"a": 1, "b": "c", "user_id": "B121092"},
            ),
            resource=SDKResource({"first_resource": "value"}),
            limits=LogRecordLimits(max_attributes=1),
            instrumentation_scope=InstrumentationScope(
                "first_name", "first_version"
            ),
        )
        ctx_log2 = set_span_in_context(
            NonRecordingSpan(SpanContext(0, 0, False))
        )
        log2 = ReadWriteLogRecord(
            LogRecord(
                timestamp=1644650249738562048,
                context=ctx_log2,
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

        return [log1, log2]
