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
from typing import List, Tuple

from opentelemetry._logs import SeverityNumber
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
    ArrayValue as PB2ArrayValue,
)
from opentelemetry.proto.common.v1.common_pb2 import (
    InstrumentationScope as PB2InstrumentationScope,
)
from opentelemetry.proto.common.v1.common_pb2 import KeyValue as PB2KeyValue
from opentelemetry.proto.common.v1.common_pb2 import (
    KeyValueList as PB2KeyValueList,
)
from opentelemetry.proto.logs.v1.logs_pb2 import LogRecord as PB2LogRecord
from opentelemetry.proto.logs.v1.logs_pb2 import (
    ResourceLogs as PB2ResourceLogs,
)
from opentelemetry.proto.logs.v1.logs_pb2 import ScopeLogs as PB2ScopeLogs
from opentelemetry.proto.resource.v1.resource_pb2 import (
    Resource as PB2Resource,
)
from opentelemetry.sdk._logs import LogData, LogLimits
from opentelemetry.sdk._logs import LogRecord as SDKLogRecord
from opentelemetry.sdk.resources import Resource as SDKResource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.trace import TraceFlags


class TestOTLPLogEncoder(unittest.TestCase):
    def test_encode(self):
        sdk_logs, expected_encoding = self.get_test_logs()
        self.assertEqual(encode_logs(sdk_logs), expected_encoding)

    def test_encode_no_body(self):
        sdk_logs, expected_encoding = self.get_test_logs()
        for log in sdk_logs:
            log.log_record.body = None

        for resource_log in expected_encoding.resource_logs:
            for scope_log in resource_log.scope_logs:
                for log_record in scope_log.log_records:
                    log_record.ClearField("body")

        self.assertEqual(encode_logs(sdk_logs), expected_encoding)

    def test_dropped_attributes_count(self):
        sdk_logs = self._get_test_logs_dropped_attributes()
        encoded_logs = encode_logs(sdk_logs)
        self.assertTrue(hasattr(sdk_logs[0].log_record, "dropped_attributes"))
        self.assertEqual(
            # pylint:disable=no-member
            encoded_logs.resource_logs[0]
            .scope_logs[0]
            .log_records[0]
            .dropped_attributes_count,
            2,
        )

    @staticmethod
    def _get_sdk_log_data() -> List[LogData]:
        log1 = LogData(
            log_record=SDKLogRecord(
                timestamp=1644650195189786880,
                observed_timestamp=1644650195189786881,
                trace_id=89564621134313219400156819398935297684,
                span_id=1312458408527513268,
                trace_flags=TraceFlags(0x01),
                severity_text="WARN",
                severity_number=SeverityNumber.WARN,
                body="Do not go gentle into that good night. Rage, rage against the dying of the light",
                resource=SDKResource(
                    {"first_resource": "value"},
                    "resource_schema_url",
                ),
                attributes={"a": 1, "b": "c"},
            ),
            instrumentation_scope=InstrumentationScope(
                "first_name", "first_version"
            ),
        )

        log2 = LogData(
            log_record=SDKLogRecord(
                timestamp=1644650249738562048,
                observed_timestamp=1644650249738562049,
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

        log3 = LogData(
            log_record=SDKLogRecord(
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

        log4 = LogData(
            log_record=SDKLogRecord(
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

        log5 = LogData(
            log_record=SDKLogRecord(
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

        log6 = LogData(
            log_record=SDKLogRecord(
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

        log7 = LogData(
            log_record=SDKLogRecord(
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

        log8 = LogData(
            log_record=SDKLogRecord(
                timestamp=1644650584292683044,
                observed_timestamp=1644650584292683044,
                trace_id=212592107417388365804938480559624925566,
                span_id=6077757853989569466,
                trace_flags=TraceFlags(0x01),
                severity_text="INFO",
                severity_number=SeverityNumber.INFO,
                body="Test export of extended attributes",
                resource=SDKResource({}),
                attributes={
                    "extended": {
                        "sequence": [{"inner": "mapping", "none": None}]
                    }
                },
            ),
            instrumentation_scope=InstrumentationScope(
                "extended_name", "extended_version"
            ),
        )
        return [log1, log2, log3, log4, log5, log6, log7, log8]

    def get_test_logs(
        self,
    ) -> Tuple[List[SDKLogRecord], ExportLogsServiceRequest]:
        sdk_logs = self._get_sdk_log_data()

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
                                        {"a": 1, "b": "c"},
                                        allow_null=True,
                                    ),
                                )
                            ],
                        ),
                        PB2ScopeLogs(
                            scope=PB2InstrumentationScope(
                                name="another_name",
                                version="another_version",
                            ),
                            log_records=[
                                PB2LogRecord(
                                    time_unix_nano=1644650584292683008,
                                    observed_time_unix_nano=1644650584292683009,
                                    trace_id=_encode_trace_id(
                                        212592107417388365804938480559624925555
                                    ),
                                    span_id=_encode_span_id(
                                        6077757853989569223
                                    ),
                                    flags=int(TraceFlags(0x01)),
                                    severity_text="INFO",
                                    severity_number=SeverityNumber.INFO.value,
                                    body=_encode_value(
                                        "Love is the one thing that transcends time and space"
                                    ),
                                    attributes=_encode_attributes(
                                        {
                                            "filename": "model.py",
                                            "func_name": "run_method",
                                        },
                                        allow_null=True,
                                    ),
                                )
                            ],
                        ),
                        PB2ScopeLogs(
                            scope=PB2InstrumentationScope(
                                name="scope_with_url",
                                version="scope_with_url_version",
                            ),
                            schema_url="instrumentation_schema_url",
                            log_records=[
                                PB2LogRecord(
                                    time_unix_nano=1644650584292683022,
                                    observed_time_unix_nano=1644650584292683022,
                                    trace_id=_encode_trace_id(
                                        212592107417388365804938480559624925522
                                    ),
                                    span_id=_encode_span_id(
                                        6077757853989569222
                                    ),
                                    flags=int(TraceFlags(0x01)),
                                    severity_text="ERROR",
                                    severity_number=SeverityNumber.ERROR.value,
                                    body=_encode_value(
                                        "This instrumentation scope has a schema url"
                                    ),
                                    attributes=_encode_attributes(
                                        {
                                            "filename": "model.py",
                                            "func_name": "run_method",
                                        },
                                        allow_null=True,
                                    ),
                                )
                            ],
                        ),
                        PB2ScopeLogs(
                            scope=PB2InstrumentationScope(
                                name="scope_with_attributes",
                                version="scope_with_attributes_version",
                                attributes=_encode_attributes(
                                    {"one": 1, "two": "2"},
                                    allow_null=True,
                                ),
                            ),
                            schema_url="instrumentation_schema_url",
                            log_records=[
                                PB2LogRecord(
                                    time_unix_nano=1644650584292683033,
                                    observed_time_unix_nano=1644650584292683033,
                                    trace_id=_encode_trace_id(
                                        212592107417388365804938480559624925533
                                    ),
                                    span_id=_encode_span_id(
                                        6077757853989569233
                                    ),
                                    flags=int(TraceFlags(0x01)),
                                    severity_text="FATAL",
                                    severity_number=SeverityNumber.FATAL.value,
                                    body=_encode_value(
                                        "This instrumentation scope has a schema url and attributes"
                                    ),
                                    attributes=_encode_attributes(
                                        {
                                            "filename": "model.py",
                                            "func_name": "run_method",
                                        },
                                        allow_null=True,
                                    ),
                                )
                            ],
                        ),
                    ],
                    schema_url="resource_schema_url",
                ),
                PB2ResourceLogs(
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
                            scope=PB2InstrumentationScope(
                                name="second_name",
                                version="second_version",
                            ),
                            log_records=[
                                PB2LogRecord(
                                    time_unix_nano=1644650249738562048,
                                    observed_time_unix_nano=1644650249738562049,
                                    trace_id=None,
                                    span_id=None,
                                    flags=int(TraceFlags.DEFAULT),
                                    severity_text="WARN",
                                    severity_number=SeverityNumber.WARN.value,
                                    body=_encode_value(
                                        "Cooper, this is no time for caution!"
                                    ),
                                    attributes={},
                                ),
                            ],
                        ),
                        PB2ScopeLogs(
                            scope=PB2InstrumentationScope(),
                            log_records=[
                                PB2LogRecord(
                                    time_unix_nano=1644650427658989056,
                                    observed_time_unix_nano=1644650427658989057,
                                    trace_id=_encode_trace_id(
                                        271615924622795969659406376515024083555
                                    ),
                                    span_id=_encode_span_id(
                                        4242561578944770265
                                    ),
                                    flags=int(TraceFlags(0x01)),
                                    severity_text="DEBUG",
                                    severity_number=SeverityNumber.DEBUG.value,
                                    body=_encode_value("To our galaxy"),
                                    attributes=_encode_attributes(
                                        {"a": 1, "b": "c"},
                                        allow_null=True,
                                    ),
                                ),
                            ],
                        ),
                    ],
                ),
                PB2ResourceLogs(
                    resource=PB2Resource(),
                    scope_logs=[
                        PB2ScopeLogs(
                            scope=PB2InstrumentationScope(
                                name="last_name",
                                version="last_version",
                            ),
                            log_records=[
                                PB2LogRecord(
                                    time_unix_nano=1644650584292683009,
                                    observed_time_unix_nano=1644650584292683010,
                                    trace_id=_encode_trace_id(
                                        212592107417388365804938480559624925555
                                    ),
                                    span_id=_encode_span_id(
                                        6077757853989569445,
                                    ),
                                    flags=int(TraceFlags(0x01)),
                                    severity_text="INFO",
                                    severity_number=SeverityNumber.INFO.value,
                                    body=PB2AnyValue(
                                        kvlist_value=PB2KeyValueList(
                                            values=[
                                                PB2KeyValue(key="error"),
                                                PB2KeyValue(
                                                    key="array_with_nones",
                                                    value=PB2AnyValue(
                                                        array_value=PB2ArrayValue(
                                                            values=[
                                                                PB2AnyValue(
                                                                    int_value=1
                                                                ),
                                                                PB2AnyValue(),
                                                                PB2AnyValue(
                                                                    int_value=2
                                                                ),
                                                            ]
                                                        )
                                                    ),
                                                ),
                                            ]
                                        )
                                    ),
                                    attributes={},
                                ),
                            ],
                        ),
                        PB2ScopeLogs(
                            scope=PB2InstrumentationScope(
                                name="extended_name",
                                version="extended_version",
                            ),
                            log_records=[
                                PB2LogRecord(
                                    time_unix_nano=1644650584292683044,
                                    observed_time_unix_nano=1644650584292683044,
                                    trace_id=_encode_trace_id(
                                        212592107417388365804938480559624925566
                                    ),
                                    span_id=_encode_span_id(
                                        6077757853989569466,
                                    ),
                                    flags=int(TraceFlags(0x01)),
                                    severity_text="INFO",
                                    severity_number=SeverityNumber.INFO.value,
                                    body=_encode_value(
                                        "Test export of extended attributes"
                                    ),
                                    attributes=_encode_attributes(
                                        {
                                            "extended": {
                                                "sequence": [
                                                    {
                                                        "inner": "mapping",
                                                        "none": None,
                                                    }
                                                ]
                                            }
                                        },
                                        allow_null=True,
                                    ),
                                ),
                            ],
                        ),
                    ],
                ),
            ]
        )

        return sdk_logs, pb2_service_request

    @staticmethod
    def _get_test_logs_dropped_attributes() -> List[LogData]:
        log1 = LogData(
            log_record=SDKLogRecord(
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

        log2 = LogData(
            log_record=SDKLogRecord(
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
