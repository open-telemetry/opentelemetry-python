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
from unittest import mock

import grpc
from google.protobuf.timestamp_pb2 import Timestamp
from opencensus.proto.metrics.v1 import metrics_pb2

from opentelemetry import metrics
from opentelemetry.ext.opencensus import metrics_exporter
from opentelemetry.sdk.metrics import (
    Counter,
    Measure,
    MeterProvider,
    get_labels_as_key,
)
from opentelemetry.sdk.metrics.export import (
    MetricRecord,
    MetricsExportResult,
    aggregate,
)


# pylint: disable=no-member
class TestCollectorMetricsExporter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # pylint: disable=protected-access
        metrics.set_meter_provider(MeterProvider())
        cls._meter = metrics.get_meter(__name__)
        cls._labels = {"environment": "staging"}
        cls._key_labels = get_labels_as_key(cls._labels)

    def test_constructor(self):
        mock_get_node = mock.Mock()
        patch = mock.patch(
            "opentelemetry.ext.opencensus.util.get_node",
            side_effect=mock_get_node,
        )
        service_name = "testServiceName"
        host_name = "testHostName"
        client = grpc.insecure_channel("")
        endpoint = "testEndpoint"
        with patch:
            exporter = metrics_exporter.OpenCensusCollectorMetricsExporter(
                service_name=service_name,
                host_name=host_name,
                endpoint=endpoint,
                client=client,
            )

        self.assertIs(exporter.client, client)
        self.assertEqual(exporter.endpoint, endpoint)
        mock_get_node.assert_called_with(service_name, host_name)

    def test_get_collector_metric_type(self):
        result = metrics_exporter.get_collector_metric_type(
            Counter("testName", "testDescription", "unit", int, None)
        )
        self.assertIs(result, metrics_pb2.MetricDescriptor.CUMULATIVE_INT64)
        result = metrics_exporter.get_collector_metric_type(
            Counter("testName", "testDescription", "unit", float, None)
        )
        self.assertIs(result, metrics_pb2.MetricDescriptor.CUMULATIVE_DOUBLE)
        result = metrics_exporter.get_collector_metric_type(
            Measure("testName", "testDescription", "unit", None, None)
        )
        self.assertIs(result, metrics_pb2.MetricDescriptor.UNSPECIFIED)

    def test_get_collector_point(self):
        aggregator = aggregate.CounterAggregator()
        int_counter = self._meter.create_metric(
            "testName", "testDescription", "unit", int, Counter
        )
        float_counter = self._meter.create_metric(
            "testName", "testDescription", "unit", float, Counter
        )
        measure = self._meter.create_metric(
            "testName", "testDescription", "unit", float, Measure
        )
        result = metrics_exporter.get_collector_point(
            MetricRecord(aggregator, self._key_labels, int_counter)
        )
        self.assertIsInstance(result, metrics_pb2.Point)
        self.assertIsInstance(result.timestamp, Timestamp)
        self.assertEqual(result.int64_value, 0)
        aggregator.update(123.5)
        aggregator.take_checkpoint()
        result = metrics_exporter.get_collector_point(
            MetricRecord(aggregator, self._key_labels, float_counter)
        )
        self.assertEqual(result.double_value, 123.5)
        self.assertRaises(
            TypeError,
            metrics_exporter.get_collector_point(
                MetricRecord(aggregator, self._key_labels, measure)
            ),
        )

    def test_export(self):
        mock_client = mock.MagicMock()
        mock_export = mock.MagicMock()
        mock_client.Export = mock_export
        host_name = "testHostName"
        collector_exporter = metrics_exporter.OpenCensusCollectorMetricsExporter(
            client=mock_client, host_name=host_name
        )
        test_metric = self._meter.create_metric(
            "testname", "testdesc", "unit", int, Counter, ["environment"]
        )
        record = MetricRecord(
            aggregate.CounterAggregator(), self._key_labels, test_metric
        )

        result = collector_exporter.export([record])
        self.assertIs(result, MetricsExportResult.SUCCESS)
        # pylint: disable=unsubscriptable-object
        export_arg = mock_export.call_args[0]
        service_request = next(export_arg[0])
        output_metrics = getattr(service_request, "metrics")
        output_node = getattr(service_request, "node")
        self.assertEqual(len(output_metrics), 1)
        self.assertIsNotNone(getattr(output_node, "library_info"))
        self.assertIsNotNone(getattr(output_node, "service_info"))
        output_identifier = getattr(output_node, "identifier")
        self.assertEqual(
            getattr(output_identifier, "host_name"), "testHostName"
        )

    def test_translate_to_collector(self):
        test_metric = self._meter.create_metric(
            "testname", "testdesc", "unit", int, Counter, ["environment"]
        )
        aggregator = aggregate.CounterAggregator()
        aggregator.update(123)
        aggregator.take_checkpoint()
        record = MetricRecord(aggregator, self._key_labels, test_metric)
        output_metrics = metrics_exporter.translate_to_collector([record])
        self.assertEqual(len(output_metrics), 1)
        self.assertIsInstance(output_metrics[0], metrics_pb2.Metric)
        self.assertEqual(output_metrics[0].metric_descriptor.name, "testname")
        self.assertEqual(
            output_metrics[0].metric_descriptor.description, "testdesc"
        )
        self.assertEqual(output_metrics[0].metric_descriptor.unit, "unit")
        self.assertEqual(
            output_metrics[0].metric_descriptor.type,
            metrics_pb2.MetricDescriptor.CUMULATIVE_INT64,
        )
        self.assertEqual(
            len(output_metrics[0].metric_descriptor.label_keys), 1
        )
        self.assertEqual(
            output_metrics[0].metric_descriptor.label_keys[0].key,
            "environment",
        )
        self.assertEqual(len(output_metrics[0].timeseries), 1)
        self.assertEqual(len(output_metrics[0].timeseries[0].label_values), 1)
        self.assertEqual(
            output_metrics[0].timeseries[0].label_values[0].has_value, True
        )
        self.assertEqual(
            output_metrics[0].timeseries[0].label_values[0].value, "staging"
        )
        self.assertEqual(len(output_metrics[0].timeseries[0].points), 1)
        self.assertEqual(
            output_metrics[0].timeseries[0].points[0].timestamp.seconds,
            record.aggregator.last_update_timestamp // 1000000000,
        )
        self.assertEqual(
            output_metrics[0].timeseries[0].points[0].timestamp.nanos,
            record.aggregator.last_update_timestamp % 1000000000,
        )
        self.assertEqual(
            output_metrics[0].timeseries[0].points[0].int64_value, 123
        )
