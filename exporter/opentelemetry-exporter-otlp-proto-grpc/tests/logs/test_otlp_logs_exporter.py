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
from concurrent.futures import ThreadPoolExecutor
from os.path import dirname
from unittest import TestCase
from unittest.mock import patch

from google.protobuf.duration_pb2 import (  # pylint: disable=no-name-in-module
    Duration,
)
from google.protobuf.json_format import MessageToDict
from google.rpc.error_details_pb2 import RetryInfo
from grpc import ChannelCredentials, Compression, StatusCode, server

from opentelemetry._logs import SeverityNumber
from opentelemetry.exporter.otlp.proto.common._internal import _encode_value
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
    OTLPLogExporter,
)
from opentelemetry.exporter.otlp.proto.grpc.version import __version__
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
                        retry_delay=Duration(nanos=int(1e7))
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

    def tearDown(self):
        self.server.stop(None)

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

    def test_otlp_headers_from_env(self):
        # pylint: disable=protected-access
        self.assertEqual(
            self.exporter._headers,
            (("user-agent", "OTel-OTLP-Exporter-Python/" + __version__),),
        )

    @patch(
        "opentelemetry.exporter.otlp.proto.grpc.exporter._create_exp_backoff_generator"
    )
    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.sleep")
    def test_unavailable(self, mock_sleep, mock_expo):

        mock_expo.configure_mock(**{"return_value": [0.01]})

        add_LogsServiceServicer_to_server(
            LogsServiceServicerUNAVAILABLE(), self.server
        )
        self.assertEqual(
            self.exporter.export([self.log_data_1]), LogExportResult.FAILURE
        )
        mock_sleep.assert_called_with(0.01)

    @patch(
        "opentelemetry.exporter.otlp.proto.grpc.exporter._create_exp_backoff_generator"
    )
    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.sleep")
    def test_unavailable_delay(self, mock_sleep, mock_expo):

        mock_expo.configure_mock(**{"return_value": [1]})

        add_LogsServiceServicer_to_server(
            LogsServiceServicerUNAVAILABLEDelay(), self.server
        )
        self.assertEqual(
            self.exporter.export([self.log_data_1]), LogExportResult.FAILURE
        )
        mock_sleep.assert_called_with(0.01)

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
