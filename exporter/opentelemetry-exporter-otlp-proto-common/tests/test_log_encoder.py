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
from opentelemetry.sdk._logs import LogData
from opentelemetry.sdk._logs import LogRecord as SDKLogRecord
from opentelemetry.sdk.resources import Resource as SDKResource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.trace import TraceFlags


class TestOTLPLogEncoder(unittest.TestCase):
    def test_encode(self):
        sdk_logs, expected_encoding = self.get_test_logs()
        self.assertEqual(encode_logs(sdk_logs), expected_encoding)

    @staticmethod
    def _get_sdk_log_data() -> List[LogData]:
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
                attributes={"a": 1, "b": "c"},
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

        log3 = LogData(
            log_record=SDKLogRecord(
                timestamp=1644650427658989056,
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
                trace_id=212592107417388365804938480559624925555,
                span_id=6077757853989569223,
                trace_flags=TraceFlags(0x01),
                severity_text="INFO",
                severity_number=SeverityNumber.INFO,
                body="Love is the one thing that transcends time and space",
                resource=SDKResource({"first_resource": "value"}),
                attributes={"filename": "model.py", "func_name": "run_method"},
            ),
            instrumentation_scope=InstrumentationScope(
                "another_name", "another_version"
            ),
        )

        return [log1, log2, log3, log4]

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
                        PB2ScopeLogs(
                            scope=PB2InstrumentationScope(
                                name="another_name",
                                version="another_version",
                            ),
                            log_records=[
                                PB2LogRecord(
                                    time_unix_nano=1644650584292683008,
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
                                        }
                                    ),
                                )
                            ],
                        ),
                    ],
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
                                    trace_id=_encode_trace_id(0),
                                    span_id=_encode_span_id(0),
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
                                        {"a": 1, "b": "c"}
                                    ),
                                ),
                            ],
                        ),
                    ],
                ),
            ]
        )

        return sdk_logs, pb2_service_request
