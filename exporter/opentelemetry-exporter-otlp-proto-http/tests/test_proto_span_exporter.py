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
from collections import OrderedDict
from unittest.mock import Mock, patch

import requests
import responses

from opentelemetry.exporter.otlp.proto.http import Compression
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    DEFAULT_COMPRESSION,
    DEFAULT_ENDPOINT,
    DEFAULT_TIMEOUT,
    DEFAULT_TRACES_EXPORT_PATH,
    OTLPSpanExporter,
    _is_backoff_v2,
)
from opentelemetry.exporter.otlp.proto.http.version import __version__
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_TIMEOUT,
    OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE,
    OTEL_EXPORTER_OTLP_TRACES_COMPRESSION,
    OTEL_EXPORTER_OTLP_TRACES_ENDPOINT,
    OTEL_EXPORTER_OTLP_TRACES_HEADERS,
    OTEL_EXPORTER_OTLP_TRACES_TIMEOUT,
)
from opentelemetry.sdk.trace import _Span

OS_ENV_ENDPOINT = "os.env.base"
OS_ENV_CERTIFICATE = "os/env/base.crt"
OS_ENV_HEADERS = "envHeader1=val1,envHeader2=val2"
OS_ENV_TIMEOUT = "30"


# pylint: disable=protected-access
class TestOTLPSpanExporter(unittest.TestCase):
    def test_constructor_default(self):

        exporter = OTLPSpanExporter()

        self.assertEqual(
            exporter._endpoint, DEFAULT_ENDPOINT + DEFAULT_TRACES_EXPORT_PATH
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
            OTEL_EXPORTER_OTLP_CERTIFICATE: OS_ENV_CERTIFICATE,
            OTEL_EXPORTER_OTLP_COMPRESSION: Compression.Gzip.value,
            OTEL_EXPORTER_OTLP_ENDPOINT: OS_ENV_ENDPOINT,
            OTEL_EXPORTER_OTLP_HEADERS: OS_ENV_HEADERS,
            OTEL_EXPORTER_OTLP_TIMEOUT: OS_ENV_TIMEOUT,
            OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE: "traces/certificate.env",
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
            headers={"testHeader1": "value1", "testHeader2": "value2"},
            timeout=20,
            compression=Compression.NoCompression,
            session=requests.Session(),
        )

        self.assertEqual(exporter._endpoint, "example.com/1234")
        self.assertEqual(exporter._certificate_file, "path/to/service.crt")
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
            OTEL_EXPORTER_OTLP_COMPRESSION: Compression.Gzip.value,
            OTEL_EXPORTER_OTLP_HEADERS: OS_ENV_HEADERS,
            OTEL_EXPORTER_OTLP_TIMEOUT: OS_ENV_TIMEOUT,
        },
    )
    def test_exporter_env(self):

        exporter = OTLPSpanExporter()

        self.assertEqual(exporter._certificate_file, OS_ENV_CERTIFICATE)
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
                    "Protocol Exporter specification: missingValue"
                ),
            )

    # pylint: disable=no-self-use
    @responses.activate
    @patch("opentelemetry.exporter.otlp.proto.http.trace_exporter.backoff")
    @patch("opentelemetry.exporter.otlp.proto.http.trace_exporter.sleep")
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
            "http://traces.example.com/export",
            json={"error": "something exploded"},
            status=500,
        )

        exporter = OTLPSpanExporter(
            endpoint="http://traces.example.com/export"
        )
        span = _Span(
            "abc",
            context=Mock(
                **{
                    "trace_state": OrderedDict([("a", "b"), ("c", "d")]),
                    "span_id": 10217189687419569865,
                    "trace_id": 67545097771067222548457157018666467027,
                }
            ),
        )

        exporter.export([span])
        mock_sleep.assert_called_once_with(1)
