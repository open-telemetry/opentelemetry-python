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

from __future__ import annotations

import unittest
from logging import WARNING
from unittest.mock import patch

import urllib3

from opentelemetry._logs import LogRecord
from opentelemetry.exporter.otlp.json.http import Compression
from opentelemetry.exporter.otlp.json.http._internal import (
    _DEFAULT_ENDPOINT,
    _DEFAULT_TIMEOUT,
)
from opentelemetry.exporter.otlp.json.http._log_exporter import (
    DEFAULT_LOGS_EXPORT_PATH,
    OTLPLogExporter,
)
from opentelemetry.exporter.otlp.json.http.version import __version__
from opentelemetry.sdk._logs import ReadWriteLogRecord
from opentelemetry.sdk._logs.export import LogRecordExportResult
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

from .helpers import CountdownEvent, _build_mock_response, mock_clock

_DEFAULT_LOGS_ENDPOINT = (
    _DEFAULT_ENDPOINT.rstrip("/") + "/" + DEFAULT_LOGS_EXPORT_PATH
)

_SIMPLE_LOG = ReadWriteLogRecord(
    LogRecord(timestamp=1),
    resource=SDKResource({}),
)


# pylint: disable=protected-access
class TestOTLPLogExporter(unittest.TestCase):
    def test_constructor_default(self):
        exporter = OTLPLogExporter()

        self.assertEqual(exporter._client._endpoint, _DEFAULT_LOGS_ENDPOINT)
        self.assertIsNone(exporter._certificate_file)
        self.assertIsNone(exporter._client_key_file)
        self.assertIsNone(exporter._client_certificate_file)
        self.assertEqual(exporter._client._timeout, _DEFAULT_TIMEOUT)
        self.assertIs(
            exporter._client._compression, Compression.NO_COMPRESSION
        )
        self.assertEqual(
            exporter._client._headers.get("Content-Type"), "application/json"
        )
        self.assertEqual(
            exporter._client._headers.get("User-Agent"),
            "OTel-OTLP-JSON-Exporter-Python/" + __version__,
        )

    @patch.dict(
        "os.environ",
        {
            OTEL_EXPORTER_OTLP_CERTIFICATE: "os/env/base.crt",
            OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE: "os/env/client-cert.pem",
            OTEL_EXPORTER_OTLP_CLIENT_KEY: "os/env/client-key.pem",
            OTEL_EXPORTER_OTLP_COMPRESSION: Compression.GZIP.value,
            OTEL_EXPORTER_OTLP_ENDPOINT: "http://os.env.base",
            OTEL_EXPORTER_OTLP_HEADERS: "envHeader1=val1,envHeader2=val2",
            OTEL_EXPORTER_OTLP_TIMEOUT: "30",
            OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE: "logs/certificate.env",
            OTEL_EXPORTER_OTLP_LOGS_CLIENT_CERTIFICATE: "logs/client-cert.pem",
            OTEL_EXPORTER_OTLP_LOGS_CLIENT_KEY: "logs/client-key.pem",
            OTEL_EXPORTER_OTLP_LOGS_COMPRESSION: Compression.DEFLATE.value,
            OTEL_EXPORTER_OTLP_LOGS_ENDPOINT: "https://logs.endpoint.env",
            OTEL_EXPORTER_OTLP_LOGS_HEADERS: "logsEnv1=val1,logsEnv2=val2",
            OTEL_EXPORTER_OTLP_LOGS_TIMEOUT: "40",
        },
    )
    def test_logs_env_take_priority(self):
        exporter = OTLPLogExporter()

        self.assertEqual(
            exporter._client._endpoint, "https://logs.endpoint.env"
        )
        self.assertEqual(exporter._certificate_file, "logs/certificate.env")
        self.assertEqual(
            exporter._client_certificate_file, "logs/client-cert.pem"
        )
        self.assertEqual(exporter._client_key_file, "logs/client-key.pem")
        self.assertEqual(exporter._client._timeout, 40)
        self.assertIs(exporter._client._compression, Compression.DEFLATE)
        self.assertEqual(exporter._client._headers.get("logsenv1"), "val1")
        self.assertEqual(exporter._client._headers.get("logsenv2"), "val2")
        self.assertNotIn("envheader1", exporter._client._headers)

    @patch.dict(
        "os.environ",
        {
            OTEL_EXPORTER_OTLP_CERTIFICATE: "os/env/base.crt",
            OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE: "os/env/client-cert.pem",
            OTEL_EXPORTER_OTLP_CLIENT_KEY: "os/env/client-key.pem",
            OTEL_EXPORTER_OTLP_COMPRESSION: Compression.GZIP.value,
            OTEL_EXPORTER_OTLP_ENDPOINT: "http://os.env.base",
            OTEL_EXPORTER_OTLP_HEADERS: "envHeader1=val1",
            OTEL_EXPORTER_OTLP_TIMEOUT: "30",
            OTEL_EXPORTER_OTLP_LOGS_ENDPOINT: "https://logs.endpoint.env",
        },
    )
    def test_constructor_args_take_priority(self):
        exporter = OTLPLogExporter(
            endpoint="https://custom.endpoint/logs",
            certificate_file="path/to/service.crt",
            client_key_file="path/to/client-key.pem",
            client_certificate_file="path/to/client-cert.pem",
            headers={"customHeader": "customValue"},
            timeout=20,
            compression=Compression.NO_COMPRESSION,
        )

        self.assertEqual(
            exporter._client._endpoint, "https://custom.endpoint/logs"
        )
        self.assertEqual(exporter._certificate_file, "path/to/service.crt")
        self.assertEqual(
            exporter._client_certificate_file, "path/to/client-cert.pem"
        )
        self.assertEqual(exporter._client_key_file, "path/to/client-key.pem")
        self.assertEqual(exporter._client._timeout, 20)
        self.assertIs(
            exporter._client._compression, Compression.NO_COMPRESSION
        )

    @patch.dict(
        "os.environ",
        {
            OTEL_EXPORTER_OTLP_CERTIFICATE: "os/env/base.crt",
            OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE: "os/env/client-cert.pem",
            OTEL_EXPORTER_OTLP_CLIENT_KEY: "os/env/client-key.pem",
            OTEL_EXPORTER_OTLP_COMPRESSION: Compression.GZIP.value,
            OTEL_EXPORTER_OTLP_HEADERS: "envHeader1=val1",
            OTEL_EXPORTER_OTLP_TIMEOUT: "30",
        },
    )
    def test_common_env_vars(self):
        exporter = OTLPLogExporter()

        self.assertEqual(exporter._certificate_file, "os/env/base.crt")
        self.assertEqual(
            exporter._client_certificate_file, "os/env/client-cert.pem"
        )
        self.assertEqual(exporter._client_key_file, "os/env/client-key.pem")
        self.assertEqual(exporter._client._timeout, 30)
        self.assertIs(exporter._client._compression, Compression.GZIP)

    def test_endpoint_env_slash_normalization(self):
        for endpoint in ("http://os.env.base", "http://os.env.base/"):
            with self.subTest(endpoint=endpoint):
                with patch.dict(
                    "os.environ",
                    {OTEL_EXPORTER_OTLP_ENDPOINT: endpoint},
                ):
                    exporter = OTLPLogExporter()
                    self.assertEqual(
                        exporter._client._endpoint,
                        f"http://os.env.base/{DEFAULT_LOGS_EXPORT_PATH}",
                    )

    @patch.dict(
        "os.environ",
        {OTEL_EXPORTER_OTLP_HEADERS: "envHeader1=val1,missingValue"},
    )
    def test_headers_parse_from_env(self):
        with self.assertLogs(level=WARNING):
            OTLPLogExporter()

    @patch.object(urllib3.PoolManager, "request")
    def test_2xx_status_code(self, mock_request):
        mock_request.return_value = _build_mock_response(200)
        result = OTLPLogExporter().export([_SIMPLE_LOG])
        self.assertEqual(result, LogRecordExportResult.SUCCESS)

    @patch.object(urllib3.PoolManager, "request")
    def test_retry_timeout(self, mock_request):
        exporter = OTLPLogExporter(timeout=1.5)
        exporter._client._jitter = 0
        mock_request.return_value = _build_mock_response(503)

        with mock_clock() as now, self.assertLogs(level=WARNING) as warning:
            result = exporter.export([_SIMPLE_LOG])

        self.assertEqual(result, LogRecordExportResult.FAILURE)
        self.assertEqual(mock_request.call_count, 2)
        self.assertEqual(now(), 1.0)
        self.assertIn("Transient error", warning.records[0].message)

    @patch.object(urllib3.PoolManager, "request")
    def test_export_retryable_timeout_error(self, mock_request):
        exporter = OTLPLogExporter(timeout=1.5)
        exporter._client._jitter = 0
        mock_request.side_effect = urllib3.exceptions.TimeoutError()

        with mock_clock() as now, self.assertLogs(level=WARNING):
            result = exporter.export([_SIMPLE_LOG])

        self.assertEqual(result, LogRecordExportResult.FAILURE)
        self.assertEqual(mock_request.call_count, 2)
        self.assertEqual(now(), 1.0)

    @patch.object(urllib3.PoolManager, "request")
    def test_export_non_retryable_error(self, mock_request):
        exporter = OTLPLogExporter(timeout=1.5)
        mock_request.side_effect = Exception("non-retryable")

        with self.assertLogs(level=WARNING):
            result = exporter.export([_SIMPLE_LOG])

        self.assertEqual(result, LogRecordExportResult.FAILURE)
        self.assertEqual(mock_request.call_count, 1)

    @patch.object(urllib3.PoolManager, "request")
    def test_shutdown_interrupts_retry_backoff(self, mock_request):
        exporter = OTLPLogExporter(timeout=100.0)
        exporter._client._jitter = 0
        exporter._client._shutdown_in_progress = CountdownEvent(
            trigger_after=2
        )
        mock_request.return_value = _build_mock_response(503)

        with mock_clock(), self.assertLogs(level=WARNING):
            result = exporter.export([_SIMPLE_LOG])

        self.assertEqual(result, LogRecordExportResult.FAILURE)
        self.assertEqual(mock_request.call_count, 2)

    def test_shutdown_logs_warning_on_double_shutdown(self):
        exporter = OTLPLogExporter()
        exporter.shutdown()
        with self.assertLogs(level=WARNING) as warning:
            exporter.shutdown()
        self.assertIn("already shutdown", warning.records[0].message)

    def test_export_after_shutdown_returns_failure(self):
        exporter = OTLPLogExporter()
        exporter.shutdown()
        with self.assertLogs(level=WARNING):
            result = exporter.export([_SIMPLE_LOG])
        self.assertEqual(result, LogRecordExportResult.FAILURE)

    def test_force_flush(self):
        self.assertTrue(OTLPLogExporter().force_flush())
