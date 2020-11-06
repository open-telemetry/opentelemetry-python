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

from grpc import ChannelCredentials

from opentelemetry.configuration import Configuration
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
                "c",
                "d",
                "e",
                int,
                MeterProvider(resource=resource,).get_meter(__name__),
                ("f",),
            ),
            [("g", "h")],
            SumAggregator(),
            resource,
        )

        Configuration._reset()  # pylint: disable=protected-access

    def tearDown(self):
        Configuration._reset()  # pylint: disable=protected-access

    @patch.dict(
        "os.environ",
        {
            "OTEL_EXPORTER_OTLP_METRIC_ENDPOINT": "collector:55680",
            "OTEL_EXPORTER_OTLP_METRIC_CERTIFICATE": "fixtures/test.cert",
            "OTEL_EXPORTER_OTLP_METRIC_HEADERS": "key1:value1;key2:value2",
            "OTEL_EXPORTER_OTLP_METRIC_TIMEOUT": "10",
        },
    )
    @patch("opentelemetry.exporter.otlp.exporter.OTLPExporterMixin.__init__")
    def test_env_variables(self, mock_exporter_mixin):
        OTLPMetricsExporter()

        self.assertTrue(len(mock_exporter_mixin.call_args_list) == 1)
        _, kwargs = mock_exporter_mixin.call_args_list[0]

        self.assertEqual(kwargs["endpoint"], "collector:55680")
        self.assertEqual(kwargs["headers"], "key1:value1;key2:value2")
        self.assertEqual(kwargs["timeout"], 10)
        self.assertIsNotNone(kwargs["credentials"])
        self.assertIsInstance(kwargs["credentials"], ChannelCredentials)

    @patch("opentelemetry.sdk.metrics.export.aggregate.time_ns")
    def test_translate_metrics(self, mock_time_ns):
        # pylint: disable=no-member

        mock_time_ns.configure_mock(**{"return_value": 1})

        self.counter_metric_record.aggregator.checkpoint = 1
        self.counter_metric_record.aggregator.initial_checkpoint_timestamp = 1
        self.counter_metric_record.aggregator.last_update_timestamp = 1

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
                                    name="c",
                                    description="d",
                                    unit="e",
                                    int_sum=IntSum(
                                        data_points=[
                                            IntDataPoint(
                                                labels=[
                                                    StringKeyValue(
                                                        key="g", value="h"
                                                    )
                                                ],
                                                value=1,
                                                time_unix_nano=1,
                                                start_time_unix_nano=1,
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
