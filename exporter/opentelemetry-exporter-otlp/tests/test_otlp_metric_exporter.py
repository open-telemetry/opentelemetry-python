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

from collections import OrderedDict
from unittest import TestCase
from unittest.mock import patch
<<<<<<< HEAD
=======
from opentelemetry.configuration import Configuration
from grpc import ChannelCredentials
>>>>>>> f2dd93b... Add env variables tests

from opentelemetry.exporter.otlp.metrics_exporter import OTLPMetricsExporter
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
)
from opentelemetry.proto.common.v1.common_pb2 import (
    AnyValue,
    KeyValue,
    StringKeyValue,
)
from opentelemetry.proto.metrics.v1.metrics_pb2 import (
    AggregationTemporality,
    InstrumentationLibraryMetrics,
    IntDataPoint,
    IntSum,
)
from opentelemetry.proto.metrics.v1.metrics_pb2 import Metric as OTLPMetric
from opentelemetry.proto.metrics.v1.metrics_pb2 import ResourceMetrics
from opentelemetry.proto.resource.v1.resource_pb2 import (
    Resource as OTLPResource,
)
from opentelemetry.sdk.metrics import Counter, MeterProvider
from opentelemetry.sdk.metrics.export import MetricRecord
from opentelemetry.sdk.metrics.export.aggregate import SumAggregator
from opentelemetry.sdk.resources import Resource as SDKResource


class TestOTLPMetricExporter(TestCase):
    def setUp(self):
        self.exporter = OTLPMetricsExporter(insecure=True)
        resource = SDKResource(OrderedDict([("a", 1), ("b", False)]))

        self.counter_metric_record = MetricRecord(
            Counter(
                "a",
                "b",
                "c",
                int,
                MeterProvider(resource=resource,).get_meter(__name__),
                ("d",),
            ),
            OrderedDict([("e", "f")]),
            SumAggregator(),
            resource,
        )

        Configuration._reset()  # pylint: disable=protected-access

    def tearDown(self):
        Configuration._reset()  # pylint: disable=protected-access

    @patch.dict("os.environ", {
        "OTEL_EXPORTER_OTLP_METRIC_ENDPOINT": "collector:55680",
        "OTEL_EXPORTER_OTLP_METRIC_HEADERS": "key1:value1;key2:value2",
        "OTEL_EXPORTER_OTLP_METRIC_CERTIFICATE": "fixtures/test.cert",
    })
    @patch("opentelemetry.exporter.otlp.exporter.OTLPExporterMixin.__init__")
    def test_env_variables(self, mock_exporter_mixin):
        OTLPMetricsExporter()
        kwargs = mock_exporter_mixin.call_args.kwargs

        self.assertEqual(kwargs["endpoint"], "collector:55680")
        self.assertEqual(kwargs["metadata"], "key1:value1;key2:value2")
        self.assertIsNotNone(kwargs["credentials"])
        self.assertIsInstance(kwargs["credentials"], ChannelCredentials)

    @patch("opentelemetry.sdk.metrics.export.aggregate.time_ns")
    def test_translate_metrics(self, mock_time_ns):
        # pylint: disable=no-member

        mock_time_ns.configure_mock(**{"return_value": 1})

        self.counter_metric_record.instrument.add(1, OrderedDict([("a", "b")]))

        expected = ExportMetricsServiceRequest(
            resource_metrics=[
                ResourceMetrics(
                    resource=OTLPResource(
                        attributes=[
                            KeyValue(key="a", value=AnyValue(int_value=1)),
                            KeyValue(
                                key="b", value=AnyValue(bool_value=False)
                            ),
                        ]
                    ),
                    instrumentation_library_metrics=[
                        InstrumentationLibraryMetrics(
                            metrics=[
                                OTLPMetric(
                                    name="a",
                                    description="b",
                                    unit="c",
                                    int_sum=IntSum(
                                        data_points=[
                                            IntDataPoint(
                                                labels=[
                                                    StringKeyValue(
                                                        key="a", value="b"
                                                    )
                                                ],
                                                value=1,
                                                time_unix_nano=1,
                                            )
                                        ],
                                        aggregation_temporality=(
                                            AggregationTemporality.AGGREGATION_TEMPORALITY_DELTA
                                        ),
                                        is_monotonic=True,
                                    ),
                                )
                            ]
                        )
                    ],
                )
            ]
        )

        # pylint: disable=protected-access
        actual = self.exporter._translate_data([self.counter_metric_record])

        self.assertEqual(expected, actual)
