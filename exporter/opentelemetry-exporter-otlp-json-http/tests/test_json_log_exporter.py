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

import json
import unittest
from typing import List
from unittest.mock import MagicMock, Mock, call, patch

import requests
import responses

from opentelemetry._logs import LogRecord, SeverityNumber
from opentelemetry.exporter.otlp.json.http import Compression
from opentelemetry.exporter.otlp.json.http._log_exporter import (
    DEFAULT_COMPRESSION,
    DEFAULT_ENDPOINT,
    DEFAULT_LOGS_EXPORT_PATH,
    DEFAULT_TIMEOUT,
    OTLPLogExporter,
)
from opentelemetry.exporter.otlp.json.http.version import __version__
from opentelemetry.sdk._logs import ReadWriteLogRecord
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
            "application/json",
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
    def test_exporter_logs_env_take_priority(self):
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

    @patch("requests.Session.post")
    def test_export_success(self, mock_post):
        mock_response = Mock()
        mock_response.ok = True
        mock_post.return_value = mock_response

        exporter = OTLPLogExporter()
        logs = self._get_sdk_log_data()

        result = exporter.export(logs)

        self.assertEqual(result, LogExportResult.SUCCESS)
        mock_post.assert_called_once()

        # Verify that the request contains JSON data
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["url"], exporter._endpoint)
        self.assertTrue(isinstance(kwargs["data"], bytes))

        # Verify the data can be decoded as JSON
        decoded_data = json.loads(kwargs["data"].decode("utf-8"))
        self.assertIn("resourceLogs", decoded_data)

    @patch("requests.Session.post")
    def test_export_failure(self, mock_post):
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 400
        mock_post.return_value = mock_response

        exporter = OTLPLogExporter()
        logs = self._get_sdk_log_data()

        result = exporter.export(logs)

        self.assertEqual(result, LogExportResult.FAILURE)

    @responses.activate
    @patch("opentelemetry.exporter.otlp.json.http._log_exporter.sleep")
    def test_exponential_backoff(self, mock_sleep):
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
        mock_sleep.assert_has_calls(
            [call(1), call(2), call(4), call(8), call(16), call(32)]
        )

    @patch.object(OTLPLogExporter, "_export", return_value=Mock(ok=True))
    def test_2xx_status_code(self, mock_otlp_log_exporter):
        """
        Test that any HTTP 2XX code returns a successful result
        """
        self.assertEqual(
            OTLPLogExporter().export(MagicMock()), LogExportResult.SUCCESS
        )

    def test_shutdown(self):
        mock_session = Mock()
        exporter = OTLPLogExporter(session=mock_session)
        exporter.shutdown()
        mock_session.close.assert_called_once()
        self.assertTrue(exporter._shutdown)

        # Second call should not close the session again
        mock_session.reset_mock()
        exporter.shutdown()
        mock_session.close.assert_not_called()

    @staticmethod
    def _get_sdk_log_data() -> List[ReadWriteLogRecord]:
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
                attributes={"a": 1, "b": "c"},
            ),
            resource=SDKResource({"first_resource": "value"}),
            instrumentation_scope=InstrumentationScope(
                "first_name", "first_version"
            ),
        )

        log2 = ReadWriteLogRecord(
            LogRecord(
                timestamp=1644650249738562048,
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
        log3 = ReadWriteLogRecord(
            LogRecord(
                timestamp=1644650427658989056,
                context=ctx_log3,
                severity_text="DEBUG",
                severity_number=SeverityNumber.DEBUG,
                body="To our galaxy",
                attributes={"a": 1, "b": "c"},
            ),
            resource=SDKResource({"second_resource": "CASE"}),
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
        log4 = ReadWriteLogRecord(
            LogRecord(
                timestamp=1644650584292683008,
                context=ctx_log4,
                severity_text="INFO",
                severity_number=SeverityNumber.INFO,
                body="Love is the one thing that transcends time and space",
                attributes={"filename": "model.py", "func_name": "run_method"},
            ),
            resource=SDKResource({"first_resource": "value"}),
            instrumentation_scope=InstrumentationScope(
                "another_name", "another_version"
            ),
        )

        return [log1, log2, log3, log4]
