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
    InstrumentationLibraryMetrics,
    Int64DataPoint,
)
from opentelemetry.proto.metrics.v1.metrics_pb2 import (
    Metric as CollectorMetric,
)
from opentelemetry.proto.metrics.v1.metrics_pb2 import (
    MetricDescriptor,
    ResourceMetrics,
)
from opentelemetry.proto.resource.v1.resource_pb2 import (
    Resource as CollectorResource,
)
from opentelemetry.sdk.metrics import Counter, MeterProvider
from opentelemetry.sdk.metrics.export import MetricRecord
from opentelemetry.sdk.metrics.export.aggregate import SumAggregator
from opentelemetry.sdk.resources import Resource as SDKResource


class TestOTLPMetricExporter(TestCase):
    def setUp(self):
        self.exporter = OTLPMetricsExporter()

        self.counter_metric_record = MetricRecord(
            Counter(
                "a",
                "b",
                "c",
                int,
                MeterProvider(
                    resource=SDKResource(OrderedDict([("a", 1), ("b", False)]))
                ).get_meter(__name__),
                ("d",),
            ),
            OrderedDict([("e", "f")]),
            SumAggregator(),
        )

    def test_translate_metrics(self):
        # pylint: disable=no-member

        self.counter_metric_record.instrument.add(1, OrderedDict([("a", "b")]))

        expected = ExportMetricsServiceRequest(
            resource_metrics=[
                ResourceMetrics(
                    resource=CollectorResource(
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
                                CollectorMetric(
                                    metric_descriptor=MetricDescriptor(
                                        name="a",
                                        description="b",
                                        unit="c",
                                        type=MetricDescriptor.Type.INT64,
                                        temporality=(
                                            MetricDescriptor.Temporality.DELTA
                                        ),
                                    ),
                                    int64_data_points=[
                                        Int64DataPoint(
                                            labels=[
                                                StringKeyValue(
                                                    key="a", value="b"
                                                )
                                            ],
                                            value=1,
                                        )
                                    ],
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
