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

import time
from concurrent.futures import ThreadPoolExecutor
from unittest import TestCase
from unittest.mock import patch

from google.protobuf.duration_pb2 import Duration
from google.rpc.error_details_pb2 import RetryInfo
from grpc import StatusCode, server

from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
    OTLPLogExporter,
)
from opentelemetry.exporter.otlp.proto.grpc.exporter import _translate_value
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceRequest,
    ExportLogsServiceResponse,
)
from opentelemetry.proto.collector.logs.v1.logs_service_pb2_grpc import (
    LogsServiceServicer,
    add_LogsServiceServicer_to_server,
)
from opentelemetry.proto.common.v1.common_pb2 import AnyValue
from opentelemetry.proto.common.v1.common_pb2 import (
    InstrumentationScope as PB2InstrumentationScope,
)
from opentelemetry.proto.common.v1.common_pb2 import KeyValue
from opentelemetry.proto.logs.v1.logs_pb2 import LogRecord as PB2LogRecord
from opentelemetry.proto.logs.v1.logs_pb2 import ResourceLogs, ScopeLogs
from opentelemetry.proto.resource.v1.resource_pb2 import (
    Resource as OTLPResource,
)
from opentelemetry.sdk._logs import LogData, LogRecord
from opentelemetry.sdk._logs.export import LogExportResult
from opentelemetry.sdk._logs.severity import (
    SeverityNumber as SDKSeverityNumber,
)
from opentelemetry.sdk.resources import Resource as SDKResource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.trace import TraceFlags


class LogsServiceServicerUNAVAILABLEDelay(LogsServiceServicer):
    # pylint: disable=invalid-name,unused-argument,no-self-use
    def Export(self, request, context):
        context.set_code(StatusCode.UNAVAILABLE)

        context.send_initial_metadata(
            (("google.rpc.retryinfo-bin", RetryInfo().SerializeToString()),)
        )
        context.set_trailing_metadata(
            (
                (
                    "google.rpc.retryinfo-bin",
                    RetryInfo(
                        retry_delay=Duration(seconds=4)
                    ).SerializeToString(),
                ),
            )
        )

        return ExportLogsServiceResponse()


class LogsServiceServicerUNAVAILABLE(LogsServiceServicer):
    # pylint: disable=invalid-name,unused-argument,no-self-use
    def Export(self, request, context):
        context.set_code(StatusCode.UNAVAILABLE)

        return ExportLogsServiceResponse()


class LogsServiceServicerSUCCESS(LogsServiceServicer):
    # pylint: disable=invalid-name,unused-argument,no-self-use
    def Export(self, request, context):
        context.set_code(StatusCode.OK)

        return ExportLogsServiceResponse()


class LogsServiceServicerALREADY_EXISTS(LogsServiceServicer):
    # pylint: disable=invalid-name,unused-argument,no-self-use
    def Export(self, request, context):
        context.set_code(StatusCode.ALREADY_EXISTS)

        return ExportLogsServiceResponse()


class TestOTLPLogExporter(TestCase):
    def setUp(self):

        self.exporter = OTLPLogExporter()

        self.server = server(ThreadPoolExecutor(max_workers=10))

        self.server.add_insecure_port("127.0.0.1:4317")

        self.server.start()

        self.log_data_1 = LogData(
            log_record=LogRecord(
                timestamp=int(time.time() * 1e9),
                trace_id=2604504634922341076776623263868986797,
                span_id=5213367945872657620,
                trace_flags=TraceFlags(0x01),
                severity_text="WARNING",
                severity_number=SDKSeverityNumber.WARN,
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
                severity_number=SDKSeverityNumber.INFO2,
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
                severity_number=SDKSeverityNumber.WARN,
                body="Mumbai, Boil water before drinking",
                resource=SDKResource({"service": "myapp"}),
            ),
            instrumentation_scope=InstrumentationScope(
                "third_name", "third_version"
            ),
        )

    def tearDown(self):
        self.server.stop(None)

    @patch(
        "opentelemetry.exporter.otlp.proto.grpc.exporter.ssl_channel_credentials"
    )
    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.secure_channel")
    @patch(
        "opentelemetry.exporter.otlp.proto.grpc._log_exporter.OTLPLogExporter._stub"
    )
    # pylint: disable=unused-argument
    def test_no_credentials_error(
        self, mock_ssl_channel, mock_secure, mock_stub
    ):
        OTLPLogExporter(insecure=False)
        self.assertTrue(mock_ssl_channel.called)

    # pylint: disable=no-self-use
    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.insecure_channel")
    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.secure_channel")
    def test_otlp_exporter_endpoint(self, mock_secure, mock_insecure):
        expected_endpoint = "localhost:4317"
        endpoints = [
            (
                "http://localhost:4317",
                None,
                mock_insecure,
            ),
            (
                "localhost:4317",
                None,
                mock_secure,
            ),
            (
                "http://localhost:4317",
                True,
                mock_insecure,
            ),
            (
                "localhost:4317",
                True,
                mock_insecure,
            ),
            (
                "http://localhost:4317",
                False,
                mock_secure,
            ),
            (
                "localhost:4317",
                False,
                mock_secure,
            ),
            (
                "https://localhost:4317",
                False,
                mock_secure,
            ),
            (
                "https://localhost:4317",
                None,
                mock_secure,
            ),
            (
                "https://localhost:4317",
                True,
                mock_secure,
            ),
        ]

        # pylint: disable=C0209
        for endpoint, insecure, mock_method in endpoints:
            OTLPLogExporter(endpoint=endpoint, insecure=insecure)
            self.assertEqual(
                1,
                mock_method.call_count,
                "expected {} to be called for {} {}".format(
                    mock_method, endpoint, insecure
                ),
            )
            self.assertEqual(
                expected_endpoint,
                mock_method.call_args[0][0],
                "expected {} got {} {}".format(
                    expected_endpoint, mock_method.call_args[0][0], endpoint
                ),
            )
            mock_method.reset_mock()

    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.expo")
    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.sleep")
    def test_unavailable(self, mock_sleep, mock_expo):

        mock_expo.configure_mock(**{"return_value": [1]})

        add_LogsServiceServicer_to_server(
            LogsServiceServicerUNAVAILABLE(), self.server
        )
        self.assertEqual(
            self.exporter.export([self.log_data_1]), LogExportResult.FAILURE
        )
        mock_sleep.assert_called_with(1)

    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.expo")
    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.sleep")
    def test_unavailable_delay(self, mock_sleep, mock_expo):

        mock_expo.configure_mock(**{"return_value": [1]})

        add_LogsServiceServicer_to_server(
            LogsServiceServicerUNAVAILABLEDelay(), self.server
        )
        self.assertEqual(
            self.exporter.export([self.log_data_1]), LogExportResult.FAILURE
        )
        mock_sleep.assert_called_with(4)

    def test_success(self):
        add_LogsServiceServicer_to_server(
            LogsServiceServicerSUCCESS(), self.server
        )
        self.assertEqual(
            self.exporter.export([self.log_data_1]), LogExportResult.SUCCESS
        )

    def test_failure(self):
        add_LogsServiceServicer_to_server(
            LogsServiceServicerALREADY_EXISTS(), self.server
        )
        self.assertEqual(
            self.exporter.export([self.log_data_1]), LogExportResult.FAILURE
        )

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
                                    body=_translate_value(
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
                                    body=_translate_value(
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
                                    body=_translate_value(
                                        "Sydney, Opera House is closed"
                                    ),
                                    attributes=[
                                        KeyValue(
                                            key="custom_attr",
                                            value=_translate_value([1, 2, 3]),
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
                                    body=_translate_value(
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
