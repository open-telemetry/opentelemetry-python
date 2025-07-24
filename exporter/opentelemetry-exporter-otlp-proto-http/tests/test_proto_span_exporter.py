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

import threading
import time
import unittest
from logging import WARNING
from unittest.mock import MagicMock, Mock, patch

import requests
from requests import Session
from requests.models import Response

from opentelemetry.exporter.otlp.proto.http import Compression
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    DEFAULT_COMPRESSION,
    DEFAULT_ENDPOINT,
    DEFAULT_TIMEOUT,
    DEFAULT_TRACES_EXPORT_PATH,
    OTLPSpanExporter,
)
from opentelemetry.exporter.otlp.proto.http.version import __version__
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_TIMEOUT,
    OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE,
    OTEL_EXPORTER_OTLP_TRACES_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_TRACES_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_TRACES_COMPRESSION,
    OTEL_EXPORTER_OTLP_TRACES_ENDPOINT,
    OTEL_EXPORTER_OTLP_TRACES_HEADERS,
    OTEL_EXPORTER_OTLP_TRACES_TIMEOUT,
)
from opentelemetry.sdk.trace import _Span
from opentelemetry.sdk.trace.export import SpanExportResult

OS_ENV_ENDPOINT = "os.env.base"
OS_ENV_CERTIFICATE = "os/env/base.crt"
OS_ENV_CLIENT_CERTIFICATE = "os/env/client-cert.pem"
OS_ENV_CLIENT_KEY = "os/env/client-key.pem"
OS_ENV_HEADERS = "envHeader1=val1,envHeader2=val2"
OS_ENV_TIMEOUT = "30"
BASIC_SPAN = _Span(
    "abc",
    context=Mock(
        **{
            "trace_state": {"a": "b", "c": "d"},
            "span_id": 10217189687419569865,
            "trace_id": 67545097771067222548457157018666467027,
        }
    ),
)


# pylint: disable=protected-access
class TestOTLPSpanExporter(unittest.TestCase):
    def test_constructor_default(self):
        exporter = OTLPSpanExporter()

        self.assertEqual(
            exporter._endpoint, DEFAULT_ENDPOINT + DEFAULT_TRACES_EXPORT_PATH
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
            OTEL_EXPORTER_OTLP_CERTIFICATE: OS_ENV_CERTIFICATE,
            OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE: OS_ENV_CLIENT_CERTIFICATE,
            OTEL_EXPORTER_OTLP_CLIENT_KEY: OS_ENV_CLIENT_KEY,
            OTEL_EXPORTER_OTLP_COMPRESSION: Compression.Gzip.value,
            OTEL_EXPORTER_OTLP_ENDPOINT: OS_ENV_ENDPOINT,
            OTEL_EXPORTER_OTLP_HEADERS: OS_ENV_HEADERS,
            OTEL_EXPORTER_OTLP_TIMEOUT: OS_ENV_TIMEOUT,
            OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE: "traces/certificate.env",
            OTEL_EXPORTER_OTLP_TRACES_CLIENT_CERTIFICATE: "traces/client-cert.pem",
            OTEL_EXPORTER_OTLP_TRACES_CLIENT_KEY: "traces/client-key.pem",
            OTEL_EXPORTER_OTLP_TRACES_COMPRESSION: Compression.Deflate.value,
            OTEL_EXPORTER_OTLP_TRACES_ENDPOINT: "https://traces.endpoint.env",
            OTEL_EXPORTER_OTLP_TRACES_HEADERS: "tracesEnv1=val1,tracesEnv2=val2,traceEnv3===val3==",
            OTEL_EXPORTER_OTLP_TRACES_TIMEOUT: "40",
        },
    )
    def test_exporter_traces_env_take_priority(self):
        exporter = OTLPSpanExporter()

        self.assertEqual(exporter._endpoint, "https://traces.endpoint.env")
        self.assertEqual(exporter._certificate_file, "traces/certificate.env")
        self.assertEqual(
            exporter._client_certificate_file, "traces/client-cert.pem"
        )
        self.assertEqual(exporter._client_key_file, "traces/client-key.pem")
        self.assertEqual(exporter._timeout, 40)
        self.assertIs(exporter._compression, Compression.Deflate)
        self.assertEqual(
            exporter._headers,
            {
                "tracesenv1": "val1",
                "tracesenv2": "val2",
                "traceenv3": "==val3==",
            },
        )
        self.assertIsInstance(exporter._session, requests.Session)

    @patch.dict(
        "os.environ",
        {
            OTEL_EXPORTER_OTLP_CERTIFICATE: OS_ENV_CERTIFICATE,
            OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE: OS_ENV_CLIENT_CERTIFICATE,
            OTEL_EXPORTER_OTLP_CLIENT_KEY: OS_ENV_CLIENT_KEY,
            OTEL_EXPORTER_OTLP_COMPRESSION: Compression.Gzip.value,
            OTEL_EXPORTER_OTLP_ENDPOINT: OS_ENV_ENDPOINT,
            OTEL_EXPORTER_OTLP_TRACES_ENDPOINT: "https://traces.endpoint.env",
            OTEL_EXPORTER_OTLP_HEADERS: OS_ENV_HEADERS,
            OTEL_EXPORTER_OTLP_TIMEOUT: OS_ENV_TIMEOUT,
        },
    )
    def test_exporter_constructor_take_priority(self):
        exporter = OTLPSpanExporter(
            endpoint="example.com/1234",
            certificate_file="path/to/service.crt",
            client_key_file="path/to/client-key.pem",
            client_certificate_file="path/to/client-cert.pem",
            headers={"testHeader1": "value1", "testHeader2": "value2"},
            timeout=20,
            compression=Compression.NoCompression,
            session=requests.Session(),
        )

        self.assertEqual(exporter._endpoint, "example.com/1234")
        self.assertEqual(exporter._certificate_file, "path/to/service.crt")
        self.assertEqual(
            exporter._client_certificate_file, "path/to/client-cert.pem"
        )
        self.assertEqual(exporter._client_key_file, "path/to/client-key.pem")
        self.assertEqual(exporter._timeout, 20)
        self.assertIs(exporter._compression, Compression.NoCompression)
        self.assertEqual(
            exporter._headers,
            {"testHeader1": "value1", "testHeader2": "value2"},
        )
        self.assertIsInstance(exporter._session, requests.Session)

    @patch.dict(
        "os.environ",
        {
            OTEL_EXPORTER_OTLP_CERTIFICATE: OS_ENV_CERTIFICATE,
            OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE: OS_ENV_CLIENT_CERTIFICATE,
            OTEL_EXPORTER_OTLP_CLIENT_KEY: OS_ENV_CLIENT_KEY,
            OTEL_EXPORTER_OTLP_COMPRESSION: Compression.Gzip.value,
            OTEL_EXPORTER_OTLP_HEADERS: OS_ENV_HEADERS,
            OTEL_EXPORTER_OTLP_TIMEOUT: OS_ENV_TIMEOUT,
        },
    )
    def test_exporter_env(self):
        exporter = OTLPSpanExporter()

        self.assertEqual(exporter._certificate_file, OS_ENV_CERTIFICATE)
        self.assertEqual(
            exporter._client_certificate_file, OS_ENV_CLIENT_CERTIFICATE
        )
        self.assertEqual(exporter._client_key_file, OS_ENV_CLIENT_KEY)
        self.assertEqual(exporter._timeout, int(OS_ENV_TIMEOUT))
        self.assertIs(exporter._compression, Compression.Gzip)
        self.assertEqual(
            exporter._headers, {"envheader1": "val1", "envheader2": "val2"}
        )

    @patch.dict(
        "os.environ",
        {OTEL_EXPORTER_OTLP_ENDPOINT: OS_ENV_ENDPOINT},
    )
    def test_exporter_env_endpoint_without_slash(self):
        exporter = OTLPSpanExporter()

        self.assertEqual(
            exporter._endpoint,
            OS_ENV_ENDPOINT + f"/{DEFAULT_TRACES_EXPORT_PATH}",
        )

    @patch.dict(
        "os.environ",
        {OTEL_EXPORTER_OTLP_ENDPOINT: OS_ENV_ENDPOINT + "/"},
    )
    def test_exporter_env_endpoint_with_slash(self):
        exporter = OTLPSpanExporter()

        self.assertEqual(
            exporter._endpoint,
            OS_ENV_ENDPOINT + f"/{DEFAULT_TRACES_EXPORT_PATH}",
        )

    @patch.dict(
        "os.environ",
        {
            OTEL_EXPORTER_OTLP_HEADERS: "envHeader1=val1,envHeader2=val2,missingValue"
        },
    )
    def test_headers_parse_from_env(self):
        with self.assertLogs(level="WARNING") as cm:
            _ = OTLPSpanExporter()

            self.assertEqual(
                cm.records[0].message,
                (
                    "Header format invalid! Header values in environment "
                    "variables must be URL encoded per the OpenTelemetry "
                    "Protocol Exporter specification or a comma separated "
                    "list of name=value occurrences: missingValue"
                ),
            )

    @patch.object(OTLPSpanExporter, "_export", return_value=Mock(ok=True))
    def test_2xx_status_code(self, mock_otlp_metric_exporter):
        """
        Test that any HTTP 2XX code returns a successful result
        """

        self.assertEqual(
            OTLPSpanExporter().export(MagicMock()), SpanExportResult.SUCCESS
        )

    @patch.object(Session, "post")
    def test_retry_timeout(self, mock_post):
        exporter = OTLPSpanExporter(timeout=1.5)

        resp = Response()
        resp.status_code = 503
        resp.reason = "UNAVAILABLE"
        mock_post.return_value = resp
        with self.assertLogs(level=WARNING) as warning:
            before = time.time()
            # Set timeout to 1.5 seconds
            self.assertEqual(
                exporter.export([BASIC_SPAN]),
                SpanExportResult.FAILURE,
            )
            after = time.time()
            # First call at time 0, second at time 1, then an early return before the second backoff sleep b/c it would exceed timeout.
            self.assertEqual(mock_post.call_count, 2)
            # There's a +/-20% jitter on each backoff.
            self.assertTrue(0.75 < after - before < 1.25)
            self.assertIn(
                "Transient error UNAVAILABLE encountered while exporting span batch, retrying in",
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
        exporter = OTLPSpanExporter(timeout=0.4)
        exporter.export([BASIC_SPAN])

    @patch.object(Session, "post")
    def test_shutdown_interrupts_retry_backoff(self, mock_post):
        exporter = OTLPSpanExporter(timeout=1.5)

        resp = Response()
        resp.status_code = 503
        resp.reason = "UNAVAILABLE"
        mock_post.return_value = resp
        thread = threading.Thread(target=exporter.export, args=([BASIC_SPAN],))
        with self.assertLogs(level=WARNING) as warning:
            before = time.time()
            thread.start()
            # Wait for the first attempt to fail, then enter a 1 second backoff.
            time.sleep(0.05)
            # Should cause export to wake up and return.
            exporter.shutdown()
            thread.join()
            after = time.time()
            self.assertIn(
                "Transient error UNAVAILABLE encountered while exporting span batch, retrying in",
                warning.records[0].message,
            )
            self.assertIn(
                "Shutdown in progress, aborting retry.",
                warning.records[1].message,
            )

            assert after - before < 0.2
