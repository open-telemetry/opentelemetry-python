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

import time
import unittest
from logging import WARNING
from typing import List
from unittest.mock import MagicMock, Mock, patch

import requests
from google.protobuf.json_format import MessageToDict
from requests import Session
from requests.models import Response

from opentelemetry._logs import SeverityNumber
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
from opentelemetry.trace import (
    NonRecordingSpan,
    SpanContext,
    TraceFlags,
    set_span_in_context,
)

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
        self.assertEqual(exporter._timeout, int(ENV_TIMEOUT))
        self.assertIs(exporter._compression, Compression.Gzip)
        self.assertEqual(
            exporter._headers, {"envheader1": "val1", "envheader2": "val2"}
        )
        self.assertIsInstance(exporter._session, requests.Session)

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
        ctx = set_span_in_context(
            NonRecordingSpan(
                SpanContext(
                    0,
                    1312458408527513292,
                    False,
                    TraceFlags(0x01),
                )
            )
        )
        log = LogData(
            log_record=SDKLogRecord(
                timestamp=1644650195189786182,
                context=ctx,
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
        ctx = set_span_in_context(
            NonRecordingSpan(
                SpanContext(
                    89564621134313219400156819398935297696,
                    0,
                    False,
                    TraceFlags(0x01),
                )
            )
        )

        log = LogData(
            log_record=SDKLogRecord(
                timestamp=1644650195189786360,
                context=ctx,
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

    @staticmethod
    def _get_sdk_log_data() -> List[LogData]:
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
        log1 = LogData(
            log_record=SDKLogRecord(
                timestamp=1644650195189786880,
                context=ctx_log1,
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

        ctx_log2 = set_span_in_context(
            NonRecordingSpan(
                SpanContext(
                    0,
                    0,
                    False,
                )
            )
        )
        log2 = LogData(
            log_record=SDKLogRecord(
                timestamp=1644650249738562048,
                context=ctx_log2,
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
        ctx_log3 = set_span_in_context(
            NonRecordingSpan(
                SpanContext(
                    271615924622795969659406376515024083555,
                    4242561578944770265,
                    False,
                    TraceFlags(0x01),
                )
            )
        )
        log3 = LogData(
            log_record=SDKLogRecord(
                timestamp=1644650427658989056,
                context=ctx_log3,
                severity_text="DEBUG",
                severity_number=SeverityNumber.DEBUG,
                body="To our galaxy",
                resource=SDKResource({"second_resource": "CASE"}),
                attributes={"a": 1, "b": "c"},
            ),
            instrumentation_scope=None,
        )
        ctx_log4 = set_span_in_context(
            NonRecordingSpan(
                SpanContext(
                    212592107417388365804938480559624925555,
                    6077757853989569223,
                    False,
                    TraceFlags(0x01),
                )
            )
        )
        log4 = LogData(
            log_record=SDKLogRecord(
                timestamp=1644650584292683008,
                context=ctx_log4,
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

    @patch.object(OTLPLogExporter, "_export", return_value=Mock(ok=True))
    def test_2xx_status_code(self, mock_otlp_metric_exporter):
        """
        Test that any HTTP 2XX code returns a successful result
        """

        self.assertEqual(
            OTLPLogExporter().export(MagicMock()), LogExportResult.SUCCESS
        )

    @patch.object(Session, "post")
    def test_retry_timeout(self, mock_post):
        exporter = OTLPLogExporter(timeout=1.5)

        resp = Response()
        resp.status_code = 503
        resp.reason = "UNAVAILABLE"
        mock_post.return_value = resp
        with self.assertLogs(level=WARNING) as warning:
            before = time.time()
            # Set timeout to 1.5 seconds
            self.assertEqual(
                exporter.export(self._get_sdk_log_data()),
                LogExportResult.FAILURE,
            )
            after = time.time()
            # First call at time 0, second at time 1, then an early return before the second backoff sleep b/c it would exceed timeout.
            self.assertEqual(mock_post.call_count, 2)
            # There's a +/-20% jitter on each backoff.
            self.assertTrue(0.75 < after - before < 1.25)
            self.assertIn(
                "Transient error UNAVAILABLE encountered while exporting logs batch, retrying in",
                warning.records[0].message,
            )

    @patch.object(Session, "post")
    def test_timeout_set_correctly(self, mock_post):
        resp = Response()
        resp.status_code = 200

        def export_side_effect(*args, **kwargs):
            # Timeout should be set to something slightly less than 400 milliseconds depending on how much time has passed.
            self.assertAlmostEqual(0.4, kwargs["timeout"], 2)
            return resp

        mock_post.side_effect = export_side_effect
        exporter = OTLPLogExporter(timeout=0.4)
        exporter.export(self._get_sdk_log_data())
