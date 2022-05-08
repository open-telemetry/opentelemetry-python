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

from concurrent.futures import ThreadPoolExecutor
from unittest import TestCase
from unittest.mock import patch

from google.protobuf.duration_pb2 import Duration
from google.rpc.error_details_pb2 import RetryInfo
from grpc import StatusCode, server

from opentelemetry.exporter.otlp.proto.grpc._metric_exporter import (
    OTLPMetricExporter,
)
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
from opentelemetry.sdk._metrics.export import MetricExportResult
from opentelemetry.sdk._metrics.point import AggregationTemporality, Histogram
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_METRICS_INSECURE,
)
from opentelemetry.test.metrictestutil import (
    _generate_gauge,
    _generate_metric,
    _generate_sum,
)


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
    def setUp(self):

        self.exporter = OTLPMetricExporter()

        self.server = server(ThreadPoolExecutor(max_workers=10))

        self.server.add_insecure_port("127.0.0.1:4317")

        self.server.start()

        self.metrics = {
            "sum_int": _generate_sum("sum_int", 33),
            "sum_double": _generate_sum("sum_double", 2.98),
            "gauge_int": _generate_gauge("gauge_int", 9000),
            "gauge_double": _generate_gauge("gauge_double", 52.028),
            "histogram": _generate_metric(
                "histogram",
                Histogram(
                    aggregation_temporality=AggregationTemporality.DELTA,
                    bucket_counts=[1, 4],
                    explicit_bounds=[10.0, 20.0],
                    max=18,
                    min=8,
                    start_time_unix_nano=1641946016139533244,
                    sum=67,
                    time_unix_nano=1641946016139533244,
                ),
            ),
        }

    def tearDown(self):
        self.server.stop(None)

    @patch(
        "opentelemetry.exporter.otlp.proto.grpc.exporter.ssl_channel_credentials"
    )
    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.secure_channel")
    @patch(
        "opentelemetry.exporter.otlp.proto.grpc._metric_exporter.OTLPMetricExporter._stub"
    )
    # pylint: disable=unused-argument
    def test_no_credentials_error(
        self, mock_ssl_channel, mock_secure, mock_stub
    ):
        OTLPMetricExporter(insecure=False)
        self.assertTrue(mock_ssl_channel.called)

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

    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.expo")
    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.sleep")
    def test_unavailable(self, mock_sleep, mock_expo):

        mock_expo.configure_mock(**{"return_value": [1]})

        add_MetricsServiceServicer_to_server(
            MetricsServiceServicerUNAVAILABLE(), self.server
        )
        self.assertEqual(
            self.exporter.export([self.metrics["sum_int"]]),
            MetricExportResult.FAILURE,
        )
        mock_sleep.assert_called_with(1)

    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.expo")
    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.sleep")
    def test_unavailable_delay(self, mock_sleep, mock_expo):

        mock_expo.configure_mock(**{"return_value": [1]})

        add_MetricsServiceServicer_to_server(
            MetricsServiceServicerUNAVAILABLEDelay(), self.server
        )
        self.assertEqual(
            self.exporter.export([self.metrics["sum_int"]]),
            MetricExportResult.FAILURE,
        )
        mock_sleep.assert_called_with(4)

    def test_success(self):
        add_MetricsServiceServicer_to_server(
            MetricsServiceServicerSUCCESS(), self.server
        )
        self.assertEqual(
            self.exporter.export([self.metrics["sum_int"]]),
            MetricExportResult.SUCCESS,
        )

    def test_failure(self):
        add_MetricsServiceServicer_to_server(
            MetricsServiceServicerALREADY_EXISTS(), self.server
        )
        self.assertEqual(
            self.exporter.export([self.metrics["sum_int"]]),
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
        actual = self.exporter._translate_data([self.metrics["sum_int"]])
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
        actual = self.exporter._translate_data([self.metrics["sum_double"]])
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
        actual = self.exporter._translate_data([self.metrics["gauge_int"]])
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
        actual = self.exporter._translate_data([self.metrics["gauge_double"]])
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
        actual = self.exporter._translate_data([self.metrics["histogram"]])
        self.assertEqual(expected, actual)
