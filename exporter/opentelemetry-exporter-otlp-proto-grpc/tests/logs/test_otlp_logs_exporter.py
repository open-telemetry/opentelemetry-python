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

# pylint: disable=too-many-lines

import time
from os.path import dirname
from unittest import TestCase
from unittest.mock import patch

from google.protobuf.json_format import MessageToDict
from grpc import ChannelCredentials, Compression

from opentelemetry._logs import SeverityNumber
from opentelemetry.exporter.otlp.proto.common._internal import _encode_value
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
    OTLPLogExporter,
)
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceRequest,
)
from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValue
from opentelemetry.proto.common.v1.common_pb2 import (
    InstrumentationScope as PB2InstrumentationScope,
)
from opentelemetry.proto.logs.v1.logs_pb2 import LogRecord as PB2LogRecord
from opentelemetry.proto.logs.v1.logs_pb2 import ResourceLogs, ScopeLogs
from opentelemetry.proto.resource.v1.resource_pb2 import (
    Resource as OTLPResource,
)
from opentelemetry.sdk._logs import LogData, LogRecord
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE,
    OTEL_EXPORTER_OTLP_LOGS_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_LOGS_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_LOGS_COMPRESSION,
    OTEL_EXPORTER_OTLP_LOGS_ENDPOINT,
    OTEL_EXPORTER_OTLP_LOGS_HEADERS,
    OTEL_EXPORTER_OTLP_LOGS_TIMEOUT,
)
from opentelemetry.sdk.resources import Resource as SDKResource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.trace import TraceFlags

THIS_DIR = dirname(__file__)


class TestOTLPLogExporter(TestCase):
    def setUp(self):
        self.exporter = OTLPLogExporter()
        self.log_data_1 = LogData(
            log_record=LogRecord(
                timestamp=int(time.time() * 1e9),
                trace_id=2604504634922341076776623263868986797,
                span_id=5213367945872657620,
                trace_flags=TraceFlags(0x01),
                severity_text="WARNING",
                severity_number=SeverityNumber.WARN,
                body="Zhengzhou, We have a heaviest rains in 1000 years",
                resource=SDKResource({"key": "value"}),
                attributes={"a": 1, "b": "c"},
            ),
            instrumentation_scope=InstrumentationScope(
                "first_name", "first_version"
            ),
        )
        self.log_data_2 = LogData(
            log_record=LogRecord(
                timestamp=int(time.time() * 1e9),
                trace_id=2604504634922341076776623263868986799,
                span_id=5213367945872657623,
                trace_flags=TraceFlags(0x01),
                severity_text="INFO",
                severity_number=SeverityNumber.INFO2,
                body="Sydney, Opera House is closed",
                resource=SDKResource({"key": "value"}),
                attributes={"custom_attr": [1, 2, 3]},
            ),
            instrumentation_scope=InstrumentationScope(
                "second_name", "second_version"
            ),
        )
        self.log_data_3 = LogData(
            log_record=LogRecord(
                timestamp=int(time.time() * 1e9),
                trace_id=2604504634922341076776623263868986800,
                span_id=5213367945872657628,
                trace_flags=TraceFlags(0x01),
                severity_text="ERROR",
                severity_number=SeverityNumber.WARN,
                body="Mumbai, Boil water before drinking",
                resource=SDKResource({"service": "myapp"}),
            ),
            instrumentation_scope=InstrumentationScope(
                "third_name", "third_version"
            ),
        )
        self.log_data_4 = LogData(
            log_record=LogRecord(
                timestamp=int(time.time() * 1e9),
                trace_id=0,
                span_id=5213367945872657629,
                trace_flags=TraceFlags(0x01),
                severity_text="ERROR",
                severity_number=SeverityNumber.WARN,
                body="Invalid trace id check",
                resource=SDKResource({"service": "myapp"}),
            ),
            instrumentation_scope=InstrumentationScope(
                "fourth_name", "fourth_version"
            ),
        )
        self.log_data_5 = LogData(
            log_record=LogRecord(
                timestamp=int(time.time() * 1e9),
                trace_id=2604504634922341076776623263868986801,
                span_id=0,
                trace_flags=TraceFlags(0x01),
                severity_text="ERROR",
                severity_number=SeverityNumber.WARN,
                body="Invalid span id check",
                resource=SDKResource({"service": "myapp"}),
            ),
            instrumentation_scope=InstrumentationScope(
                "fifth_name", "fifth_version"
            ),
        )

    def test_exporting(self):
        # pylint: disable=protected-access
        self.assertEqual(self.exporter._exporting, "logs")

    @patch.dict(
        "os.environ",
        {
            OTEL_EXPORTER_OTLP_LOGS_ENDPOINT: "logs:4317",
            OTEL_EXPORTER_OTLP_LOGS_HEADERS: " key1=value1,KEY2 = VALUE=2",
            OTEL_EXPORTER_OTLP_LOGS_TIMEOUT: "10",
            OTEL_EXPORTER_OTLP_LOGS_COMPRESSION: "gzip",
        },
    )
    @patch(
        "opentelemetry.exporter.otlp.proto.grpc.exporter.OTLPExporterMixin.__init__"
    )
    def test_env_variables(self, mock_exporter_mixin):
        OTLPLogExporter()

        self.assertTrue(len(mock_exporter_mixin.call_args_list) == 1)
        _, kwargs = mock_exporter_mixin.call_args_list[0]
        self.assertEqual(kwargs["endpoint"], "logs:4317")
        self.assertEqual(kwargs["headers"], " key1=value1,KEY2 = VALUE=2")
        self.assertEqual(kwargs["timeout"], 10)
        self.assertEqual(kwargs["compression"], Compression.Gzip)
        self.assertIsNone(kwargs["credentials"])

    # Create a new test method specifically for client certificates
    @patch.dict(
        "os.environ",
        {
            OTEL_EXPORTER_OTLP_LOGS_ENDPOINT: "logs:4317",
            OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE: THIS_DIR
            + "/../fixtures/test.cert",
            OTEL_EXPORTER_OTLP_LOGS_CLIENT_CERTIFICATE: THIS_DIR
            + "/../fixtures/test-client-cert.pem",
            OTEL_EXPORTER_OTLP_LOGS_CLIENT_KEY: THIS_DIR
            + "/../fixtures/test-client-key.pem",
            OTEL_EXPORTER_OTLP_LOGS_HEADERS: " key1=value1,KEY2 = VALUE=2",
            OTEL_EXPORTER_OTLP_LOGS_TIMEOUT: "10",
            OTEL_EXPORTER_OTLP_LOGS_COMPRESSION: "gzip",
        },
    )
    @patch(
        "opentelemetry.exporter.otlp.proto.grpc.exporter.OTLPExporterMixin.__init__"
    )
    def test_env_variables_with_client_certificates(self, mock_exporter_mixin):
        OTLPLogExporter()

        self.assertTrue(len(mock_exporter_mixin.call_args_list) == 1)
        _, kwargs = mock_exporter_mixin.call_args_list[0]
        self.assertEqual(kwargs["endpoint"], "logs:4317")
        self.assertEqual(kwargs["headers"], " key1=value1,KEY2 = VALUE=2")
        self.assertEqual(kwargs["timeout"], 10)
        self.assertEqual(kwargs["compression"], Compression.Gzip)
        self.assertIsNotNone(kwargs["credentials"])
        self.assertIsInstance(kwargs["credentials"], ChannelCredentials)

    @patch.dict(
        "os.environ",
        {
            OTEL_EXPORTER_OTLP_LOGS_ENDPOINT: "logs:4317",
            OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE: THIS_DIR
            + "/../fixtures/test.cert",
            OTEL_EXPORTER_OTLP_LOGS_HEADERS: " key1=value1,KEY2 = VALUE=2",
            OTEL_EXPORTER_OTLP_LOGS_TIMEOUT: "10",
            OTEL_EXPORTER_OTLP_LOGS_COMPRESSION: "gzip",
        },
    )
    @patch(
        "opentelemetry.exporter.otlp.proto.grpc.exporter.OTLPExporterMixin.__init__"
    )
    @patch("logging.Logger.error")
    def test_env_variables_with_only_certificate(
        self, mock_logger_error, mock_exporter_mixin
    ):
        OTLPLogExporter()

        self.assertTrue(len(mock_exporter_mixin.call_args_list) == 1)
        _, kwargs = mock_exporter_mixin.call_args_list[0]
        self.assertEqual(kwargs["endpoint"], "logs:4317")
        self.assertEqual(kwargs["headers"], " key1=value1,KEY2 = VALUE=2")
        self.assertEqual(kwargs["timeout"], 10)
        self.assertEqual(kwargs["compression"], Compression.Gzip)
        self.assertIsNotNone(kwargs["credentials"])
        self.assertIsInstance(kwargs["credentials"], ChannelCredentials)

        mock_logger_error.assert_not_called()

    def export_log_and_deserialize(self, log_data):
        # pylint: disable=protected-access
        translated_data = self.exporter._translate_data([log_data])
        request_dict = MessageToDict(translated_data)
        log_records = (
            request_dict.get("resourceLogs")[0]
            .get("scopeLogs")[0]
            .get("logRecords")
        )
        return log_records

    def test_exported_log_without_trace_id(self):
        log_records = self.export_log_and_deserialize(self.log_data_4)
        if log_records:
            log_record = log_records[0]
            self.assertIn("spanId", log_record)
            self.assertNotIn(
                "traceId",
                log_record,
                "traceId should not be present in the log record",
            )
        else:
            self.fail("No log records found")

    def test_exported_log_without_span_id(self):
        log_records = self.export_log_and_deserialize(self.log_data_5)
        if log_records:
            log_record = log_records[0]
            self.assertIn("traceId", log_record)
            self.assertNotIn(
                "spanId",
                log_record,
                "spanId should not be present in the log record",
            )
        else:
            self.fail("No log records found")

    def test_translate_log_data(self):
        expected = ExportLogsServiceRequest(
            resource_logs=[
                ResourceLogs(
                    resource=OTLPResource(
                        attributes=[
                            KeyValue(
                                key="key", value=AnyValue(string_value="value")
                            ),
                        ]
                    ),
                    scope_logs=[
                        ScopeLogs(
                            scope=PB2InstrumentationScope(
                                name="first_name", version="first_version"
                            ),
                            log_records=[
                                PB2LogRecord(
                                    # pylint: disable=no-member
                                    time_unix_nano=self.log_data_1.log_record.timestamp,
                                    observed_time_unix_nano=self.log_data_1.log_record.observed_timestamp,
                                    severity_number=self.log_data_1.log_record.severity_number.value,
                                    severity_text="WARNING",
                                    span_id=int.to_bytes(
                                        5213367945872657620, 8, "big"
                                    ),
                                    trace_id=int.to_bytes(
                                        2604504634922341076776623263868986797,
                                        16,
                                        "big",
                                    ),
                                    body=_encode_value(
                                        "Zhengzhou, We have a heaviest rains in 1000 years"
                                    ),
                                    attributes=[
                                        KeyValue(
                                            key="a",
                                            value=AnyValue(int_value=1),
                                        ),
                                        KeyValue(
                                            key="b",
                                            value=AnyValue(string_value="c"),
                                        ),
                                    ],
                                    flags=int(
                                        self.log_data_1.log_record.trace_flags
                                    ),
                                )
                            ],
                        )
                    ],
                ),
            ]
        )

        # pylint: disable=protected-access
        self.assertEqual(
            expected, self.exporter._translate_data([self.log_data_1])
        )

    def test_translate_multiple_logs(self):
        expected = ExportLogsServiceRequest(
            resource_logs=[
                ResourceLogs(
                    resource=OTLPResource(
                        attributes=[
                            KeyValue(
                                key="key", value=AnyValue(string_value="value")
                            ),
                        ]
                    ),
                    scope_logs=[
                        ScopeLogs(
                            scope=PB2InstrumentationScope(
                                name="first_name", version="first_version"
                            ),
                            log_records=[
                                PB2LogRecord(
                                    # pylint: disable=no-member
                                    time_unix_nano=self.log_data_1.log_record.timestamp,
                                    observed_time_unix_nano=self.log_data_1.log_record.observed_timestamp,
                                    severity_number=self.log_data_1.log_record.severity_number.value,
                                    severity_text="WARNING",
                                    span_id=int.to_bytes(
                                        5213367945872657620, 8, "big"
                                    ),
                                    trace_id=int.to_bytes(
                                        2604504634922341076776623263868986797,
                                        16,
                                        "big",
                                    ),
                                    body=_encode_value(
                                        "Zhengzhou, We have a heaviest rains in 1000 years"
                                    ),
                                    attributes=[
                                        KeyValue(
                                            key="a",
                                            value=AnyValue(int_value=1),
                                        ),
                                        KeyValue(
                                            key="b",
                                            value=AnyValue(string_value="c"),
                                        ),
                                    ],
                                    flags=int(
                                        self.log_data_1.log_record.trace_flags
                                    ),
                                )
                            ],
                        ),
                        ScopeLogs(
                            scope=PB2InstrumentationScope(
                                name="second_name", version="second_version"
                            ),
                            log_records=[
                                PB2LogRecord(
                                    # pylint: disable=no-member
                                    time_unix_nano=self.log_data_2.log_record.timestamp,
                                    observed_time_unix_nano=self.log_data_2.log_record.observed_timestamp,
                                    severity_number=self.log_data_2.log_record.severity_number.value,
                                    severity_text="INFO",
                                    span_id=int.to_bytes(
                                        5213367945872657623, 8, "big"
                                    ),
                                    trace_id=int.to_bytes(
                                        2604504634922341076776623263868986799,
                                        16,
                                        "big",
                                    ),
                                    body=_encode_value(
                                        "Sydney, Opera House is closed"
                                    ),
                                    attributes=[
                                        KeyValue(
                                            key="custom_attr",
                                            value=_encode_value([1, 2, 3]),
                                        ),
                                    ],
                                    flags=int(
                                        self.log_data_2.log_record.trace_flags
                                    ),
                                )
                            ],
                        ),
                    ],
                ),
                ResourceLogs(
                    resource=OTLPResource(
                        attributes=[
                            KeyValue(
                                key="service",
                                value=AnyValue(string_value="myapp"),
                            ),
                        ]
                    ),
                    scope_logs=[
                        ScopeLogs(
                            scope=PB2InstrumentationScope(
                                name="third_name", version="third_version"
                            ),
                            log_records=[
                                PB2LogRecord(
                                    # pylint: disable=no-member
                                    time_unix_nano=self.log_data_3.log_record.timestamp,
                                    observed_time_unix_nano=self.log_data_3.log_record.observed_timestamp,
                                    severity_number=self.log_data_3.log_record.severity_number.value,
                                    severity_text="ERROR",
                                    span_id=int.to_bytes(
                                        5213367945872657628, 8, "big"
                                    ),
                                    trace_id=int.to_bytes(
                                        2604504634922341076776623263868986800,
                                        16,
                                        "big",
                                    ),
                                    body=_encode_value(
                                        "Mumbai, Boil water before drinking"
                                    ),
                                    attributes=[],
                                    flags=int(
                                        self.log_data_3.log_record.trace_flags
                                    ),
                                )
                            ],
                        )
                    ],
                ),
            ]
        )

        # pylint: disable=protected-access
        self.assertEqual(
            expected,
            self.exporter._translate_data(
                [self.log_data_1, self.log_data_2, self.log_data_3]
            ),
        )
