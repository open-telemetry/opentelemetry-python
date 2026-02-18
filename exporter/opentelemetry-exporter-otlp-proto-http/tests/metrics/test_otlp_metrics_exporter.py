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
import threading
import time
from logging import WARNING
from os import environ
from typing import List
from unittest import TestCase
from unittest.mock import ANY, MagicMock, Mock, call, patch

import requests
from requests import Session
from requests.exceptions import ConnectionError
from requests.models import Response

from opentelemetry.exporter.otlp.proto.common.metrics_encoder import (
    encode_metrics,
)
from opentelemetry.exporter.otlp.proto.http import Compression
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    DEFAULT_COMPRESSION,
    DEFAULT_ENDPOINT,
    DEFAULT_METRICS_EXPORT_PATH,
    DEFAULT_TIMEOUT,
    OTLPMetricExporter,
    _get_split_resource_metrics_pb2,
    _split_metrics_data,
)
from opentelemetry.exporter.otlp.proto.http.version import __version__
from opentelemetry.proto.common.v1.common_pb2 import (
    InstrumentationScope,
    KeyValue,
)
from opentelemetry.proto.metrics.v1 import metrics_pb2 as pb2
from opentelemetry.proto.resource.v1.resource_pb2 import (
    Resource as Pb2Resource,
)
from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_EXPORTER_OTLP_HTTP_METRICS_CREDENTIAL_PROVIDER,
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE,
    OTEL_EXPORTER_OTLP_METRICS_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_METRICS_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_METRICS_COMPRESSION,
    OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION,
    OTEL_EXPORTER_OTLP_METRICS_ENDPOINT,
    OTEL_EXPORTER_OTLP_METRICS_HEADERS,
    OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE,
    OTEL_EXPORTER_OTLP_METRICS_TIMEOUT,
    OTEL_EXPORTER_OTLP_TIMEOUT,
)
from opentelemetry.sdk.metrics import (
    Counter,
    Histogram,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    MetricExportResult,
    MetricsData,
    ResourceMetrics,
    ScopeMetrics,
)
from opentelemetry.sdk.metrics.view import (
    ExplicitBucketHistogramAggregation,
    ExponentialBucketHistogramAggregation,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import (
    InstrumentationScope as SDKInstrumentationScope,
)
from opentelemetry.test.metrictestutil import _generate_sum
from opentelemetry.test.mock_test_classes import IterEntryPoint

OS_ENV_ENDPOINT = "os.env.base"
OS_ENV_CERTIFICATE = "os/env/base.crt"
OS_ENV_CLIENT_CERTIFICATE = "os/env/client-cert.pem"
OS_ENV_CLIENT_KEY = "os/env/client-key.pem"
OS_ENV_HEADERS = "envHeader1=val1,envHeader2=val2,User-agent=Overridden"
OS_ENV_TIMEOUT = "30"


# pylint: disable=protected-access
class TestOTLPMetricExporter(TestCase):
    # pylint: disable=too-many-public-methods
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
        self.assertEqual(exporter._client_certificate_file, None)
        self.assertEqual(exporter._client_key_file, None)
        self.assertEqual(exporter._timeout, DEFAULT_TIMEOUT)
        self.assertIs(exporter._compression, DEFAULT_COMPRESSION)
        self.assertEqual(exporter._headers, {})
        self.assertIsInstance(exporter._session, Session)
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
            OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE: "metrics/certificate.env",
            OTEL_EXPORTER_OTLP_METRICS_CLIENT_CERTIFICATE: "metrics/client-cert.pem",
            OTEL_EXPORTER_OTLP_METRICS_CLIENT_KEY: "metrics/client-key.pem",
            OTEL_EXPORTER_OTLP_METRICS_COMPRESSION: Compression.Deflate.value,
            OTEL_EXPORTER_OTLP_METRICS_ENDPOINT: "https://metrics.endpoint.env",
            OTEL_EXPORTER_OTLP_METRICS_HEADERS: "metricsEnv1=val1,metricsEnv2=val2,metricEnv3===val3==,User-agent=metrics-user-agent",
            OTEL_EXPORTER_OTLP_METRICS_TIMEOUT: "40",
            _OTEL_PYTHON_EXPORTER_OTLP_HTTP_METRICS_CREDENTIAL_PROVIDER: "credential_provider",
        },
    )
    @patch("opentelemetry.exporter.otlp.proto.http._common.entry_points")
    def test_exporter_metrics_env_take_priority(self, mock_entry_points):
        credential = Session()

        def f():
            return credential

        mock_entry_points.configure_mock(
            return_value=[IterEntryPoint("custom_credential", f)]
        )
        exporter = OTLPMetricExporter()

        self.assertEqual(exporter._endpoint, "https://metrics.endpoint.env")
        self.assertEqual(exporter._certificate_file, "metrics/certificate.env")
        self.assertEqual(
            exporter._client_certificate_file, "metrics/client-cert.pem"
        )
        self.assertEqual(exporter._client_key_file, "metrics/client-key.pem")
        self.assertEqual(exporter._timeout, 40)
        self.assertIs(exporter._compression, Compression.Deflate)
        self.assertEqual(
            exporter._headers,
            {
                "metricsenv1": "val1",
                "metricsenv2": "val2",
                "metricenv3": "==val3==",
                "user-agent": "metrics-user-agent",
            },
        )
        self.assertIsInstance(exporter._session, Session)
        self.assertEqual(
            exporter._session.headers.get("User-Agent"),
            "metrics-user-agent",
        )
        self.assertEqual(
            exporter._session.headers.get("Content-Type"),
            "application/x-protobuf",
        )

    @patch.dict(
        "os.environ",
        {
            OTEL_EXPORTER_OTLP_CERTIFICATE: OS_ENV_CERTIFICATE,
            OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE: OS_ENV_CLIENT_CERTIFICATE,
            OTEL_EXPORTER_OTLP_CLIENT_KEY: OS_ENV_CLIENT_KEY,
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
            client_key_file="path/to/client-key.pem",
            client_certificate_file="path/to/client-cert.pem",
            headers={"testHeader1": "value1", "testHeader2": "value2"},
            timeout=20,
            compression=Compression.NoCompression,
            session=Session(),
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
        self.assertIsInstance(exporter._session, Session)

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
        exporter = OTLPMetricExporter()

        self.assertEqual(exporter._certificate_file, OS_ENV_CERTIFICATE)
        self.assertEqual(
            exporter._client_certificate_file, OS_ENV_CLIENT_CERTIFICATE
        )
        self.assertEqual(exporter._client_key_file, OS_ENV_CLIENT_KEY)
        self.assertEqual(exporter._timeout, int(OS_ENV_TIMEOUT))
        self.assertIs(exporter._compression, Compression.Gzip)
        self.assertEqual(
            exporter._headers,
            {
                "envheader1": "val1",
                "envheader2": "val2",
                "user-agent": "Overridden",
            },
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
                    "Protocol Exporter specification or a comma separated "
                    "list of name=value occurrences: missingValue"
                ),
            )

    @patch.object(Session, "post")
    def test_success(self, mock_post):
        resp = Response()
        resp.status_code = 200
        mock_post.return_value = resp

        exporter = OTLPMetricExporter()

        self.assertEqual(
            exporter.export(self.metrics["sum_int"]),
            MetricExportResult.SUCCESS,
        )

    @patch.object(Session, "post")
    def test_failure(self, mock_post):
        resp = Response()
        resp.status_code = 401
        mock_post.return_value = resp

        exporter = OTLPMetricExporter()

        self.assertEqual(
            exporter.export(self.metrics["sum_int"]),
            MetricExportResult.FAILURE,
        )

    @patch.object(Session, "post")
    def test_serialization(self, mock_post):
        resp = Response()
        resp.status_code = 200
        mock_post.return_value = resp

        exporter = OTLPMetricExporter()

        self.assertEqual(
            exporter.export(self.metrics["sum_int"]),
            MetricExportResult.SUCCESS,
        )

        serialized_data = encode_metrics(self.metrics["sum_int"])
        mock_post.assert_called_once_with(
            url=exporter._endpoint,
            data=serialized_data.SerializeToString(),
            verify=exporter._certificate_file,
            timeout=ANY,  # Timeout is a float based on real time, can't put an exact value here.
            cert=exporter._client_cert,
        )

    def test_split_metrics_data_many_data_points(self):
        metrics_data = pb2.MetricsData(
            resource_metrics=[
                _resource_metrics(
                    index=1,
                    scope_metrics=[
                        _scope_metrics(
                            index=1,
                            metrics=[
                                _gauge(
                                    index=1,
                                    data_points=[
                                        _number_data_point(11),
                                        _number_data_point(12),
                                        _number_data_point(13),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ]
        )
        split_metrics_data: List[MetricsData] = list(
            # pylint: disable=protected-access
            _split_metrics_data(
                metrics_data=metrics_data,
                max_export_batch_size=2,
            )
        )

        self.assertEqual(
            [
                pb2.MetricsData(
                    resource_metrics=[
                        _resource_metrics(
                            index=1,
                            scope_metrics=[
                                _scope_metrics(
                                    index=1,
                                    metrics=[
                                        _gauge(
                                            index=1,
                                            data_points=[
                                                _number_data_point(11),
                                                _number_data_point(12),
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ]
                ),
                pb2.MetricsData(
                    resource_metrics=[
                        _resource_metrics(
                            index=1,
                            scope_metrics=[
                                _scope_metrics(
                                    index=1,
                                    metrics=[
                                        _gauge(
                                            index=1,
                                            data_points=[
                                                _number_data_point(13),
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ]
                ),
            ],
            split_metrics_data,
        )

    def test_split_metrics_data_nb_data_points_equal_batch_size(self):
        metrics_data = pb2.MetricsData(
            resource_metrics=[
                _resource_metrics(
                    index=1,
                    scope_metrics=[
                        _scope_metrics(
                            index=1,
                            metrics=[
                                _gauge(
                                    index=1,
                                    data_points=[
                                        _number_data_point(11),
                                        _number_data_point(12),
                                        _number_data_point(13),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ]
        )

        split_metrics_data: List[MetricsData] = list(
            # pylint: disable=protected-access
            _split_metrics_data(
                metrics_data=metrics_data,
                max_export_batch_size=3,
            )
        )

        self.assertEqual(
            [
                pb2.MetricsData(
                    resource_metrics=[
                        _resource_metrics(
                            index=1,
                            scope_metrics=[
                                _scope_metrics(
                                    index=1,
                                    metrics=[
                                        _gauge(
                                            index=1,
                                            data_points=[
                                                _number_data_point(11),
                                                _number_data_point(12),
                                                _number_data_point(13),
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ]
                ),
            ],
            split_metrics_data,
        )

    def test_split_metrics_data_many_resources_scopes_metrics(self):
        # GIVEN
        metrics_data = pb2.MetricsData(
            resource_metrics=[
                _resource_metrics(
                    index=1,
                    scope_metrics=[
                        _scope_metrics(
                            index=1,
                            metrics=[
                                _gauge(
                                    index=1,
                                    data_points=[
                                        _number_data_point(11),
                                    ],
                                ),
                                _gauge(
                                    index=2,
                                    data_points=[
                                        _number_data_point(12),
                                    ],
                                ),
                            ],
                        ),
                        _scope_metrics(
                            index=2,
                            metrics=[
                                _gauge(
                                    index=3,
                                    data_points=[
                                        _number_data_point(13),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
                _resource_metrics(
                    index=2,
                    scope_metrics=[
                        _scope_metrics(
                            index=3,
                            metrics=[
                                _gauge(
                                    index=4,
                                    data_points=[
                                        _number_data_point(14),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ]
        )

        split_metrics_data: List[MetricsData] = list(
            # pylint: disable=protected-access
            _split_metrics_data(
                metrics_data=metrics_data,
                max_export_batch_size=2,
            )
        )

        self.assertEqual(
            [
                pb2.MetricsData(
                    resource_metrics=[
                        _resource_metrics(
                            index=1,
                            scope_metrics=[
                                _scope_metrics(
                                    index=1,
                                    metrics=[
                                        _gauge(
                                            index=1,
                                            data_points=[
                                                _number_data_point(11),
                                            ],
                                        ),
                                        _gauge(
                                            index=2,
                                            data_points=[
                                                _number_data_point(12),
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ]
                ),
                pb2.MetricsData(
                    resource_metrics=[
                        _resource_metrics(
                            index=1,
                            scope_metrics=[
                                _scope_metrics(
                                    index=2,
                                    metrics=[
                                        _gauge(
                                            index=3,
                                            data_points=[
                                                _number_data_point(13),
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        _resource_metrics(
                            index=2,
                            scope_metrics=[
                                _scope_metrics(
                                    index=3,
                                    metrics=[
                                        _gauge(
                                            index=4,
                                            data_points=[
                                                _number_data_point(14),
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ]
                ),
            ],
            split_metrics_data,
        )

    def test_get_split_resource_metrics_pb2_one_of_each(self):
        split_resource_metrics = [
            {
                "resource": Pb2Resource(
                    attributes=[
                        KeyValue(key="foo", value={"string_value": "bar"})
                    ],
                ),
                "schema_url": "http://foo-bar",
                "scope_metrics": [
                    {
                        "scope": InstrumentationScope(
                            name="foo-scope", version="1.0.0"
                        ),
                        "schema_url": "http://foo-baz",
                        "metrics": [
                            {
                                "name": "foo-metric",
                                "description": "foo-description",
                                "unit": "foo-unit",
                                "sum": {
                                    "aggregation_temporality": 1,
                                    "is_monotonic": True,
                                    "data_points": [
                                        pb2.NumberDataPoint(
                                            attributes=[
                                                KeyValue(
                                                    key="dp_key",
                                                    value={
                                                        "string_value": "dp_value"
                                                    },
                                                )
                                            ],
                                            start_time_unix_nano=12345,
                                            time_unix_nano=12350,
                                            as_double=42.42,
                                        )
                                    ],
                                },
                            }
                        ],
                    }
                ],
            }
        ]

        result = _get_split_resource_metrics_pb2(split_resource_metrics)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], pb2.ResourceMetrics)
        self.assertEqual(result[0].schema_url, "http://foo-bar")
        self.assertEqual(len(result[0].scope_metrics), 1)
        self.assertEqual(result[0].scope_metrics[0].scope.name, "foo-scope")
        self.assertEqual(len(result[0].scope_metrics[0].metrics), 1)
        self.assertEqual(
            result[0].scope_metrics[0].metrics[0].name, "foo-metric"
        )
        self.assertEqual(
            result[0].scope_metrics[0].metrics[0].sum.is_monotonic, True
        )

    def test_get_split_resource_metrics_pb2_multiples(self):
        split_resource_metrics = [
            {
                "resource": Pb2Resource(
                    attributes=[
                        KeyValue(key="foo1", value={"string_value": "bar2"})
                    ],
                ),
                "schema_url": "http://foo-bar-1",
                "scope_metrics": [
                    {
                        "scope": InstrumentationScope(
                            name="foo-scope-1", version="1.0.0"
                        ),
                        "schema_url": "http://foo-baz-1",
                        "metrics": [
                            {
                                "name": "foo-metric-1",
                                "description": "foo-description-1",
                                "unit": "foo-unit-1",
                                "gauge": {
                                    "data_points": [
                                        pb2.NumberDataPoint(
                                            attributes=[
                                                KeyValue(
                                                    key="dp_key",
                                                    value={
                                                        "string_value": "dp_value"
                                                    },
                                                )
                                            ],
                                            start_time_unix_nano=12345,
                                            time_unix_nano=12350,
                                            as_double=42.42,
                                        )
                                    ],
                                },
                            }
                        ],
                    }
                ],
            },
            {
                "resource": Pb2Resource(
                    attributes=[
                        KeyValue(key="foo2", value={"string_value": "bar2"})
                    ],
                ),
                "schema_url": "http://foo-bar-2",
                "scope_metrics": [
                    {
                        "scope": InstrumentationScope(
                            name="foo-scope-2", version="2.0.0"
                        ),
                        "schema_url": "http://foo-baz-2",
                        "metrics": [
                            {
                                "name": "foo-metric-2",
                                "description": "foo-description-2",
                                "unit": "foo-unit-2",
                                "histogram": {
                                    "aggregation_temporality": 2,
                                    "data_points": [
                                        pb2.HistogramDataPoint(
                                            attributes=[
                                                KeyValue(
                                                    key="dp_key",
                                                    value={
                                                        "string_value": "dp_value"
                                                    },
                                                )
                                            ],
                                            start_time_unix_nano=12345,
                                            time_unix_nano=12350,
                                        )
                                    ],
                                },
                            }
                        ],
                    }
                ],
            },
        ]

        result = _get_split_resource_metrics_pb2(split_resource_metrics)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].schema_url, "http://foo-bar-1")
        self.assertEqual(result[1].schema_url, "http://foo-bar-2")
        self.assertEqual(len(result[0].scope_metrics), 1)
        self.assertEqual(len(result[1].scope_metrics), 1)
        self.assertEqual(result[0].scope_metrics[0].scope.name, "foo-scope-1")
        self.assertEqual(result[1].scope_metrics[0].scope.name, "foo-scope-2")
        self.assertEqual(
            result[0].scope_metrics[0].metrics[0].name, "foo-metric-1"
        )
        self.assertEqual(
            result[1].scope_metrics[0].metrics[0].name, "foo-metric-2"
        )

    def test_get_split_resource_metrics_pb2_unsupported_metric_type(self):
        split_resource_metrics = [
            {
                "resource": Pb2Resource(
                    attributes=[
                        KeyValue(key="foo", value={"string_value": "bar"})
                    ],
                ),
                "schema_url": "http://foo-bar",
                "scope_metrics": [
                    {
                        "scope": InstrumentationScope(
                            name="foo", version="1.0.0"
                        ),
                        "schema_url": "http://foo-baz",
                        "metrics": [
                            {
                                "name": "unsupported-metric",
                                "description": "foo-bar",
                                "unit": "foo-bar",
                                "unsupported_metric_type": {},
                            }
                        ],
                    }
                ],
            }
        ]

        with self.assertLogs(level="WARNING") as log:
            result = _get_split_resource_metrics_pb2(split_resource_metrics)
        self.assertEqual(len(result), 1)
        self.assertIn(
            "Tried to split and export an unsupported metric type",
            log.output[0],
        )

    @patch.object(OTLPMetricExporter, "_export")
    @patch("opentelemetry.exporter.otlp.proto.http.metric_exporter.random")
    @patch("opentelemetry.exporter.otlp.proto.http.metric_exporter.time")
    @patch(
        "opentelemetry.exporter.otlp.proto.http.metric_exporter.encode_metrics"
    )
    def test_export_retries_with_batching_success(
        self,
        mock_encode_metrics,
        mock_time,
        mock_random,
        mock_export,
    ):
        mock_time.return_value = 0
        mock_random.uniform.return_value = 1
        mock_export.side_effect = [
            # Success
            MagicMock(ok=True),
            MagicMock(ok=True),
        ]
        mock_encode_metrics.return_value = pb2.MetricsData(
            resource_metrics=[
                _resource_metrics(
                    index=1,
                    scope_metrics=[
                        _scope_metrics(
                            index=1,
                            metrics=[
                                _gauge(
                                    index=1,
                                    data_points=[
                                        _number_data_point(11),
                                        _number_data_point(12),
                                        _number_data_point(13),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ]
        )
        batch_1 = pb2.MetricsData(
            resource_metrics=[
                _resource_metrics(
                    index=1,
                    scope_metrics=[
                        _scope_metrics(
                            index=1,
                            metrics=[
                                _gauge(
                                    index=1,
                                    data_points=[
                                        _number_data_point(11),
                                        _number_data_point(12),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ]
        )
        batch_2 = pb2.MetricsData(
            resource_metrics=[
                _resource_metrics(
                    index=1,
                    scope_metrics=[
                        _scope_metrics(
                            index=1,
                            metrics=[
                                _gauge(
                                    index=1,
                                    data_points=[
                                        _number_data_point(13),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ]
        )

        exporter = OTLPMetricExporter(max_export_batch_size=2)
        result = exporter.export("foo")
        self.assertEqual(result, MetricExportResult.SUCCESS)
        self.assertEqual(mock_export.call_count, 2)
        mock_export.assert_has_calls(
            [
                call(batch_1.SerializeToString(), 10),
                call(batch_2.SerializeToString(), 10),
            ]
        )

    @patch.object(OTLPMetricExporter, "_export")
    @patch("opentelemetry.exporter.otlp.proto.http.metric_exporter.random")
    @patch("opentelemetry.exporter.otlp.proto.http.metric_exporter.time")
    @patch(
        "opentelemetry.exporter.otlp.proto.http.metric_exporter.encode_metrics"
    )
    def test_export_retries_with_batching_failure_first(
        self,
        mock_encode_metrics,
        mock_time,
        mock_random,
        mock_export,
    ):
        mock_time.return_value = 0
        mock_random.uniform.return_value = 1
        mock_export.side_effect = [
            # Non-retryable
            MagicMock(ok=False, status_code=400, reason="bad request"),
            MagicMock(ok=True),
            MagicMock(ok=True),
        ]
        mock_encode_metrics.return_value = pb2.MetricsData(
            resource_metrics=[
                _resource_metrics(
                    index=1,
                    scope_metrics=[
                        _scope_metrics(
                            index=1,
                            metrics=[
                                _gauge(
                                    index=1,
                                    data_points=[
                                        _number_data_point(11),
                                        _number_data_point(12),
                                        _number_data_point(13),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ]
        )
        batch_1 = pb2.MetricsData(
            resource_metrics=[
                _resource_metrics(
                    index=1,
                    scope_metrics=[
                        _scope_metrics(
                            index=1,
                            metrics=[
                                _gauge(
                                    index=1,
                                    data_points=[
                                        _number_data_point(11),
                                        _number_data_point(12),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ]
        )

        exporter = OTLPMetricExporter(max_export_batch_size=2)
        result = exporter.export("foo")
        self.assertEqual(result, MetricExportResult.SUCCESS)
        self.assertEqual(mock_export.call_count, 2)
        mock_export.assert_has_calls(
            [
                call(batch_1.SerializeToString(), 10),
            ]
        )

    @patch.object(OTLPMetricExporter, "_export")
    @patch("opentelemetry.exporter.otlp.proto.http.metric_exporter.random")
    @patch("opentelemetry.exporter.otlp.proto.http.metric_exporter.time")
    @patch(
        "opentelemetry.exporter.otlp.proto.http.metric_exporter.encode_metrics"
    )
    def test_export_retries_with_batching_failure_last(
        self,
        mock_encode_metrics,
        mock_time,
        mock_random,
        mock_export,
    ):
        mock_time.return_value = 0
        mock_random.uniform.return_value = 1
        mock_export.side_effect = [
            # Success
            MagicMock(ok=True),
            # Non-retryable
            MagicMock(ok=False, status_code=400, reason="bad request"),
        ]
        mock_encode_metrics.return_value = pb2.MetricsData(
            resource_metrics=[
                _resource_metrics(
                    index=1,
                    scope_metrics=[
                        _scope_metrics(
                            index=1,
                            metrics=[
                                _gauge(
                                    index=1,
                                    data_points=[
                                        _number_data_point(11),
                                        _number_data_point(12),
                                        _number_data_point(13),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ]
        )
        batch_1 = pb2.MetricsData(
            resource_metrics=[
                _resource_metrics(
                    index=1,
                    scope_metrics=[
                        _scope_metrics(
                            index=1,
                            metrics=[
                                _gauge(
                                    index=1,
                                    data_points=[
                                        _number_data_point(11),
                                        _number_data_point(12),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ]
        )
        batch_2 = pb2.MetricsData(
            resource_metrics=[
                _resource_metrics(
                    index=1,
                    scope_metrics=[
                        _scope_metrics(
                            index=1,
                            metrics=[
                                _gauge(
                                    index=1,
                                    data_points=[
                                        _number_data_point(13),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ]
        )

        exporter = OTLPMetricExporter(max_export_batch_size=2)
        result = exporter.export("foo")
        self.assertEqual(result, MetricExportResult.FAILURE)
        self.assertEqual(mock_export.call_count, 2)
        mock_export.assert_has_calls(
            [
                call(batch_1.SerializeToString(), 10),
                call(batch_2.SerializeToString(), 10),
            ]
        )

    @patch.object(OTLPMetricExporter, "_export")
    @patch("opentelemetry.exporter.otlp.proto.http.metric_exporter.random")
    @patch("opentelemetry.exporter.otlp.proto.http.metric_exporter.time")
    @patch(
        "opentelemetry.exporter.otlp.proto.http.metric_exporter.encode_metrics"
    )
    def test_export_retries_with_batching_failure_retryable(
        self,
        mock_encode_metrics,
        mock_time,
        mock_random,
        mock_export,
    ):
        mock_time.return_value = 0
        mock_random.uniform.return_value = 1
        mock_export.side_effect = [
            # Success
            MagicMock(ok=True),
            # Retryable
            MagicMock(
                ok=False, status_code=500, reason="internal server error"
            ),
            # Then success
            MagicMock(ok=True),
        ]
        mock_encode_metrics.return_value = pb2.MetricsData(
            resource_metrics=[
                _resource_metrics(
                    index=1,
                    scope_metrics=[
                        _scope_metrics(
                            index=1,
                            metrics=[
                                _gauge(
                                    index=1,
                                    data_points=[
                                        _number_data_point(11),
                                        _number_data_point(12),
                                        _number_data_point(13),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ]
        )
        batch_1 = pb2.MetricsData(
            resource_metrics=[
                _resource_metrics(
                    index=1,
                    scope_metrics=[
                        _scope_metrics(
                            index=1,
                            metrics=[
                                _gauge(
                                    index=1,
                                    data_points=[
                                        _number_data_point(11),
                                        _number_data_point(12),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ]
        )
        batch_2 = pb2.MetricsData(
            resource_metrics=[
                _resource_metrics(
                    index=1,
                    scope_metrics=[
                        _scope_metrics(
                            index=1,
                            metrics=[
                                _gauge(
                                    index=1,
                                    data_points=[
                                        _number_data_point(13),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ]
        )

        exporter = OTLPMetricExporter(max_export_batch_size=2)
        result = exporter.export("foo")
        self.assertEqual(result, MetricExportResult.SUCCESS)
        self.assertEqual(mock_export.call_count, 3)
        mock_export.assert_has_calls(
            [
                call(batch_1.SerializeToString(), 10),
                call(batch_2.SerializeToString(), 10),
                call(batch_2.SerializeToString(), 10),
            ]
        )

    def test_aggregation_temporality(self):
        otlp_metric_exporter = OTLPMetricExporter()

        for (
            temporality
        ) in otlp_metric_exporter._preferred_temporality.values():
            self.assertEqual(temporality, AggregationTemporality.CUMULATIVE)

        with patch.dict(
            environ,
            {OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE: "CUMULATIVE"},
        ):
            otlp_metric_exporter = OTLPMetricExporter()

            for (
                temporality
            ) in otlp_metric_exporter._preferred_temporality.values():
                self.assertEqual(
                    temporality, AggregationTemporality.CUMULATIVE
                )

        with patch.dict(
            environ, {OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE: "ABC"}
        ):
            with self.assertLogs(level=WARNING):
                otlp_metric_exporter = OTLPMetricExporter()

            for (
                temporality
            ) in otlp_metric_exporter._preferred_temporality.values():
                self.assertEqual(
                    temporality, AggregationTemporality.CUMULATIVE
                )

        with patch.dict(
            environ,
            {OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE: "DELTA"},
        ):
            otlp_metric_exporter = OTLPMetricExporter()

            self.assertEqual(
                otlp_metric_exporter._preferred_temporality[Counter],
                AggregationTemporality.DELTA,
            )
            self.assertEqual(
                otlp_metric_exporter._preferred_temporality[UpDownCounter],
                AggregationTemporality.CUMULATIVE,
            )
            self.assertEqual(
                otlp_metric_exporter._preferred_temporality[Histogram],
                AggregationTemporality.DELTA,
            )
            self.assertEqual(
                otlp_metric_exporter._preferred_temporality[ObservableCounter],
                AggregationTemporality.DELTA,
            )
            self.assertEqual(
                otlp_metric_exporter._preferred_temporality[
                    ObservableUpDownCounter
                ],
                AggregationTemporality.CUMULATIVE,
            )
            self.assertEqual(
                otlp_metric_exporter._preferred_temporality[ObservableGauge],
                AggregationTemporality.CUMULATIVE,
            )

        with patch.dict(
            environ,
            {OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE: "LOWMEMORY"},
        ):
            otlp_metric_exporter = OTLPMetricExporter()

            self.assertEqual(
                otlp_metric_exporter._preferred_temporality[Counter],
                AggregationTemporality.DELTA,
            )
            self.assertEqual(
                otlp_metric_exporter._preferred_temporality[UpDownCounter],
                AggregationTemporality.CUMULATIVE,
            )
            self.assertEqual(
                otlp_metric_exporter._preferred_temporality[Histogram],
                AggregationTemporality.DELTA,
            )
            self.assertEqual(
                otlp_metric_exporter._preferred_temporality[ObservableCounter],
                AggregationTemporality.CUMULATIVE,
            )
            self.assertEqual(
                otlp_metric_exporter._preferred_temporality[
                    ObservableUpDownCounter
                ],
                AggregationTemporality.CUMULATIVE,
            )
            self.assertEqual(
                otlp_metric_exporter._preferred_temporality[ObservableGauge],
                AggregationTemporality.CUMULATIVE,
            )

    def test_exponential_explicit_bucket_histogram(self):
        self.assertIsInstance(
            OTLPMetricExporter()._preferred_aggregation[Histogram],
            ExplicitBucketHistogramAggregation,
        )

        with patch.dict(
            environ,
            {
                OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION: "base2_exponential_bucket_histogram"
            },
        ):
            self.assertIsInstance(
                OTLPMetricExporter()._preferred_aggregation[Histogram],
                ExponentialBucketHistogramAggregation,
            )

        with patch.dict(
            environ,
            {OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION: "abc"},
        ):
            with self.assertLogs(level=WARNING) as log:
                self.assertIsInstance(
                    OTLPMetricExporter()._preferred_aggregation[Histogram],
                    ExplicitBucketHistogramAggregation,
                )
            self.assertIn(
                (
                    "Invalid value for OTEL_EXPORTER_OTLP_METRICS_DEFAULT_"
                    "HISTOGRAM_AGGREGATION: abc, using explicit bucket "
                    "histogram aggregation"
                ),
                log.output[0],
            )

        with patch.dict(
            environ,
            {
                OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION: "explicit_bucket_histogram"
            },
        ):
            self.assertIsInstance(
                OTLPMetricExporter()._preferred_aggregation[Histogram],
                ExplicitBucketHistogramAggregation,
            )

    @patch.object(OTLPMetricExporter, "_export", return_value=Mock(ok=True))
    def test_2xx_status_code(self, mock_otlp_metric_exporter):
        """
        Test that any HTTP 2XX code returns a successful result
        """

        self.assertEqual(
            OTLPMetricExporter().export(MagicMock()),
            MetricExportResult.SUCCESS,
        )

    def test_preferred_aggregation_override(self):
        histogram_aggregation = ExplicitBucketHistogramAggregation(
            boundaries=[0.05, 0.1, 0.5, 1, 5, 10],
        )

        exporter = OTLPMetricExporter(
            preferred_aggregation={
                Histogram: histogram_aggregation,
            },
        )

        self.assertEqual(
            exporter._preferred_aggregation[Histogram], histogram_aggregation
        )

    @patch.object(Session, "post")
    def test_retry_timeout(self, mock_post):
        exporter = OTLPMetricExporter(timeout=1.5)

        resp = Response()
        resp.status_code = 503
        resp.reason = "UNAVAILABLE"
        mock_post.return_value = resp
        with self.assertLogs(level=WARNING) as warning:
            before = time.time()
            self.assertEqual(
                exporter.export(self.metrics["sum_int"]),
                MetricExportResult.FAILURE,
            )
            after = time.time()

            # First call at time 0, second at time 1, then an early return before the second backoff sleep b/c it would exceed timeout.
            self.assertEqual(mock_post.call_count, 2)
            # There's a +/-20% jitter on each backoff.
            self.assertTrue(0.75 < after - before < 1.25)
            self.assertIn(
                "Transient error UNAVAILABLE encountered while exporting metrics batch, retrying in",
                warning.records[0].message,
            )

    @patch.object(Session, "post")
    def test_export_no_collector_available_retryable(self, mock_post):
        exporter = OTLPMetricExporter(timeout=1.5)
        msg = "Server not available."
        mock_post.side_effect = ConnectionError(msg)
        with self.assertLogs(level=WARNING) as warning:
            self.assertEqual(
                exporter.export(self.metrics["sum_int"]),
                MetricExportResult.FAILURE,
            )
            # Check for greater 2 because the request is on each retry
            # done twice at the moment.
            self.assertGreater(mock_post.call_count, 2)
            self.assertIn(
                f"Transient error {msg} encountered while exporting metrics batch, retrying in",
                warning.records[0].message,
            )

    @patch.object(Session, "post")
    def test_export_no_collector_available(self, mock_post):
        exporter = OTLPMetricExporter(timeout=1.5)

        mock_post.side_effect = requests.exceptions.RequestException()
        with self.assertLogs(level=WARNING) as warning:
            self.assertEqual(
                exporter.export(self.metrics["sum_int"]),
                MetricExportResult.FAILURE,
            )
            self.assertEqual(mock_post.call_count, 1)
            self.assertIn(
                "Failed to export metrics batch code",
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
        exporter = OTLPMetricExporter(timeout=0.4)
        exporter.export(self.metrics["sum_int"])

    @patch.object(Session, "post")
    def test_shutdown_interrupts_retry_backoff(self, mock_post):
        exporter = OTLPMetricExporter(timeout=1.5)

        resp = Response()
        resp.status_code = 503
        resp.reason = "UNAVAILABLE"
        mock_post.return_value = resp
        thread = threading.Thread(
            target=exporter.export, args=(self.metrics["sum_int"],)
        )
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
                "Transient error UNAVAILABLE encountered while exporting metrics batch, retrying in",
                warning.records[0].message,
            )
            self.assertIn(
                "Shutdown in progress, aborting retry.",
                warning.records[1].message,
            )

            assert after - before < 0.2


def _resource_metrics(
    index: int, scope_metrics: List[pb2.ScopeMetrics]
) -> pb2.ResourceMetrics:
    return pb2.ResourceMetrics(
        resource={
            "attributes": [KeyValue(key="a", value={"int_value": index})],
        },
        schema_url=f"resource_url_{index}",
        scope_metrics=scope_metrics,
    )


def _scope_metrics(index: int, metrics: List[pb2.Metric]) -> pb2.ScopeMetrics:
    return pb2.ScopeMetrics(
        scope=InstrumentationScope(name=f"scope_{index}"),
        schema_url=f"scope_url_{index}",
        metrics=metrics,
    )


def _gauge(index: int, data_points: List[pb2.NumberDataPoint]) -> pb2.Metric:
    return pb2.Metric(
        name=f"gauge_{index}",
        description="description",
        unit="unit",
        gauge=pb2.Gauge(data_points=data_points),
    )


def _number_data_point(value: int) -> pb2.NumberDataPoint:
    return pb2.NumberDataPoint(
        attributes=[
            KeyValue(key="a", value={"int_value": 1}),
            KeyValue(key="b", value={"bool_value": True}),
        ],
        start_time_unix_nano=1641946015139533244,
        time_unix_nano=1641946016139533244,
        as_int=value,
    )
