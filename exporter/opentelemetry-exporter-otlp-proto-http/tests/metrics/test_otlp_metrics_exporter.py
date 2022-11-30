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
from unittest.mock import patch

import requests
import responses

from opentelemetry.exporter.otlp.proto.http import Compression
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    DEFAULT_COMPRESSION,
    DEFAULT_ENDPOINT,
    DEFAULT_METRICS_EXPORT_PATH,
    DEFAULT_TIMEOUT,
    OTLPMetricExporter,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE,
    OTEL_EXPORTER_OTLP_METRICS_COMPRESSION,
    OTEL_EXPORTER_OTLP_METRICS_ENDPOINT,
    OTEL_EXPORTER_OTLP_METRICS_HEADERS,
    OTEL_EXPORTER_OTLP_METRICS_TIMEOUT,
    OTEL_EXPORTER_OTLP_TIMEOUT,
)
from opentelemetry.sdk.metrics.export import (
    MetricExportResult,
    MetricsData,
    ResourceMetrics,
    ScopeMetrics,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import (
    InstrumentationScope as SDKInstrumentationScope,
)
from opentelemetry.test.metrictestutil import _generate_sum

OS_ENV_ENDPOINT = "os.env.base"
OS_ENV_CERTIFICATE = "os/env/base.crt"
OS_ENV_HEADERS = "envHeader1=val1,envHeader2=val2"
OS_ENV_TIMEOUT = "30"


# pylint: disable=protected-access
class TestOTLPMetricExporter(unittest.TestCase):
    def setUp(self):

        self.metrics = {
            "sum_int": MetricsData(
                resource_metrics=[
                    ResourceMetrics(
                        resource=Resource(
                            attributes={"a": 1, "b": False},
                            schema_url="resource_schema_url",
                        ),
                        scope_metrics=[
                            ScopeMetrics(
                                scope=SDKInstrumentationScope(
                                    name="first_name",
                                    version="first_version",
                                    schema_url="insrumentation_scope_schema_url",
                                ),
                                metrics=[_generate_sum("sum_int", 33)],
                                schema_url="instrumentation_scope_schema_url",
                            )
                        ],
                        schema_url="resource_schema_url",
                    )
                ]
            ),
        }

    def test_constructor_default(self):

        exporter = OTLPMetricExporter()

        self.assertEqual(
            exporter._endpoint, DEFAULT_ENDPOINT + DEFAULT_METRICS_EXPORT_PATH
        )
        self.assertEqual(exporter._certificate_file, True)
        self.assertEqual(exporter._timeout, DEFAULT_TIMEOUT)
        self.assertIs(exporter._compression, DEFAULT_COMPRESSION)
        self.assertEqual(exporter._headers, {})
        self.assertIsInstance(exporter._session, requests.Session)

    @patch.dict(
        "os.environ",
        {
            OTEL_EXPORTER_OTLP_CERTIFICATE: OS_ENV_CERTIFICATE,
            OTEL_EXPORTER_OTLP_COMPRESSION: Compression.Gzip.value,
            OTEL_EXPORTER_OTLP_ENDPOINT: OS_ENV_ENDPOINT,
            OTEL_EXPORTER_OTLP_HEADERS: OS_ENV_HEADERS,
            OTEL_EXPORTER_OTLP_TIMEOUT: OS_ENV_TIMEOUT,
            OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE: "metrics/certificate.env",
            OTEL_EXPORTER_OTLP_METRICS_COMPRESSION: Compression.Deflate.value,
            OTEL_EXPORTER_OTLP_METRICS_ENDPOINT: "https://metrics.endpoint.env",
            OTEL_EXPORTER_OTLP_METRICS_HEADERS: "metricsEnv1=val1,metricsEnv2=val2,metricEnv3===val3==",
            OTEL_EXPORTER_OTLP_METRICS_TIMEOUT: "40",
        },
    )
    def test_exporter_metrics_env_take_priority(self):
        exporter = OTLPMetricExporter()

        self.assertEqual(exporter._endpoint, "https://metrics.endpoint.env")
        self.assertEqual(exporter._certificate_file, "metrics/certificate.env")
        self.assertEqual(exporter._timeout, 40)
        self.assertIs(exporter._compression, Compression.Deflate)
        self.assertEqual(
            exporter._headers,
            {
                "metricsenv1": "val1",
                "metricsenv2": "val2",
                "metricenv3": "==val3==",
            },
        )
        self.assertIsInstance(exporter._session, requests.Session)

    @patch.dict(
        "os.environ",
        {
            OTEL_EXPORTER_OTLP_CERTIFICATE: OS_ENV_CERTIFICATE,
            OTEL_EXPORTER_OTLP_COMPRESSION: Compression.Gzip.value,
            OTEL_EXPORTER_OTLP_ENDPOINT: OS_ENV_ENDPOINT,
            OTEL_EXPORTER_OTLP_METRICS_ENDPOINT: "https://metrics.endpoint.env",
            OTEL_EXPORTER_OTLP_HEADERS: OS_ENV_HEADERS,
            OTEL_EXPORTER_OTLP_TIMEOUT: OS_ENV_TIMEOUT,
        },
    )
    def test_exporter_constructor_take_priority(self):
        exporter = OTLPMetricExporter(
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

        exporter = OTLPMetricExporter()

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

        exporter = OTLPMetricExporter()

        self.assertEqual(
            exporter._endpoint,
            OS_ENV_ENDPOINT + f"/{DEFAULT_METRICS_EXPORT_PATH}",
        )

    @patch.dict(
        "os.environ",
        {OTEL_EXPORTER_OTLP_ENDPOINT: OS_ENV_ENDPOINT + "/"},
    )
    def test_exporter_env_endpoint_with_slash(self):

        exporter = OTLPMetricExporter()

        self.assertEqual(
            exporter._endpoint,
            OS_ENV_ENDPOINT + f"/{DEFAULT_METRICS_EXPORT_PATH}",
        )

    @patch.dict(
        "os.environ",
        {
            OTEL_EXPORTER_OTLP_HEADERS: "envHeader1=val1,envHeader2=val2,missingValue"
        },
    )
    def test_headers_parse_from_env(self):

        with self.assertLogs(level="WARNING") as cm:
            _ = OTLPMetricExporter()

            self.assertEqual(
                cm.records[0].message,
                (
                    "Header format invalid! Header values in environment "
                    "variables must be URL encoded per the OpenTelemetry "
                    "Protocol Exporter specification: missingValue"
                ),
            )

    @patch.object(requests.Session, "post")
    def test_success(self, mock_post):
        resp = requests.models.Response()
        resp.status_code = 200
        mock_post.return_value = resp

        exporter = OTLPMetricExporter()

        self.assertEqual(
            exporter.export(self.metrics["sum_int"]),
            MetricExportResult.SUCCESS,
        )

    @patch.object(requests.Session, "post")
    def test_failure(self, mock_post):
        resp = requests.models.Response()
        resp.status_code = 401
        mock_post.return_value = resp

        exporter = OTLPMetricExporter()

        self.assertEqual(
            exporter.export(self.metrics["sum_int"]),
            MetricExportResult.FAILURE,
        )

    @patch.object(requests.Session, "post")
    def test_serialization(self, mock_post):

        resp = requests.models.Response()
        resp.status_code = 200
        mock_post.return_value = resp

        exporter = OTLPMetricExporter()

        self.assertEqual(
            exporter.export(self.metrics["sum_int"]),
            MetricExportResult.SUCCESS,
        )

        serialized_data = exporter._translate_data(self.metrics["sum_int"])
        mock_post.assert_called_once_with(
            url=exporter._endpoint,
            data=serialized_data.SerializeToString(),
            verify=exporter._certificate_file,
            timeout=exporter._timeout,
        )

    @responses.activate
    @patch("opentelemetry.exporter.otlp.proto.http.metric_exporter.backoff")
    @patch("opentelemetry.exporter.otlp.proto.http.metric_exporter.sleep")
    def test_handles_backoff_v2_api(self, mock_sleep, mock_backoff):
        # In backoff ~= 2.0.0 the first value yielded from expo is None.
        def generate_delays(*args, **kwargs):
            yield None
            yield 1

        mock_backoff.expo.configure_mock(**{"side_effect": generate_delays})

        # return a retryable error
        responses.add(
            responses.POST,
            "http://metrics.example.com/export",
            json={"error": "something exploded"},
            status=500,
        )

        exporter = OTLPMetricExporter(
            endpoint="http://metrics.example.com/export"
        )
        metrics_data = self.metrics["sum_int"]

        exporter.export(metrics_data)
        mock_sleep.assert_called_once_with(1)
