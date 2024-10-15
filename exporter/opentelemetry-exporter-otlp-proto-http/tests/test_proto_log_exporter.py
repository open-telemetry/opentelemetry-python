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
from time import time
from typing import List
from unittest.mock import MagicMock, Mock, call, patch

import requests
import responses
from google.protobuf.json_format import MessageToDict
from responses.registries import OrderedRegistry

from opentelemetry._logs import SeverityNumber
from opentelemetry.exporter.otlp.proto.common.exporter import (
    RetryableExportError,
)
from opentelemetry.exporter.otlp.proto.http import Compression
from opentelemetry.exporter.otlp.proto.http._log_exporter import (
    DEFAULT_COMPRESSION,
    DEFAULT_ENDPOINT,
    DEFAULT_LOGS_EXPORT_PATH,
    DEFAULT_TIMEOUT,
    OTLPLogExporter,
)
from opentelemetry.exporter.otlp.proto.http.version import __version__
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceRequest,
)
from opentelemetry.sdk._logs import LogData
from opentelemetry.sdk._logs import LogRecord as SDKLogRecord
from opentelemetry.sdk._logs.export import LogExportResult
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE,
    OTEL_EXPORTER_OTLP_LOGS_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_LOGS_CLIENT_KEY,
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
ENV_CLIENT_CERTIFICATE = "/etc/client-cert.pem"
ENV_CLIENT_KEY = "/etc/client-key.pem"
ENV_HEADERS = "envHeader1=val1,envHeader2=val2"
ENV_TIMEOUT = "30"


class TestOTLPHTTPLogExporter(unittest.TestCase):
    def test_constructor_default(self):

        exporter = OTLPLogExporter()

        self.assertEqual(
            exporter._endpoint, DEFAULT_ENDPOINT + DEFAULT_LOGS_EXPORT_PATH
        )
        self.assertEqual(exporter._certificate_file, True)
        self.assertEqual(exporter._client_certificate_file, None)
        self.assertEqual(exporter._client_key_file, None)
        self.assertEqual(exporter._exporter._timeout_sec, DEFAULT_TIMEOUT)
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
            OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE: ENV_CLIENT_CERTIFICATE,
            OTEL_EXPORTER_OTLP_CLIENT_KEY: ENV_CLIENT_KEY,
            OTEL_EXPORTER_OTLP_COMPRESSION: Compression.Gzip.value,
            OTEL_EXPORTER_OTLP_ENDPOINT: ENV_ENDPOINT,
            OTEL_EXPORTER_OTLP_HEADERS: ENV_HEADERS,
            OTEL_EXPORTER_OTLP_TIMEOUT: ENV_TIMEOUT,
            OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE: "logs/certificate.env",
            OTEL_EXPORTER_OTLP_LOGS_CLIENT_CERTIFICATE: "logs/client-cert.pem",
            OTEL_EXPORTER_OTLP_LOGS_CLIENT_KEY: "logs/client-key.pem",
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
        self.assertEqual(
            exporter._client_certificate_file, "logs/client-cert.pem"
        )
        self.assertEqual(exporter._client_key_file, "logs/client-key.pem")
        self.assertEqual(exporter._exporter._timeout_sec, 40)
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
            OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE: ENV_CLIENT_CERTIFICATE,
            OTEL_EXPORTER_OTLP_CLIENT_KEY: ENV_CLIENT_KEY,
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
            client_key_file="/client-key.pem",
            client_certificate_file="/client-cert.pem",
            headers={"testHeader1": "value1", "testHeader2": "value2"},
            timeout=70,
            compression=Compression.NoCompression,
            session=sess(),
        )

        self.assertEqual(exporter._endpoint, "endpoint.local:69/logs")
        self.assertEqual(exporter._certificate_file, "/hello.crt")
        self.assertEqual(exporter._client_certificate_file, "/client-cert.pem")
        self.assertEqual(exporter._client_key_file, "/client-key.pem")
        self.assertEqual(exporter._exporter._timeout_sec, 70)
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
            OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE: ENV_CLIENT_CERTIFICATE,
            OTEL_EXPORTER_OTLP_CLIENT_KEY: ENV_CLIENT_KEY,
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
        self.assertEqual(
            exporter._client_certificate_file, ENV_CLIENT_CERTIFICATE
        )
        self.assertEqual(exporter._client_key_file, ENV_CLIENT_KEY)
        self.assertEqual(exporter._exporter._timeout_sec, int(ENV_TIMEOUT))
        self.assertIs(exporter._compression, Compression.Gzip)
        self.assertEqual(
            exporter._headers, {"envheader1": "val1", "envheader2": "val2"}
        )
        self.assertIsInstance(exporter._session, requests.Session)

    @patch(
        "opentelemetry.exporter.otlp.proto.http._log_exporter.OTLPLogExporter._export",
        side_effect=RetryableExportError(None),
    )
    def test_export_uses_arg_timeout_when_given(self, export_mock) -> None:
        exporter = OTLPLogExporter(
            endpoint="http://traces.example.com/export", timeout=20
        )

        with self.assertLogs(level="WARNING"):
            start = time()
            exporter.export(self._get_sdk_log_data(), timeout_millis=100.0)
            duration = time() - start
        self.assertAlmostEqual(duration, 0.1, places=1)

    @staticmethod
    def export_log_and_deserialize(log):
        with patch("requests.Session.post") as mock_post:
            exporter = OTLPLogExporter()
            exporter.export([log])
            request_body = mock_post.call_args[1]["data"]
            request = ExportLogsServiceRequest()
            request.ParseFromString(request_body)
            request_dict = MessageToDict(request)
            log_records = (
                request_dict.get("resourceLogs")[0]
                .get("scopeLogs")[0]
                .get("logRecords")
            )
            return log_records

    def test_exported_log_without_trace_id(self):
        log = LogData(
            log_record=SDKLogRecord(
                timestamp=1644650195189786182,
                trace_id=0,
                span_id=1312458408527513292,
                trace_flags=TraceFlags(0x01),
                severity_text="WARN",
                severity_number=SeverityNumber.WARN,
                body="Invalid trace id check",
                resource=SDKResource({"first_resource": "value"}),
                attributes={"a": 1, "b": "c"},
            ),
            instrumentation_scope=InstrumentationScope("name", "version"),
        )
        log_records = TestOTLPHTTPLogExporter.export_log_and_deserialize(log)
        if log_records:
            log_record = log_records[0]
            self.assertIn("spanId", log_record)
            self.assertNotIn(
                "traceId",
                log_record,
                "trace_id should not be present in the log record",
            )
        else:
            self.fail("No log records found")

    def test_exported_log_without_span_id(self):
        log = LogData(
            log_record=SDKLogRecord(
                timestamp=1644650195189786360,
                trace_id=89564621134313219400156819398935297696,
                span_id=0,
                trace_flags=TraceFlags(0x01),
                severity_text="WARN",
                severity_number=SeverityNumber.WARN,
                body="Invalid span id check",
                resource=SDKResource({"first_resource": "value"}),
                attributes={"a": 1, "b": "c"},
            ),
            instrumentation_scope=InstrumentationScope("name", "version"),
        )
        log_records = TestOTLPHTTPLogExporter.export_log_and_deserialize(log)
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

    # Pylint is wrong about this
    @responses.activate(  # pylint: disable=unexpected-keyword-arg,no-value-for-parameter
        registry=OrderedRegistry
    )
    def test_exponential_backoff(self):
        for status in [500, 500, 500, 200]:
            responses.add(
                responses.POST,
                "http://logs.example.com/export",
                json={"error": "something exploded"},
                status=status,
            )

        exporter = OTLPLogExporter(endpoint="http://logs.example.com/export")
        logs = self._get_sdk_log_data()

        with patch.object(
            exporter._exporter._shutdown,  # pylint: disable=protected-access
            "wait",
        ) as wait_mock:
            exporter.export(logs)
        wait_mock.assert_has_calls([call(1), call(2), call(4)])

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

    def test_2xx_status_code(self):
        """
        Test that any HTTP 2XX code returns a successful result
        """

        self.assertEqual(
            OTLPLogExporter(
                session=Mock(**{"post.return_value": Mock(ok=True)})
            ).export(MagicMock()),
            LogExportResult.SUCCESS,
        )
