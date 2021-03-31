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

import os
from collections import OrderedDict
from unittest import TestCase
from unittest.mock import Mock, patch

from grpc import ChannelCredentials

from opentelemetry.exporter.otlp.proto.grpc.metrics_exporter import (
    OTLPMetricsExporter,
)
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
)
from opentelemetry.proto.common.v1.common_pb2 import (
    AnyValue,
    InstrumentationLibrary,
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
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_METRIC_CERTIFICATE,
    OTEL_EXPORTER_OTLP_METRIC_ENDPOINT,
    OTEL_EXPORTER_OTLP_METRIC_HEADERS,
    OTEL_EXPORTER_OTLP_METRIC_TIMEOUT,
)
from opentelemetry.sdk.metrics import (
    Counter,
    MeterProvider,
    SumObserver,
    UpDownCounter,
    UpDownSumObserver,
)
from opentelemetry.sdk.metrics.export import ExportRecord
from opentelemetry.sdk.metrics.export.aggregate import SumAggregator
from opentelemetry.sdk.resources import Resource as SDKResource

THIS_DIR = os.path.dirname(__file__)


class TestOTLPMetricExporter(TestCase):
    def setUp(self):  # pylint: disable=arguments-differ
        self.exporter = OTLPMetricsExporter(insecure=True)
        self.resource = SDKResource(OrderedDict([("a", 1), ("b", False)]))
        self.meter = MeterProvider(resource=self.resource,).get_meter(
            "name", "version"
        )

    @patch.dict(
        "os.environ",
        {
            OTEL_EXPORTER_OTLP_METRIC_ENDPOINT: "collector:4317",
            OTEL_EXPORTER_OTLP_METRIC_CERTIFICATE: THIS_DIR
            + "/fixtures/test.cert",
            OTEL_EXPORTER_OTLP_METRIC_HEADERS: "key1=value1,key2=value2",
            OTEL_EXPORTER_OTLP_METRIC_TIMEOUT: "10",
        },
    )
    @patch(
        "opentelemetry.exporter.otlp.proto.grpc.exporter.OTLPExporterMixin.__init__"
    )
    def test_env_variables(self, mock_exporter_mixin):
        OTLPMetricsExporter()

        self.assertTrue(len(mock_exporter_mixin.call_args_list) == 1)
        _, kwargs = mock_exporter_mixin.call_args_list[0]

        self.assertEqual(kwargs["endpoint"], "collector:4317")
        self.assertEqual(kwargs["headers"], "key1=value1,key2=value2")
        self.assertEqual(kwargs["timeout"], 10)
        self.assertIsNotNone(kwargs["credentials"])
        self.assertIsInstance(kwargs["credentials"], ChannelCredentials)

    @patch(
        "opentelemetry.exporter.otlp.proto.grpc.exporter.ssl_channel_credentials"
    )
    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.secure_channel")
    @patch(
        "opentelemetry.exporter.otlp.proto.grpc.metrics_exporter.OTLPMetricsExporter._stub"
    )
    # pylint: disable=unused-argument
    def test_no_credentials_error(
        self, mock_ssl_channel, mock_secure, mock_stub
    ):
        OTLPMetricsExporter(insecure=False)
        self.assertTrue(mock_ssl_channel.called)

    @patch.dict(
        "os.environ",
        {OTEL_EXPORTER_OTLP_METRIC_HEADERS: "key1=value1,key2=value2"},
    )
    @patch(
        "opentelemetry.exporter.otlp.proto.grpc.exporter.ssl_channel_credentials"
    )
    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.secure_channel")
    # pylint: disable=unused-argument
    def test_otlp_headers_from_env(self, mock_ssl_channel, mock_secure):
        exporter = OTLPMetricsExporter()
        # pylint: disable=protected-access
        self.assertEqual(
            exporter._headers, (("key1", "value1"), ("key2", "value2")),
        )
        exporter = OTLPMetricsExporter(
            headers=(("key3", "value3"), ("key4", "value4"))
        )
        # pylint: disable=protected-access
        self.assertEqual(
            exporter._headers, (("key3", "value3"), ("key4", "value4")),
        )

    @patch(
        "opentelemetry.exporter.otlp.proto.grpc.exporter.ssl_channel_credentials"
    )
    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.secure_channel")
    # pylint: disable=unused-argument
    def test_otlp_headers(self, mock_ssl_channel, mock_secure):
        exporter = OTLPMetricsExporter()
        # pylint: disable=protected-access
        self.assertIsNone(exporter._headers, None)

    @patch("opentelemetry.sdk.metrics.export.aggregate._time_ns")
    def test_translate_counter_export_record(self, mock_time_ns):
        mock_time_ns.configure_mock(**{"return_value": 1})

        counter_export_record = ExportRecord(
            Counter("c", "d", "e", int, self.meter, ("f",),),
            [("g", "h")],
            SumAggregator(),
            self.resource,
        )

        counter_export_record.aggregator.checkpoint = 1
        counter_export_record.aggregator.initial_checkpoint_timestamp = 1
        counter_export_record.aggregator.last_update_timestamp = 1

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
                            instrumentation_library=InstrumentationLibrary(
                                name="name", version="version",
                            ),
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
                                            AggregationTemporality.AGGREGATION_TEMPORALITY_CUMULATIVE
                                        ),
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
        actual = self.exporter._translate_data([counter_export_record])

        self.assertEqual(expected, actual)

    @patch("opentelemetry.sdk.metrics.export.aggregate._time_ns")
    def test_translate_sum_observer_export_record(self, mock_time_ns):
        mock_time_ns.configure_mock(**{"return_value": 1})
        counter_export_record = ExportRecord(
            SumObserver(Mock(), "c", "d", "e", int, self.meter, ("f",),),
            [("g", "h")],
            SumAggregator(),
            self.resource,
        )

        counter_export_record.aggregator.checkpoint = 1
        counter_export_record.aggregator.initial_checkpoint_timestamp = 1
        counter_export_record.aggregator.last_update_timestamp = 1

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
                            instrumentation_library=InstrumentationLibrary(
                                name="name", version="version",
                            ),
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
                                            AggregationTemporality.AGGREGATION_TEMPORALITY_CUMULATIVE
                                        ),
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
        actual = self.exporter._translate_data([counter_export_record])

        self.assertEqual(expected, actual)

    @patch("opentelemetry.sdk.metrics.export.aggregate._time_ns")
    def test_translate_updowncounter_export_record(self, mock_time_ns):
        mock_time_ns.configure_mock(**{"return_value": 1})

        counter_export_record = ExportRecord(
            UpDownCounter("c", "d", "e", int, self.meter),
            [("g", "h")],
            SumAggregator(),
            self.resource,
        )

        counter_export_record.aggregator.checkpoint = 1
        counter_export_record.aggregator.initial_checkpoint_timestamp = 1
        counter_export_record.aggregator.last_update_timestamp = 1

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
                            instrumentation_library=InstrumentationLibrary(
                                name="name", version="version",
                            ),
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
                                            AggregationTemporality.AGGREGATION_TEMPORALITY_CUMULATIVE
                                        ),
                                    ),
                                )
                            ],
                        )
                    ],
                )
            ]
        )

        # pylint: disable=protected-access
        actual = self.exporter._translate_data([counter_export_record])

        self.assertEqual(expected, actual)

    @patch("opentelemetry.sdk.metrics.export.aggregate._time_ns")
    def test_translate_updownsum_observer_export_record(self, mock_time_ns):
        mock_time_ns.configure_mock(**{"return_value": 1})
        counter_export_record = ExportRecord(
            UpDownSumObserver(Mock(), "c", "d", "e", int, self.meter, ("f",),),
            [("g", "h")],
            SumAggregator(),
            self.resource,
        )

        counter_export_record.aggregator.checkpoint = 1
        counter_export_record.aggregator.initial_checkpoint_timestamp = 1
        counter_export_record.aggregator.last_update_timestamp = 1

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
                            instrumentation_library=InstrumentationLibrary(
                                name="name", version="version",
                            ),
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
                                            AggregationTemporality.AGGREGATION_TEMPORALITY_CUMULATIVE
                                        ),
                                    ),
                                )
                            ],
                        )
                    ],
                )
            ]
        )

        # pylint: disable=protected-access
        actual = self.exporter._translate_data([counter_export_record])

        self.assertEqual(expected, actual)
