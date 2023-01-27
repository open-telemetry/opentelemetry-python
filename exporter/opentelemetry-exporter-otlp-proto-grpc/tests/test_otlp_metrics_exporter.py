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
from concurrent.futures import ThreadPoolExecutor
from os.path import dirname
from typing import List
from unittest import TestCase
from unittest.mock import patch

from google.protobuf.duration_pb2 import Duration
from google.rpc.error_details_pb2 import RetryInfo
from grpc import ChannelCredentials, Compression, StatusCode, server

from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.exporter.otlp.proto.grpc.version import __version__
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
    ExportMetricsServiceResponse,
)
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2_grpc import (
    MetricsServiceServicer,
    add_MetricsServiceServicer_to_server,
)
from opentelemetry.proto.common.v1.common_pb2 import (
    AnyValue,
    InstrumentationScope,
    KeyValue,
)
from opentelemetry.proto.metrics.v1 import metrics_pb2 as pb2
from opentelemetry.proto.resource.v1.resource_pb2 import (
    Resource as OTLPResource,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE,
    OTEL_EXPORTER_OTLP_METRICS_COMPRESSION,
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
from opentelemetry.sdk.metrics.export import AggregationTemporality, Gauge
from opentelemetry.sdk.metrics.export import Histogram as HistogramType
from opentelemetry.sdk.metrics.export import (
    HistogramDataPoint,
    Metric,
    MetricExportResult,
    MetricsData,
    NumberDataPoint,
    ResourceMetrics,
    ScopeMetrics,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import (
    InstrumentationScope as SDKInstrumentationScope,
)
from opentelemetry.test.metrictestutil import _generate_gauge, _generate_sum

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
                        retry_delay=Duration(seconds=4)
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

        histogram = Metric(
            name="histogram",
            description="foo",
            unit="s",
            data=HistogramType(
                data_points=[
                    HistogramDataPoint(
                        attributes={"a": 1, "b": True},
                        start_time_unix_nano=1641946016139533244,
                        time_unix_nano=1641946016139533244,
                        count=5,
                        sum=67,
                        bucket_counts=[1, 4],
                        explicit_bounds=[10.0, 20.0],
                        min=8,
                        max=18,
                    )
                ],
                aggregation_temporality=AggregationTemporality.DELTA,
            ),
        )

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
            "sum_double": MetricsData(
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
                                metrics=[_generate_sum("sum_double", 2.98)],
                                schema_url="instrumentation_scope_schema_url",
                            )
                        ],
                        schema_url="resource_schema_url",
                    )
                ]
            ),
            "gauge_int": MetricsData(
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
                                metrics=[_generate_gauge("gauge_int", 9000)],
                                schema_url="instrumentation_scope_schema_url",
                            )
                        ],
                        schema_url="resource_schema_url",
                    )
                ]
            ),
            "gauge_double": MetricsData(
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
                                metrics=[
                                    _generate_gauge("gauge_double", 52.028)
                                ],
                                schema_url="instrumentation_scope_schema_url",
                            )
                        ],
                        schema_url="resource_schema_url",
                    )
                ]
            ),
            "histogram": MetricsData(
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
                                metrics=[histogram],
                                schema_url="instrumentation_scope_schema_url",
                            )
                        ],
                        schema_url="resource_schema_url",
                    )
                ]
            ),
        }

        self.multiple_scope_histogram = MetricsData(
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
                            metrics=[histogram, histogram],
                            schema_url="instrumentation_scope_schema_url",
                        ),
                        ScopeMetrics(
                            scope=SDKInstrumentationScope(
                                name="second_name",
                                version="second_version",
                                schema_url="insrumentation_scope_schema_url",
                            ),
                            metrics=[histogram],
                            schema_url="instrumentation_scope_schema_url",
                        ),
                        ScopeMetrics(
                            scope=SDKInstrumentationScope(
                                name="third_name",
                                version="third_version",
                                schema_url="insrumentation_scope_schema_url",
                            ),
                            metrics=[histogram],
                            schema_url="instrumentation_scope_schema_url",
                        ),
                    ],
                    schema_url="resource_schema_url",
                )
            ]
        )

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
    def test_env_variables(self, mock_exporter_mixin):
        OTLPMetricExporter()

        self.assertTrue(len(mock_exporter_mixin.call_args_list) == 1)
        _, kwargs = mock_exporter_mixin.call_args_list[0]

        self.assertEqual(kwargs["endpoint"], "collector:4317")
        self.assertEqual(kwargs["headers"], " key1=value1,KEY2 = value=2")
        self.assertEqual(kwargs["timeout"], 10)
        self.assertEqual(kwargs["compression"], Compression.Gzip)
        self.assertIsNotNone(kwargs["credentials"])
        self.assertIsInstance(kwargs["credentials"], ChannelCredentials)

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
    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter._expo")
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

    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter._expo")
    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.sleep")
    def test_unavailable(self, mock_sleep, mock_expo):

        mock_expo.configure_mock(**{"return_value": [1]})

        add_MetricsServiceServicer_to_server(
            MetricsServiceServicerUNAVAILABLE(), self.server
        )
        self.assertEqual(
            self.exporter.export(self.metrics["sum_int"]),
            MetricExportResult.FAILURE,
        )
        mock_sleep.assert_called_with(1)

    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter._expo")
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
        mock_sleep.assert_called_with(4)

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

    def test_translate_sum_int(self):
        expected = ExportMetricsServiceRequest(
            resource_metrics=[
                pb2.ResourceMetrics(
                    resource=OTLPResource(
                        attributes=[
                            KeyValue(key="a", value=AnyValue(int_value=1)),
                            KeyValue(
                                key="b", value=AnyValue(bool_value=False)
                            ),
                        ]
                    ),
                    scope_metrics=[
                        pb2.ScopeMetrics(
                            scope=InstrumentationScope(
                                name="first_name", version="first_version"
                            ),
                            metrics=[
                                pb2.Metric(
                                    name="sum_int",
                                    unit="s",
                                    description="foo",
                                    sum=pb2.Sum(
                                        data_points=[
                                            pb2.NumberDataPoint(
                                                attributes=[
                                                    KeyValue(
                                                        key="a",
                                                        value=AnyValue(
                                                            int_value=1
                                                        ),
                                                    ),
                                                    KeyValue(
                                                        key="b",
                                                        value=AnyValue(
                                                            bool_value=True
                                                        ),
                                                    ),
                                                ],
                                                start_time_unix_nano=1641946015139533244,
                                                time_unix_nano=1641946016139533244,
                                                as_int=33,
                                            )
                                        ],
                                        aggregation_temporality=AggregationTemporality.CUMULATIVE,
                                        is_monotonic=True,
                                    ),
                                )
                            ],
                        )
                    ],
                )
            ]
        )
        # pylint: disable=protected-access
        actual = self.exporter._translate_data(self.metrics["sum_int"])
        self.assertEqual(expected, actual)

    def test_translate_sum_double(self):
        expected = ExportMetricsServiceRequest(
            resource_metrics=[
                pb2.ResourceMetrics(
                    resource=OTLPResource(
                        attributes=[
                            KeyValue(key="a", value=AnyValue(int_value=1)),
                            KeyValue(
                                key="b", value=AnyValue(bool_value=False)
                            ),
                        ]
                    ),
                    scope_metrics=[
                        pb2.ScopeMetrics(
                            scope=InstrumentationScope(
                                name="first_name", version="first_version"
                            ),
                            metrics=[
                                pb2.Metric(
                                    name="sum_double",
                                    unit="s",
                                    description="foo",
                                    sum=pb2.Sum(
                                        data_points=[
                                            pb2.NumberDataPoint(
                                                attributes=[
                                                    KeyValue(
                                                        key="a",
                                                        value=AnyValue(
                                                            int_value=1
                                                        ),
                                                    ),
                                                    KeyValue(
                                                        key="b",
                                                        value=AnyValue(
                                                            bool_value=True
                                                        ),
                                                    ),
                                                ],
                                                start_time_unix_nano=1641946015139533244,
                                                time_unix_nano=1641946016139533244,
                                                as_double=2.98,
                                            )
                                        ],
                                        aggregation_temporality=AggregationTemporality.CUMULATIVE,
                                        is_monotonic=True,
                                    ),
                                )
                            ],
                        )
                    ],
                )
            ]
        )
        # pylint: disable=protected-access
        actual = self.exporter._translate_data(self.metrics["sum_double"])
        self.assertEqual(expected, actual)

    def test_translate_gauge_int(self):
        expected = ExportMetricsServiceRequest(
            resource_metrics=[
                pb2.ResourceMetrics(
                    resource=OTLPResource(
                        attributes=[
                            KeyValue(key="a", value=AnyValue(int_value=1)),
                            KeyValue(
                                key="b", value=AnyValue(bool_value=False)
                            ),
                        ]
                    ),
                    scope_metrics=[
                        pb2.ScopeMetrics(
                            scope=InstrumentationScope(
                                name="first_name", version="first_version"
                            ),
                            metrics=[
                                pb2.Metric(
                                    name="gauge_int",
                                    unit="s",
                                    description="foo",
                                    gauge=pb2.Gauge(
                                        data_points=[
                                            pb2.NumberDataPoint(
                                                attributes=[
                                                    KeyValue(
                                                        key="a",
                                                        value=AnyValue(
                                                            int_value=1
                                                        ),
                                                    ),
                                                    KeyValue(
                                                        key="b",
                                                        value=AnyValue(
                                                            bool_value=True
                                                        ),
                                                    ),
                                                ],
                                                time_unix_nano=1641946016139533244,
                                                as_int=9000,
                                            )
                                        ],
                                    ),
                                )
                            ],
                        )
                    ],
                )
            ]
        )
        # pylint: disable=protected-access
        actual = self.exporter._translate_data(self.metrics["gauge_int"])
        self.assertEqual(expected, actual)

    def test_translate_gauge_double(self):
        expected = ExportMetricsServiceRequest(
            resource_metrics=[
                pb2.ResourceMetrics(
                    resource=OTLPResource(
                        attributes=[
                            KeyValue(key="a", value=AnyValue(int_value=1)),
                            KeyValue(
                                key="b", value=AnyValue(bool_value=False)
                            ),
                        ]
                    ),
                    scope_metrics=[
                        pb2.ScopeMetrics(
                            scope=InstrumentationScope(
                                name="first_name", version="first_version"
                            ),
                            metrics=[
                                pb2.Metric(
                                    name="gauge_double",
                                    unit="s",
                                    description="foo",
                                    gauge=pb2.Gauge(
                                        data_points=[
                                            pb2.NumberDataPoint(
                                                attributes=[
                                                    KeyValue(
                                                        key="a",
                                                        value=AnyValue(
                                                            int_value=1
                                                        ),
                                                    ),
                                                    KeyValue(
                                                        key="b",
                                                        value=AnyValue(
                                                            bool_value=True
                                                        ),
                                                    ),
                                                ],
                                                time_unix_nano=1641946016139533244,
                                                as_double=52.028,
                                            )
                                        ],
                                    ),
                                )
                            ],
                        )
                    ],
                )
            ]
        )
        # pylint: disable=protected-access
        actual = self.exporter._translate_data(self.metrics["gauge_double"])
        self.assertEqual(expected, actual)

    def test_translate_histogram(self):
        expected = ExportMetricsServiceRequest(
            resource_metrics=[
                pb2.ResourceMetrics(
                    resource=OTLPResource(
                        attributes=[
                            KeyValue(key="a", value=AnyValue(int_value=1)),
                            KeyValue(
                                key="b", value=AnyValue(bool_value=False)
                            ),
                        ]
                    ),
                    scope_metrics=[
                        pb2.ScopeMetrics(
                            scope=InstrumentationScope(
                                name="first_name", version="first_version"
                            ),
                            metrics=[
                                pb2.Metric(
                                    name="histogram",
                                    unit="s",
                                    description="foo",
                                    histogram=pb2.Histogram(
                                        data_points=[
                                            pb2.HistogramDataPoint(
                                                attributes=[
                                                    KeyValue(
                                                        key="a",
                                                        value=AnyValue(
                                                            int_value=1
                                                        ),
                                                    ),
                                                    KeyValue(
                                                        key="b",
                                                        value=AnyValue(
                                                            bool_value=True
                                                        ),
                                                    ),
                                                ],
                                                start_time_unix_nano=1641946016139533244,
                                                time_unix_nano=1641946016139533244,
                                                count=5,
                                                sum=67,
                                                bucket_counts=[1, 4],
                                                explicit_bounds=[10.0, 20.0],
                                                exemplars=[],
                                                flags=pb2.DataPointFlags.FLAG_NONE,
                                                max=18.0,
                                                min=8.0,
                                            )
                                        ],
                                        aggregation_temporality=AggregationTemporality.DELTA,
                                    ),
                                )
                            ],
                        )
                    ],
                )
            ]
        )
        # pylint: disable=protected-access
        actual = self.exporter._translate_data(self.metrics["histogram"])
        self.assertEqual(expected, actual)

    def test_translate_multiple_scope_histogram(self):
        expected = ExportMetricsServiceRequest(
            resource_metrics=[
                pb2.ResourceMetrics(
                    resource=OTLPResource(
                        attributes=[
                            KeyValue(key="a", value=AnyValue(int_value=1)),
                            KeyValue(
                                key="b", value=AnyValue(bool_value=False)
                            ),
                        ]
                    ),
                    scope_metrics=[
                        pb2.ScopeMetrics(
                            scope=InstrumentationScope(
                                name="first_name", version="first_version"
                            ),
                            metrics=[
                                pb2.Metric(
                                    name="histogram",
                                    unit="s",
                                    description="foo",
                                    histogram=pb2.Histogram(
                                        data_points=[
                                            pb2.HistogramDataPoint(
                                                attributes=[
                                                    KeyValue(
                                                        key="a",
                                                        value=AnyValue(
                                                            int_value=1
                                                        ),
                                                    ),
                                                    KeyValue(
                                                        key="b",
                                                        value=AnyValue(
                                                            bool_value=True
                                                        ),
                                                    ),
                                                ],
                                                start_time_unix_nano=1641946016139533244,
                                                time_unix_nano=1641946016139533244,
                                                count=5,
                                                sum=67,
                                                bucket_counts=[1, 4],
                                                explicit_bounds=[10.0, 20.0],
                                                exemplars=[],
                                                flags=pb2.DataPointFlags.FLAG_NONE,
                                                max=18.0,
                                                min=8.0,
                                            )
                                        ],
                                        aggregation_temporality=AggregationTemporality.DELTA,
                                    ),
                                ),
                                pb2.Metric(
                                    name="histogram",
                                    unit="s",
                                    description="foo",
                                    histogram=pb2.Histogram(
                                        data_points=[
                                            pb2.HistogramDataPoint(
                                                attributes=[
                                                    KeyValue(
                                                        key="a",
                                                        value=AnyValue(
                                                            int_value=1
                                                        ),
                                                    ),
                                                    KeyValue(
                                                        key="b",
                                                        value=AnyValue(
                                                            bool_value=True
                                                        ),
                                                    ),
                                                ],
                                                start_time_unix_nano=1641946016139533244,
                                                time_unix_nano=1641946016139533244,
                                                count=5,
                                                sum=67,
                                                bucket_counts=[1, 4],
                                                explicit_bounds=[10.0, 20.0],
                                                exemplars=[],
                                                flags=pb2.DataPointFlags.FLAG_NONE,
                                                max=18.0,
                                                min=8.0,
                                            )
                                        ],
                                        aggregation_temporality=AggregationTemporality.DELTA,
                                    ),
                                ),
                            ],
                        ),
                        pb2.ScopeMetrics(
                            scope=InstrumentationScope(
                                name="second_name", version="second_version"
                            ),
                            metrics=[
                                pb2.Metric(
                                    name="histogram",
                                    unit="s",
                                    description="foo",
                                    histogram=pb2.Histogram(
                                        data_points=[
                                            pb2.HistogramDataPoint(
                                                attributes=[
                                                    KeyValue(
                                                        key="a",
                                                        value=AnyValue(
                                                            int_value=1
                                                        ),
                                                    ),
                                                    KeyValue(
                                                        key="b",
                                                        value=AnyValue(
                                                            bool_value=True
                                                        ),
                                                    ),
                                                ],
                                                start_time_unix_nano=1641946016139533244,
                                                time_unix_nano=1641946016139533244,
                                                count=5,
                                                sum=67,
                                                bucket_counts=[1, 4],
                                                explicit_bounds=[10.0, 20.0],
                                                exemplars=[],
                                                flags=pb2.DataPointFlags.FLAG_NONE,
                                                max=18.0,
                                                min=8.0,
                                            )
                                        ],
                                        aggregation_temporality=AggregationTemporality.DELTA,
                                    ),
                                )
                            ],
                        ),
                        pb2.ScopeMetrics(
                            scope=InstrumentationScope(
                                name="third_name", version="third_version"
                            ),
                            metrics=[
                                pb2.Metric(
                                    name="histogram",
                                    unit="s",
                                    description="foo",
                                    histogram=pb2.Histogram(
                                        data_points=[
                                            pb2.HistogramDataPoint(
                                                attributes=[
                                                    KeyValue(
                                                        key="a",
                                                        value=AnyValue(
                                                            int_value=1
                                                        ),
                                                    ),
                                                    KeyValue(
                                                        key="b",
                                                        value=AnyValue(
                                                            bool_value=True
                                                        ),
                                                    ),
                                                ],
                                                start_time_unix_nano=1641946016139533244,
                                                time_unix_nano=1641946016139533244,
                                                count=5,
                                                sum=67,
                                                bucket_counts=[1, 4],
                                                explicit_bounds=[10.0, 20.0],
                                                exemplars=[],
                                                flags=pb2.DataPointFlags.FLAG_NONE,
                                                max=18.0,
                                                min=8.0,
                                            )
                                        ],
                                        aggregation_temporality=AggregationTemporality.DELTA,
                                    ),
                                )
                            ],
                        ),
                    ],
                )
            ]
        )
        # pylint: disable=protected-access
        actual = self.exporter._translate_data(self.multiple_scope_histogram)
        self.assertEqual(expected, actual)

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
