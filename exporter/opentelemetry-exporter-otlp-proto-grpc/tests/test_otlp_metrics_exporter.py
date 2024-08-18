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
from concurrent.futures import ThreadPoolExecutor

# pylint: disable=too-many-lines
from logging import WARNING
from os import environ
from os.path import dirname
from time import time_ns
from typing import List
from unittest import TestCase
from unittest.mock import patch

from google.protobuf.duration_pb2 import (  # pylint: disable=no-name-in-module
    Duration,
)
from google.rpc.error_details_pb2 import RetryInfo
from grpc import ChannelCredentials, Compression, StatusCode, server

from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.exporter.otlp.proto.grpc.version import __version__
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceResponse,
)
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2_grpc import (
    MetricsServiceServicer,
    add_MetricsServiceServicer_to_server,
)
from opentelemetry.proto.common.v1.common_pb2 import InstrumentationScope
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE,
    OTEL_EXPORTER_OTLP_METRICS_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_METRICS_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_METRICS_COMPRESSION,
    OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION,
    OTEL_EXPORTER_OTLP_METRICS_ENDPOINT,
    OTEL_EXPORTER_OTLP_METRICS_HEADERS,
    OTEL_EXPORTER_OTLP_METRICS_INSECURE,
    OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE,
    OTEL_EXPORTER_OTLP_METRICS_TIMEOUT,
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
    Gauge,
    Metric,
    MetricExportResult,
    MetricsData,
    NumberDataPoint,
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

THIS_DIR = dirname(__file__)


class MetricsServiceServicerUNAVAILABLEDelay(MetricsServiceServicer):
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

        return ExportMetricsServiceResponse()


class MetricsServiceServicerUNAVAILABLE(MetricsServiceServicer):
    # pylint: disable=invalid-name,unused-argument,no-self-use
    def Export(self, request, context):
        context.set_code(StatusCode.UNAVAILABLE)

        return ExportMetricsServiceResponse()


class MetricsServiceServicerUNKNOWN(MetricsServiceServicer):
    # pylint: disable=invalid-name,unused-argument,no-self-use
    def Export(self, request, context):
        context.set_code(StatusCode.UNKNOWN)

        return ExportMetricsServiceResponse()


class MetricsServiceServicerSUCCESS(MetricsServiceServicer):
    # pylint: disable=invalid-name,unused-argument,no-self-use
    def Export(self, request, context):
        context.set_code(StatusCode.OK)

        return ExportMetricsServiceResponse()


class MetricsServiceServicerALREADY_EXISTS(MetricsServiceServicer):
    # pylint: disable=invalid-name,unused-argument,no-self-use
    def Export(self, request, context):
        context.set_code(StatusCode.ALREADY_EXISTS)

        return ExportMetricsServiceResponse()


class TestOTLPMetricExporter(TestCase):
    # pylint: disable=too-many-public-methods

    def setUp(self):

        self.exporter = OTLPMetricExporter()

        self.server = server(ThreadPoolExecutor(max_workers=10))

        self.server.add_insecure_port("127.0.0.1:4317")

        self.server.start()

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
            )
        }

    def tearDown(self):
        self.server.stop(None)

    def test_exporting(self):
        # pylint: disable=protected-access
        self.assertEqual(self.exporter._exporting, "metrics")

    @patch.dict(
        "os.environ",
        {OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE: "DELTA"},
    )
    def test_preferred_temporality(self):
        # pylint: disable=protected-access
        exporter = OTLPMetricExporter(
            preferred_temporality={Counter: AggregationTemporality.CUMULATIVE}
        )
        self.assertEqual(
            exporter._preferred_temporality[Counter],
            AggregationTemporality.CUMULATIVE,
        )
        self.assertEqual(
            exporter._preferred_temporality[UpDownCounter],
            AggregationTemporality.CUMULATIVE,
        )
        self.assertEqual(
            exporter._preferred_temporality[Histogram],
            AggregationTemporality.DELTA,
        )
        self.assertEqual(
            exporter._preferred_temporality[ObservableCounter],
            AggregationTemporality.DELTA,
        )
        self.assertEqual(
            exporter._preferred_temporality[ObservableUpDownCounter],
            AggregationTemporality.CUMULATIVE,
        )
        self.assertEqual(
            exporter._preferred_temporality[ObservableGauge],
            AggregationTemporality.CUMULATIVE,
        )

    @patch.dict(
        "os.environ",
        {
            OTEL_EXPORTER_OTLP_METRICS_ENDPOINT: "collector:4317",
            OTEL_EXPORTER_OTLP_METRICS_HEADERS: " key1=value1,KEY2 = value=2",
            OTEL_EXPORTER_OTLP_METRICS_TIMEOUT: "10",
            OTEL_EXPORTER_OTLP_METRICS_COMPRESSION: "gzip",
        },
    )
    @patch(
        "opentelemetry.exporter.otlp.proto.grpc.exporter.OTLPExporterMixin.__init__"
    )
    def test_env_variables(self, mock_exporter_mixin):
        OTLPMetricExporter()

        self.assertTrue(len(mock_exporter_mixin.call_args_list) == 1)
        _, kwargs = mock_exporter_mixin.call_args_list[0]

        self.assertEqual(kwargs["endpoint"], "collector:4317")
        self.assertEqual(kwargs["headers"], " key1=value1,KEY2 = value=2")
        self.assertEqual(kwargs["timeout"], 10)
        self.assertEqual(kwargs["compression"], Compression.Gzip)
        self.assertIsNone(kwargs["credentials"])

    @patch.dict(
        "os.environ",
        {
            OTEL_EXPORTER_OTLP_METRICS_ENDPOINT: "collector:4317",
            OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE: THIS_DIR
            + "/fixtures/test.cert",
            OTEL_EXPORTER_OTLP_METRICS_CLIENT_CERTIFICATE: THIS_DIR
            + "/fixtures/test-client-cert.pem",
            OTEL_EXPORTER_OTLP_METRICS_CLIENT_KEY: THIS_DIR
            + "/fixtures/test-client-key.pem",
            OTEL_EXPORTER_OTLP_METRICS_HEADERS: " key1=value1,KEY2 = value=2",
            OTEL_EXPORTER_OTLP_METRICS_TIMEOUT: "10",
            OTEL_EXPORTER_OTLP_METRICS_COMPRESSION: "gzip",
        },
    )
    @patch(
        "opentelemetry.exporter.otlp.proto.grpc.exporter.OTLPExporterMixin.__init__"
    )
    def test_env_variables_with_client_certificates(self, mock_exporter_mixin):
        OTLPMetricExporter()

        self.assertTrue(len(mock_exporter_mixin.call_args_list) == 1)
        _, kwargs = mock_exporter_mixin.call_args_list[0]

        self.assertEqual(kwargs["endpoint"], "collector:4317")
        self.assertEqual(kwargs["headers"], " key1=value1,KEY2 = value=2")
        self.assertEqual(kwargs["timeout"], 10)
        self.assertEqual(kwargs["compression"], Compression.Gzip)
        self.assertIsNotNone(kwargs["credentials"])
        self.assertIsInstance(kwargs["credentials"], ChannelCredentials)

    @patch.dict(
        "os.environ",
        {
            OTEL_EXPORTER_OTLP_METRICS_ENDPOINT: "collector:4317",
            OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE: THIS_DIR
            + "/fixtures/test.cert",
            OTEL_EXPORTER_OTLP_METRICS_HEADERS: " key1=value1,KEY2 = value=2",
            OTEL_EXPORTER_OTLP_METRICS_TIMEOUT: "10",
            OTEL_EXPORTER_OTLP_METRICS_COMPRESSION: "gzip",
        },
    )
    @patch(
        "opentelemetry.exporter.otlp.proto.grpc.exporter.OTLPExporterMixin.__init__"
    )
    @patch("logging.Logger.error")
    def test_env_variables_with_only_certificate(
        self, mock_logger_error, mock_exporter_mixin
    ):
        OTLPMetricExporter()

        self.assertTrue(len(mock_exporter_mixin.call_args_list) == 1)
        _, kwargs = mock_exporter_mixin.call_args_list[0]
        self.assertEqual(kwargs["endpoint"], "collector:4317")
        self.assertEqual(kwargs["headers"], " key1=value1,KEY2 = value=2")
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
        "opentelemetry.exporter.otlp.proto.grpc.metric_exporter.OTLPMetricExporter._stub"
    )
    # pylint: disable=unused-argument
    def test_no_credentials_error(
        self, mock_ssl_channel, mock_secure, mock_stub
    ):
        OTLPMetricExporter(insecure=False)
        self.assertTrue(mock_ssl_channel.called)

    @patch.dict(
        "os.environ",
        {OTEL_EXPORTER_OTLP_METRICS_HEADERS: " key1=value1,KEY2 = VALUE=2 "},
    )
    @patch(
        "opentelemetry.exporter.otlp.proto.grpc.exporter.ssl_channel_credentials"
    )
    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.secure_channel")
    # pylint: disable=unused-argument
    def test_otlp_headers_from_env(self, mock_ssl_channel, mock_secure):
        exporter = OTLPMetricExporter()
        # pylint: disable=protected-access
        self.assertEqual(
            exporter._headers,
            (
                ("key1", "value1"),
                ("key2", "VALUE=2"),
                ("user-agent", "OTel-OTLP-Exporter-Python/" + __version__),
            ),
        )
        exporter = OTLPMetricExporter(
            headers=(("key3", "value3"), ("key4", "value4"))
        )
        # pylint: disable=protected-access
        self.assertEqual(
            exporter._headers,
            (
                ("key3", "value3"),
                ("key4", "value4"),
                ("user-agent", "OTel-OTLP-Exporter-Python/" + __version__),
            ),
        )

    @patch.dict(
        "os.environ",
        {OTEL_EXPORTER_OTLP_METRICS_INSECURE: "True"},
    )
    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.insecure_channel")
    # pylint: disable=unused-argument
    def test_otlp_insecure_from_env(self, mock_insecure):
        OTLPMetricExporter()
        # pylint: disable=protected-access
        self.assertTrue(mock_insecure.called)
        self.assertEqual(
            1,
            mock_insecure.call_count,
            f"expected {mock_insecure} to be called",
        )

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
            OTLPMetricExporter(endpoint=endpoint, insecure=insecure)
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

    # pylint: disable=no-self-use
    @patch(
        "opentelemetry.exporter.otlp.proto.grpc.exporter._create_exp_backoff_generator"
    )
    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.insecure_channel")
    @patch.dict("os.environ", {OTEL_EXPORTER_OTLP_COMPRESSION: "gzip"})
    def test_otlp_exporter_otlp_compression_envvar(
        self, mock_insecure_channel, mock_expo
    ):
        """Just OTEL_EXPORTER_OTLP_COMPRESSION should work"""
        OTLPMetricExporter(insecure=True)
        mock_insecure_channel.assert_called_once_with(
            "localhost:4317", compression=Compression.Gzip
        )

    # pylint: disable=no-self-use
    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.insecure_channel")
    @patch.dict("os.environ", {OTEL_EXPORTER_OTLP_COMPRESSION: "gzip"})
    def test_otlp_exporter_otlp_compression_kwarg(self, mock_insecure_channel):
        """Specifying kwarg should take precedence over env"""
        OTLPMetricExporter(
            insecure=True, compression=Compression.NoCompression
        )
        mock_insecure_channel.assert_called_once_with(
            "localhost:4317", compression=Compression.NoCompression
        )

    # pylint: disable=no-self-use
    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.insecure_channel")
    @patch.dict("os.environ", {})
    def test_otlp_exporter_otlp_compression_unspecified(
        self, mock_insecure_channel
    ):
        """No env or kwarg should be NoCompression"""
        OTLPMetricExporter(insecure=True)
        mock_insecure_channel.assert_called_once_with(
            "localhost:4317", compression=Compression.NoCompression
        )

    @patch(
        "opentelemetry.exporter.otlp.proto.grpc.exporter._create_exp_backoff_generator"
    )
    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.sleep")
    def test_unavailable(self, mock_sleep, mock_expo):

        mock_expo.configure_mock(**{"return_value": [0.01]})

        add_MetricsServiceServicer_to_server(
            MetricsServiceServicerUNAVAILABLE(), self.server
        )
        self.assertEqual(
            self.exporter.export(self.metrics["sum_int"]),
            MetricExportResult.FAILURE,
        )
        mock_sleep.assert_called_with(0.01)

    @patch(
        "opentelemetry.exporter.otlp.proto.grpc.exporter._create_exp_backoff_generator"
    )
    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.sleep")
    def test_unavailable_delay(self, mock_sleep, mock_expo):

        mock_expo.configure_mock(**{"return_value": [1]})

        add_MetricsServiceServicer_to_server(
            MetricsServiceServicerUNAVAILABLEDelay(), self.server
        )
        self.assertEqual(
            self.exporter.export(self.metrics["sum_int"]),
            MetricExportResult.FAILURE,
        )
        mock_sleep.assert_called_with(0.01)

    @patch(
        "opentelemetry.exporter.otlp.proto.grpc.exporter._create_exp_backoff_generator"
    )
    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.sleep")
    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.logger.error")
    def test_unknown_logs(self, mock_logger_error, mock_sleep, mock_expo):

        mock_expo.configure_mock(**{"return_value": [1]})

        add_MetricsServiceServicer_to_server(
            MetricsServiceServicerUNKNOWN(), self.server
        )
        self.assertEqual(
            self.exporter.export(self.metrics["sum_int"]),
            MetricExportResult.FAILURE,
        )
        mock_sleep.assert_not_called()
        mock_logger_error.assert_called_with(
            "Failed to export %s to %s, error code: %s",
            "metrics",
            "localhost:4317",
            StatusCode.UNKNOWN,
            exc_info=True,
        )

    def test_success(self):
        add_MetricsServiceServicer_to_server(
            MetricsServiceServicerSUCCESS(), self.server
        )
        self.assertEqual(
            self.exporter.export(self.metrics["sum_int"]),
            MetricExportResult.SUCCESS,
        )

    def test_failure(self):
        add_MetricsServiceServicer_to_server(
            MetricsServiceServicerALREADY_EXISTS(), self.server
        )
        self.assertEqual(
            self.exporter.export(self.metrics["sum_int"]),
            MetricExportResult.FAILURE,
        )

    def test_split_metrics_data_many_data_points(self):
        # GIVEN
        metrics_data = MetricsData(
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
        # WHEN
        split_metrics_data: List[MetricsData] = list(
            # pylint: disable=protected-access
            OTLPMetricExporter(max_export_batch_size=2)._split_metrics_data(
                metrics_data=metrics_data,
            )
        )
        # THEN
        self.assertEqual(
            [
                MetricsData(
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
                MetricsData(
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
        # GIVEN
        metrics_data = MetricsData(
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
        # WHEN
        split_metrics_data: List[MetricsData] = list(
            # pylint: disable=protected-access
            OTLPMetricExporter(max_export_batch_size=3)._split_metrics_data(
                metrics_data=metrics_data,
            )
        )
        # THEN
        self.assertEqual(
            [
                MetricsData(
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
        metrics_data = MetricsData(
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
        # WHEN
        split_metrics_data: List[MetricsData] = list(
            # pylint: disable=protected-access
            OTLPMetricExporter(max_export_batch_size=2)._split_metrics_data(
                metrics_data=metrics_data,
            )
        )
        # THEN
        self.assertEqual(
            [
                MetricsData(
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
                MetricsData(
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

    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.secure_channel")
    def test_insecure_https_endpoint(self, mock_secure_channel):
        OTLPMetricExporter(endpoint="https://ab.c:123", insecure=True)
        mock_secure_channel.assert_called()

    def test_shutdown(self):
        add_MetricsServiceServicer_to_server(
            MetricsServiceServicerSUCCESS(), self.server
        )
        self.assertEqual(
            self.exporter.export(self.metrics["sum_int"]),
            MetricExportResult.SUCCESS,
        )
        self.exporter.shutdown()
        with self.assertLogs(level=WARNING) as warning:
            self.assertEqual(
                self.exporter.export(self.metrics["sum_int"]),
                MetricExportResult.FAILURE,
            )
            self.assertEqual(
                warning.records[0].message,
                "Exporter already shutdown, ignoring batch",
            )
        self.exporter = OTLPMetricExporter()

    def test_shutdown_wait_last_export(self):
        add_MetricsServiceServicer_to_server(
            MetricsServiceServicerUNAVAILABLEDelay(), self.server
        )

        export_thread = threading.Thread(
            target=self.exporter.export, args=(self.metrics["sum_int"],)
        )
        export_thread.start()
        try:
            # pylint: disable=protected-access
            self.assertTrue(self.exporter._export_lock.locked())
            # delay is 4 seconds while the default shutdown timeout is 30_000 milliseconds
            start_time = time_ns()
            self.exporter.shutdown()
            now = time_ns()
            self.assertGreaterEqual(now, (start_time + 30 / 1000))
            # pylint: disable=protected-access
            self.assertTrue(self.exporter._shutdown)
            # pylint: disable=protected-access
            self.assertFalse(self.exporter._export_lock.locked())
        finally:
            export_thread.join()

    def test_aggregation_temporality(self):
        # pylint: disable=protected-access

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
            # pylint: disable=protected-access
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
                # pylint: disable=protected-access
                OTLPMetricExporter()._preferred_aggregation[Histogram],
                ExponentialBucketHistogramAggregation,
            )

        with patch.dict(
            environ,
            {OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION: "abc"},
        ):
            with self.assertLogs(level=WARNING) as log:
                self.assertIsInstance(
                    # pylint: disable=protected-access
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
                # pylint: disable=protected-access
                OTLPMetricExporter()._preferred_aggregation[Histogram],
                ExplicitBucketHistogramAggregation,
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
            # pylint: disable=protected-access
            exporter._preferred_aggregation[Histogram],
            histogram_aggregation,
        )


def _resource_metrics(
    index: int, scope_metrics: List[ScopeMetrics]
) -> ResourceMetrics:
    return ResourceMetrics(
        resource=Resource(
            attributes={"a": index},
            schema_url=f"resource_url_{index}",
        ),
        schema_url=f"resource_url_{index}",
        scope_metrics=scope_metrics,
    )


def _scope_metrics(index: int, metrics: List[Metric]) -> ScopeMetrics:
    return ScopeMetrics(
        scope=InstrumentationScope(name=f"scope_{index}"),
        schema_url=f"scope_url_{index}",
        metrics=metrics,
    )


def _gauge(index: int, data_points: List[NumberDataPoint]) -> Metric:
    return Metric(
        name=f"gauge_{index}",
        description="description",
        unit="unit",
        data=Gauge(data_points=data_points),
    )


def _number_data_point(value: int) -> NumberDataPoint:
    return NumberDataPoint(
        attributes={"a": 1, "b": True},
        start_time_unix_nano=1641946015139533244,
        time_unix_nano=1641946016139533244,
        value=value,
    )
