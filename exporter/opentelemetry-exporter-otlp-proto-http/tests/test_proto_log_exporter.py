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

# pylint: disable=protected-access

import unittest
from typing import List, Tuple
from unittest.mock import MagicMock, patch

import requests
import responses

from opentelemetry._logs import SeverityNumber
from opentelemetry.exporter.otlp.proto.http import Compression
from opentelemetry.exporter.otlp.proto.http._log_exporter import (
    DEFAULT_COMPRESSION,
    DEFAULT_ENDPOINT,
    DEFAULT_LOGS_EXPORT_PATH,
    DEFAULT_TIMEOUT,
    OTLPLogExporter,
    _is_backoff_v2,
)
from opentelemetry.exporter.otlp.proto.http._log_exporter.encoder import (
    _encode_attributes,
    _encode_span_id,
    _encode_trace_id,
    _encode_value,
    _ProtobufEncoder,
)
from opentelemetry.exporter.otlp.proto.http.version import __version__
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
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE,
    OTEL_EXPORTER_OTLP_LOGS_COMPRESSION,
    OTEL_EXPORTER_OTLP_LOGS_ENDPOINT,
    OTEL_EXPORTER_OTLP_LOGS_HEADERS,
    OTEL_EXPORTER_OTLP_LOGS_TIMEOUT,
    OTEL_EXPORTER_OTLP_TIMEOUT,
)
from opentelemetry.sdk.resources import Resource as SDKResource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.trace import TraceFlags

ENV_ENDPOINT = "http://localhost.env:8080/"
ENV_CERTIFICATE = "/etc/base.crt"
ENV_HEADERS = "envHeader1=val1,envHeader2=val2"
ENV_TIMEOUT = "30"


class TestOTLPHTTPLogExporter(unittest.TestCase):
    def test_constructor_default(self):

        exporter = OTLPLogExporter()

        self.assertEqual(
            exporter._endpoint, DEFAULT_ENDPOINT + DEFAULT_LOGS_EXPORT_PATH
        )
        self.assertEqual(exporter._certificate_file, True)
        self.assertEqual(exporter._timeout, DEFAULT_TIMEOUT)
        self.assertIs(exporter._compression, DEFAULT_COMPRESSION)
        self.assertEqual(exporter._headers, {})
        self.assertIsInstance(exporter._session, requests.Session)
        self.assertIn("User-Agent", exporter._session.headers)
        self.assertEqual(
            exporter._session.headers.get("Content-Type"),
            "application/x-protobuf",
        )
        self.assertEqual(
            exporter._session.headers.get("User-Agent"),
            "OTel-OTLP-Exporter-Python/" + __version__,
        )

    @patch.dict(
        "os.environ",
        {
            OTEL_EXPORTER_OTLP_CERTIFICATE: ENV_CERTIFICATE,
            OTEL_EXPORTER_OTLP_COMPRESSION: Compression.Gzip.value,
            OTEL_EXPORTER_OTLP_ENDPOINT: ENV_ENDPOINT,
            OTEL_EXPORTER_OTLP_HEADERS: ENV_HEADERS,
            OTEL_EXPORTER_OTLP_TIMEOUT: ENV_TIMEOUT,
            OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE: "logs/certificate.env",
            OTEL_EXPORTER_OTLP_LOGS_COMPRESSION: Compression.Deflate.value,
            OTEL_EXPORTER_OTLP_LOGS_ENDPOINT: "https://logs.endpoint.env",
            OTEL_EXPORTER_OTLP_LOGS_HEADERS: "logsEnv1=val1,logsEnv2=val2,logsEnv3===val3==",
            OTEL_EXPORTER_OTLP_LOGS_TIMEOUT: "40",
        },
    )
    def test_exporter_metrics_env_take_priority(self):
        exporter = OTLPLogExporter()

        self.assertEqual(exporter._endpoint, "https://logs.endpoint.env")
        self.assertEqual(exporter._certificate_file, "logs/certificate.env")
        self.assertEqual(exporter._timeout, 40)
        self.assertIs(exporter._compression, Compression.Deflate)
        self.assertEqual(
            exporter._headers,
            {
                "logsenv1": "val1",
                "logsenv2": "val2",
                "logsenv3": "==val3==",
            },
        )
        self.assertIsInstance(exporter._session, requests.Session)

    @patch.dict(
        "os.environ",
        {
            OTEL_EXPORTER_OTLP_CERTIFICATE: ENV_CERTIFICATE,
            OTEL_EXPORTER_OTLP_COMPRESSION: Compression.Gzip.value,
            OTEL_EXPORTER_OTLP_ENDPOINT: ENV_ENDPOINT,
            OTEL_EXPORTER_OTLP_HEADERS: ENV_HEADERS,
            OTEL_EXPORTER_OTLP_TIMEOUT: ENV_TIMEOUT,
        },
    )
    def test_exporter_constructor_take_priority(self):
        sess = MagicMock()
        exporter = OTLPLogExporter(
            endpoint="endpoint.local:69/logs",
            certificate_file="/hello.crt",
            headers={"testHeader1": "value1", "testHeader2": "value2"},
            timeout=70,
            compression=Compression.NoCompression,
            session=sess(),
        )

        self.assertEqual(exporter._endpoint, "endpoint.local:69/logs")
        self.assertEqual(exporter._certificate_file, "/hello.crt")
        self.assertEqual(exporter._timeout, 70)
        self.assertIs(exporter._compression, Compression.NoCompression)
        self.assertEqual(
            exporter._headers,
            {"testHeader1": "value1", "testHeader2": "value2"},
        )
        self.assertTrue(sess.called)

    @patch.dict(
        "os.environ",
        {
            OTEL_EXPORTER_OTLP_CERTIFICATE: ENV_CERTIFICATE,
            OTEL_EXPORTER_OTLP_COMPRESSION: Compression.Gzip.value,
            OTEL_EXPORTER_OTLP_ENDPOINT: ENV_ENDPOINT,
            OTEL_EXPORTER_OTLP_HEADERS: ENV_HEADERS,
            OTEL_EXPORTER_OTLP_TIMEOUT: ENV_TIMEOUT,
        },
    )
    def test_exporter_env(self):

        exporter = OTLPLogExporter()

        self.assertEqual(
            exporter._endpoint, ENV_ENDPOINT + DEFAULT_LOGS_EXPORT_PATH
        )
        self.assertEqual(exporter._certificate_file, ENV_CERTIFICATE)
        self.assertEqual(exporter._timeout, int(ENV_TIMEOUT))
        self.assertIs(exporter._compression, Compression.Gzip)
        self.assertEqual(
            exporter._headers, {"envheader1": "val1", "envheader2": "val2"}
        )
        self.assertIsInstance(exporter._session, requests.Session)

    def test_encode(self):
        sdk_logs, expected_encoding = self.get_test_logs()
        self.assertEqual(
            _ProtobufEncoder().encode(sdk_logs), expected_encoding
        )

    def test_serialize(self):
        sdk_logs, expected_encoding = self.get_test_logs()
        self.assertEqual(
            _ProtobufEncoder().serialize(sdk_logs),
            expected_encoding.SerializeToString(),
        )

    @responses.activate
    @patch("opentelemetry.exporter.otlp.proto.http._log_exporter.backoff")
    @patch("opentelemetry.exporter.otlp.proto.http._log_exporter.sleep")
    def test_handles_backoff_v2_api(self, mock_sleep, mock_backoff):
        # In backoff ~= 2.0.0 the first value yielded from expo is None.
        def generate_delays(*args, **kwargs):
            if _is_backoff_v2:
                yield None
            yield 1

        mock_backoff.expo.configure_mock(**{"side_effect": generate_delays})

        # return a retryable error
        responses.add(
            responses.POST,
            "http://logs.example.com/export",
            json={"error": "something exploded"},
            status=500,
        )

        exporter = OTLPLogExporter(endpoint="http://logs.example.com/export")
        logs = self._get_sdk_log_data()

        exporter.export(logs)
        mock_sleep.assert_called_once_with(1)

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
